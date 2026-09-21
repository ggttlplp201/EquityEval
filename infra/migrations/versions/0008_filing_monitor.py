"""D035 pinned SEC discovery, reviewed baseline lineage and per-attempt 200 bodies."""

from importlib import import_module

from alembic import op

revision = "0008_filing_monitor"
down_revision = "0007_bootstrap_intent"
branch_labels = None
depends_on = None

SQL = r"""
CREATE TABLE filing_monitor_seed_approvals (
 id UUID PRIMARY KEY, security_id UUID NOT NULL REFERENCES securities(id),
 request_id UUID NOT NULL REFERENCES analysis_requests(id),
 execution_id UUID NOT NULL REFERENCES analysis_executions(id),
 request_parameters_hash TEXT NOT NULL CHECK(request_parameters_hash ~ '^[a-f0-9]{64}$'),
 manifest_sha256 TEXT NOT NULL CHECK(manifest_sha256 ~ '^[a-f0-9]{64}$'),
 capture_id UUID NOT NULL REFERENCES source_captures(id),
 cutoff TIMESTAMPTZ NOT NULL CHECK(isfinite(cutoff)), scope JSONB NOT NULL,
 review_reference TEXT NOT NULL CHECK(btrim(review_reference)<>''),
 review_sha256 TEXT NOT NULL CHECK(review_sha256 ~ '^[a-f0-9]{64}$'),
 reviewed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(request_id,execution_id,cutoff)
);
CREATE TRIGGER filing_monitor_seed_immutable BEFORE UPDATE OR DELETE ON filing_monitor_seed_approvals
 FOR EACH ROW EXECUTE FUNCTION evidence_immutable();
CREATE TRIGGER filing_monitor_seed_no_truncate BEFORE TRUNCATE ON filing_monitor_seed_approvals
 FOR EACH STATEMENT EXECUTE FUNCTION evidence_immutable();
CREATE TABLE source_attempt_payloads (
 attempt_id UUID PRIMARY KEY REFERENCES source_fetch_attempts(id),
 fetched_at TIMESTAMPTZ NOT NULL CHECK(isfinite(fetched_at)),
 body_sha256 TEXT NOT NULL CHECK(body_sha256 ~ '^[a-f0-9]{64}$'),
 byte_count BIGINT NOT NULL CHECK(byte_count>=0),
 blob_key TEXT NOT NULL CHECK(btrim(blob_key)<>'')
);
CREATE TRIGGER source_attempt_payloads_immutable BEFORE UPDATE OR DELETE ON source_attempt_payloads
 FOR EACH ROW EXECUTE FUNCTION evidence_immutable();
CREATE TRIGGER source_attempt_payloads_no_truncate BEFORE TRUNCATE ON source_attempt_payloads
 FOR EACH STATEMENT EXECUTE FUNCTION evidence_immutable();
ALTER TABLE analysis_requests ADD COLUMN filing_monitor_plan JSONB;
ALTER TABLE analysis_requests DROP CONSTRAINT analysis_requests_trigger_check;
ALTER TABLE analysis_requests ADD CONSTRAINT analysis_requests_trigger_check
 CHECK(trigger IN ('watchlist_add','manual_refresh','source_bootstrap','sec_filing_monitor'));
ALTER TABLE analysis_requests DROP CONSTRAINT workflow_bootstrap_shape;
ALTER TABLE analysis_requests ADD CONSTRAINT workflow_bootstrap_shape CHECK(
 (trigger NOT IN ('source_bootstrap','sec_filing_monitor') AND quote_identifier_id IS NOT NULL) OR
 (trigger IN ('source_bootstrap','sec_filing_monitor') AND quote_identifier_id IS NULL AND membership_id IS NULL
  AND parent_request_id IS NULL AND market_plan_revision IS NULL
  AND price_source_id IS NULL AND price_start IS NULL AND price_end IS NULL
  AND macro_source_id IS NULL AND macro_series_keys IS NULL AND macro_start IS NULL
  AND macro_end IS NULL AND macro_source_as_of_date IS NULL));

CREATE FUNCTION workflow_valid_monitor_plan(p JSONB) RETURNS BOOLEAN
LANGUAGE plpgsql IMMUTABLE SET search_path=public,pg_temp AS $$
DECLARE k TEXT; b JSONB; c TEXT; start_day DATE; end_day DATE; cutoff TIMESTAMPTZ;
BEGIN
 IF p IS NULL OR jsonb_typeof(p)<>'object'
 OR NOT p ?& ARRAY['version','issuer_id','cik','source_id','policy_revision_id','inventory_start','inventory_end','cutoff','forms','resources','baseline']
 OR p-ARRAY['version','issuer_id','cik','source_id','policy_revision_id','inventory_start','inventory_end','cutoff','forms','resources','baseline']<>'{}'::JSONB
 OR p->>'version' IS DISTINCT FROM 'sec-filing-monitor-v1' THEN RETURN FALSE; END IF;
 c:=p->>'cik';
 IF c IS NULL OR c !~ '^[0-9]{10}$' OR c='0000000000' THEN RETURN FALSE; END IF;
 FOREACH k IN ARRAY ARRAY['issuer_id','source_id','policy_revision_id'] LOOP
  IF coalesce(p->>k,'') !~ '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$' THEN RETURN FALSE; END IF;
 END LOOP;
 IF coalesce(p->>'inventory_start','') !~ '^\d{4}-\d{2}-\d{2}$'
 OR coalesce(p->>'inventory_end','') !~ '^\d{4}-\d{2}-\d{2}$'
 OR coalesce(p->>'cutoff','') !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$' THEN RETURN FALSE; END IF;
 start_day:=(p->>'inventory_start')::DATE; end_day:=(p->>'inventory_end')::DATE;
 cutoff:=(p->>'cutoff')::TIMESTAMPTZ;
 IF end_day-start_day NOT BETWEEN 0 AND 730 OR NOT isfinite(cutoff)
 OR (cutoff AT TIME ZONE 'UTC')::DATE NOT BETWEEN start_day AND end_day THEN RETURN FALSE; END IF;
 IF jsonb_typeof(p->'forms') IS DISTINCT FROM 'array' OR jsonb_typeof(p->'resources') IS DISTINCT FROM 'array' THEN RETURN FALSE; END IF;
 IF jsonb_array_length(p->'forms') NOT BETWEEN 1 AND 4
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(p->'forms') x WHERE jsonb_typeof(x)<>'string' OR x#>>'{}' NOT IN ('10-Q','10-K','10-Q/A','10-K/A'))
 OR (SELECT count(DISTINCT x) FROM jsonb_array_elements(p->'forms') x)<>jsonb_array_length(p->'forms') THEN RETURN FALSE; END IF;
 IF jsonb_array_length(p->'resources') NOT BETWEEN 1 AND 11 OR NOT (p->'resources') ? ('submissions/'||c)
 OR (SELECT count(DISTINCT x) FROM jsonb_array_elements(p->'resources') x)<>jsonb_array_length(p->'resources') THEN RETURN FALSE; END IF;
 FOR k IN SELECT jsonb_array_elements_text(p->'resources') LOOP
  IF k IS NULL OR (k<>'submissions/'||c AND k !~ ('^submissions_history/'||c||'/CIK'||c||'-submissions-[0-9]{3}\.json$')) THEN RETURN FALSE; END IF;
 END LOOP;
 b:=p->'baseline';
 IF jsonb_typeof(b) IS DISTINCT FROM 'object'
 OR NOT b ?& ARRAY['kind','request_id','execution_id','manifest_sha256','cutoff','version','seed_approval_id','plan_sha256','capture_id','manifest_id']
 OR b-ARRAY['kind','request_id','execution_id','manifest_sha256','cutoff','version','seed_approval_id','plan_sha256','capture_id','manifest_id']<>'{}'::JSONB
 OR b->>'version' IS DISTINCT FROM p->>'version'
 OR coalesce(b->>'manifest_sha256','') !~ '^[a-f0-9]{64}$'
 OR coalesce(b->>'cutoff','') !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$'
 OR (b->>'cutoff')::TIMESTAMPTZ>cutoff THEN RETURN FALSE; END IF;
 FOREACH k IN ARRAY ARRAY['request_id','execution_id'] LOOP
  IF coalesce(b->>k,'') !~ '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$' THEN RETURN FALSE; END IF;
 END LOOP;
 IF b->>'kind'='initial_seed' THEN
  IF b->>'manifest_id' IS NOT NULL OR coalesce(b->>'plan_sha256','') !~ '^[a-f0-9]{64}$' THEN RETURN FALSE; END IF;
  FOREACH k IN ARRAY ARRAY['seed_approval_id','capture_id'] LOOP
   IF coalesce(b->>k,'') !~ '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$' THEN RETURN FALSE; END IF;
  END LOOP;
 ELSIF b->>'kind'='prior_monitor_result' THEN
  IF b->>'seed_approval_id' IS NOT NULL OR b->>'plan_sha256' IS NOT NULL OR b->>'capture_id' IS NOT NULL
  OR coalesce(b->>'manifest_id','') !~ '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$' THEN RETURN FALSE; END IF;
 ELSE RETURN FALSE; END IF;
 RETURN TRUE;
EXCEPTION WHEN invalid_text_representation OR datetime_field_overflow THEN RETURN FALSE;
END $$;
ALTER TABLE analysis_requests ADD CONSTRAINT workflow_monitor_shape CHECK(
 (trigger='sec_filing_monitor' AND filing_monitor_plan IS NOT NULL AND bootstrap_plan IS NULL
  AND workflow_valid_monitor_plan(filing_monitor_plan)) OR
 (trigger<>'sec_filing_monitor' AND filing_monitor_plan IS NULL));

CREATE FUNCTION workflow_monitor_scope(p JSONB) RETURNS JSONB
LANGUAGE sql IMMUTABLE SET search_path=public,pg_temp AS $$
 SELECT p-ARRAY['cutoff','baseline','resources']
$$;
CREATE FUNCTION workflow_monitor_baseline(p JSONB,p_security UUID) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE b JSONB:=p->'baseline'; r analysis_requests%ROWTYPE; e analysis_executions%ROWTYPE;
 seed filing_monitor_seed_approvals%ROWTYPE; result JSONB; capture source_captures%ROWTYPE;
BEGIN
 IF NOT workflow_valid_monitor_plan(p) THEN RAISE EXCEPTION 'invalid monitor plan' USING ERRCODE='22023'; END IF;
 SELECT * INTO r FROM analysis_requests WHERE id=(b->>'request_id')::UUID;
 SELECT * INTO e FROM analysis_executions WHERE id=(b->>'execution_id')::UUID AND request_id=r.id;
 IF r.id IS NULL OR e.id IS NULL OR r.security_id<>p_security OR e.state<>'completed'
 OR NOT EXISTS(SELECT 1 FROM analysis_request_state WHERE request_id=r.id AND current_execution_id=e.id AND terminal_outcome='completed')
 THEN RAISE EXCEPTION 'baseline needs exact terminal complete predecessor' USING ERRCODE='23514'; END IF;
 IF b->>'kind'='initial_seed' THEN
  SELECT * INTO seed FROM filing_monitor_seed_approvals WHERE id=(b->>'seed_approval_id')::UUID;
  SELECT result_reference::JSONB INTO result FROM analysis_stage_attempts
   WHERE execution_id=e.id AND stage_key='sec_bootstrap_manifest' AND state='completed';
  SELECT * INTO capture FROM source_captures WHERE id=(b->>'capture_id')::UUID;
  IF seed.id IS NULL OR r.trigger<>'source_bootstrap' OR result IS NULL
  OR seed.security_id<>p_security OR seed.request_id<>r.id OR seed.execution_id<>e.id
  OR seed.request_parameters_hash<>r.request_parameters_hash OR seed.request_parameters_hash<>b->>'plan_sha256'
  OR seed.manifest_sha256<>b->>'manifest_sha256' OR seed.manifest_sha256 IS DISTINCT FROM result#>>'{manifest,body_sha256}'
  OR result->>'version' IS DISTINCT FROM 'sec-bootstrap-result-v1'
  OR result#>>'{readiness,registration_review_ready}' IS DISTINCT FROM 'true'
  OR seed.capture_id IS DISTINCT FROM capture.id OR capture.id::TEXT IS DISTINCT FROM result#>>'{readiness,identity_capture_id}'
  OR seed.cutoff IS DISTINCT FROM (b->>'cutoff')::TIMESTAMPTZ OR seed.cutoff>capture.requested_at
  OR seed.scope IS DISTINCT FROM workflow_monitor_scope(p)
  OR r.bootstrap_plan->>'issuer_id' IS DISTINCT FROM p->>'issuer_id'
  OR r.bootstrap_plan->>'source_id' IS DISTINCT FROM p->>'source_id'
  OR r.bootstrap_plan->>'policy_revision_id' IS DISTINCT FROM p->>'policy_revision_id'
  OR r.bootstrap_plan->>'cik' IS DISTINCT FROM p->>'cik'
  OR r.bootstrap_plan->>'inventory_start' IS DISTINCT FROM p->>'inventory_start'
  OR r.bootstrap_plan->>'inventory_end' IS DISTINCT FROM p->>'inventory_end'
  OR capture.source_object_key IS DISTINCT FROM 'submissions/'||(p->>'cik')
  OR capture.source_id IS DISTINCT FROM (p->>'source_id')::UUID
  OR NOT EXISTS(SELECT 1 FROM capture_policy_links WHERE capture_id=capture.id AND policy_revision_id=(p->>'policy_revision_id')::UUID)
  THEN RAISE EXCEPTION 'initial baseline differs from reviewed seed lineage' USING ERRCODE='23514'; END IF;
  RETURN jsonb_build_object('capture_ids',jsonb_build_array(capture.id),'cutoff',b->>'cutoff','lineage',b);
 END IF;
 SELECT result_reference::JSONB INTO result FROM analysis_stage_attempts
  WHERE execution_id=e.id AND stage_key='sec_monitor_result' AND state='completed';
 IF r.trigger<>'sec_filing_monitor' OR result IS NULL
 OR result->>'version' IS DISTINCT FROM 'sec-filing-monitor-result-v1'
 OR result->>'baseline_eligible' IS DISTINCT FROM 'true'
 OR result->>'outcome' NOT IN ('no_change','new_filing','amendment','mixed_changes')
 OR result->>'manifest_id' IS DISTINCT FROM b->>'manifest_id'
 OR result#>>'{manifest,body_sha256}' IS DISTINCT FROM b->>'manifest_sha256'
 OR r.filing_monitor_plan->>'cutoff' IS DISTINCT FROM b->>'cutoff'
 OR workflow_monitor_scope(r.filing_monitor_plan) IS DISTINCT FROM workflow_monitor_scope(p)
 THEN RAISE EXCEPTION 'prior baseline differs from complete result or comparison scope; review rebase' USING ERRCODE='23514'; END IF;
 RETURN jsonb_build_object('capture_ids',result->'current_capture_ids','cutoff',b->>'cutoff','lineage',b);
END $$;

CREATE FUNCTION workflow_monitor_intent_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
 IF NEW.trigger='sec_filing_monitor' THEN
  IF NOT workflow_valid_monitor_plan(NEW.filing_monitor_plan)
  OR NEW.history_mode<>'latest_reported' OR NEW.requested_periods<>'[]'::JSONB
  OR NEW.filed_cutoff IS NOT NULL OR NEW.retrieval_vintage IS NOT NULL OR NEW.retrieval_policy<>'refresh'
  OR NEW.max_attempts NOT BETWEEN 1 AND 3 OR (NEW.filing_monitor_plan->>'cutoff')::TIMESTAMPTZ>clock_timestamp()
  OR NOT EXISTS(SELECT 1 FROM securities s JOIN issuers i ON i.id=s.issuer_id
   JOIN source_policy_revisions p ON p.id=(NEW.filing_monitor_plan->>'policy_revision_id')::UUID
   JOIN sources src ON src.id=p.source_id
   WHERE s.id=NEW.security_id AND i.id=(NEW.filing_monitor_plan->>'issuer_id')::UUID
    AND i.cik=NEW.filing_monitor_plan->>'cik' AND src.id=(NEW.filing_monitor_plan->>'source_id')::UUID
    AND src.base_url='https://data.sec.gov')
  THEN RAISE EXCEPTION 'invalid monitor identity, cutoff or acquisition-only intent' USING ERRCODE='23514'; END IF;
  PERFORM workflow_monitor_baseline(NEW.filing_monitor_plan,NEW.security_id);
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER workflow_monitor_intent BEFORE INSERT ON analysis_requests
 FOR EACH ROW EXECUTE FUNCTION workflow_monitor_intent_guard();

CREATE FUNCTION workflow_enqueue_monitor(p_workspace UUID,p_security UUID,p_key TEXT,p_options JSONB)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE plan JSONB; params_hash TEXT; attempts INTEGER; existing analysis_request_keys%ROWTYPE;
 request UUID; execution UUID; k TEXT;
BEGIN
 IF p_key IS NULL OR length(p_key) NOT BETWEEN 1 AND 200 OR p_options IS NULL
 OR jsonb_typeof(p_options)<>'object' OR p_options-ARRAY['plan','max_attempts']<>'{}'::JSONB
 OR NOT workflow_valid_monitor_plan(p_options->'plan')
 OR jsonb_typeof(p_options->'max_attempts') IS DISTINCT FROM 'number' OR p_options->>'max_attempts' !~ '^[1-3]$'
 THEN RAISE EXCEPTION 'invalid pinned monitor request' USING ERRCODE='22023'; END IF;
 plan:=p_options->'plan'; attempts:=(p_options->>'max_attempts')::INTEGER;
 FOREACH k IN ARRAY ARRAY['forms','resources'] LOOP
  plan:=jsonb_set(plan,ARRAY[k],(SELECT jsonb_agg(x ORDER BY (x#>>'{}') COLLATE "C") FROM jsonb_array_elements(plan->k) x));
 END LOOP;
 PERFORM 1 FROM workspaces WHERE id=p_workspace FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'unknown workspace' USING ERRCODE='23503'; END IF;
 params_hash:=encode(sha256(convert_to(jsonb_build_object('workspace',p_workspace,'security',p_security,
 'trigger','sec_filing_monitor','plan',plan,'max_attempts',attempts)::TEXT,'UTF8')),'hex');
 SELECT * INTO existing FROM analysis_request_keys WHERE workspace_id=p_workspace AND idempotency_key=p_key;
 IF FOUND THEN
  IF existing.parameters_hash<>params_hash THEN RAISE EXCEPTION 'idempotency key reused with different parameters' USING ERRCODE='22023'; END IF;
  RETURN workflow_request_result(existing.request_id);
 END IF;
 request:=gen_random_uuid(); execution:=gen_random_uuid();
 INSERT INTO analysis_requests(id,workspace_id,security_id,quote_identifier_id,trigger,idempotency_key,
 history_mode,requested_periods,retrieval_policy,max_attempts,request_parameters_hash,filing_monitor_plan)
 VALUES(request,p_workspace,p_security,NULL,'sec_filing_monitor',p_key,'latest_reported','[]','refresh',attempts,params_hash,plan);
 INSERT INTO analysis_request_keys(workspace_id,idempotency_key,request_id,parameters_hash) VALUES(p_workspace,p_key,request,params_hash);
 INSERT INTO analysis_executions(id,request_id,attempt_no,state) VALUES(execution,request,1,'queued');
 INSERT INTO analysis_request_state(request_id,current_execution_id,attempt_epoch) VALUES(request,execution,1);
 PERFORM workflow_event(execution,'queued',jsonb_build_object('trigger','sec_filing_monitor','plan_version',plan->>'version'));
 RETURN workflow_request_result(request);
END $$;

CREATE FUNCTION workflow_monitor_stage_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM analysis_executions e JOIN analysis_requests r ON r.id=e.request_id
 WHERE e.id=NEW.execution_id AND r.trigger='sec_filing_monitor')
 AND NEW.stage_key<>'sec_monitor_result' AND NEW.stage_key !~ '^sec_fetch_[a-f0-9]{24}$'
 THEN RAISE EXCEPTION 'monitor permits only Submissions acquisition and comparison' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER workflow_monitor_stage BEFORE INSERT ON analysis_stage_attempts FOR EACH ROW EXECUTE FUNCTION workflow_monitor_stage_guard();
CREATE FUNCTION workflow_monitor_attempt_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE p JSONB;
BEGIN
 SELECT r.filing_monitor_plan INTO p FROM analysis_stage_attempts st JOIN analysis_executions e ON e.id=st.execution_id
 JOIN analysis_requests r ON r.id=e.request_id WHERE st.id=NEW.stage_attempt_id AND r.trigger='sec_filing_monitor';
 IF p IS NOT NULL AND (NEW.source_id IS DISTINCT FROM (p->>'source_id')::UUID
 OR NEW.policy_revision_id IS DISTINCT FROM (p->>'policy_revision_id')::UUID
 OR NOT (p->'resources') ? NEW.source_object_key
 OR NOT market_sec_resource(NEW.source_id,NEW.policy_revision_id,NEW.request_url,NEW.source_object_key))
 THEN RAISE EXCEPTION 'monitor fetch differs from immutable source/resource plan' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER workflow_monitor_attempt BEFORE INSERT ON source_fetch_attempts FOR EACH ROW EXECUTE FUNCTION workflow_monitor_attempt_guard();

ALTER TABLE source_fetch_attempts DROP CONSTRAINT source_fetch_attempts_state_check;
ALTER TABLE source_fetch_attempts ADD CONSTRAINT source_fetch_attempts_state_check CHECK(state IN
 ('prepared','in_progress','complete','not_modified','content_unchanged','redirected','http_error',
 'transport_error','body_limit','redirect_refused','archive_error','cancelled','interrupted_unknown'));
ALTER TABLE source_fetch_attempts DROP CONSTRAINT source_fetch_attempts_check12;
ALTER TABLE source_fetch_attempts ADD CONSTRAINT source_fetch_attempts_check12
 CHECK((state IN ('not_modified','content_unchanged'))=(reused_capture_id IS NOT NULL));
ALTER TABLE source_fetch_attempts ADD CONSTRAINT monitor_unchanged_shape
 CHECK(state<>'content_unchanged' OR (http_status=200 AND http_status IS NOT NULL AND reused_capture_id IS NOT NULL));

CREATE FUNCTION ingestion_monitor_payload(p_lease JSONB,p_attempt UUID,p_payload JSONB) RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE a source_fetch_attempts%ROWTYPE;
BEGIN
 a:=ingestion_locked_attempt(p_lease,p_attempt);
 IF a.state<>'in_progress' OR a.http_status IS DISTINCT FROM 200 OR a.headers_received_at IS NULL
 OR NOT EXISTS(SELECT 1 FROM analysis_stage_attempts st JOIN analysis_executions e ON e.id=st.execution_id
 JOIN analysis_requests r ON r.id=e.request_id WHERE st.id=a.stage_attempt_id AND r.trigger='sec_filing_monitor')
 OR p_payload IS NULL OR jsonb_typeof(p_payload)<>'object'
 OR NOT p_payload ?& ARRAY['fetched_at','body_sha256','byte_count','blob_key']
 OR p_payload-ARRAY['fetched_at','body_sha256','byte_count','blob_key']<>'{}'::JSONB
 OR (p_payload->>'fetched_at')::TIMESTAMPTZ<a.headers_received_at
 THEN RAISE EXCEPTION 'monitor payload requires exact dispatched 200 attempt and complete archived body' USING ERRCODE='23514'; END IF;
 INSERT INTO source_attempt_payloads(attempt_id,fetched_at,body_sha256,byte_count,blob_key)
 VALUES(a.id,(p_payload->>'fetched_at')::TIMESTAMPTZ,p_payload->>'body_sha256',(p_payload->>'byte_count')::BIGINT,p_payload->>'blob_key');
 RETURN TRUE;
END $$;
CREATE FUNCTION ingestion_monitor_payload_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE p source_attempt_payloads%ROWTYPE; c source_captures%ROWTYPE; monitor BOOLEAN;
BEGIN
 SELECT r.trigger='sec_filing_monitor' INTO monitor FROM analysis_stage_attempts st JOIN analysis_executions e ON e.id=st.execution_id
 JOIN analysis_requests r ON r.id=e.request_id WHERE st.id=NEW.stage_attempt_id;
 IF NEW.state='content_unchanged' AND NOT coalesce(monitor,FALSE) THEN
  RAISE EXCEPTION 'content reuse is monitor-only' USING ERRCODE='23514'; END IF;
 IF monitor AND NEW.http_status=200 AND NEW.state IN ('complete','content_unchanged') THEN
  SELECT * INTO p FROM source_attempt_payloads WHERE attempt_id=NEW.id;
  SELECT * INTO c FROM source_captures WHERE id=coalesce(NEW.completed_capture_id,NEW.reused_capture_id);
  IF p.attempt_id IS NULL OR c.id IS NULL OR p.fetched_at<NEW.headers_received_at OR p.fetched_at>NEW.finished_at
  OR p.body_sha256<>c.body_sha256 OR p.byte_count<>c.byte_count
  OR c.source_id<>NEW.source_id OR c.source_object_key<>NEW.source_object_key
  OR c.request_url<>NEW.request_url OR c.request_params_hash<>NEW.request_params_hash
  OR c.http_status NOT BETWEEN 200 AND 299
  OR NOT EXISTS(SELECT 1 FROM capture_policy_links WHERE capture_id=c.id AND policy_revision_id=NEW.policy_revision_id)
  OR (NEW.state='content_unchanged' AND (c.completed_at>NEW.prepared_at OR NOT EXISTS
   (SELECT 1 FROM source_fetch_attempts WHERE completed_capture_id=c.id AND state='complete')))
  OR (NEW.state='complete' AND (p.blob_key<>c.blob_key OR p.fetched_at<>c.fetched_at))
  THEN RAISE EXCEPTION 'monitor completion lacks exact archived attempt body and matching representation' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER source_attempt_payload_guard BEFORE UPDATE ON source_fetch_attempts FOR EACH ROW EXECUTE FUNCTION ingestion_monitor_payload_guard();
CREATE FUNCTION ingestion_monitor_unchanged(p_lease JSONB,p_attempt UUID,p_finished TIMESTAMPTZ,p_reused UUID) RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE a source_fetch_attempts%ROWTYPE;
BEGIN
 a:=ingestion_locked_attempt(p_lease,p_attempt);
 IF a.state<>'in_progress' OR a.http_status IS DISTINCT FROM 200 OR p_finished IS NULL THEN
  RAISE EXCEPTION 'unchanged body needs actual HTTP 200 attempt' USING ERRCODE='23514'; END IF;
 UPDATE source_fetch_attempts SET state='content_unchanged',finished_at=p_finished,reused_capture_id=p_reused WHERE id=a.id;
 RETURN TRUE;
END $$;

CREATE FUNCTION workflow_complete_monitor(p_lease JSONB,p_stage UUID,p_result JSONB) RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE e analysis_executions%ROWTYPE; p JSONB; b JSONB; c TEXT; expected TIMESTAMPTZ; n INTEGER; m INTEGER;
BEGIN
 e:=ingestion_locked_stage(p_lease,p_stage);
 SELECT filing_monitor_plan INTO p FROM analysis_requests WHERE id=e.request_id AND trigger='sec_filing_monitor';
 IF p IS NULL OR p_result IS NULL OR jsonb_typeof(p_result)<>'object'
 OR p_result->>'version' IS DISTINCT FROM 'sec-filing-monitor-result-v1'
 OR p_result->'plan' IS DISTINCT FROM p
 OR p_result->>'outcome' NOT IN ('no_change','new_filing','amendment','mixed_changes','incomplete','error')
 OR p_result->>'outcome' IS NULL
 OR p_result#>>'{downstream,dispatched}' IS DISTINCT FROM 'false'
 OR jsonb_typeof(p_result#>'{downstream,blockers}') IS DISTINCT FROM 'array'
 OR NOT (p_result#>'{downstream,blockers}') ? 'handoff_not_implemented'
 OR coalesce(p_result->>'manifest_id','') !~ '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
 OR coalesce(p_result#>>'{manifest,body_sha256}','') !~ '^[a-f0-9]{64}$'
 OR coalesce(p_result#>>'{manifest,byte_count}','') !~ '^[0-9]+$'
 OR btrim(coalesce(p_result#>>'{manifest,blob_key}',''))=''
 OR jsonb_typeof(p_result->'baseline_capture_ids') IS DISTINCT FROM 'array'
 OR jsonb_typeof(p_result->'current_capture_ids') IS DISTINCT FROM 'array'
 OR EXISTS(SELECT 1 FROM unnest(ARRAY['flags','new_filings','amendments','metadata_changes','missing_accessions','baseline_filings','current_filings']) k WHERE jsonb_typeof(p_result->'comparison'->k) IS DISTINCT FROM 'array')
 OR p_result#>>'{comparison,outcome}' IS DISTINCT FROM p_result->>'outcome'
 OR p_result#>>'{comparison,baseline_eligible}' IS DISTINCT FROM p_result->>'baseline_eligible'
 OR jsonb_typeof(p_result->'baseline_eligible') IS DISTINCT FROM 'boolean'
 OR jsonb_typeof(p_result#>'{comparison,baseline_eligible}') IS DISTINCT FROM 'boolean'
 OR p_result->>'baseline_eligible' IS DISTINCT FROM
  (CASE WHEN p_result->>'outcome' IN ('no_change','new_filing','amendment','mixed_changes') THEN 'true' ELSE 'false' END)
 THEN RAISE EXCEPTION 'invalid typed monitor result' USING ERRCODE='23514'; END IF;
 b:=workflow_monitor_baseline(p,(SELECT security_id FROM analysis_requests WHERE id=e.request_id));
 IF p_result->'baseline_capture_ids' IS DISTINCT FROM b->'capture_ids'
 THEN RAISE EXCEPTION 'result baseline differs from reviewed predecessor' USING ERRCODE='23514'; END IF;
 IF (SELECT count(DISTINCT x) FROM jsonb_array_elements(p_result->'current_capture_ids') x)<>jsonb_array_length(p_result->'current_capture_ids')
 OR (SELECT count(DISTINCT source_object_key) FROM source_captures WHERE id::TEXT IN
  (SELECT jsonb_array_elements_text(p_result->'current_capture_ids')))<>jsonb_array_length(p_result->'current_capture_ids')
 THEN RAISE EXCEPTION 'duplicate or ambiguous current capture' USING ERRCODE='23514'; END IF;
 FOR c IN SELECT jsonb_array_elements_text(p_result->'current_capture_ids') LOOP
  IF NOT EXISTS(SELECT 1 FROM source_captures sc JOIN capture_policy_links l ON l.capture_id=sc.id
   WHERE sc.id=c::UUID AND sc.source_id=(p->>'source_id')::UUID AND l.policy_revision_id=(p->>'policy_revision_id')::UUID
   AND sc.http_status=200 AND (p->'resources') ? sc.source_object_key
   AND EXISTS(SELECT 1 FROM source_fetch_attempts a JOIN analysis_stage_attempts st ON st.id=a.stage_attempt_id
    JOIN analysis_executions ex ON ex.id=st.execution_id WHERE ex.request_id=e.request_id
    AND (a.completed_capture_id=sc.id OR a.reused_capture_id=sc.id)
    AND a.state IN ('complete','not_modified','content_unchanged'))
   AND EXISTS(SELECT 1 FROM analysis_stage_attempts st WHERE st.execution_id=e.id AND st.state='completed'
    AND (EXISTS(SELECT 1 FROM source_fetch_attempts a WHERE a.stage_attempt_id=st.id AND
      (a.completed_capture_id=sc.id OR a.reused_capture_id=sc.id) AND a.state IN ('complete','not_modified','content_unchanged'))
      OR (st.input_manifest->'reused_capture_ids') ? c)))
  THEN RAISE EXCEPTION 'current capture lacks monitor execution source evidence' USING ERRCODE='23514'; END IF;
 END LOOP;
 SELECT max(a.finished_at) INTO expected FROM source_fetch_attempts a JOIN analysis_stage_attempts st ON st.id=a.stage_attempt_id
 JOIN analysis_executions ex ON ex.id=st.execution_id WHERE ex.request_id=e.request_id;
 IF (p_result->>'checked_at')::TIMESTAMPTZ IS DISTINCT FROM expected THEN
  RAISE EXCEPTION 'checked time must equal actual attempt completion' USING ERRCODE='23514'; END IF;
 IF p_result->>'baseline_eligible'='true' THEN
  IF expected IS NULL OR jsonb_array_length(p_result#>'{comparison,flags}')<>0
  OR p_result#>>'{coverage,baseline}' IS DISTINCT FROM 'complete'
  OR p_result#>>'{coverage,current}' IS DISTINCT FROM 'complete'
  OR jsonb_typeof(p_result#>'{comparison,new_filings}') IS DISTINCT FROM 'array'
  OR jsonb_typeof(p_result#>'{comparison,amendments}') IS DISTINCT FROM 'array'
  OR jsonb_array_length(p_result#>'{comparison,metadata_changes}')<>0
  OR jsonb_array_length(p_result#>'{comparison,missing_accessions}')<>0
  OR NOT EXISTS(SELECT 1 FROM source_captures WHERE id::TEXT IN (SELECT jsonb_array_elements_text(p_result->'current_capture_ids')) AND source_object_key='submissions/'||(p->>'cik'))
  THEN RAISE EXCEPTION 'complete monitor requires complete clean inventories' USING ERRCODE='23514'; END IF;
  n:=jsonb_array_length(p_result#>'{comparison,new_filings}'); m:=jsonb_array_length(p_result#>'{comparison,amendments}');
  IF p_result->>'outcome' IS DISTINCT FROM (CASE WHEN n>0 AND m>0 THEN 'mixed_changes' WHEN n>0 THEN 'new_filing' WHEN m>0 THEN 'amendment' ELSE 'no_change' END)
  THEN RAISE EXCEPTION 'change outcome disagrees with observed filings' USING ERRCODE='23514'; END IF;
 END IF;
 UPDATE analysis_stage_attempts SET state='completed',finished_at=clock_timestamp(),error_code=NULL,error_detail=NULL,
 result_reference=p_result::TEXT,input_manifest=jsonb_build_object('filing_monitor_plan',p,'baseline_lineage',p->'baseline')
 WHERE id=p_stage AND execution_id=e.id AND stage_key='sec_monitor_result' AND state='running';
 IF NOT FOUND THEN RAISE EXCEPTION 'monitor result stage is not active' USING ERRCODE='55000'; END IF;
 UPDATE analysis_executions SET current_stage=NULL WHERE id=e.id;
 PERFORM workflow_event(e.id,'stage_finished',jsonb_build_object('stage_id',p_stage,'outcome','completed','result',p_result));
 RETURN TRUE;
END $$;
CREATE FUNCTION workflow_monitor_success_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE monitor BOOLEAN; result JSONB;
BEGIN
 IF TG_TABLE_NAME='analysis_executions' THEN
  SELECT trigger='sec_filing_monitor' INTO monitor FROM analysis_requests WHERE id=NEW.request_id;
 ELSE
  SELECT r.trigger='sec_filing_monitor' INTO monitor FROM analysis_requests r JOIN analysis_executions e ON e.request_id=r.id WHERE e.id=NEW.execution_id;
 END IF;
 IF monitor AND NEW.state IN ('completed','completed_with_gaps') THEN
  IF NEW.error_code IS NOT NULL OR NEW.error_detail IS NOT NULL THEN RAISE EXCEPTION 'successful monitor cannot carry error fields' USING ERRCODE='23514'; END IF;
  IF TG_TABLE_NAME='analysis_stage_attempts' THEN
   IF NEW.stage_key='sec_monitor_result' AND NEW.result_reference IS NULL THEN RAISE EXCEPTION 'monitor requires typed result' USING ERRCODE='23514'; END IF;
  ELSE
   SELECT result_reference::JSONB INTO result FROM analysis_stage_attempts WHERE execution_id=NEW.id AND stage_key='sec_monitor_result' AND state='completed';
   IF result IS NULL OR (NEW.state='completed' AND result->>'baseline_eligible' IS DISTINCT FROM 'true')
   OR (NEW.state='completed_with_gaps' AND result->>'outcome' IS DISTINCT FROM 'incomplete')
   THEN RAISE EXCEPTION 'monitor execution needs matching typed result' USING ERRCODE='23514'; END IF;
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER workflow_monitor_success BEFORE UPDATE ON analysis_executions FOR EACH ROW EXECUTE FUNCTION workflow_monitor_success_guard();
CREATE TRIGGER workflow_monitor_stage_success BEFORE UPDATE ON analysis_stage_attempts FOR EACH ROW EXECUTE FUNCTION workflow_monitor_success_guard();

REVOKE ALL ON filing_monitor_seed_approvals,source_attempt_payloads FROM PUBLIC,equity_runtime;
GRANT SELECT ON filing_monitor_seed_approvals,source_attempt_payloads TO equity_runtime;
DO $$ DECLARE f RECORD; BEGIN
 FOR f IN SELECT p.oid::regprocedure AS signature FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
 WHERE n.nspname='public' AND (p.proname LIKE 'workflow_%monitor%' OR p.proname LIKE 'ingestion_monitor%') LOOP
  EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC,equity_runtime',f.signature);
 END LOOP;
END $$;
GRANT EXECUTE ON FUNCTION workflow_enqueue_monitor(UUID,UUID,TEXT,JSONB),workflow_monitor_baseline(JSONB,UUID),
 workflow_complete_monitor(JSONB,UUID,JSONB),ingestion_monitor_payload(JSONB,UUID,JSONB),
 ingestion_monitor_unchanged(JSONB,UUID,TIMESTAMPTZ,UUID) TO equity_runtime;
"""


