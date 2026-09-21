"""D031 source-only bootstrap requests using existing W1 leases and SEC transport."""

from alembic import op

revision = "0006_source_bootstrap"
down_revision = "0005_market_data_hypertables"
branch_labels = None
depends_on = None

SQL = r"""
ALTER TABLE analysis_requests DROP CONSTRAINT analysis_requests_trigger_check;
ALTER TABLE analysis_requests ALTER COLUMN quote_identifier_id DROP NOT NULL;
ALTER TABLE analysis_requests ADD CONSTRAINT analysis_requests_trigger_check
 CHECK(trigger IN ('watchlist_add','manual_refresh','source_bootstrap'));
ALTER TABLE analysis_requests ADD CONSTRAINT workflow_bootstrap_shape CHECK(
 (trigger<>'source_bootstrap' AND quote_identifier_id IS NOT NULL) OR
 (trigger='source_bootstrap' AND quote_identifier_id IS NULL AND membership_id IS NULL
  AND parent_request_id IS NULL AND market_plan_revision IS NULL
  AND price_source_id IS NULL AND price_start IS NULL AND price_end IS NULL
  AND macro_source_id IS NULL AND macro_series_keys IS NULL AND macro_start IS NULL
  AND macro_end IS NULL AND macro_source_as_of_date IS NULL));

CREATE FUNCTION workflow_enqueue_bootstrap(p_workspace UUID,p_security UUID,p_key TEXT,p_options JSONB)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE options JSONB; params_hash TEXT; vintage TIMESTAMPTZ;
 existing analysis_request_keys%ROWTYPE; request UUID; execution UUID;
BEGIN
 IF p_key IS NULL OR length(p_key) NOT BETWEEN 1 AND 200 OR p_options IS NULL
 OR jsonb_typeof(p_options)<>'object'
 OR p_options-'history_mode'-'filed_cutoff'-'requested_periods'-'retrieval_vintage'-'max_attempts'<>'{}'::jsonb THEN
  RAISE EXCEPTION 'unknown bootstrap option or invalid intent' USING ERRCODE='22023'; END IF;
 PERFORM 1 FROM workspaces WHERE id=p_workspace FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'unknown workspace' USING ERRCODE='23503'; END IF;
 PERFORM 1 FROM securities s JOIN issuers i ON i.id=s.issuer_id
 WHERE s.id=p_security AND i.cik ~ '^[0-9]{10}$' AND i.cik<>'0000000000';
 IF NOT FOUND THEN RAISE EXCEPTION 'bootstrap needs registered security and SEC issuer' USING ERRCODE='23503'; END IF;
 IF p_options->>'retrieval_vintage' IS NOT NULL
 AND p_options->>'retrieval_vintage' !~ '(Z|[+-][0-9]{2}:[0-9]{2})$' THEN
  RAISE EXCEPTION 'retrieval vintage requires explicit timezone' USING ERRCODE='22023'; END IF;
 vintage:=(p_options->>'retrieval_vintage')::TIMESTAMPTZ;
 IF vintage IS NOT NULL AND NOT isfinite(vintage) THEN
  RAISE EXCEPTION 'retrieval vintage must be finite' USING ERRCODE='22023'; END IF;
 options:=jsonb_build_object(
  'history_mode',coalesce(p_options->>'history_mode','latest_reported'),
  'filed_cutoff',(p_options->>'filed_cutoff')::DATE,
  'requested_periods',coalesce(p_options->'requested_periods','[]'::jsonb),
  'retrieval_vintage',CASE WHEN vintage IS NULL THEN NULL
   ELSE to_char(vintage AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"') END,
  'max_attempts',coalesce((p_options->>'max_attempts')::INTEGER,3));
 params_hash:=encode(sha256(convert_to(jsonb_build_object(
  'workspace',p_workspace,'security',p_security,'trigger','source_bootstrap','options',options)::TEXT,'UTF8')),'hex');
 SELECT * INTO existing FROM analysis_request_keys WHERE workspace_id=p_workspace AND idempotency_key=p_key;
 IF FOUND THEN
  IF existing.parameters_hash<>params_hash THEN
   RAISE EXCEPTION 'idempotency key reused with different parameters' USING ERRCODE='22023'; END IF;
  RETURN workflow_request_result(existing.request_id);
 END IF;
 request:=gen_random_uuid(); execution:=gen_random_uuid();
 INSERT INTO analysis_requests(id,workspace_id,security_id,quote_identifier_id,trigger,
  membership_id,parent_request_id,idempotency_key,history_mode,filed_cutoff,requested_periods,
  retrieval_policy,retrieval_vintage,max_attempts,request_parameters_hash)
 VALUES(request,p_workspace,p_security,NULL,'source_bootstrap',NULL,NULL,p_key,
  options->>'history_mode',(options->>'filed_cutoff')::DATE,options->'requested_periods',
  CASE WHEN vintage IS NULL THEN 'refresh' ELSE 'pinned_vintage' END,vintage,
  (options->>'max_attempts')::INTEGER,params_hash);
 INSERT INTO analysis_request_keys(workspace_id,idempotency_key,request_id,parameters_hash)
 VALUES(p_workspace,p_key,request,params_hash);
 INSERT INTO analysis_executions(id,request_id,attempt_no,state) VALUES(execution,request,1,'queued');
 INSERT INTO analysis_request_state(request_id,current_execution_id,attempt_epoch) VALUES(request,execution,1);
 PERFORM workflow_event(execution,'queued',jsonb_build_object('trigger','source_bootstrap'));
 RETURN workflow_request_result(request);
END $$;

CREATE FUNCTION workflow_bootstrap_stage_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM analysis_executions e JOIN analysis_requests r ON r.id=e.request_id
 WHERE e.id=NEW.execution_id AND r.trigger='source_bootstrap')
 AND NEW.stage_key NOT IN ('sec_inventory_parse','sec_inventory','sec_bootstrap_manifest')
 AND NEW.stage_key !~ '^sec_(fetch|parse)_[a-f0-9]{24}$' THEN
  RAISE EXCEPTION 'bootstrap permits SEC capture and inventory stages only' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER workflow_bootstrap_stage BEFORE INSERT ON analysis_stage_attempts
 FOR EACH ROW EXECUTE FUNCTION workflow_bootstrap_stage_guard();


CREATE FUNCTION workflow_bootstrap_attempt_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE kind TEXT; cik TEXT;
BEGIN
 SELECT r.trigger,i.cik INTO kind,cik FROM analysis_stage_attempts st
 JOIN analysis_executions e ON e.id=st.execution_id JOIN analysis_requests r ON r.id=e.request_id
 JOIN securities s ON s.id=r.security_id JOIN issuers i ON i.id=s.issuer_id
 WHERE st.id=NEW.stage_attempt_id;
 IF kind='source_bootstrap' AND
 (split_part(NEW.source_object_key,'/',2) IS DISTINCT FROM cik
 OR NOT market_sec_resource(NEW.source_id,NEW.policy_revision_id,NEW.request_url,NEW.source_object_key)) THEN
  RAISE EXCEPTION 'bootstrap resource must be SEC evidence for its registered issuer' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER workflow_bootstrap_attempt BEFORE INSERT ON source_fetch_attempts
 FOR EACH ROW EXECUTE FUNCTION workflow_bootstrap_attempt_guard();
REVOKE ALL ON FUNCTION workflow_bootstrap_attempt_guard() FROM PUBLIC,equity_runtime;

CREATE FUNCTION workflow_claim_kind(p_worker TEXT,p_seconds INTEGER,p_bootstrap BOOLEAN,p_request UUID) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE control analysis_request_state%ROWTYPE; execution analysis_executions%ROWTYPE; next_id UUID;
BEGIN
    IF p_bootstrap IS NULL OR p_worker IS NULL OR length(trim(p_worker)) NOT BETWEEN 1 AND 200
        OR p_seconds IS NULL OR p_seconds NOT BETWEEN 1 AND 3600 THEN
        RAISE EXCEPTION 'invalid worker or lease duration' USING ERRCODE='22023';
    END IF;
    LOOP
        SELECT s.* INTO control FROM analysis_request_state s
            JOIN analysis_executions e ON e.id=s.current_execution_id
            JOIN analysis_requests r ON r.id=s.request_id
            WHERE (r.trigger='source_bootstrap')=p_bootstrap AND (p_request IS NULL OR r.id=p_request)
              AND s.terminal_outcome IS NULL AND (
                (e.state='queued' AND e.available_at<=clock_timestamp()) OR
                (e.state='running' AND e.lease_expires_at<=clock_timestamp()))
            ORDER BY e.available_at,r.request_sequence FOR UPDATE OF s SKIP LOCKED LIMIT 1;
        IF NOT FOUND THEN RETURN NULL; END IF;
        SELECT * INTO execution FROM analysis_executions WHERE id=control.current_execution_id FOR UPDATE;
        IF execution.state='running' THEN
            next_id:=workflow_close_retry(execution.id,'lease_expired',0);
            IF next_id IS NULL THEN CONTINUE; END IF;
            SELECT * INTO execution FROM analysis_executions WHERE id=next_id;
        END IF;
        UPDATE analysis_executions SET state='running',lease_owner=p_worker,
            lease_expires_at=clock_timestamp()+make_interval(secs=>p_seconds),
            fencing_token=fencing_token+1,started_at=clock_timestamp() WHERE id=execution.id;
        PERFORM workflow_event(execution.id,'claimed',jsonb_build_object('worker_id',p_worker));
        RETURN workflow_lease_result(execution.id);
    END LOOP;
END $$;

CREATE OR REPLACE FUNCTION workflow_claim(p_worker TEXT,p_seconds INTEGER) RETURNS JSONB
LANGUAGE sql SECURITY DEFINER SET search_path=public,pg_temp AS $$
 SELECT workflow_claim_kind(p_worker,p_seconds,false,NULL)
$$;
CREATE FUNCTION workflow_claim_bootstrap(p_worker TEXT,p_seconds INTEGER,p_request UUID DEFAULT NULL) RETURNS JSONB
LANGUAGE sql SECURITY DEFINER SET search_path=public,pg_temp AS $$
 SELECT workflow_claim_kind(p_worker,p_seconds,true,p_request)
$$;
REVOKE ALL ON FUNCTION workflow_enqueue_bootstrap(UUID,UUID,TEXT,JSONB),
 workflow_claim_kind(TEXT,INTEGER,BOOLEAN,UUID),workflow_claim_bootstrap(TEXT,INTEGER,UUID),
 workflow_bootstrap_stage_guard() FROM PUBLIC,equity_runtime;
GRANT EXECUTE ON FUNCTION workflow_enqueue_bootstrap(UUID,UUID,TEXT,JSONB),
 workflow_claim_bootstrap(TEXT,INTEGER,UUID) TO equity_runtime;
"""

