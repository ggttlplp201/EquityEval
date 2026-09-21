"""D036 fixed-scope scheduling and fenced operator lifecycle; no background service."""

from alembic import op

revision = "0010_filing_scheduler"
down_revision = "0009_monitor_result_identity"
branch_labels = None
depends_on = None

SQL = r"""
CREATE FUNCTION scheduler_now() RETURNS TIMESTAMPTZ LANGUAGE sql VOLATILE
 SET search_path=public,pg_temp AS $$ SELECT clock_timestamp() $$;
CREATE FUNCTION scheduler_hash(p JSONB) RETURNS TEXT LANGUAGE sql IMMUTABLE
 SET search_path=public,pg_temp AS $$ SELECT encode(sha256(convert_to(p::TEXT,'UTF8')),'hex') $$;
CREATE FUNCTION scheduler_valid(c JSONB) RETURNS BOOLEAN LANGUAGE plpgsql IMMUTABLE
 SET search_path=public,pg_temp AS $$
DECLARE k TEXT; cadence INTEGER; jitter INTEGER; budget INTEGER; attempts INTEGER; lag INTEGER;
BEGIN
 IF c IS NULL OR jsonb_typeof(c)<>'object'
 OR NOT c ?& ARRAY['version','plan','anchor','cadence_seconds','jitter_seconds','budget_units','max_attempts','lag_seconds','active']
 OR c-ARRAY['version','plan','anchor','cadence_seconds','jitter_seconds','budget_units','max_attempts','lag_seconds','active']<>'{}'
 OR c->>'version' IS DISTINCT FROM 'sec-filing-schedule-v1'
 OR NOT workflow_valid_monitor_plan(c->'plan') OR jsonb_typeof(c->'active') IS DISTINCT FROM 'boolean'
 OR coalesce(c->>'anchor','') !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$'
 THEN RETURN FALSE; END IF;
 FOREACH k IN ARRAY ARRAY['cadence_seconds','jitter_seconds','budget_units','max_attempts','lag_seconds'] LOOP
  IF jsonb_typeof(c->k) IS DISTINCT FROM 'number' OR c->>k !~ '^[0-9]{1,8}$' THEN RETURN FALSE; END IF;
 END LOOP;
 cadence:=(c->>'cadence_seconds')::INT; jitter:=(c->>'jitter_seconds')::INT;
 budget:=(c->>'budget_units')::INT; attempts:=(c->>'max_attempts')::INT; lag:=(c->>'lag_seconds')::INT;
 RETURN cadence BETWEEN 300 AND 86400 AND jitter BETWEEN 0 AND least(60,cadence/10)
 AND attempts BETWEEN 1 AND 3 AND budget BETWEEN 3*jsonb_array_length(c#>'{plan,resources}')*attempts AND 10000
 AND lag BETWEEN cadence AND 2592000 AND isfinite((c->>'anchor')::TIMESTAMPTZ)
 AND (c->>'anchor')::TIMESTAMPTZ >= (c#>>'{plan,baseline,cutoff}')::TIMESTAMPTZ;
EXCEPTION WHEN invalid_text_representation OR datetime_field_overflow OR numeric_value_out_of_range THEN RETURN FALSE;
END $$;
CREATE TABLE filing_schedules (
 id UUID PRIMARY KEY, workspace_id UUID NOT NULL REFERENCES workspaces(id),
 security_id UUID NOT NULL REFERENCES securities(id), source_id UUID NOT NULL REFERENCES sources(id),
 policy_revision_id UUID NOT NULL REFERENCES source_policy_revisions(id),
 creation_key TEXT NOT NULL CHECK(length(creation_key) BETWEEN 1 AND 200),
 config_hash TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT scheduler_now(),
 UNIQUE(workspace_id,creation_key), UNIQUE(workspace_id,security_id,source_id,policy_revision_id)
);
CREATE TABLE filing_schedule_revisions (
 id UUID PRIMARY KEY, schedule_id UUID NOT NULL REFERENCES filing_schedules(id),
 epoch INTEGER NOT NULL CHECK(epoch>0), predecessor UUID REFERENCES filing_schedule_revisions(id),
 first_slot BIGINT NOT NULL CHECK(first_slot>=0), config JSONB NOT NULL CHECK(scheduler_valid(config)),
 config_hash TEXT NOT NULL, operation_key TEXT NOT NULL CHECK(length(operation_key) BETWEEN 1 AND 200),
 operation_hash TEXT NOT NULL, reason TEXT NOT NULL CHECK(length(btrim(reason)) BETWEEN 1 AND 1000),
 actor TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT scheduler_now(),
 UNIQUE(schedule_id,epoch), UNIQUE(schedule_id,operation_key)
);
CREATE TABLE filing_schedule_slots (
 id UUID PRIMARY KEY, schedule_id UUID NOT NULL REFERENCES filing_schedules(id),
 revision_id UUID NOT NULL REFERENCES filing_schedule_revisions(id), slot_index BIGINT NOT NULL CHECK(slot_index>=0),
 nominal_at TIMESTAMPTZ NOT NULL, due_at TIMESTAMPTZ NOT NULL,
 plan JSONB NOT NULL CHECK(workflow_valid_monitor_plan(plan)), plan_hash TEXT NOT NULL,
 request_id UUID NOT NULL UNIQUE REFERENCES analysis_requests(id), request_key TEXT NOT NULL,
 reserved_units INTEGER NOT NULL CHECK(reserved_units BETWEEN 3 AND 99),
 created_at TIMESTAMPTZ NOT NULL DEFAULT scheduler_now(), UNIQUE(schedule_id,slot_index)
);
CREATE TABLE filing_schedule_state (
 schedule_id UUID PRIMARY KEY REFERENCES filing_schedules(id),
 revision_id UUID NOT NULL REFERENCES filing_schedule_revisions(id), epoch INTEGER NOT NULL,
 last_slot BIGINT NOT NULL DEFAULT -1, unresolved_slot UUID REFERENCES filing_schedule_slots(id),
 baseline JSONB NOT NULL, baseline_slot BIGINT NOT NULL DEFAULT -1,
 failures INTEGER NOT NULL DEFAULT 0 CHECK(failures>=0), retry_at TIMESTAMPTZ,
 rebase_reason TEXT, last_tick_at TIMESTAMPTZ
);
CREATE TABLE filing_schedule_events (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), schedule_id UUID NOT NULL REFERENCES filing_schedules(id),
 revision_id UUID NOT NULL REFERENCES filing_schedule_revisions(id), slot_id UUID REFERENCES filing_schedule_slots(id),
 kind TEXT NOT NULL CHECK(kind IN ('created','revised','missed_range','materialized','resolved','deferred','blocked','observed')),
 semantic_key TEXT NOT NULL, details JSONB NOT NULL, at TIMESTAMPTZ NOT NULL DEFAULT scheduler_now(),
 UNIQUE(schedule_id,semantic_key)
);
CREATE FUNCTION scheduler_baseline_guard() RETURNS TRIGGER LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE sl filing_schedule_slots%ROWTYPE; security UUID;
BEGIN
 IF NEW.baseline IS DISTINCT FROM OLD.baseline OR NEW.baseline_slot IS DISTINCT FROM OLD.baseline_slot THEN
  IF NEW.baseline_slot<=OLD.baseline_slot OR NEW.baseline IS NOT DISTINCT FROM OLD.baseline
  OR (NEW.baseline->>'cutoff')::TIMESTAMPTZ<(OLD.baseline->>'cutoff')::TIMESTAMPTZ THEN
   RAISE EXCEPTION 'baseline regression refused' USING ERRCODE='23514'; END IF;
  SELECT * INTO sl FROM filing_schedule_slots WHERE id=OLD.unresolved_slot AND schedule_id=OLD.schedule_id
   AND slot_index=NEW.baseline_slot AND request_id=(NEW.baseline->>'request_id')::UUID;
  IF sl.id IS NULL THEN RAISE EXCEPTION 'baseline must reconcile the current slot' USING ERRCODE='23514'; END IF;
  SELECT security_id INTO security FROM filing_schedules WHERE id=OLD.schedule_id;
  PERFORM workflow_monitor_baseline(jsonb_set(sl.plan,'{baseline}',NEW.baseline),security);
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER scheduler_monotonic_baseline BEFORE UPDATE ON filing_schedule_state
 FOR EACH ROW EXECUTE FUNCTION scheduler_baseline_guard();
CREATE FUNCTION scheduler_event(s UUID,r UUID,sl UUID,k TEXT,key TEXT,d JSONB) RETURNS VOID
 LANGUAGE sql SET search_path=public,pg_temp AS $$
 INSERT INTO filing_schedule_events(schedule_id,revision_id,slot_id,kind,semantic_key,details)
 VALUES(s,r,sl,k,key,d) ON CONFLICT(schedule_id,semantic_key) DO NOTHING
$$;
CREATE FUNCTION scheduler_lock(s UUID) RETURNS VOID LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE w UUID;
BEGIN
 SELECT workspace_id INTO w FROM filing_schedules WHERE id=s;
 IF w IS NULL THEN RAISE EXCEPTION 'unknown schedule' USING ERRCODE='23503'; END IF;
 PERFORM 1 FROM workspaces WHERE id=w FOR UPDATE;
 PERFORM 1 FROM filing_schedule_state WHERE schedule_id=s FOR UPDATE;
END $$;
CREATE FUNCTION scheduler_due(s UUID,r UUID,k BIGINT) RETURNS TIMESTAMPTZ
 LANGUAGE plpgsql STABLE SET search_path=public,pg_temp AS $$
DECLARE c JSONB; bytes BYTEA; n NUMERIC:=0; i INTEGER;
BEGIN
 SELECT config INTO c FROM filing_schedule_revisions WHERE id=r AND schedule_id=s;
 IF c IS NULL OR k<0 THEN RAISE EXCEPTION 'invalid slot identity' USING ERRCODE='22023'; END IF;
 bytes:=sha256(convert_to('sec-filing-schedule-v1'||chr(10)||s::TEXT||chr(10)||r::TEXT||chr(10)||k::TEXT,'UTF8'));
 FOR i IN 0..7 LOOP n:=n*256+get_byte(bytes,i); END LOOP;
 RETURN (c->>'anchor')::TIMESTAMPTZ + make_interval(secs=>k*(c->>'cadence_seconds')::DOUBLE PRECISION)
 + make_interval(secs=>mod(n,(c->>'jitter_seconds')::INT+1)::DOUBLE PRECISION);
END $$;
CREATE FUNCTION scheduler_create(w UUID,security UUID,key TEXT,c JSONB,review TEXT) RETURNS UUID
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE s UUID:=gen_random_uuid(); r UUID:=gen_random_uuid(); old filing_schedules%ROWTYPE; hash TEXT;
BEGIN
 IF NOT scheduler_valid(c) OR length(coalesce(key,'')) NOT BETWEEN 1 AND 200 OR length(btrim(coalesce(review,''))) NOT BETWEEN 1 AND 1000
 THEN RAISE EXCEPTION 'invalid schedule configuration/review' USING ERRCODE='22023'; END IF;
 c:=jsonb_set(jsonb_set(c,'{plan,forms}',(SELECT jsonb_agg(x ORDER BY (x#>>'{}') COLLATE "C") FROM jsonb_array_elements(c#>'{plan,forms}') x)),
 '{plan,resources}',(SELECT jsonb_agg(x ORDER BY (x#>>'{}') COLLATE "C") FROM jsonb_array_elements(c#>'{plan,resources}') x));
 PERFORM 1 FROM workspaces WHERE id=w FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'unknown workspace' USING ERRCODE='23503'; END IF;
 hash:=scheduler_hash(jsonb_build_object('security',security,'config',c,'review',review));
 SELECT * INTO old FROM filing_schedules WHERE workspace_id=w AND creation_key=key;
 IF FOUND THEN
  IF old.config_hash<>hash THEN RAISE EXCEPTION 'creation key conflict' USING ERRCODE='22023'; END IF;
  RETURN old.id;
 END IF;
 PERFORM workflow_monitor_baseline(c->'plan',security);
 INSERT INTO filing_schedules(id,workspace_id,security_id,source_id,policy_revision_id,creation_key,config_hash)
 VALUES(s,w,security,(c#>>'{plan,source_id}')::UUID,(c#>>'{plan,policy_revision_id}')::UUID,key,hash);
 INSERT INTO filing_schedule_revisions(id,schedule_id,epoch,first_slot,config,config_hash,operation_key,operation_hash,reason,actor)
 VALUES(r,s,1,0,c,scheduler_hash(c),key,hash,review,session_user);
 INSERT INTO filing_schedule_state(schedule_id,revision_id,epoch,baseline) VALUES(s,r,1,c#>'{plan,baseline}');
 PERFORM scheduler_event(s,r,NULL,'created','created',jsonb_build_object('review',review,'active',c->'active'));
 RETURN s;
END $$;
CREATE FUNCTION scheduler_revise(s UUID,expected INTEGER,key TEXT,c JSONB,reason TEXT) RETURNS UUID
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE st filing_schedule_state%ROWTYPE; old filing_schedule_revisions%ROWTYPE; previous JSONB;
 r UUID:=gen_random_uuid(); hash TEXT;
BEGIN
 IF NOT scheduler_valid(c) OR length(coalesce(key,'')) NOT BETWEEN 1 AND 200 OR length(btrim(coalesce(reason,''))) NOT BETWEEN 1 AND 1000
 THEN RAISE EXCEPTION 'invalid revision' USING ERRCODE='22023'; END IF;
 c:=jsonb_set(jsonb_set(c,'{plan,forms}',(SELECT jsonb_agg(x ORDER BY (x#>>'{}') COLLATE "C") FROM jsonb_array_elements(c#>'{plan,forms}') x)),
 '{plan,resources}',(SELECT jsonb_agg(x ORDER BY (x#>>'{}') COLLATE "C") FROM jsonb_array_elements(c#>'{plan,resources}') x));
 PERFORM scheduler_lock(s);
 hash:=scheduler_hash(jsonb_build_object('epoch',expected,'config',c,'reason',reason));
 SELECT * INTO old FROM filing_schedule_revisions WHERE schedule_id=s AND operation_key=key;
 IF FOUND THEN
  IF old.operation_hash<>hash THEN RAISE EXCEPTION 'revision key conflict' USING ERRCODE='22023'; END IF;
  RETURN old.id;
 END IF;
 SELECT * INTO st FROM filing_schedule_state WHERE schedule_id=s;
 IF st.epoch IS DISTINCT FROM expected THEN RAISE EXCEPTION 'stale schedule revision' USING ERRCODE='40001'; END IF;
 SELECT config INTO previous FROM filing_schedule_revisions WHERE id=st.revision_id;
 -- Full plan equality deliberately includes resources/forms/policy/version and original baseline.
 IF c-ARRAY['active','jitter_seconds','budget_units','lag_seconds'] IS DISTINCT FROM previous-ARRAY['active','jitter_seconds','budget_units','lag_seconds']
 THEN RAISE EXCEPTION 'rebase_required: immutable scope/cadence/intent' USING ERRCODE='23514'; END IF;
 INSERT INTO filing_schedule_revisions(id,schedule_id,epoch,predecessor,first_slot,config,config_hash,operation_key,operation_hash,reason,actor)
 VALUES(r,s,st.epoch+1,st.revision_id,st.last_slot+1,c,scheduler_hash(c),key,hash,reason,session_user);
 UPDATE filing_schedule_state SET revision_id=r,epoch=epoch+1 WHERE schedule_id=s;
 PERFORM scheduler_event(s,r,NULL,'revised','revision:'||r,jsonb_build_object('active',c->'active','reason',reason));
 RETURN r;
END $$;
CREATE FUNCTION scheduler_budget(s UUID) RETURNS INTEGER LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
 SELECT coalesce(sum(sl.reserved_units),0)::INT FROM filing_schedule_slots sl
 LEFT JOIN filing_schedule_events e ON e.slot_id=sl.id AND e.kind='resolved'
 WHERE sl.schedule_id=s AND (e.id IS NULL OR e.at>scheduler_now()-interval '24 hours')
$$;
CREATE FUNCTION scheduler_reconcile(s UUID) RETURNS VOID LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE st filing_schedule_state%ROWTYPE; sl filing_schedule_slots%ROWTYPE; ctrl analysis_request_state%ROWTYPE;
 result JSONB; b JSONB; c JSONB; success BOOLEAN; delay INTEGER;
BEGIN
 SELECT * INTO st FROM filing_schedule_state WHERE schedule_id=s;
 IF st.unresolved_slot IS NULL THEN RETURN; END IF;
 SELECT * INTO sl FROM filing_schedule_slots WHERE id=st.unresolved_slot;
 SELECT * INTO ctrl FROM analysis_request_state WHERE request_id=sl.request_id;
 IF ctrl.terminal_outcome IS NULL THEN RETURN; END IF;
 SELECT result_reference::JSONB INTO result FROM analysis_stage_attempts
 WHERE execution_id=ctrl.current_execution_id AND stage_key='sec_monitor_result' AND state='completed';
 success:=coalesce(ctrl.terminal_outcome='completed' AND result->>'baseline_eligible'='true'
 AND result->>'outcome' IN ('no_change','new_filing','amendment','mixed_changes'),FALSE);
 IF success THEN
  b:=jsonb_build_object('kind','prior_monitor_result','request_id',sl.request_id,'execution_id',ctrl.current_execution_id,
  'manifest_sha256',result#>>'{manifest,body_sha256}','manifest_id',result->>'manifest_id',
  'cutoff',sl.plan->>'cutoff','version','sec-filing-monitor-v1','seed_approval_id',NULL,'plan_sha256',NULL,'capture_id',NULL);
  PERFORM workflow_monitor_baseline(jsonb_set(sl.plan,'{baseline}',b),(SELECT security_id FROM filing_schedules WHERE id=s));
  IF sl.slot_index<=st.baseline_slot OR (b->>'cutoff')::TIMESTAMPTZ<(st.baseline->>'cutoff')::TIMESTAMPTZ
  THEN RAISE EXCEPTION 'baseline regression refused' USING ERRCODE='23514'; END IF;
 ELSE b:=st.baseline;
 END IF;
 SELECT config INTO c FROM filing_schedule_revisions WHERE id=st.revision_id;
 delay:=least(3600,(c->>'cadence_seconds')::INT * power(2,least(st.failures,4))::INT);
 UPDATE filing_schedule_state SET unresolved_slot=NULL, baseline=b,
 baseline_slot=CASE WHEN success THEN sl.slot_index ELSE baseline_slot END,
 failures=CASE WHEN success THEN 0 ELSE least(failures+1,1000000) END,
 retry_at=CASE WHEN success THEN NULL ELSE scheduler_now()+make_interval(secs=>delay) END,
 rebase_reason=CASE WHEN NOT success AND (
 (result#>'{comparison,flags}') ?| ARRAY['unplanned_overlapping_history','history_limit_exceeded','baseline_history_limit_exceeded','baseline_submissions_invalid','baseline_inventory_incomplete']
 ) THEN 'structural_coverage_incomplete' ELSE rebase_reason END
 WHERE schedule_id=s;
 PERFORM scheduler_event(s,st.revision_id,sl.id,'resolved','resolved:'||sl.id,
 jsonb_build_object('execution_id',ctrl.current_execution_id,'terminal_outcome',ctrl.terminal_outcome,
 'checked_at',result->>'checked_at','outcome',coalesce(result->>'outcome','error'),'eligible',success,'manifest_sha256',result#>>'{manifest,body_sha256}',
 'baseline',b,'retry_at',CASE WHEN success THEN NULL ELSE scheduler_now()+make_interval(secs=>delay) END));
END $$;
CREATE FUNCTION scheduler_tick(s UUID) RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE st filing_schedule_state%ROWTYPE; c JSONB; rev filing_schedule_revisions%ROWTYPE;
 base filing_schedules%ROWTYPE; sl filing_schedule_slots%ROWTYPE; now_at TIMESTAMPTZ:=scheduler_now();
 k BIGINT; due TIMESTAMPTZ; nominal TIMESTAMPTZ; p JSONB; req JSONB; key TEXT; reason TEXT; units INTEGER;
BEGIN
 PERFORM scheduler_lock(s); PERFORM scheduler_reconcile(s);
 SELECT * INTO st FROM filing_schedule_state WHERE schedule_id=s;
 SELECT * INTO base FROM filing_schedules WHERE id=s;
 SELECT config INTO c FROM filing_schedule_revisions WHERE id=st.revision_id;
 UPDATE filing_schedule_state SET last_tick_at=now_at WHERE schedule_id=s;
 IF now_at AT TIME ZONE 'UTC' >= ((c#>>'{plan,inventory_end}')::DATE+1)::TIMESTAMP OR st.rebase_reason IS NOT NULL THEN
  reason:=coalesce(st.rebase_reason,'filed_window_expired');
  PERFORM scheduler_event(s,st.revision_id,st.unresolved_slot,'blocked','rebase:'||st.revision_id||':'||reason,
   jsonb_build_object('version','sec-filing-schedule-block-v1','reason','rebase_required','mismatch',reason,
    'old_scope_sha256',scheduler_hash((c->'plan')-ARRAY['cutoff','baseline']), 'baseline',st.baseline,
    'proposed_slot',greatest(st.last_slot+1,0),
    'cutoff',(c->>'anchor')::TIMESTAMPTZ+make_interval(secs=>greatest(st.last_slot+1,0)*(c->>'cadence_seconds')::DOUBLE PRECISION),
    'requires_owner_review',true));
  RETURN jsonb_build_object('state','rebase_required','reason',reason);
 END IF;
 IF NOT (c->>'active')::BOOLEAN THEN RETURN jsonb_build_object('state','paused'); END IF;
 IF st.unresolved_slot IS NOT NULL THEN
  SELECT * INTO sl FROM filing_schedule_slots WHERE id=st.unresolved_slot;
  RETURN jsonb_build_object('state','pending','slot_id',sl.id,'request_id',sl.request_id);
 END IF;
 IF st.retry_at>now_at THEN
  PERFORM scheduler_event(s,st.revision_id,NULL,'deferred','retry:'||st.last_slot,jsonb_build_object('reason','backoff','until',st.retry_at));
  RETURN jsonb_build_object('state','deferred','reason','backoff','until',st.retry_at);
 END IF;
 k:=floor(extract(epoch FROM now_at-(c->>'anchor')::TIMESTAMPTZ)/(c->>'cadence_seconds')::INT)::BIGINT;
 IF k<0 OR k<=st.last_slot THEN RETURN jsonb_build_object('state','not_due'); END IF;
 SELECT * INTO rev FROM filing_schedule_revisions WHERE schedule_id=s AND first_slot<=k ORDER BY epoch DESC LIMIT 1;
 due:=scheduler_due(s,rev.id,k);
 IF due>now_at THEN
  k:=k-1;
  IF k<0 OR k<=st.last_slot THEN RETURN jsonb_build_object('state','not_due'); END IF;
  SELECT * INTO rev FROM filing_schedule_revisions WHERE schedule_id=s AND first_slot<=k ORDER BY epoch DESC LIMIT 1;
  due:=scheduler_due(s,rev.id,k);
 END IF;
 nominal:=(c->>'anchor')::TIMESTAMPTZ+make_interval(secs=>k*(c->>'cadence_seconds')::DOUBLE PRECISION);
 IF (nominal AT TIME ZONE 'UTC')::DATE NOT BETWEEN (c#>>'{plan,inventory_start}')::DATE AND (c#>>'{plan,inventory_end}')::DATE THEN
  PERFORM scheduler_event(s,st.revision_id,NULL,'blocked','rebase:'||st.revision_id||':'||'cutoff',
   jsonb_build_object('version','sec-filing-schedule-block-v1','reason','rebase_required','mismatch','cutoff_outside_scope',
   'proposed_slot',k,'cutoff',nominal,'baseline',st.baseline,'requires_owner_review',true));
  RETURN jsonb_build_object('state','rebase_required','reason','cutoff_outside_scope');
 END IF;
 units:=3*jsonb_array_length(c#>'{plan,resources}')*(c->>'max_attempts')::INT;
 IF scheduler_budget(s)+units>(c->>'budget_units')::INT THEN
  PERFORM scheduler_event(s,st.revision_id,NULL,'deferred','budget:'||st.revision_id||':'||st.last_slot,
   jsonb_build_object('reason','budget','reserved',scheduler_budget(s),'capacity',c->'budget_units'));
  RETURN jsonb_build_object('state','deferred','reason','budget');
 END IF;
 p:=jsonb_set(jsonb_set(c->'plan','{baseline}',st.baseline),'{cutoff}',to_jsonb(to_char(nominal AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')));
 -- Never use D4a's reduced scope helper for schedule equality.
 IF p-ARRAY['cutoff','baseline'] IS DISTINCT FROM (c->'plan')-ARRAY['cutoff','baseline'] THEN
  RAISE EXCEPTION 'schedule scope mismatch' USING ERRCODE='23514'; END IF;
 key:='sec-schedule-v1:'||s||':'||k;
 req:=workflow_enqueue_monitor(base.workspace_id,base.security_id,key,jsonb_build_object('plan',p,'max_attempts',c->'max_attempts'));
 INSERT INTO filing_schedule_slots(id,schedule_id,revision_id,slot_index,nominal_at,due_at,plan,plan_hash,request_id,request_key,reserved_units)
 VALUES(gen_random_uuid(),s,rev.id,k,nominal,due,p,scheduler_hash(p),(req->>'request_id')::UUID,key,units) RETURNING * INTO sl;
 IF k>st.last_slot+1 THEN
  PERFORM scheduler_event(s,st.revision_id,NULL,'missed_range','missed:'||(st.last_slot+1)||':'||(k-1),
   jsonb_build_object('first',st.last_slot+1,'last',k-1,'count',k-st.last_slot-1,'reason','no_historical_check'));
 END IF;
 UPDATE filing_schedule_state SET last_slot=k,unresolved_slot=sl.id WHERE schedule_id=s;
 PERFORM scheduler_event(s,rev.id,sl.id,'materialized','slot:'||k,jsonb_build_object('request_id',sl.request_id,'plan_hash',sl.plan_hash,'baseline',st.baseline));
 RETURN jsonb_build_object('state','pending','slot_id',sl.id,'request_id',sl.request_id);
END $$;
CREATE FUNCTION scheduler_request_allowed(request UUID) RETURNS BOOLEAN LANGUAGE plpgsql
 SET search_path=public,pg_temp AS $$
DECLARE sl filing_schedule_slots%ROWTYPE; st filing_schedule_state%ROWTYPE; c JSONB; p JSONB;
BEGIN
 SELECT * INTO sl FROM filing_schedule_slots WHERE request_id=request;
 IF NOT FOUND THEN RETURN TRUE; END IF;
 PERFORM scheduler_lock(sl.schedule_id);
 SELECT * INTO st FROM filing_schedule_state WHERE schedule_id=sl.schedule_id;
 SELECT config INTO c FROM filing_schedule_revisions WHERE id=st.revision_id;
 SELECT filing_monitor_plan INTO p FROM analysis_requests WHERE id=request;
 RETURN (c->>'active')::BOOLEAN AND st.rebase_reason IS NULL AND st.unresolved_slot=sl.id
 AND scheduler_now() AT TIME ZONE 'UTC'<((c#>>'{plan,inventory_end}')::DATE+1)::TIMESTAMP
 AND p=sl.plan AND p-ARRAY['cutoff','baseline']=(c->'plan')-ARRAY['cutoff','baseline']
 AND p->'baseline'=st.baseline AND scheduler_budget(sl.schedule_id)<=(c->>'budget_units')::INT;
END $$;
ALTER FUNCTION workflow_retry(JSONB,TEXT,INTEGER) RENAME TO workflow_retry_d4a;
REVOKE ALL ON FUNCTION workflow_retry_d4a(JSONB,TEXT,INTEGER) FROM PUBLIC,equity_runtime;
CREATE FUNCTION workflow_retry(p_lease JSONB,p_error TEXT,p_delay INTEGER) RETURNS UUID
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE request UUID; attempt INTEGER; schedule UUID;
BEGIN
 IF p_delay IS NULL OR p_delay NOT BETWEEN 0 AND 86400 OR coalesce(length(trim(p_error)),0)=0 THEN
  RAISE EXCEPTION 'retry requires an error and bounded delay' USING ERRCODE='22023'; END IF;
 SELECT e.request_id,e.attempt_no,sl.schedule_id INTO request,attempt,schedule FROM analysis_executions e
 LEFT JOIN filing_schedule_slots sl ON sl.request_id=e.request_id WHERE e.id=(p_lease->>'execution_id')::UUID;
 IF schedule IS NOT NULL THEN
  PERFORM scheduler_lock(schedule);
  p_delay:=greatest(p_delay,least(3600,60*power(2,attempt-1)::INT));
 END IF;
 RETURN workflow_retry_d4a(p_lease,p_error,p_delay);
END $$;
-- Preserve the exact applied D4a entry points for empty downgrade; revoke bypass access.
ALTER FUNCTION workflow_claim_monitor(TEXT,INTEGER,UUID) RENAME TO workflow_claim_monitor_d4a;
REVOKE ALL ON FUNCTION workflow_claim_monitor_d4a(TEXT,INTEGER,UUID) FROM PUBLIC,equity_runtime;
CREATE FUNCTION workflow_claim_monitor(p_worker TEXT,p_seconds INTEGER,p_request UUID DEFAULT NULL) RETURNS JSONB
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE candidate UUID; result JSONB; execution analysis_executions%ROWTYPE;
BEGIN
 IF p_worker IS NULL OR length(trim(p_worker)) NOT BETWEEN 1 AND 200
 OR p_seconds IS NULL OR p_seconds NOT BETWEEN 1 AND 3600 THEN
  RAISE EXCEPTION 'invalid worker or lease duration' USING ERRCODE='22023'; END IF;
 FOR candidate IN SELECT r.id FROM analysis_requests r JOIN analysis_request_state st ON st.request_id=r.id
 JOIN analysis_executions e ON e.id=st.current_execution_id
 WHERE r.trigger='sec_filing_monitor' AND (p_request IS NULL OR r.id=p_request) AND st.terminal_outcome IS NULL
 AND ((e.state='queued' AND e.available_at<=clock_timestamp()) OR (e.state='running' AND e.lease_expires_at<=clock_timestamp()))
 ORDER BY r.workspace_id,e.available_at,r.request_sequence LOOP
  IF scheduler_request_allowed(candidate) THEN
   IF EXISTS(SELECT 1 FROM filing_schedule_slots WHERE request_id=candidate) THEN
    PERFORM 1 FROM analysis_request_state WHERE request_id=candidate FOR UPDATE;
    SELECT e.* INTO execution FROM analysis_executions e JOIN analysis_request_state st ON st.current_execution_id=e.id
     WHERE st.request_id=candidate FOR UPDATE OF e;
    IF execution.state='running' AND execution.lease_expires_at<=clock_timestamp() THEN
     PERFORM workflow_close_retry(execution.id,'lease_expired',least(3600,60*power(2,execution.attempt_no-1)::INT));
     CONTINUE;
    END IF;
   END IF;
   result:=workflow_claim_monitor_d4a(p_worker,p_seconds,candidate);
   IF result IS NOT NULL THEN RETURN result; END IF;
  END IF;
 END LOOP;
 RETURN NULL;
END $$;
ALTER FUNCTION ingestion_dispatch(JSONB,UUID,TIMESTAMPTZ) RENAME TO ingestion_dispatch_d4a;
REVOKE ALL ON FUNCTION ingestion_dispatch_d4a(JSONB,UUID,TIMESTAMPTZ) FROM PUBLIC,equity_runtime;
CREATE FUNCTION ingestion_dispatch(p_lease JSONB,p_attempt UUID,p_requested_at TIMESTAMPTZ) RETURNS BOOLEAN
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE request UUID; sl filing_schedule_slots%ROWTYPE; used INTEGER;
BEGIN
 SELECT e.request_id INTO request FROM source_fetch_attempts a JOIN analysis_stage_attempts st ON st.id=a.stage_attempt_id
 JOIN analysis_executions e ON e.id=st.execution_id WHERE a.id=p_attempt;
 IF scheduler_request_allowed(request) IS DISTINCT FROM TRUE THEN RAISE EXCEPTION 'scheduled dispatch blocked' USING ERRCODE='55000'; END IF;
 SELECT * INTO sl FROM filing_schedule_slots WHERE request_id=request;
 IF FOUND THEN
  SELECT count(*) INTO used FROM source_fetch_attempts a JOIN analysis_stage_attempts st ON st.id=a.stage_attempt_id
  JOIN analysis_executions e ON e.id=st.execution_id WHERE e.request_id=request AND a.requested_at IS NOT NULL;
  IF used>=sl.reserved_units THEN RAISE EXCEPTION 'schedule attempt budget exhausted' USING ERRCODE='55000'; END IF;
 END IF;
 RETURN ingestion_dispatch_d4a(p_lease,p_attempt,p_requested_at);
END $$;
"""