def _claim() -> str:
    frozen = import_module("infra.migrations.versions.0006_source_bootstrap").SQL
    return frozen.split("CREATE FUNCTION workflow_claim_kind", 1)[1].split(
        "CREATE OR REPLACE FUNCTION workflow_claim", 1
    )[0]


def upgrade() -> None:
    op.execute(SQL)
    original = "CREATE OR REPLACE FUNCTION workflow_claim_kind" + _claim()
    op.execute(
        original.replace(
            "WHERE (r.trigger='source_bootstrap')=p_bootstrap",
            "WHERE r.trigger<>'sec_filing_monitor' AND (r.trigger='source_bootstrap')=p_bootstrap",
        )
    )
    monitor = (
        ("CREATE FUNCTION workflow_claim_monitor" + _claim())
        .replace(
            "p_seconds INTEGER,p_bootstrap BOOLEAN,p_request UUID",
            "p_seconds INTEGER,p_request UUID",
        )
        .replace("p_bootstrap IS NULL OR ", "")
        .replace("(r.trigger='source_bootstrap')=p_bootstrap", "r.trigger='sec_filing_monitor'")
    )
    op.execute(monitor)
    op.execute("""
    REVOKE ALL ON FUNCTION workflow_claim_monitor(TEXT,INTEGER,UUID) FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION workflow_claim_monitor(TEXT,INTEGER,UUID) TO equity_runtime;
    """)