RESTORE_CLAIM = r"""CREATE OR REPLACE FUNCTION workflow_claim(p_worker TEXT,p_seconds INTEGER) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE control analysis_request_state%ROWTYPE; execution analysis_executions%ROWTYPE; next_id UUID;
BEGIN
    IF p_worker IS NULL OR length(trim(p_worker)) NOT BETWEEN 1 AND 200
        OR p_seconds IS NULL OR p_seconds NOT BETWEEN 1 AND 3600 THEN
        RAISE EXCEPTION 'invalid worker or lease duration' USING ERRCODE='22023';
    END IF;
    LOOP
        SELECT s.* INTO control FROM analysis_request_state s
            JOIN analysis_executions e ON e.id=s.current_execution_id
            JOIN analysis_requests r ON r.id=s.request_id
            WHERE s.terminal_outcome IS NULL AND (
                (e.state='queued' AND e.available_at<=clock_timestamp()) OR
                (e.state='running' AND e.lease_expires_at<=clock_timestamp()))
            ORDER BY e.available_at,r.request_sequence FOR UPDATE OF s SKIP LOCKED LIMIT 1;
        IF NOT FOUND THEN RETURN NULL; END IF;
        SELECT * INTO execution FROM analysis_executions WHERE id=control.current_execution_id FOR UPDATE;
        IF execution.state='running' THEN
            next_id:=workflow_close_retry(execution.id,'lease_expired',0);
            IF next_id IS NULL THEN CONTINUE; END IF;
            SELECT * INTO execution FROM analysis_executions WHERE id=next_id;
        END IF;
        UPDATE analysis_executions SET state='running',lease_owner=p_worker,
            lease_expires_at=clock_timestamp()+make_interval(secs=>p_seconds),
            fencing_token=fencing_token+1,started_at=clock_timestamp() WHERE id=execution.id;
        PERFORM workflow_event(execution.id,'claimed',jsonb_build_object('worker_id',p_worker));
        RETURN workflow_lease_result(execution.id);
    END LOOP;
END $$;"""