TABLES = ("filing_schedules", "filing_schedule_revisions", "filing_schedule_slots", "filing_schedule_events")


def upgrade() -> None:
    op.execute(SQL)
    for table in TABLES:
        op.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION evidence_immutable()")
        op.execute(f"CREATE TRIGGER {table}_no_truncate BEFORE TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION evidence_immutable()")
    op.execute("""
    REVOKE ALL ON filing_schedules,filing_schedule_revisions,filing_schedule_slots,filing_schedule_state,filing_schedule_events FROM PUBLIC,equity_runtime;
    GRANT SELECT ON filing_schedules,filing_schedule_revisions,filing_schedule_slots,filing_schedule_state,filing_schedule_events TO equity_runtime;
    REVOKE ALL ON FUNCTION scheduler_now(),scheduler_hash(JSONB),scheduler_valid(JSONB),scheduler_event(UUID,UUID,UUID,TEXT,TEXT,JSONB),
    scheduler_lock(UUID),scheduler_due(UUID,UUID,BIGINT),scheduler_create(UUID,UUID,TEXT,JSONB,TEXT),scheduler_revise(UUID,INTEGER,TEXT,JSONB,TEXT),
    scheduler_baseline_guard(),scheduler_budget(UUID),scheduler_reconcile(UUID),scheduler_tick(UUID),scheduler_request_allowed(UUID) FROM PUBLIC,equity_runtime;
    GRANT EXECUTE ON FUNCTION scheduler_tick(UUID),scheduler_due(UUID,UUID,BIGINT),scheduler_budget(UUID),scheduler_now() TO equity_runtime;
    REVOKE ALL ON FUNCTION workflow_retry(JSONB,TEXT,INTEGER),workflow_claim_monitor(TEXT,INTEGER,UUID),ingestion_dispatch(JSONB,UUID,TIMESTAMPTZ) FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION workflow_retry(JSONB,TEXT,INTEGER),workflow_claim_monitor(TEXT,INTEGER,UUID),ingestion_dispatch(JSONB,UUID,TIMESTAMPTZ) TO equity_runtime;
    """)