def downgrade() -> None:
    op.execute("""
    DO $$ BEGIN
     IF EXISTS(SELECT 1 FROM analysis_requests WHERE trigger='sec_filing_monitor')
     OR EXISTS(SELECT 1 FROM filing_monitor_seed_approvals) OR EXISTS(SELECT 1 FROM source_attempt_payloads)
     THEN RAISE EXCEPTION 'refusing to discard monitor lineage or payload history' USING ERRCODE='55000'; END IF;
    END $$;
    DROP TRIGGER workflow_monitor_success ON analysis_executions;
    DROP TRIGGER workflow_monitor_stage_success ON analysis_stage_attempts;
    DROP FUNCTION workflow_monitor_success_guard();
    DROP FUNCTION workflow_complete_monitor(JSONB,UUID,JSONB);
    DROP TRIGGER source_attempt_payload_guard ON source_fetch_attempts;
    DROP FUNCTION ingestion_monitor_payload_guard();
    DROP FUNCTION ingestion_monitor_unchanged(JSONB,UUID,TIMESTAMPTZ,UUID);
    DROP FUNCTION ingestion_monitor_payload(JSONB,UUID,JSONB);
    DROP TRIGGER workflow_monitor_attempt ON source_fetch_attempts;
    DROP FUNCTION workflow_monitor_attempt_guard();
    DROP TRIGGER workflow_monitor_stage ON analysis_stage_attempts;
    DROP FUNCTION workflow_monitor_stage_guard();
    DROP FUNCTION workflow_claim_monitor(TEXT,INTEGER,UUID);
    DROP FUNCTION workflow_enqueue_monitor(UUID,UUID,TEXT,JSONB);
    DROP TRIGGER workflow_monitor_intent ON analysis_requests;
    DROP FUNCTION workflow_monitor_intent_guard();
    DROP FUNCTION workflow_monitor_baseline(JSONB,UUID);
    DROP FUNCTION workflow_monitor_scope(JSONB);
    ALTER TABLE analysis_requests DROP CONSTRAINT workflow_monitor_shape;
    DROP FUNCTION workflow_valid_monitor_plan(JSONB);
    ALTER TABLE analysis_requests DROP COLUMN filing_monitor_plan;
    DROP TABLE source_attempt_payloads;
    DROP TABLE filing_monitor_seed_approvals;
    ALTER TABLE source_fetch_attempts DROP CONSTRAINT monitor_unchanged_shape;
    ALTER TABLE source_fetch_attempts DROP CONSTRAINT source_fetch_attempts_check12;
    ALTER TABLE source_fetch_attempts ADD CONSTRAINT source_fetch_attempts_check12 CHECK((state='not_modified')=(reused_capture_id IS NOT NULL));
    ALTER TABLE source_fetch_attempts DROP CONSTRAINT source_fetch_attempts_state_check;
    ALTER TABLE source_fetch_attempts ADD CONSTRAINT source_fetch_attempts_state_check CHECK(state IN
     ('prepared','in_progress','complete','not_modified','redirected','http_error','transport_error','body_limit','redirect_refused','archive_error','cancelled','interrupted_unknown'));
    ALTER TABLE analysis_requests DROP CONSTRAINT analysis_requests_trigger_check;
    ALTER TABLE analysis_requests ADD CONSTRAINT analysis_requests_trigger_check CHECK(trigger IN ('watchlist_add','manual_refresh','source_bootstrap'));
    ALTER TABLE analysis_requests DROP CONSTRAINT workflow_bootstrap_shape;
    """)
    frozen = import_module("infra.migrations.versions.0006_source_bootstrap").SQL
    shape = frozen.split(
        "ALTER TABLE analysis_requests ADD CONSTRAINT workflow_bootstrap_shape", 1
    )[1].split("CREATE FUNCTION", 1)[0]
    op.execute("ALTER TABLE analysis_requests ADD CONSTRAINT workflow_bootstrap_shape" + shape)
    op.execute("CREATE OR REPLACE FUNCTION workflow_claim_kind" + _claim())
