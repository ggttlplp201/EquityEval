"""Durable watchlists, immutable requests and fenced execution attempts.

Revision ID: 0002_watchlist
Revises: 0001_evidence
"""

from alembic import op

revision = "0002_watchlist"
down_revision = "0001_evidence"
branch_labels = None
depends_on = None

SQL = r"""
CREATE SEQUENCE workflow_request_sequence;
CREATE TABLE workspaces (
    id UUID PRIMARY KEY, name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    display_timezone TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE watchlists (
    id UUID PRIMARY KEY, workspace_id UUID NOT NULL REFERENCES workspaces(id),
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
ALTER TABLE security_identifiers ADD CONSTRAINT workflow_quote_security UNIQUE (id, security_id);
CREATE TABLE watchlist_memberships (
    id UUID PRIMARY KEY, watchlist_id UUID NOT NULL REFERENCES watchlists(id),
    security_id UUID NOT NULL REFERENCES securities(id), quote_identifier_id UUID NOT NULL,
    added_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(), removed_at TIMESTAMPTZ,
    generation INTEGER NOT NULL CHECK (generation > 0),
    FOREIGN KEY (quote_identifier_id, security_id) REFERENCES security_identifiers(id, security_id),
    UNIQUE (watchlist_id, security_id, generation),
    CHECK (removed_at IS NULL OR removed_at >= added_at)
);
CREATE UNIQUE INDEX workflow_active_membership
    ON watchlist_memberships(watchlist_id, security_id) WHERE removed_at IS NULL;
CREATE TABLE analysis_requests (
    id UUID PRIMARY KEY, workspace_id UUID NOT NULL REFERENCES workspaces(id),
    security_id UUID NOT NULL REFERENCES securities(id), quote_identifier_id UUID NOT NULL,
    trigger TEXT NOT NULL CHECK (trigger IN ('watchlist_add', 'manual_refresh')),
    membership_id UUID REFERENCES watchlist_memberships(id),
    parent_request_id UUID REFERENCES analysis_requests(id),
    request_sequence BIGINT NOT NULL DEFAULT nextval('workflow_request_sequence'),
    idempotency_key TEXT NOT NULL CHECK (length(idempotency_key) BETWEEN 1 AND 200),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    history_mode TEXT NOT NULL CHECK (history_mode IN
        ('latest_reported','as_filed_by_date','original_as_filed')),
    filed_cutoff DATE, requested_periods JSONB NOT NULL,
    retrieval_policy TEXT NOT NULL CHECK (retrieval_policy IN ('refresh','pinned_vintage')),
    retrieval_vintage TIMESTAMPTZ,
    max_attempts INTEGER NOT NULL CHECK (max_attempts BETWEEN 1 AND 10),
    request_parameters_hash TEXT NOT NULL CHECK (request_parameters_hash ~ '^[0-9a-f]{64}$'),
    FOREIGN KEY (quote_identifier_id, security_id) REFERENCES security_identifiers(id, security_id),
    UNIQUE (workspace_id, idempotency_key), UNIQUE (workspace_id, security_id, request_sequence),
    CHECK ((trigger = 'watchlist_add') = (membership_id IS NOT NULL)),
    CHECK (id <> parent_request_id),
    CHECK (history_mode <> 'as_filed_by_date' OR filed_cutoff IS NOT NULL),
    CHECK (history_mode <> 'latest_reported' OR filed_cutoff IS NULL),
    CHECK ((retrieval_policy = 'pinned_vintage') = (retrieval_vintage IS NOT NULL)),
    CHECK (jsonb_typeof(requested_periods) = 'array')
);
CREATE UNIQUE INDEX workflow_membership_initial_request
    ON analysis_requests(membership_id) WHERE trigger = 'watchlist_add';
CREATE TABLE analysis_request_keys (
    workspace_id UUID NOT NULL REFERENCES workspaces(id), idempotency_key TEXT NOT NULL,
    request_id UUID NOT NULL REFERENCES analysis_requests(id),
    parameters_hash TEXT NOT NULL CHECK (parameters_hash ~ '^[0-9a-f]{64}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (workspace_id, idempotency_key),
    CHECK (length(idempotency_key) BETWEEN 1 AND 200)
);
CREATE TABLE analysis_executions (
    id UUID PRIMARY KEY, request_id UUID NOT NULL REFERENCES analysis_requests(id),
    attempt_no INTEGER NOT NULL CHECK (attempt_no > 0),
    state TEXT NOT NULL CHECK (state IN ('queued','running','waiting_for_input',
        'retry_scheduled','completed','completed_with_gaps','failed','cancelled')),
    current_stage TEXT, available_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    lease_owner TEXT, lease_expires_at TIMESTAMPTZ, fencing_token BIGINT NOT NULL DEFAULT 0,
    cancellation_requested_at TIMESTAMPTZ, started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ,
    error_code TEXT, error_detail TEXT,
    UNIQUE (request_id, attempt_no), UNIQUE (id, request_id),
    CHECK (fencing_token >= 0),
    CHECK ((state='running') = (lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL)),
    CHECK (finished_at IS NULL OR state NOT IN ('queued','running'))
);
CREATE INDEX workflow_due_executions ON analysis_executions(available_at)
    WHERE state IN ('queued','running');
CREATE TABLE analysis_request_state (
    request_id UUID PRIMARY KEY REFERENCES analysis_requests(id),
    current_execution_id UUID NOT NULL,
    attempt_epoch BIGINT NOT NULL CHECK (attempt_epoch > 0),
    terminal_outcome TEXT CHECK (terminal_outcome IN
        ('completed','completed_with_gaps','waiting_for_input','failed','cancelled')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (current_execution_id, request_id)
        REFERENCES analysis_executions(id, request_id)
);
CREATE TABLE analysis_stage_attempts (
    id UUID PRIMARY KEY, execution_id UUID NOT NULL REFERENCES analysis_executions(id),
    stage_key TEXT NOT NULL CHECK (stage_key ~ '^[a-z][a-z0-9_]{0,79}$'),
    attempt_no INTEGER NOT NULL CHECK (attempt_no > 0),
    state TEXT NOT NULL CHECK (state IN
        ('running','completed','blocked','unsupported','failed','cancelled')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(), finished_at TIMESTAMPTZ,
    input_manifest JSONB, result_reference TEXT, error_code TEXT, error_detail TEXT,
    UNIQUE (execution_id, stage_key, attempt_no),
    CHECK ((state='running') = (finished_at IS NULL)),
    CHECK (state IN ('running','completed') OR length(trim(error_code)) > 0),
    CHECK (input_manifest IS NULL OR jsonb_typeof(input_manifest)='object')
);
CREATE UNIQUE INDEX workflow_running_stage ON analysis_stage_attempts(execution_id, stage_key)
    WHERE state='running';
CREATE TABLE execution_events (
    id UUID PRIMARY KEY, execution_id UUID NOT NULL REFERENCES analysis_executions(id),
    event_sequence BIGINT NOT NULL CHECK (event_sequence > 0),
    event_kind TEXT NOT NULL, occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    detail JSONB NOT NULL DEFAULT '{}', UNIQUE (execution_id, event_sequence)
);

CREATE FUNCTION workflow_guard_history() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'workflow history is immutable' USING ERRCODE='55000';
END $$;
CREATE TRIGGER workflow_requests_immutable BEFORE UPDATE OR DELETE ON analysis_requests
    FOR EACH ROW EXECUTE FUNCTION workflow_guard_history();
CREATE TRIGGER workflow_keys_immutable BEFORE UPDATE OR DELETE ON analysis_request_keys
    FOR EACH ROW EXECUTE FUNCTION workflow_guard_history();
CREATE TRIGGER workflow_events_immutable BEFORE UPDATE OR DELETE ON execution_events
    FOR EACH ROW EXECUTE FUNCTION workflow_guard_history();
CREATE FUNCTION workflow_guard_stage() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.state <> 'running' OR NEW.id <> OLD.id OR NEW.execution_id <> OLD.execution_id
        OR NEW.stage_key <> OLD.stage_key OR NEW.attempt_no <> OLD.attempt_no
        OR NEW.started_at <> OLD.started_at THEN
        RAISE EXCEPTION 'finished stage history is immutable' USING ERRCODE='55000';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER workflow_stage_guard BEFORE UPDATE ON analysis_stage_attempts
    FOR EACH ROW EXECUTE FUNCTION workflow_guard_stage();
CREATE FUNCTION workflow_guard_membership() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (to_jsonb(NEW)-'removed_at') IS DISTINCT FROM (to_jsonb(OLD)-'removed_at')
       OR OLD.removed_at IS NOT NULL OR NEW.removed_at IS NULL THEN
        RAISE EXCEPTION 'membership history can only be ended once' USING ERRCODE='55000';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER workflow_membership_guard BEFORE UPDATE ON watchlist_memberships
    FOR EACH ROW EXECUTE FUNCTION workflow_guard_membership();
DO $$ DECLARE tab TEXT; BEGIN
    FOREACH tab IN ARRAY ARRAY['workspaces','watchlists','watchlist_memberships',
        'analysis_requests','analysis_request_keys','analysis_request_state',
        'analysis_executions','analysis_stage_attempts','execution_events'] LOOP
        EXECUTE format('CREATE TRIGGER workflow_no_truncate BEFORE TRUNCATE ON %I '
            'FOR EACH STATEMENT EXECUTE FUNCTION workflow_guard_history()',tab);
    END LOOP;
END $$;

CREATE FUNCTION workflow_validate_request() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE item JSONB; start_day DATE; end_day DATE;
BEGIN
    IF NEW.membership_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM watchlist_memberships m JOIN watchlists w ON w.id=m.watchlist_id
        WHERE m.id=NEW.membership_id AND m.security_id=NEW.security_id
          AND m.quote_identifier_id=NEW.quote_identifier_id AND w.workspace_id=NEW.workspace_id
    ) THEN
        RAISE EXCEPTION 'membership does not match workspace/security/quote' USING ERRCODE='23514';
    END IF;
    IF NEW.parent_request_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM analysis_requests r WHERE r.id=NEW.parent_request_id
          AND r.workspace_id=NEW.workspace_id AND r.security_id=NEW.security_id
    ) THEN
        RAISE EXCEPTION 'parent request does not match workspace/security' USING ERRCODE='23514';
    END IF;
    IF jsonb_array_length(NEW.requested_periods) > 200 THEN
        RAISE EXCEPTION 'too many requested periods' USING ERRCODE='22023';
    END IF;
    FOR item IN SELECT value FROM jsonb_array_elements(NEW.requested_periods) LOOP
        IF jsonb_typeof(item)<>'object' OR item-'kind'-'start'-'end'<>'{}'::jsonb
            OR NOT (item ?& ARRAY['kind','start','end']) THEN
            RAISE EXCEPTION 'invalid requested period shape' USING ERRCODE='22023';
        END IF;
        start_day := (item->>'start')::DATE; end_day := (item->>'end')::DATE;
        IF end_day IS NULL OR NOT isfinite(end_day)
            OR (start_day IS NOT NULL AND NOT isfinite(start_day))
            OR item->>'kind' IS NULL OR item->>'kind' NOT IN ('instant','duration')
            OR (item->>'kind'='instant' AND start_day IS NOT NULL)
            OR (item->>'kind'='duration' AND (start_day IS NULL OR start_day>end_day)) THEN
            RAISE EXCEPTION 'invalid requested period dates' USING ERRCODE='22023';
        END IF;
    END LOOP;
    RETURN NEW;
END $$;
CREATE TRIGGER workflow_request_links BEFORE INSERT ON analysis_requests
    FOR EACH ROW EXECUTE FUNCTION workflow_validate_request();
CREATE FUNCTION workflow_validate_key() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM analysis_requests WHERE id=NEW.request_id
                   AND workspace_id=NEW.workspace_id) THEN
        RAISE EXCEPTION 'request key workspace mismatch' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER workflow_key_links BEFORE INSERT ON analysis_request_keys
    FOR EACH ROW EXECUTE FUNCTION workflow_validate_key();

CREATE FUNCTION workflow_event(p_execution UUID,p_kind TEXT,p_detail JSONB DEFAULT '{}')
RETURNS VOID LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
    INSERT INTO execution_events(id,execution_id,event_sequence,event_kind,detail)
    SELECT gen_random_uuid(),p_execution,coalesce(max(event_sequence),0)+1,p_kind,p_detail
    FROM execution_events WHERE execution_id=p_execution;
END $$;
CREATE FUNCTION workflow_request_result(p_request UUID) RETURNS JSONB
LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
    SELECT jsonb_build_object('request_id',r.id,'request_sequence',r.request_sequence,
        'membership_id',r.membership_id,'generation',m.generation)
    FROM analysis_requests r LEFT JOIN watchlist_memberships m ON m.id=r.membership_id
    WHERE r.id=p_request
$$;
CREATE FUNCTION workflow_lease_result(p_execution UUID) RETURNS JSONB
LANGUAGE sql STABLE SET search_path=public,pg_temp AS $$
    SELECT jsonb_build_object('request_id',e.request_id,'execution_id',e.id,
        'epoch',s.attempt_epoch,'fencing_token',e.fencing_token,
        'worker_id',e.lease_owner,'expires_at',e.lease_expires_at)
    FROM analysis_executions e JOIN analysis_request_state s ON s.request_id=e.request_id
    WHERE e.id=p_execution
$$;

CREATE FUNCTION workflow_create_workspace(p_name TEXT,p_timezone TEXT) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE workspace UUID:=gen_random_uuid(); watchlist UUID:=gen_random_uuid();
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_timezone_names WHERE name=p_timezone) THEN
        RAISE EXCEPTION 'unknown display timezone' USING ERRCODE='22023';
    END IF;
    INSERT INTO workspaces(id,name,display_timezone) VALUES(workspace,p_name,p_timezone);
    INSERT INTO watchlists(id,workspace_id,name) VALUES(watchlist,workspace,'Watchlist');
    RETURN jsonb_build_object('workspace_id',workspace,'watchlist_id',watchlist);
END $$;

CREATE FUNCTION workflow_enqueue(
    p_workspace UUID,p_watchlist UUID,p_security UUID,p_quote UUID,p_key TEXT,
    p_options JSONB,p_trigger TEXT,p_parent UUID
) RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE workspace UUID; membership UUID; request UUID; execution UUID; generation INTEGER;
    options JSONB; params_hash TEXT; existing analysis_request_keys%ROWTYPE;
    existing_membership watchlist_memberships%ROWTYPE; vintage TIMESTAMPTZ;
BEGIN
    IF p_trigger NOT IN ('watchlist_add','manual_refresh') OR p_trigger IS NULL
        OR p_key IS NULL OR length(p_key) NOT BETWEEN 1 AND 200
        OR p_options IS NULL OR jsonb_typeof(p_options)<>'object'
        OR p_options-'history_mode'-'filed_cutoff'-'requested_periods'-'retrieval_vintage'-'max_attempts'
            <> '{}'::jsonb THEN
        RAISE EXCEPTION 'unknown request option or invalid intent' USING ERRCODE='22023';
    END IF;
    IF p_trigger='watchlist_add' THEN
        IF p_workspace IS NOT NULL OR p_watchlist IS NULL OR p_parent IS NOT NULL THEN
            RAISE EXCEPTION 'add requires a watchlist and no manual parent' USING ERRCODE='22023';
        END IF;
        SELECT workspace_id INTO workspace FROM watchlists WHERE id=p_watchlist;
    ELSE
        IF p_workspace IS NULL OR p_watchlist IS NOT NULL THEN
            RAISE EXCEPTION 'refresh requires a workspace' USING ERRCODE='22023';
        END IF;
        workspace:=p_workspace;
    END IF;
    PERFORM 1 FROM workspaces WHERE id=workspace FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'unknown workspace/watchlist' USING ERRCODE='23503';
    END IF;
    IF p_options->>'retrieval_vintage' IS NOT NULL
        AND p_options->>'retrieval_vintage' !~ '(Z|[+-][0-9]{2}:[0-9]{2})$' THEN
        RAISE EXCEPTION 'retrieval vintage requires explicit timezone' USING ERRCODE='22023';
    END IF;
    vintage := (p_options->>'retrieval_vintage')::TIMESTAMPTZ;
    IF vintage IS NOT NULL AND NOT isfinite(vintage) THEN
        RAISE EXCEPTION 'retrieval vintage must be finite' USING ERRCODE='22023';
    END IF;
    options := jsonb_build_object(
        'history_mode',coalesce(p_options->>'history_mode','latest_reported'),
        'filed_cutoff',(p_options->>'filed_cutoff')::DATE,
        'requested_periods',coalesce(p_options->'requested_periods','[]'::jsonb),
        'retrieval_vintage',CASE WHEN vintage IS NULL THEN NULL
            ELSE to_char(vintage AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"') END,
        'max_attempts',coalesce((p_options->>'max_attempts')::INTEGER,3));
    params_hash := encode(sha256(convert_to(jsonb_build_object(
        'workspace',workspace,'watchlist',p_watchlist,'security',p_security,'quote',p_quote,
        'trigger',p_trigger,'parent',p_parent,'options',options)::TEXT,'UTF8')),'hex');
    SELECT * INTO existing FROM analysis_request_keys
        WHERE workspace_id=workspace AND idempotency_key=p_key;
    IF FOUND THEN
        IF existing.parameters_hash<>params_hash THEN
            RAISE EXCEPTION 'idempotency key reused with different parameters' USING ERRCODE='22023';
        END IF;
        RETURN workflow_request_result(existing.request_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM security_identifiers WHERE id=p_quote AND security_id=p_security) THEN
        RAISE EXCEPTION 'quote does not belong to security' USING ERRCODE='23503';
    END IF;
    -- A new request chooses a listing valid now. Historical prices gain their
    -- own explicit quote/session identity with S4; filed cutoff is not a quote date.
    -- Pin the immutable raw quote ID, but check the current interval projection.
    -- SHARE serializes enqueue with a concurrent interval closure without
    -- changing previously committed requests or transport replay results.
    PERFORM 1 FROM security_identifier_validity WHERE quote_identifier_id=p_quote
        AND security_id=p_security
        AND valid_from <= (clock_timestamp() AT TIME ZONE 'UTC')::DATE
        AND (current_valid_to IS NULL
             OR current_valid_to > (clock_timestamp() AT TIME ZONE 'UTC')::DATE)
        FOR SHARE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'quote identifier is not currently valid' USING ERRCODE='23514';
    END IF;
    IF p_trigger='watchlist_add' THEN
        SELECT * INTO existing_membership FROM watchlist_memberships
            WHERE watchlist_id=p_watchlist AND security_id=p_security AND removed_at IS NULL;
        IF FOUND THEN
            IF existing_membership.quote_identifier_id<>p_quote THEN
                RAISE EXCEPTION 'existing stock has another quote; use explicit refresh'
                    USING ERRCODE='22023';
            END IF;
            SELECT id INTO request FROM analysis_requests
                WHERE membership_id=existing_membership.id AND trigger='watchlist_add';
            IF request IS NULL THEN
                RAISE EXCEPTION 'membership has no atomic initial request' USING ERRCODE='55000';
            END IF;
            IF (SELECT request_parameters_hash FROM analysis_requests WHERE id=request) <> params_hash THEN
                RAISE EXCEPTION 'existing Add has different options; use explicit refresh'
                    USING ERRCODE='22023';
            END IF;
            INSERT INTO analysis_request_keys(workspace_id,idempotency_key,request_id,parameters_hash)
                VALUES(workspace,p_key,request,params_hash);
            RETURN workflow_request_result(request);
        END IF;
        SELECT coalesce(max(m.generation),0)+1 INTO generation FROM watchlist_memberships m
            WHERE m.watchlist_id=p_watchlist AND m.security_id=p_security;
        membership:=gen_random_uuid();
        INSERT INTO watchlist_memberships(id,watchlist_id,security_id,quote_identifier_id,generation)
            VALUES(membership,p_watchlist,p_security,p_quote,generation);
    END IF;
    request:=gen_random_uuid(); execution:=gen_random_uuid();
    INSERT INTO analysis_requests(id,workspace_id,security_id,quote_identifier_id,trigger,
        membership_id,parent_request_id,idempotency_key,history_mode,filed_cutoff,requested_periods,
        retrieval_policy,retrieval_vintage,max_attempts,request_parameters_hash)
    VALUES(request,workspace,p_security,p_quote,p_trigger,membership,p_parent,p_key,
        options->>'history_mode',(options->>'filed_cutoff')::DATE,options->'requested_periods',
        CASE WHEN vintage IS NULL THEN 'refresh' ELSE 'pinned_vintage' END,vintage,
        (options->>'max_attempts')::INTEGER,params_hash);
    INSERT INTO analysis_request_keys(workspace_id,idempotency_key,request_id,parameters_hash)
        VALUES(workspace,p_key,request,params_hash);
    INSERT INTO analysis_executions(id,request_id,attempt_no,state)
        VALUES(execution,request,1,'queued');
    INSERT INTO analysis_request_state(request_id,current_execution_id,attempt_epoch)
        VALUES(request,execution,1);
    PERFORM workflow_event(execution,'queued',jsonb_build_object('trigger',p_trigger));
    RETURN workflow_request_result(request);
END $$;

CREATE FUNCTION workflow_remove_membership(p_membership UUID) RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE workspace UUID;
BEGIN
    SELECT w.workspace_id INTO workspace FROM watchlist_memberships m
        JOIN watchlists w ON w.id=m.watchlist_id WHERE m.id=p_membership;
    IF workspace IS NULL THEN
        RAISE EXCEPTION 'unknown membership' USING ERRCODE='23503';
    END IF;
    PERFORM 1 FROM workspaces WHERE id=workspace FOR UPDATE;
    UPDATE watchlist_memberships SET removed_at=clock_timestamp()
        WHERE id=p_membership AND removed_at IS NULL;
    RETURN FOUND;
END $$;

CREATE FUNCTION workflow_locked_lease(p_lease JSONB) RETURNS analysis_executions
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE control analysis_request_state%ROWTYPE; execution analysis_executions%ROWTYPE;
BEGIN
    SELECT * INTO control FROM analysis_request_state
        WHERE request_id=(p_lease->>'request_id')::UUID FOR UPDATE;
    IF NOT FOUND OR control.terminal_outcome IS NOT NULL
        OR control.current_execution_id IS DISTINCT FROM (p_lease->>'execution_id')::UUID
        OR control.attempt_epoch IS DISTINCT FROM (p_lease->>'epoch')::BIGINT THEN
        RAISE EXCEPTION 'lease lost: request attempt superseded or terminal' USING ERRCODE='55000';
    END IF;
    SELECT * INTO execution FROM analysis_executions WHERE id=control.current_execution_id FOR UPDATE;
    IF execution.state<>'running'
        OR execution.lease_owner IS DISTINCT FROM p_lease->>'worker_id'
        OR execution.fencing_token IS DISTINCT FROM (p_lease->>'fencing_token')::BIGINT
        OR execution.lease_expires_at <= clock_timestamp()
        OR execution.cancellation_requested_at IS NOT NULL THEN
        RAISE EXCEPTION 'lease lost: worker expired or no longer owns execution' USING ERRCODE='55000';
    END IF;
    RETURN execution;
END $$;

CREATE FUNCTION workflow_close_retry(p_execution UUID,p_error TEXT,p_delay INTEGER) RETURNS UUID
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE previous analysis_executions%ROWTYPE; maximum INTEGER; following UUID;
BEGIN
    SELECT * INTO previous FROM analysis_executions WHERE id=p_execution;
    SELECT max_attempts INTO maximum FROM analysis_requests WHERE id=previous.request_id;
    UPDATE analysis_stage_attempts SET state='failed',finished_at=clock_timestamp(),error_code=p_error
        WHERE execution_id=p_execution AND state='running';
    UPDATE analysis_executions SET state='failed',finished_at=clock_timestamp(),error_code=p_error,
        lease_owner=NULL,lease_expires_at=NULL,current_stage=NULL WHERE id=p_execution;
    IF previous.attempt_no >= maximum THEN
        UPDATE analysis_request_state SET terminal_outcome='failed',attempt_epoch=attempt_epoch+1,
            updated_at=clock_timestamp() WHERE request_id=previous.request_id;
        PERFORM workflow_event(p_execution,'retry_exhausted',jsonb_build_object('error_code',p_error));
        RETURN NULL;
    END IF;
    following:=gen_random_uuid();
    INSERT INTO analysis_executions(id,request_id,attempt_no,state,available_at)
        VALUES(following,previous.request_id,previous.attempt_no+1,'queued',
            clock_timestamp()+make_interval(secs=>p_delay));
    UPDATE analysis_request_state SET current_execution_id=following,attempt_epoch=attempt_epoch+1,
        updated_at=clock_timestamp() WHERE request_id=previous.request_id;
    PERFORM workflow_event(p_execution,'retry_scheduled',
        jsonb_build_object('error_code',p_error,'next_execution_id',following,'delay_seconds',p_delay));
    PERFORM workflow_event(following,'queued',jsonb_build_object('previous_execution_id',p_execution));
    RETURN following;
END $$;

CREATE FUNCTION workflow_claim(p_worker TEXT,p_seconds INTEGER) RETURNS JSONB
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
END $$;

CREATE FUNCTION workflow_renew(p_lease JSONB,p_seconds INTEGER) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE execution analysis_executions%ROWTYPE;
BEGIN
    IF p_seconds IS NULL OR p_seconds NOT BETWEEN 1 AND 3600 THEN
        RAISE EXCEPTION 'invalid lease duration' USING ERRCODE='22023';
    END IF;
    execution:=workflow_locked_lease(p_lease);
    UPDATE analysis_executions SET lease_expires_at=clock_timestamp()+make_interval(secs=>p_seconds)
        WHERE id=execution.id;
    PERFORM workflow_event(execution.id,'lease_renewed');
    RETURN workflow_lease_result(execution.id);
END $$;

CREATE FUNCTION workflow_start_stage(p_lease JSONB,p_stage TEXT) RETURNS UUID
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE execution analysis_executions%ROWTYPE; stage UUID:=gen_random_uuid(); attempt INTEGER;
BEGIN
    execution:=workflow_locked_lease(p_lease);
    SELECT coalesce(max(attempt_no),0)+1 INTO attempt FROM analysis_stage_attempts
        WHERE execution_id=execution.id AND stage_key=p_stage;
    INSERT INTO analysis_stage_attempts(id,execution_id,stage_key,attempt_no,state)
        VALUES(stage,execution.id,p_stage,attempt,'running');
    UPDATE analysis_executions SET current_stage=p_stage WHERE id=execution.id;
    PERFORM workflow_event(execution.id,'stage_started',jsonb_build_object('stage_id',stage,'stage',p_stage));
    RETURN stage;
END $$;

CREATE FUNCTION workflow_finish_stage(
    p_lease JSONB,p_stage UUID,p_outcome TEXT,p_reason TEXT,p_reused UUID[]
) RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE execution analysis_executions%ROWTYPE; capture UUID;
BEGIN
    execution:=workflow_locked_lease(p_lease);
    IF p_outcome IS NULL OR p_outcome NOT IN ('completed','blocked','unsupported','failed','cancelled')
        OR (p_outcome<>'completed' AND coalesce(length(trim(p_reason)),0)=0) THEN
        RAISE EXCEPTION 'invalid stage outcome or missing reason' USING ERRCODE='22023';
    END IF;
    FOREACH capture IN ARRAY coalesce(p_reused,ARRAY[]::UUID[]) LOOP
        IF NOT EXISTS (SELECT 1 FROM source_captures WHERE id=capture
            AND http_status BETWEEN 200 AND 299 AND completed_at IS NOT NULL
            AND body_sha256 IS NOT NULL AND blob_key IS NOT NULL
            AND byte_count IS NOT NULL AND fetched_at IS NOT NULL) THEN
            RAISE EXCEPTION 'reused capture is missing or not successful' USING ERRCODE='23503';
        END IF;
    END LOOP;
    UPDATE analysis_stage_attempts SET state=p_outcome,finished_at=clock_timestamp(),
        error_code=p_reason,input_manifest=jsonb_build_object('reused_capture_ids',coalesce(p_reused,ARRAY[]::UUID[]))
        WHERE id=p_stage AND execution_id=execution.id AND state='running';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'stage is not an active stage of this execution' USING ERRCODE='55000';
    END IF;
    UPDATE analysis_executions SET current_stage=(SELECT stage_key FROM analysis_stage_attempts
        WHERE execution_id=execution.id AND state='running' ORDER BY started_at LIMIT 1)
        WHERE id=execution.id;
    PERFORM workflow_event(execution.id,'stage_finished',
        jsonb_build_object('stage_id',p_stage,'outcome',p_outcome,'reason',p_reason));
    RETURN TRUE;
END $$;

CREATE FUNCTION workflow_finish(p_lease JSONB,p_outcome TEXT,p_reason TEXT) RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE execution analysis_executions%ROWTYPE;
BEGIN
    execution:=workflow_locked_lease(p_lease);
    IF p_outcome IS NULL OR p_outcome NOT IN
        ('completed','completed_with_gaps','waiting_for_input','failed') THEN
        RAISE EXCEPTION 'invalid terminal outcome' USING ERRCODE='22023';
    END IF;
    IF EXISTS (SELECT 1 FROM analysis_stage_attempts WHERE execution_id=execution.id AND state='running') THEN
        RAISE EXCEPTION 'cannot finish while a stage is running' USING ERRCODE='55000';
    END IF;
    IF p_outcome='completed' AND EXISTS (SELECT 1 FROM analysis_stage_attempts
        WHERE execution_id=execution.id AND state<>'completed') THEN
        RAISE EXCEPTION 'a gapped stage cannot become a complete analysis' USING ERRCODE='55000';
    END IF;
    IF p_outcome IN ('failed','waiting_for_input') AND coalesce(length(trim(p_reason)),0)=0 THEN
        RAISE EXCEPTION 'terminal outcome requires a reason' USING ERRCODE='22023';
    END IF;
    UPDATE analysis_executions SET state=p_outcome,finished_at=clock_timestamp(),
        lease_owner=NULL,lease_expires_at=NULL,current_stage=NULL,error_code=p_reason WHERE id=execution.id;
    UPDATE analysis_request_state SET terminal_outcome=p_outcome,updated_at=clock_timestamp()
        WHERE request_id=execution.request_id;
    PERFORM workflow_event(execution.id,'finished',jsonb_build_object('outcome',p_outcome,'reason',p_reason));
    RETURN TRUE;
END $$;

CREATE FUNCTION workflow_retry(p_lease JSONB,p_error TEXT,p_delay INTEGER) RETURNS UUID
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE execution analysis_executions%ROWTYPE;
BEGIN
    IF p_delay IS NULL OR p_delay NOT BETWEEN 0 AND 86400
        OR coalesce(length(trim(p_error)),0)=0 THEN
        RAISE EXCEPTION 'retry requires an error and bounded delay' USING ERRCODE='22023';
    END IF;
    execution:=workflow_locked_lease(p_lease);
    RETURN workflow_close_retry(execution.id,p_error,p_delay);
END $$;

CREATE FUNCTION workflow_cancel(p_request UUID) RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE control analysis_request_state%ROWTYPE;
BEGIN
    SELECT * INTO control FROM analysis_request_state WHERE request_id=p_request FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'unknown request' USING ERRCODE='23503'; END IF;
    IF control.terminal_outcome IS NOT NULL THEN RETURN FALSE; END IF;
    UPDATE analysis_stage_attempts SET state='cancelled',finished_at=clock_timestamp(),error_code='user_cancelled'
        WHERE execution_id=control.current_execution_id AND state='running';
    UPDATE analysis_executions SET state='cancelled',finished_at=clock_timestamp(),
        cancellation_requested_at=clock_timestamp(),lease_owner=NULL,lease_expires_at=NULL,
        current_stage=NULL,error_code='user_cancelled' WHERE id=control.current_execution_id;
    UPDATE analysis_request_state SET terminal_outcome='cancelled',attempt_epoch=attempt_epoch+1,
        updated_at=clock_timestamp() WHERE request_id=p_request;
    PERFORM workflow_event(control.current_execution_id,'cancelled');
    RETURN TRUE;
END $$;

REVOKE ALL ON workspaces,watchlists,watchlist_memberships,analysis_requests,analysis_request_keys,
    analysis_executions,analysis_request_state,analysis_stage_attempts,execution_events FROM PUBLIC;
GRANT SELECT ON workspaces,watchlists,watchlist_memberships,analysis_requests,analysis_request_keys,
    analysis_executions,analysis_request_state,analysis_stage_attempts,execution_events TO equity_runtime;
REVOKE ALL ON SEQUENCE workflow_request_sequence FROM PUBLIC;
DO $$ DECLARE f RECORD; BEGIN
    FOR f IN SELECT oid::regprocedure AS signature,proname FROM pg_proc
        WHERE pronamespace='public'::regnamespace AND proname LIKE 'workflow\_%' ESCAPE '\' LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC',f.signature);
        IF f.proname IN ('workflow_create_workspace','workflow_enqueue','workflow_remove_membership',
            'workflow_claim','workflow_renew','workflow_start_stage','workflow_finish_stage',
            'workflow_finish','workflow_retry','workflow_cancel') THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO equity_runtime',f.signature);
        END IF;
    END LOOP;
END $$;
"""


def upgrade() -> None:
    op.execute(SQL)


def downgrade() -> None:
    op.execute(r"""
    DO $$ DECLARE f RECORD; BEGIN
        FOR f IN SELECT oid::regprocedure AS signature FROM pg_proc
            WHERE pronamespace='public'::regnamespace AND proname LIKE 'workflow\_%' ESCAPE '\' LOOP
            EXECUTE format('DROP FUNCTION IF EXISTS %s CASCADE',f.signature);
        END LOOP;
    END $$;
    DROP TABLE execution_events,analysis_stage_attempts,analysis_request_state,
        analysis_executions,analysis_request_keys,analysis_requests,watchlist_memberships,
        watchlists,workspaces;
    ALTER TABLE security_identifiers DROP CONSTRAINT workflow_quote_security;
    DROP SEQUENCE workflow_request_sequence;
    """)