def downgrade() -> None:
    op.execute("""
    DO $$ BEGIN IF EXISTS(SELECT 1 FROM filing_schedules) THEN
     RAISE EXCEPTION 'refusing to discard schedule history' USING ERRCODE='55000'; END IF; END $$;
    DROP FUNCTION workflow_retry(JSONB,TEXT,INTEGER),ingestion_dispatch(JSONB,UUID,TIMESTAMPTZ),workflow_claim_monitor(TEXT,INTEGER,UUID);
    ALTER FUNCTION workflow_retry_d4a(JSONB,TEXT,INTEGER) RENAME TO workflow_retry;
    ALTER FUNCTION ingestion_dispatch_d4a(JSONB,UUID,TIMESTAMPTZ) RENAME TO ingestion_dispatch;
    ALTER FUNCTION workflow_claim_monitor_d4a(TEXT,INTEGER,UUID) RENAME TO workflow_claim_monitor;
    GRANT EXECUTE ON FUNCTION workflow_retry(JSONB,TEXT,INTEGER),workflow_claim_monitor(TEXT,INTEGER,UUID),ingestion_dispatch(JSONB,UUID,TIMESTAMPTZ) TO equity_runtime;
    DROP FUNCTION scheduler_tick(UUID),scheduler_reconcile(UUID),scheduler_request_allowed(UUID),scheduler_create(UUID,UUID,TEXT,JSONB,TEXT),
    scheduler_revise(UUID,INTEGER,TEXT,JSONB,TEXT),scheduler_due(UUID,UUID,BIGINT),scheduler_budget(UUID),scheduler_event(UUID,UUID,UUID,TEXT,TEXT,JSONB),scheduler_lock(UUID);
    DROP TABLE filing_schedule_events,filing_schedule_state,filing_schedule_slots,filing_schedule_revisions,filing_schedules;
    DROP FUNCTION scheduler_baseline_guard(),scheduler_valid(JSONB),scheduler_hash(JSONB),scheduler_now();
    """)
