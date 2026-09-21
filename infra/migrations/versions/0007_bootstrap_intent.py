"""Pin D031 acquisition intent and persist typed, fenced bootstrap readiness."""

from importlib import import_module

from alembic import op

revision = "0007_bootstrap_intent"
down_revision = "0006_source_bootstrap"
branch_labels = None
depends_on = None

SQL = r"""
CREATE FUNCTION workflow_valid_bootstrap_plan(p JSONB) RETURNS BOOLEAN
LANGUAGE plpgsql IMMUTABLE SET search_path=public,pg_temp AS $$
DECLARE k TEXT; c TEXT; n INTEGER; f INTEGER:=0; h INTEGER:=0; first_day DATE; last_day DATE;
BEGIN
 IF p IS NULL OR jsonb_typeof(p)<>'object'
 OR NOT p ?& ARRAY['version','issuer_id','cik','source_id','policy_revision_id','inventory_start','inventory_end','resources']
 OR p-'version'-'issuer_id'-'cik'-'source_id'-'policy_revision_id'-'inventory_start'-'inventory_end'-'resources'<>'{}'::jsonb
 OR p->>'version' IS DISTINCT FROM 'sec-identity-bootstrap-v1'
 OR jsonb_typeof(p->'resources') IS DISTINCT FROM 'array' THEN RETURN FALSE; END IF;
 c:=p->>'cik';
 IF c IS NULL OR c !~ '^[0-9]{10}$' OR c='0000000000' THEN RETURN FALSE; END IF;
 FOREACH k IN ARRAY ARRAY['issuer_id','source_id','policy_revision_id'] LOOP
  IF p->>k IS NULL OR p->>k !~ '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
  THEN RETURN FALSE; END IF;
 END LOOP;
 IF coalesce(p->>'inventory_start','') !~ '^\d{4}-\d{2}-\d{2}$'
 OR coalesce(p->>'inventory_end','') !~ '^\d{4}-\d{2}-\d{2}$' THEN RETURN FALSE; END IF;
 first_day:=(p->>'inventory_start')::DATE; last_day:=(p->>'inventory_end')::DATE;
 IF last_day-first_day NOT BETWEEN 0 AND 730 THEN RETURN FALSE; END IF;
 n:=jsonb_array_length(p->'resources');
 IF n NOT BETWEEN 2 AND 17 OR NOT (p->'resources') ?& ARRAY['company_facts/'||c,'submissions/'||c]
 OR (SELECT count(DISTINCT value) FROM jsonb_array_elements(p->'resources'))<>n
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(p->'resources') WHERE jsonb_typeof(value)<>'string')
 THEN RETURN FALSE; END IF;
 FOR k IN SELECT jsonb_array_elements_text(p->'resources') LOOP
  IF k IN ('company_facts/'||c,'submissions/'||c) THEN CONTINUE;
  ELSIF k ~ ('^filing_document/'||c||'/[0-9]{10}-[0-9]{2}-[0-9]{6}/[A-Za-z0-9][A-Za-z0-9_.-]*\.(htm|html|xml|txt|xsd)$')
   AND position('..' IN k)=0 THEN f:=f+1;
  ELSIF k ~ ('^submissions_history/'||c||'/CIK'||c||'-submissions-[0-9]{3}\.json$') THEN h:=h+1;
  ELSE RETURN FALSE; END IF;
 END LOOP;
 RETURN f<=5 AND h<=10;
EXCEPTION WHEN invalid_text_representation OR datetime_field_overflow THEN RETURN FALSE;
END $$;
ALTER TABLE analysis_requests ADD COLUMN bootstrap_plan JSONB;
ALTER TABLE analysis_requests ADD CONSTRAINT workflow_bootstrap_plan_shape CHECK(
 bootstrap_plan IS NULL OR (trigger='source_bootstrap' AND
 workflow_valid_bootstrap_plan(bootstrap_plan)));

CREATE FUNCTION workflow_bootstrap_intent_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
 IF NEW.trigger='source_bootstrap' THEN
  IF NOT workflow_valid_bootstrap_plan(NEW.bootstrap_plan)
   OR NEW.history_mode<>'latest_reported' OR NEW.requested_periods<>'[]'::jsonb
   OR NEW.filed_cutoff IS NOT NULL OR NEW.retrieval_vintage IS NOT NULL
   OR NEW.retrieval_policy<>'refresh' OR NEW.max_attempts NOT BETWEEN 1 AND 3 THEN
   RAISE EXCEPTION 'bootstrap requires a bounded acquisition plan only' USING ERRCODE='23514'; END
 IF;
  IF NOT EXISTS(SELECT 1 FROM securities s JOIN issuers i ON i.id=s.issuer_id
    JOIN source_policy_revisions p ON p.id=(NEW.bootstrap_plan->>'policy_revision_id')::UUID
    JOIN sources src ON src.id=p.source_id
    WHERE s.id=NEW.security_id AND i.id=(NEW.bootstrap_plan->>'issuer_id')::UUID
     AND i.cik=NEW.bootstrap_plan->>'cik' AND src.id=(NEW.bootstrap_plan->>'source_id')::UUID
     AND src.base_url='https://data.sec.gov') THEN
   RAISE EXCEPTION 'bootstrap plan differs from registered issuer or reviewed SEC policy' USING
 ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER workflow_bootstrap_intent BEFORE INSERT ON analysis_requests
 FOR EACH ROW EXECUTE FUNCTION workflow_bootstrap_intent_guard();

CREATE OR REPLACE FUNCTION workflow_enqueue_bootstrap(p_workspace UUID,p_security UUID,p_key
 TEXT,p_options JSONB)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE plan JSONB; params_hash TEXT; attempts INTEGER;
 existing analysis_request_keys%ROWTYPE; request UUID; execution UUID;
BEGIN
 IF p_key IS NULL OR length(p_key) NOT BETWEEN 1 AND 200 OR p_options IS NULL
 OR jsonb_typeof(p_options)<>'object' OR p_options-'plan'-'max_attempts'<>'{}'::jsonb
 OR NOT workflow_valid_bootstrap_plan(p_options->'plan')
 OR jsonb_typeof(p_options->'max_attempts') IS DISTINCT FROM 'number'
 OR p_options->>'max_attempts' !~ '^[1-3]$' THEN
  RAISE EXCEPTION 'unknown bootstrap option or invalid acquisition plan' USING ERRCODE='22023';
 END IF;
 plan:=p_options->'plan'; attempts:=(p_options->>'max_attempts')::INTEGER;
 -- Canonical resource order makes identical sets the same immutable intent.
 plan:=jsonb_set(plan,'{resources}',(SELECT jsonb_agg(value ORDER BY (value#>>'{}') COLLATE "C") FROM
 jsonb_array_elements(plan->'resources')));
 PERFORM 1 FROM workspaces WHERE id=p_workspace FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'unknown workspace' USING ERRCODE='23503'; END IF;
 params_hash:=encode(sha256(convert_to(jsonb_build_object('workspace',p_workspace,'security',p_security,
  'trigger','source_bootstrap','plan',plan,'max_attempts',attempts)::TEXT,'UTF8')),'hex');
 SELECT * INTO existing FROM analysis_request_keys WHERE workspace_id=p_workspace AND
 idempotency_key=p_key;
 IF FOUND THEN
  IF existing.parameters_hash<>params_hash THEN RAISE EXCEPTION
 'idempotency key reused with different parameters' USING ERRCODE='22023'; END IF;
  RETURN workflow_request_result(existing.request_id);
 END IF;
 request:=gen_random_uuid(); execution:=gen_random_uuid();
 INSERT INTO analysis_requests(id,workspace_id,security_id,quote_identifier_id,trigger,
  idempotency_key,history_mode,requested_periods,retrieval_policy,max_attempts,request_parameters_hash,bootstrap_plan)
 VALUES(request,p_workspace,p_security,NULL,'source_bootstrap',p_key,'latest_reported','[]','refresh',attempts,params_hash,plan);
 INSERT INTO analysis_request_keys(workspace_id,idempotency_key,request_id,parameters_hash)
 VALUES(p_workspace,p_key,request,params_hash);
 INSERT INTO analysis_executions(id,request_id,attempt_no,state)
 VALUES(execution,request,1,'queued');
 INSERT INTO analysis_request_state(request_id,current_execution_id,attempt_epoch)
 VALUES(request,execution,1);
 PERFORM workflow_event(execution,'queued',jsonb_build_object('trigger','source_bootstrap','plan_version',plan->>'version'));
 RETURN workflow_request_result(request);
END $$;

CREATE OR REPLACE FUNCTION workflow_bootstrap_attempt_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE kind TEXT; cik TEXT; plan JSONB;
BEGIN
 SELECT r.trigger,i.cik,r.bootstrap_plan INTO kind,cik,plan FROM analysis_stage_attempts st
 JOIN analysis_executions e ON e.id=st.execution_id JOIN analysis_requests r ON r.id=e.request_id
 JOIN securities s ON s.id=r.security_id JOIN issuers i ON i.id=s.issuer_id WHERE
 st.id=NEW.stage_attempt_id;
 IF kind='source_bootstrap' AND (plan IS NULL
 OR split_part(NEW.source_object_key,'/',2) IS DISTINCT FROM cik
 OR NEW.source_id IS DISTINCT FROM (plan->>'source_id')::UUID
 OR NEW.policy_revision_id IS DISTINCT FROM (plan->>'policy_revision_id')::UUID
 OR NOT (plan->'resources') ? NEW.source_object_key
 OR NOT market_sec_resource(NEW.source_id,NEW.policy_revision_id,NEW.request_url,NEW.source_object_key)) THEN
  RAISE EXCEPTION 'bootstrap resource outside pinned plan for registered issuer' USING
 ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;

CREATE FUNCTION workflow_complete_bootstrap_stage(p_lease JSONB,p_stage UUID,p_result JSONB)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE execution analysis_executions%ROWTYPE; plan JSONB; ready JSONB; capture UUID;
BEGIN
 execution:=workflow_locked_lease(p_lease);
 SELECT bootstrap_plan INTO plan FROM analysis_requests WHERE id=execution.request_id AND
 trigger='source_bootstrap';
 ready:=p_result->'readiness';
 IF plan IS NULL OR p_result IS NULL OR jsonb_typeof(p_result)<>'object'
 OR p_result-'version'-'manifest'-'readiness'<>'{}'::jsonb
 OR p_result->>'version' IS DISTINCT FROM 'sec-bootstrap-result-v1'
 OR (p_result->'manifest')-'blob_key'-'body_sha256'-'byte_count'<>'{}'::jsonb
 OR position('..' IN coalesce(p_result->'manifest'->>'blob_key',''))>0
 OR coalesce(p_result->'manifest'->>'body_sha256','') !~ '^[a-f0-9]{64}$'
 OR coalesce(p_result->'manifest'->>'blob_key','') NOT LIKE 'bootstrap/%'
 OR coalesce(p_result->'manifest'->>'byte_count','') !~ '^[1-9][0-9]*$'
 OR jsonb_typeof(ready) IS DISTINCT FROM 'object'
 OR ready-'identity_capture_id'-'identity_status'-'registration_review_ready'-'blocking_reasons'<>'{}'::jsonb
 OR NOT ready ?&
 ARRAY['identity_capture_id','identity_status','registration_review_ready','blocking_reasons']
 OR jsonb_typeof(ready->'registration_review_ready') IS DISTINCT FROM 'boolean'
 OR jsonb_typeof(ready->'blocking_reasons') IS DISTINCT FROM 'array'
 OR ready->>'identity_status' IS NULL
 OR ready->>'identity_status' NOT IN ('captured','unavailable') THEN
  RAISE EXCEPTION 'invalid typed bootstrap result' USING ERRCODE='22023'; END IF;
 IF EXISTS(SELECT 1 FROM jsonb_array_elements(ready->'blocking_reasons') x
  WHERE jsonb_typeof(x)<>'string' OR length(trim(x#>>'{}'))=0) THEN
  RAISE EXCEPTION 'invalid bootstrap blocking reasons' USING ERRCODE='22023'; END IF;
 capture:=(ready->>'identity_capture_id')::UUID;
 IF (capture IS NOT NULL) IS DISTINCT FROM (ready->>'identity_status'='captured')
 OR (ready->>'registration_review_ready')::BOOLEAN IS DISTINCT FROM
  (capture IS NOT NULL AND jsonb_array_length(ready->'blocking_reasons')=0)
 OR (capture IS NULL AND jsonb_array_length(ready->'blocking_reasons')=0) THEN
  RAISE EXCEPTION 'inconsistent bootstrap readiness' USING ERRCODE='22023'; END IF;
 IF capture IS NOT NULL AND NOT EXISTS(
  SELECT 1 FROM source_captures c JOIN capture_policy_links l ON l.capture_id=c.id
  WHERE c.id=capture AND c.source_id=(plan->>'source_id')::UUID
   AND l.policy_revision_id=(plan->>'policy_revision_id')::UUID
   AND c.source_object_key='submissions/'||(plan->>'cik') AND c.http_status BETWEEN 200 AND 299
   AND EXISTS(SELECT 1 FROM analysis_stage_attempts st WHERE st.execution_id=execution.id AND
     (EXISTS(SELECT 1 FROM source_fetch_attempts a WHERE a.stage_attempt_id=st.id AND
 a.completed_capture_id=c.id AND a.state='complete')
      OR (st.input_manifest->'reused_capture_ids') ? c.id::TEXT))) THEN
  RAISE EXCEPTION 'identity capture must be this execution verified SEC Submissions' USING
 ERRCODE='23514'; END IF;
 UPDATE analysis_stage_attempts SET state='completed',finished_at=clock_timestamp(),
  error_code=NULL,error_detail=NULL,result_reference=p_result::TEXT,
  input_manifest=jsonb_build_object('bootstrap_plan',plan)
 WHERE id=p_stage AND execution_id=execution.id AND stage_key='sec_bootstrap_manifest' AND
 state='running';
 IF NOT FOUND THEN RAISE EXCEPTION 'bootstrap stage is not active' USING ERRCODE='55000'; END IF;
 UPDATE analysis_executions SET current_stage=(SELECT stage_key FROM analysis_stage_attempts
  WHERE execution_id=execution.id AND state='running' ORDER BY started_at LIMIT 1) WHERE
 id=execution.id;
 PERFORM workflow_event(execution.id,'stage_finished',jsonb_build_object('stage_id',p_stage,'outcome','completed','result',p_result));
 RETURN TRUE;
END $$;
CREATE FUNCTION workflow_bootstrap_success_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE pinned BOOLEAN;
BEGIN
 IF TG_TABLE_NAME='analysis_executions' THEN
  SELECT bootstrap_plan IS NOT NULL INTO pinned FROM analysis_requests WHERE id=NEW.request_id;
 ELSE
  SELECT r.bootstrap_plan IS NOT NULL INTO pinned FROM analysis_requests r
   JOIN analysis_executions e ON e.request_id=r.id WHERE e.id=NEW.execution_id;
 END IF;
 IF pinned AND NEW.state IN ('completed','completed_with_gaps') THEN
  IF NEW.error_code IS NOT NULL OR NEW.error_detail IS NOT NULL THEN
   RAISE EXCEPTION 'successful bootstrap cannot carry error fields' USING ERRCODE='23514'; END IF;
  IF TG_TABLE_NAME='analysis_stage_attempts' THEN
   IF NEW.stage_key='sec_bootstrap_manifest' AND NEW.result_reference IS NULL THEN
    RAISE EXCEPTION 'bootstrap manifest requires typed result reference' USING ERRCODE='23514'; END IF;
  END IF;
  IF TG_TABLE_NAME='analysis_executions' AND NOT EXISTS(
   SELECT 1 FROM analysis_stage_attempts st WHERE st.execution_id=NEW.id
    AND st.stage_key='sec_bootstrap_manifest' AND st.state='completed'
    AND st.result_reference IS NOT NULL) THEN
   RAISE EXCEPTION 'bootstrap success requires a typed acquisition result' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER workflow_bootstrap_success BEFORE UPDATE ON analysis_executions
 FOR EACH ROW EXECUTE FUNCTION workflow_bootstrap_success_guard();
CREATE TRIGGER workflow_bootstrap_stage_success BEFORE UPDATE ON analysis_stage_attempts
 FOR EACH ROW EXECUTE FUNCTION workflow_bootstrap_success_guard();
REVOKE ALL ON FUNCTION workflow_bootstrap_success_guard() FROM PUBLIC,equity_runtime;

REVOKE ALL ON FUNCTION workflow_valid_bootstrap_plan(JSONB),workflow_bootstrap_intent_guard(),
 workflow_complete_bootstrap_stage(JSONB,UUID,JSONB) FROM PUBLIC,equity_runtime;
GRANT EXECUTE ON FUNCTION workflow_complete_bootstrap_stage(JSONB,UUID,JSONB) TO equity_runtime;
"""


