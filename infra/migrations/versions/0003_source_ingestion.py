"""Versioned source policies and committed, W1-fenced transport attempts."""

from alembic import op

revision = "0003_source_ingestion"
down_revision = "0002_watchlist"
branch_labels = None
depends_on = None

SQL = r"""
CREATE TABLE source_policy_revisions (
    id uuid PRIMARY KEY, source_id uuid NOT NULL REFERENCES sources(id),
    review_key text NOT NULL CHECK (btrim(review_key)<>''),
    licence_label text NOT NULL CHECK (btrim(licence_label)<>''),
    content_scope text NOT NULL CHECK (btrim(content_scope)<>''),
    redistribution_status text NOT NULL CHECK (redistribution_status IN ('allowed','prohibited','unknown')),
    permitted_use text NOT NULL CHECK (btrim(permitted_use)<>''),
    attribution_requirements text NOT NULL,
    terms_urls text[] NOT NULL CHECK (cardinality(terms_urls)>0 AND array_position(terms_urls,NULL) IS NULL),
    reviewed_at timestamptz NOT NULL CHECK (isfinite(reviewed_at)),
    reviewed_by text NOT NULL CHECK (btrim(reviewed_by)<>''),
    review_artifact_reference text NOT NULL CHECK (btrim(review_artifact_reference)<>''),
    review_artifact_sha256 text NOT NULL CHECK (review_artifact_sha256 ~ '^[0-9a-f]{64}$'),
    UNIQUE(source_id,review_key)
);
CREATE TABLE capture_policy_links (
    capture_id uuid PRIMARY KEY REFERENCES source_captures(id),
    policy_revision_id uuid NOT NULL REFERENCES source_policy_revisions(id)
);
CREATE INDEX capture_policy_links_policy_fk ON capture_policy_links(policy_revision_id);
CREATE VIEW source_capture_policy_status AS
    SELECT c.id AS capture_id,p.policy_revision_id,
           CASE WHEN p.capture_id IS NULL THEN 'legacy_unreviewed' ELSE 'reviewed' END AS review_status
    FROM source_captures c LEFT JOIN capture_policy_links p ON p.capture_id=c.id;

CREATE FUNCTION ingestion_header_evidence_valid(headers jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT headers IS NOT NULL AND jsonb_typeof(headers)='object' AND octet_length(headers::text)<=16384
       AND NOT EXISTS (SELECT FROM jsonb_each(headers) h WHERE h.key NOT IN
           ('content_type','content_encoding','etag','last_modified','retry_after','location')
           OR jsonb_typeof(h.value)<>'string' OR octet_length(h.value#>>'{}')>4096
           OR h.value#>>'{}' ~ E'[\\r\\n]')
$$;
CREATE TABLE source_fetch_attempts (
    id uuid PRIMARY KEY, logical_fetch_id uuid NOT NULL,
    sequence_no integer NOT NULL CHECK (sequence_no BETWEEN 1 AND 3),
    source_id uuid NOT NULL REFERENCES sources(id),
    policy_revision_id uuid NOT NULL REFERENCES source_policy_revisions(id),
    source_object_key text NOT NULL CHECK (btrim(source_object_key)<>''),
    request_url text NOT NULL CHECK (request_url ~ '^https://[^/?#@[:space:]]+/[^#[:space:]]*$'),
    request_params_hash text NOT NULL CHECK (request_params_hash ~ '^[0-9a-f]{64}$'),
    stage_attempt_id uuid NOT NULL REFERENCES analysis_stage_attempts(id),
    lease_epoch bigint NOT NULL CHECK (lease_epoch>0), lease_fencing_token bigint NOT NULL CHECK (lease_fencing_token>0),
    lease_owner text NOT NULL CHECK (btrim(lease_owner)<>''),
    creation_transaction_id xid8 NOT NULL DEFAULT pg_current_xact_id(),
    prepared_at timestamptz NOT NULL DEFAULT clock_timestamp(), requested_at timestamptz,
    headers_received_at timestamptz, finished_at timestamptz,
    http_status integer CHECK (http_status BETWEEN 100 AND 599),
    state text NOT NULL DEFAULT 'prepared' CHECK (state IN ('prepared','in_progress','complete','not_modified',
        'redirected','http_error','transport_error','body_limit','redirect_refused','archive_error','cancelled','interrupted_unknown')),
    completed_capture_id uuid UNIQUE REFERENCES source_captures(id),
    reused_capture_id uuid REFERENCES source_captures(id), validator_capture_id uuid REFERENCES source_captures(id),
    if_none_match text CHECK (octet_length(if_none_match) BETWEEN 1 AND 4096 AND if_none_match !~ E'[\\r\\n]'),
    if_modified_since text CHECK (octet_length(if_modified_since) BETWEEN 1 AND 4096 AND if_modified_since !~ E'[\\r\\n]'),
    response_headers jsonb NOT NULL DEFAULT '{}' CHECK (ingestion_header_evidence_valid(response_headers)),
    failure_code text CHECK (octet_length(failure_code) BETWEEN 1 AND 128),
    failure_detail text CHECK (octet_length(failure_detail)<=2048),
    quarantine_sha256 text CHECK (quarantine_sha256 ~ '^[0-9a-f]{64}$'),
    quarantine_byte_count bigint CHECK (quarantine_byte_count>=0), quarantine_blob_key text,
    UNIQUE(logical_fetch_id,sequence_no),
    CHECK ((validator_capture_id IS NULL AND if_none_match IS NULL AND if_modified_since IS NULL) OR
           (validator_capture_id IS NOT NULL AND (if_none_match IS NOT NULL OR if_modified_since IS NOT NULL))),
    CHECK (isfinite(prepared_at) AND (requested_at IS NULL OR (isfinite(requested_at) AND requested_at>=prepared_at))),
    CHECK ((headers_received_at IS NULL AND http_status IS NULL) OR
           (headers_received_at IS NOT NULL AND isfinite(headers_received_at) AND requested_at IS NOT NULL
            AND headers_received_at>=requested_at AND http_status IS NOT NULL)),
    CHECK ((state IN ('prepared','in_progress') AND finished_at IS NULL) OR
           (state NOT IN ('prepared','in_progress') AND finished_at IS NOT NULL AND isfinite(finished_at)
            AND finished_at>=coalesce(headers_received_at,requested_at,prepared_at))),
    CHECK (state<>'prepared' OR (requested_at IS NULL AND headers_received_at IS NULL)),
    CHECK (state<>'in_progress' OR requested_at IS NOT NULL),
    CHECK (state<>'complete' OR (http_status IS NOT NULL AND http_status BETWEEN 200 AND 299 AND completed_capture_id IS NOT NULL)),
    CHECK (state<>'http_error' OR (http_status IS NOT NULL AND http_status BETWEEN 400 AND 599)),
    CHECK (state<>'not_modified' OR (http_status IS NOT NULL AND http_status=304 AND reused_capture_id IS NOT NULL
           AND reused_capture_id=validator_capture_id)),
    CHECK (state<>'redirected' OR (http_status IS NOT NULL AND http_status IN (301,302,303,307,308) AND response_headers ? 'location')),
    CHECK (state<>'redirect_refused' OR (http_status IS NOT NULL AND http_status BETWEEN 300 AND 399 AND http_status<>304)),
    CHECK (completed_capture_id IS NULL OR state IN ('complete','http_error','redirected','redirect_refused')),
    CHECK ((state='not_modified')=(reused_capture_id IS NOT NULL)),
    CHECK (NOT (completed_capture_id IS NOT NULL AND reused_capture_id IS NOT NULL)),
    CHECK ((quarantine_sha256 IS NULL AND quarantine_byte_count IS NULL AND quarantine_blob_key IS NULL) OR
           (quarantine_sha256 IS NOT NULL AND quarantine_byte_count IS NOT NULL AND quarantine_blob_key IS NOT NULL
            AND btrim(quarantine_blob_key)<>'' AND completed_capture_id IS NULL)),
    CHECK (state NOT IN ('transport_error','body_limit','redirect_refused','archive_error','cancelled','interrupted_unknown')
           OR (failure_code IS NOT NULL AND btrim(failure_code)<>''))
);
CREATE INDEX source_fetch_attempts_source_object ON source_fetch_attempts(source_id,source_object_key,prepared_at);
CREATE INDEX source_fetch_attempts_policy_fk ON source_fetch_attempts(policy_revision_id);
CREATE INDEX source_fetch_attempts_stage_fk ON source_fetch_attempts(stage_attempt_id);
CREATE INDEX source_fetch_attempts_reuse_fk ON source_fetch_attempts(reused_capture_id);
CREATE INDEX source_fetch_attempts_validator_fk ON source_fetch_attempts(validator_capture_id);
CREATE INDEX source_fetch_attempts_unfinished ON source_fetch_attempts(stage_attempt_id,prepared_at)
    WHERE state IN ('prepared','in_progress');

CREATE FUNCTION ingestion_capture_policy_check() RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path=public,pg_temp AS $$ BEGIN
    IF NOT EXISTS (SELECT FROM source_captures c JOIN source_policy_revisions p ON p.source_id=c.source_id
                   WHERE c.id=NEW.capture_id AND p.id=NEW.policy_revision_id AND c.terms_review_reference=p.review_key) THEN
        RAISE EXCEPTION 'capture policy source or review key mismatch' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE FUNCTION ingestion_capture_policy_required() RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path=public,pg_temp AS $$ BEGIN
    IF NEW.completed_at IS NULL OR NEW.fetched_at IS NULL OR NEW.body_sha256 IS NULL
       OR NEW.blob_key IS NULL OR NEW.byte_count IS NULL OR NEW.http_status IS NULL THEN
        RAISE EXCEPTION 'new captures require complete archived bodies; partial failures belong to attempts' USING ERRCODE='23514';
    END IF;
    IF NOT EXISTS (SELECT FROM capture_policy_links WHERE capture_id=NEW.id) THEN
        RAISE EXCEPTION 'new capture requires a matching policy link in its creation transaction' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER capture_policy_links_validate BEFORE INSERT ON capture_policy_links
    FOR EACH ROW EXECUTE FUNCTION ingestion_capture_policy_check();
CREATE CONSTRAINT TRIGGER source_captures_policy_required AFTER INSERT ON source_captures
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ingestion_capture_policy_required();
CREATE TRIGGER source_policy_revisions_immutable BEFORE UPDATE OR DELETE ON source_policy_revisions
    FOR EACH ROW EXECUTE FUNCTION evidence_immutable();
CREATE TRIGGER capture_policy_links_immutable BEFORE UPDATE OR DELETE ON capture_policy_links
    FOR EACH ROW EXECUTE FUNCTION evidence_immutable();

CREATE FUNCTION ingestion_attempt_guard() RETURNS trigger LANGUAGE plpgsql
SET search_path=public,pg_temp AS $$
DECLARE c source_captures%ROWTYPE; policy_source uuid;
BEGIN
    IF TG_OP='DELETE' THEN RAISE EXCEPTION 'transport attempt history is immutable' USING ERRCODE='55000'; END IF;
    IF TG_OP='INSERT' AND (NEW.state<>'prepared' OR NEW.creation_transaction_id<>pg_current_xact_id()) THEN
        RAISE EXCEPTION 'attempt starts as prepared in its creation transaction' USING ERRCODE='23514';
    END IF;
    IF TG_OP='UPDATE' THEN
        IF OLD.state NOT IN ('prepared','in_progress') THEN
            RAISE EXCEPTION 'terminal transport attempt is immutable' USING ERRCODE='55000';
        END IF;
        IF (to_jsonb(NEW)-ARRAY['state','requested_at','headers_received_at','finished_at','http_status','response_headers',
              'completed_capture_id','reused_capture_id','failure_code','failure_detail','quarantine_sha256',
              'quarantine_byte_count','quarantine_blob_key']) IS DISTINCT FROM
           (to_jsonb(OLD)-ARRAY['state','requested_at','headers_received_at','finished_at','http_status','response_headers',
              'completed_capture_id','reused_capture_id','failure_code','failure_detail','quarantine_sha256',
              'quarantine_byte_count','quarantine_blob_key']) THEN
            RAISE EXCEPTION 'attempt identity, stage and policy are immutable' USING ERRCODE='23514';
        END IF;
        IF (OLD.requested_at IS NOT NULL AND NEW.requested_at IS DISTINCT FROM OLD.requested_at) OR
           (OLD.headers_received_at IS NOT NULL AND (NEW.headers_received_at IS DISTINCT FROM OLD.headers_received_at
             OR NEW.http_status IS DISTINCT FROM OLD.http_status OR NEW.response_headers IS DISTINCT FROM OLD.response_headers))
           OR NEW.state='prepared' THEN
            RAISE EXCEPTION 'attempt evidence cannot move backwards or overwrite received headers' USING ERRCODE='23514';
        END IF;
    END IF;
    SELECT source_id INTO policy_source FROM source_policy_revisions WHERE id=NEW.policy_revision_id;
    IF policy_source IS DISTINCT FROM NEW.source_id THEN
        RAISE EXCEPTION 'attempt policy source mismatch' USING ERRCODE='23514';
    END IF;
    IF NEW.completed_capture_id IS NOT NULL THEN
        SELECT * INTO c FROM source_captures WHERE id=NEW.completed_capture_id;
        IF c.source_id IS DISTINCT FROM NEW.source_id OR c.source_object_key IS DISTINCT FROM NEW.source_object_key
           OR c.request_url IS DISTINCT FROM NEW.request_url OR c.request_params_hash IS DISTINCT FROM NEW.request_params_hash
           OR c.http_status IS DISTINCT FROM NEW.http_status OR c.requested_at IS DISTINCT FROM NEW.requested_at
           OR c.completed_at IS DISTINCT FROM NEW.finished_at OR NOT EXISTS (
                SELECT FROM capture_policy_links WHERE capture_id=c.id AND policy_revision_id=NEW.policy_revision_id) THEN
            RAISE EXCEPTION 'completed capture does not match attempt and pinned policy' USING ERRCODE='23514';
        END IF;
    END IF;
    IF NEW.validator_capture_id IS NOT NULL THEN
        SELECT * INTO c FROM source_captures WHERE id=NEW.validator_capture_id;
        IF c.source_id IS DISTINCT FROM NEW.source_id OR c.source_object_key IS DISTINCT FROM NEW.source_object_key
           OR c.request_url IS DISTINCT FROM NEW.request_url OR c.request_params_hash IS DISTINCT FROM NEW.request_params_hash
           OR c.http_status IS NULL OR c.http_status NOT BETWEEN 200 AND 299 OR c.body_sha256 IS NULL
           OR c.completed_at IS NULL OR c.fetched_at IS NULL OR c.blob_key IS NULL OR c.byte_count IS NULL
           OR c.completed_at>NEW.prepared_at OR NOT EXISTS (
                SELECT FROM source_fetch_attempts prior WHERE prior.completed_capture_id=c.id AND prior.state='complete'
                AND (NEW.if_none_match IS NULL OR prior.response_headers->>'etag'=NEW.if_none_match)
                AND (NEW.if_modified_since IS NULL OR prior.response_headers->>'last_modified'=NEW.if_modified_since)) THEN
            RAISE EXCEPTION 'conditional validators lack an exact earlier successful representation' USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER source_fetch_attempts_guard BEFORE INSERT OR UPDATE OR DELETE ON source_fetch_attempts
    FOR EACH ROW EXECUTE FUNCTION ingestion_attempt_guard();

CREATE FUNCTION ingestion_locked_stage(p_lease jsonb,p_stage uuid) RETURNS analysis_executions
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE execution analysis_executions%ROWTYPE; stage analysis_stage_attempts%ROWTYPE;
BEGIN
    execution:=workflow_locked_lease(p_lease);
    SELECT * INTO stage FROM analysis_stage_attempts WHERE id=p_stage FOR SHARE;
    IF NOT FOUND OR stage.execution_id IS DISTINCT FROM execution.id OR stage.state<>'running' THEN
        RAISE EXCEPTION 'lease lost: source stage ended or belongs to another execution' USING ERRCODE='55000';
    END IF;
    RETURN execution;
END $$;
CREATE FUNCTION ingestion_locked_attempt(p_lease jsonb,p_attempt uuid) RETURNS source_fetch_attempts
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE attempt source_fetch_attempts%ROWTYPE;
BEGIN
    SELECT * INTO attempt FROM source_fetch_attempts WHERE id=p_attempt;
    IF NOT FOUND THEN RAISE EXCEPTION 'unknown source attempt' USING ERRCODE='23503'; END IF;
    PERFORM ingestion_locked_stage(p_lease,attempt.stage_attempt_id);
    SELECT * INTO attempt FROM source_fetch_attempts WHERE id=p_attempt FOR UPDATE;
    IF attempt.lease_epoch IS DISTINCT FROM (p_lease->>'epoch')::bigint
       OR attempt.lease_fencing_token IS DISTINCT FROM (p_lease->>'fencing_token')::bigint
       OR attempt.lease_owner IS DISTINCT FROM p_lease->>'worker_id' THEN
        RAISE EXCEPTION 'lease lost: attempt belongs to another fence' USING ERRCODE='55000';
    END IF;
    IF attempt.state NOT IN ('prepared','in_progress') THEN
        RAISE EXCEPTION 'source attempt is already terminal' USING ERRCODE='55000';
    END IF;
    RETURN attempt;
END $$;
CREATE FUNCTION ingestion_validate_stage(p_lease jsonb,p_stage uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$ BEGIN
    PERFORM ingestion_locked_stage(p_lease,p_stage); RETURN true;
END $$;

CREATE FUNCTION ingestion_prepare(p_lease jsonb,p_stage uuid,p_request jsonb) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE execution analysis_executions%ROWTYPE; existing source_fetch_attempts%ROWTYPE;
        new_id uuid:=gen_random_uuid(); logical_id uuid:=(p_request->>'logical_fetch_id')::uuid;
        seq integer:=(p_request->>'sequence')::integer; count_before integer;
BEGIN
    execution:=ingestion_locked_stage(p_lease,p_stage);
    IF p_request IS NULL OR jsonb_typeof(p_request)<>'object' OR
       p_request-ARRAY['logical_fetch_id','sequence','source_id','policy_revision_id','source_object_key','request_url',
           'request_params_hash','validator_capture_id','if_none_match','if_modified_since']<>'{}'::jsonb THEN
        RAISE EXCEPTION 'unknown source request field' USING ERRCODE='22023';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(logical_id::text,531));
    SELECT * INTO existing FROM source_fetch_attempts WHERE logical_fetch_id=logical_id AND sequence_no=seq;
    IF FOUND THEN
        IF existing.source_id IS DISTINCT FROM (p_request->>'source_id')::uuid
           OR existing.policy_revision_id IS DISTINCT FROM (p_request->>'policy_revision_id')::uuid
           OR existing.source_object_key IS DISTINCT FROM p_request->>'source_object_key'
           OR existing.request_url IS DISTINCT FROM p_request->>'request_url'
           OR existing.request_params_hash IS DISTINCT FROM p_request->>'request_params_hash'
           OR existing.validator_capture_id IS DISTINCT FROM (p_request->>'validator_capture_id')::uuid
           OR existing.if_none_match IS DISTINCT FROM p_request->>'if_none_match'
           OR existing.if_modified_since IS DISTINCT FROM p_request->>'if_modified_since'
           OR existing.stage_attempt_id IS DISTINCT FROM p_stage OR existing.lease_epoch IS DISTINCT FROM (p_lease->>'epoch')::bigint
           OR existing.lease_fencing_token IS DISTINCT FROM execution.fencing_token OR existing.lease_owner IS DISTINCT FROM execution.lease_owner THEN
            RAISE EXCEPTION 'fetch sequence reused with different request or fence' USING ERRCODE='22023';
        END IF;
        IF existing.state<>'prepared' THEN RAISE EXCEPTION 'source attempt already progressed' USING ERRCODE='55000'; END IF;
        RETURN existing.id;
    END IF;
    SELECT count(*) INTO count_before FROM source_fetch_attempts WHERE logical_fetch_id=logical_id;
    IF seq IS NULL OR seq<>count_before+1 OR seq>3 THEN
        RAISE EXCEPTION 'fetch sequence must be contiguous within the three-dispatch budget' USING ERRCODE='22023';
    END IF;
    IF EXISTS (SELECT FROM source_fetch_attempts WHERE logical_fetch_id=logical_id AND
        (source_id IS DISTINCT FROM (p_request->>'source_id')::uuid OR policy_revision_id IS DISTINCT FROM (p_request->>'policy_revision_id')::uuid
         OR source_object_key IS DISTINCT FROM p_request->>'source_object_key' OR request_params_hash IS DISTINCT FROM p_request->>'request_params_hash'
         OR stage_attempt_id IS DISTINCT FROM p_stage OR state IN ('prepared','in_progress'))) THEN
        RAISE EXCEPTION 'logical fetch changed identity or previous hop is unfinished' USING ERRCODE='23514';
    END IF;
    INSERT INTO source_fetch_attempts(id,logical_fetch_id,sequence_no,source_id,policy_revision_id,source_object_key,
        request_url,request_params_hash,stage_attempt_id,lease_epoch,lease_fencing_token,lease_owner,
        validator_capture_id,if_none_match,if_modified_since)
    VALUES(new_id,logical_id,seq,(p_request->>'source_id')::uuid,(p_request->>'policy_revision_id')::uuid,
        p_request->>'source_object_key',p_request->>'request_url',p_request->>'request_params_hash',p_stage,
        (p_lease->>'epoch')::bigint,execution.fencing_token,execution.lease_owner,
        (p_request->>'validator_capture_id')::uuid,p_request->>'if_none_match',p_request->>'if_modified_since');
    RETURN new_id;
END $$;
CREATE FUNCTION ingestion_dispatch(p_lease jsonb,p_attempt uuid,p_requested_at timestamptz) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE attempt source_fetch_attempts%ROWTYPE;
BEGIN
    attempt:=ingestion_locked_attempt(p_lease,p_attempt);
    IF attempt.state<>'prepared' OR attempt.creation_transaction_id=pg_current_xact_id() THEN
        RAISE EXCEPTION 'dispatch requires a previously committed prepared attempt' USING ERRCODE='55000';
    END IF;
    IF p_requested_at IS NULL THEN RAISE EXCEPTION 'dispatch timestamp is required' USING ERRCODE='23514'; END IF;
    UPDATE source_fetch_attempts SET state='in_progress',requested_at=p_requested_at WHERE id=p_attempt;
    RETURN true;
END $$;
CREATE FUNCTION ingestion_headers(p_lease jsonb,p_attempt uuid,p_received_at timestamptz,p_status integer,p_headers jsonb) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE attempt source_fetch_attempts%ROWTYPE;
BEGIN
    attempt:=ingestion_locked_attempt(p_lease,p_attempt);
    IF attempt.state<>'in_progress' OR attempt.headers_received_at IS NOT NULL THEN
        RAISE EXCEPTION 'headers require one dispatched attempt with no previous headers' USING ERRCODE='55000';
    END IF;
    IF p_received_at IS NULL OR p_status IS NULL OR NOT ingestion_header_evidence_valid(p_headers) THEN
        RAISE EXCEPTION 'invalid or unrestricted HTTP evidence' USING ERRCODE='23514';
    END IF;
    UPDATE source_fetch_attempts SET headers_received_at=p_received_at,http_status=p_status,response_headers=p_headers WHERE id=p_attempt;
    RETURN true;
END $$;
CREATE FUNCTION ingestion_finalize(p_lease jsonb,p_attempt uuid,p_outcome text,p_finished_at timestamptz,
    p_capture jsonb,p_reused uuid,p_failure_code text,p_failure_detail text,p_quarantine jsonb) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE attempt source_fetch_attempts%ROWTYPE; policy source_policy_revisions%ROWTYPE; capture_id uuid;
BEGIN
    attempt:=ingestion_locked_attempt(p_lease,p_attempt);
    IF p_outcome IS NULL OR p_outcome NOT IN ('complete','not_modified','redirected','http_error','transport_error',
       'body_limit','redirect_refused','archive_error','cancelled') THEN
        RAISE EXCEPTION 'invalid worker terminal outcome; unknown interruption is recovery-only' USING ERRCODE='22023';
    END IF;
    IF attempt.state='prepared' AND p_outcome NOT IN ('transport_error','archive_error','cancelled') THEN
        RAISE EXCEPTION 'HTTP outcome requires committed dispatch evidence' USING ERRCODE='55000';
    END IF;
    IF p_finished_at IS NULL THEN RAISE EXCEPTION 'completion timestamp is required' USING ERRCODE='23514'; END IF;
    IF p_capture IS NOT NULL THEN
        IF p_outcome NOT IN ('complete','http_error','redirected','redirect_refused') OR jsonb_typeof(p_capture)<>'object' OR
           p_capture-ARRAY['capture_id','fetched_at','body_sha256','blob_key','byte_count','content_type']<>'{}'::jsonb
           OR attempt.headers_received_at IS NULL OR p_quarantine IS NOT NULL THEN
            RAISE EXCEPTION 'complete capture is incompatible with this attempt outcome' USING ERRCODE='23514';
        END IF;
        IF NOT (p_capture ?& ARRAY['capture_id','fetched_at','body_sha256','blob_key','byte_count'])
           OR (p_capture->>'fetched_at')::timestamptz < attempt.headers_received_at THEN
            RAISE EXCEPTION 'capture metadata must identify complete post-header archived bytes' USING ERRCODE='23514';
        END IF;
        IF p_capture->>'content_type' IS NOT NULL AND
           p_capture->>'content_type' IS DISTINCT FROM attempt.response_headers->>'content_type' THEN
            RAISE EXCEPTION 'capture content type must match recorded HTTP headers' USING ERRCODE='23514';
        END IF;
        SELECT * INTO policy FROM source_policy_revisions WHERE id=attempt.policy_revision_id;
        capture_id:=(p_capture->>'capture_id')::uuid;
        INSERT INTO source_captures(id,source_id,source_object_key,request_url,request_params_hash,requested_at,
            completed_at,fetched_at,http_status,body_sha256,blob_key,byte_count,content_type,terms_review_reference)
        VALUES(capture_id,attempt.source_id,attempt.source_object_key,attempt.request_url,attempt.request_params_hash,
            attempt.requested_at,p_finished_at,(p_capture->>'fetched_at')::timestamptz,attempt.http_status,
            p_capture->>'body_sha256',p_capture->>'blob_key',(p_capture->>'byte_count')::bigint,
            coalesce(p_capture->>'content_type',attempt.response_headers->>'content_type'),policy.review_key);
        INSERT INTO capture_policy_links(capture_id,policy_revision_id) VALUES(capture_id,policy.id);
    END IF;
    IF p_quarantine IS NOT NULL AND (jsonb_typeof(p_quarantine)<>'object' OR
       p_quarantine-ARRAY['body_sha256','byte_count','blob_key']<>'{}'::jsonb) THEN
        RAISE EXCEPTION 'unknown quarantine evidence field' USING ERRCODE='23514';
    END IF;
    UPDATE source_fetch_attempts SET state=p_outcome,finished_at=p_finished_at,completed_capture_id=capture_id,
        reused_capture_id=p_reused,failure_code=p_failure_code,failure_detail=p_failure_detail,
        quarantine_sha256=p_quarantine->>'body_sha256',quarantine_byte_count=(p_quarantine->>'byte_count')::bigint,
        quarantine_blob_key=p_quarantine->>'blob_key' WHERE id=p_attempt;
    RETURN capture_id;
END $$;
CREATE FUNCTION ingestion_recover(p_attempt uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE attempt source_fetch_attempts%ROWTYPE; stage analysis_stage_attempts%ROWTYPE;
        execution analysis_executions%ROWTYPE; control analysis_request_state%ROWTYPE;
BEGIN
    SELECT * INTO attempt FROM source_fetch_attempts WHERE id=p_attempt;
    IF NOT FOUND THEN RAISE EXCEPTION 'unknown source attempt' USING ERRCODE='23503'; END IF;
    SELECT * INTO stage FROM analysis_stage_attempts WHERE id=attempt.stage_attempt_id;
    SELECT * INTO execution FROM analysis_executions WHERE id=stage.execution_id;
    SELECT * INTO control FROM analysis_request_state WHERE request_id=execution.request_id FOR UPDATE;
    SELECT * INTO execution FROM analysis_executions WHERE id=stage.execution_id FOR UPDATE;
    SELECT * INTO stage FROM analysis_stage_attempts WHERE id=attempt.stage_attempt_id FOR SHARE;
    SELECT * INTO attempt FROM source_fetch_attempts WHERE id=p_attempt FOR UPDATE;
    IF attempt.state NOT IN ('prepared','in_progress') THEN RETURN false; END IF;
    IF control.terminal_outcome IS NULL AND control.current_execution_id=execution.id
       AND control.attempt_epoch=attempt.lease_epoch AND execution.fencing_token=attempt.lease_fencing_token
       AND execution.lease_owner=attempt.lease_owner AND execution.state='running' AND stage.state='running'
       AND execution.lease_expires_at>clock_timestamp() AND execution.cancellation_requested_at IS NULL THEN
        RAISE EXCEPTION 'cannot recover an attempt still owned by an active stage lease' USING ERRCODE='55000';
    END IF;
    UPDATE source_fetch_attempts SET state='interrupted_unknown',finished_at=greatest(clock_timestamp(),
        coalesce(headers_received_at,requested_at,prepared_at)),failure_code='lost_stage_lease',
        failure_detail='Stage ownership ended before a verified terminal result; remote outcome is unknown' WHERE id=p_attempt;
    RETURN true;
END $$;

REVOKE INSERT ON source_captures FROM equity_runtime;
REVOKE ALL ON source_policy_revisions,capture_policy_links,source_fetch_attempts FROM PUBLIC;
GRANT SELECT ON source_policy_revisions,capture_policy_links,source_fetch_attempts,source_capture_policy_status TO equity_runtime;
DO $$ DECLARE f record; BEGIN
    FOR f IN SELECT oid::regprocedure AS signature,proname FROM pg_proc
        WHERE pronamespace='public'::regnamespace AND proname LIKE 'ingestion\_%' ESCAPE '\' LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC',f.signature);
        IF f.proname IN ('ingestion_validate_stage','ingestion_prepare','ingestion_dispatch','ingestion_headers',
                        'ingestion_finalize','ingestion_recover') THEN
            EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO equity_runtime',f.signature);
        END IF;
    END LOOP;
END $$;
"""


def upgrade() -> None:
    op.execute(SQL)


def downgrade() -> None:
    op.execute(r"""
    DROP TRIGGER source_captures_policy_required ON source_captures;
    DROP VIEW source_capture_policy_status;
    DROP FUNCTION ingestion_locked_attempt(jsonb,uuid);
    DROP TABLE source_fetch_attempts,capture_policy_links,source_policy_revisions;
    DO $$ DECLARE f record; BEGIN
        FOR f IN SELECT oid::regprocedure AS signature FROM pg_proc
            WHERE pronamespace='public'::regnamespace AND proname LIKE 'ingestion\_%' ESCAPE '\' LOOP
            EXECUTE format('DROP FUNCTION %s',f.signature);
        END LOOP;
    END $$;
    GRANT INSERT ON source_captures TO equity_runtime;
    """)