def upgrade() -> None:
    op.execute(SQL)


def downgrade() -> None:
    op.execute("""
    DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM analysis_requests WHERE trigger='source_bootstrap') THEN
        RAISE EXCEPTION 'refusing to discard bootstrap request history' USING ERRCODE='55000';
      END IF;
    END $$;
    DROP TRIGGER workflow_bootstrap_attempt ON source_fetch_attempts;
    DROP FUNCTION workflow_bootstrap_attempt_guard();
    DROP TRIGGER workflow_bootstrap_stage ON analysis_stage_attempts;
    DROP FUNCTION workflow_bootstrap_stage_guard();
    DROP FUNCTION workflow_enqueue_bootstrap(UUID,UUID,TEXT,JSONB);
    DROP FUNCTION workflow_claim_bootstrap(TEXT,INTEGER,UUID);
    """)
    op.execute(RESTORE_CLAIM)
    op.execute("""
    DROP FUNCTION workflow_claim_kind(TEXT,INTEGER,BOOLEAN,UUID);
    ALTER TABLE analysis_requests DROP CONSTRAINT workflow_bootstrap_shape;
    ALTER TABLE analysis_requests DROP CONSTRAINT analysis_requests_trigger_check;
    ALTER TABLE analysis_requests ALTER COLUMN quote_identifier_id SET NOT NULL;
    ALTER TABLE analysis_requests ADD CONSTRAINT analysis_requests_trigger_check
      CHECK(trigger IN ('watchlist_add','manual_refresh'));
    """)