def upgrade() -> None:
    op.execute(SQL)


def downgrade() -> None:
    op.execute("""
    DO $$ BEGIN IF EXISTS(SELECT 1 FROM analysis_requests WHERE bootstrap_plan IS NOT NULL) THEN
      RAISE EXCEPTION 'refusing to discard pinned bootstrap intent' USING ERRCODE='55000';
    END IF; END $$;
    DROP TRIGGER workflow_bootstrap_success ON analysis_executions;
    DROP TRIGGER workflow_bootstrap_stage_success ON analysis_stage_attempts;
    DROP FUNCTION workflow_bootstrap_success_guard();
    DROP FUNCTION workflow_complete_bootstrap_stage(JSONB,UUID,JSONB);
    DROP TRIGGER workflow_bootstrap_intent ON analysis_requests;
    DROP FUNCTION workflow_bootstrap_intent_guard();
    ALTER TABLE analysis_requests DROP CONSTRAINT workflow_bootstrap_plan_shape;
    ALTER TABLE analysis_requests DROP COLUMN bootstrap_plan;
    DROP FUNCTION workflow_valid_bootstrap_plan(JSONB);
    """)
    # Restore exactly the frozen 0006 definitions; never reinterpret legacy requests.
    frozen = import_module("infra.migrations.versions.0006_source_bootstrap").SQL
    for name, end in (
        ("workflow_enqueue_bootstrap", "CREATE FUNCTION workflow_bootstrap_stage_guard"),
        ("workflow_bootstrap_attempt_guard", "CREATE TRIGGER workflow_bootstrap_attempt"),
    ):
        statement = frozen.split("CREATE FUNCTION " + name, 1)[1].split(end, 1)[0]
        op.execute("CREATE OR REPLACE FUNCTION " + name + statement)
