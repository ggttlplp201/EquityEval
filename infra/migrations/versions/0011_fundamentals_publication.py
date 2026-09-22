"""D037 governed synthetic fundamentals publication using existing W1 fences."""
from alembic import op

revision = "0011_fundamentals_publication"
down_revision = "0010_filing_scheduler"
branch_labels = None
depends_on = None

REFERENCES = {
    "batches": "normalization_batches", "captures": "source_captures",
    "editions": "filing_versions", "coverage": "statement_coverage",
    "events": "filing_events", "quality": "data_quality_flags",
    "resolutions": "fact_resolutions", "observations": "source_observations",
}
SQL = r"""
CREATE FUNCTION fundamentals_canonical(p JSONB) RETURNS TEXT LANGUAGE plpgsql IMMUTABLE
 SET search_path=public,pg_temp AS $$
DECLARE result TEXT;
BEGIN
 CASE jsonb_typeof(p)
 WHEN 'object' THEN SELECT '{'||coalesce(string_agg(to_jsonb(key)::TEXT||':'||fundamentals_canonical(value),',' ORDER BY key COLLATE "C"),'')||'}' INTO result FROM jsonb_each(p);
 WHEN 'array' THEN SELECT '['||coalesce(string_agg(fundamentals_canonical(value),',' ORDER BY n),'')||']' INTO result FROM jsonb_array_elements(p) WITH ORDINALITY AS a(value,n);
 WHEN 'number' THEN
   IF p::TEXT !~ '^-?(0|[1-9][0-9]*)$' THEN RAISE EXCEPTION 'canonical financial numbers require strings'; END IF;
   result:=p::TEXT;
 ELSE result:=p::TEXT;
 END CASE;
 RETURN result;
END $$;
CREATE FUNCTION fundamentals_hash(p TEXT) RETURNS TEXT LANGUAGE sql IMMUTABLE
 SET search_path=public,pg_temp AS $$ SELECT encode(sha256(convert_to(p,'UTF8')),'hex') $$;
CREATE TABLE fundamentals_input_reviews (
 id UUID PRIMARY KEY, workspace_id UUID NOT NULL REFERENCES workspaces(id),
 issuer_id UUID NOT NULL REFERENCES issuers(id), security_id UUID NOT NULL REFERENCES securities(id),
 quote_identifier_id UUID NOT NULL, manifest_text TEXT NOT NULL, manifest_hash TEXT NOT NULL,
 compatibility_text TEXT NOT NULL, compatibility_hash TEXT NOT NULL,
 expected_payload_hash TEXT NOT NULL CHECK(expected_payload_hash ~ '^[0-9a-f]{64}$'),
 reviewed_by TEXT NOT NULL CHECK(length(trim(reviewed_by))>0),
 reason TEXT NOT NULL CHECK(length(trim(reason))>0),
 reviewed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 creation_transaction_id BIGINT NOT NULL DEFAULT txid_current(),
 FOREIGN KEY(quote_identifier_id,security_id) REFERENCES security_identifiers(id,security_id),
 UNIQUE(workspace_id,manifest_hash),
 CHECK(manifest_hash=fundamentals_hash(manifest_text)),
 CHECK(manifest_text=fundamentals_canonical(manifest_text::JSONB)),
 CHECK(compatibility_text=fundamentals_canonical(manifest_text::JSONB->'selector')),
 CHECK(compatibility_hash=fundamentals_hash(compatibility_text)),
 CHECK((manifest_text::JSONB->>'version') IS NOT DISTINCT FROM 's6-input-v1'),
 CHECK((manifest_text::JSONB->>'evidence_mode') IS NOT DISTINCT FROM 'synthetic'),
 CHECK((manifest_text::JSONB->>'fixture_label') IS NOT DISTINCT FROM 'Synthetic integration fixture — not company data'),
 CHECK((manifest_text::JSONB#>>'{selector,issuer_id}') IS NOT DISTINCT FROM issuer_id::TEXT),
 CHECK((manifest_text::JSONB#>>'{selector,security_id}') IS NOT DISTINCT FROM security_id::TEXT),
 CHECK((manifest_text::JSONB#>>'{selector,quote_identifier_id}') IS NOT DISTINCT FROM quote_identifier_id::TEXT)
);
CREATE TABLE fundamentals_review_inputs (
 review_id UUID NOT NULL REFERENCES fundamentals_input_reviews(id), input_index INTEGER NOT NULL CHECK(input_index>=0),
 period_id UUID NOT NULL REFERENCES periods(id), unit_id UUID NOT NULL REFERENCES units(id),
 scope_id UUID NOT NULL REFERENCES semantic_scopes(id), mapping_id UUID NOT NULL REFERENCES mapping_revisions(id),
 selection_hash TEXT NOT NULL CHECK(selection_hash ~ '^[0-9a-f]{64}$'), PRIMARY KEY(review_id,input_index)
);
CREATE TABLE fundamentals_request_intents (
 request_id UUID PRIMARY KEY REFERENCES analysis_requests(id), review_id UUID NOT NULL REFERENCES fundamentals_input_reviews(id),
 membership_id UUID REFERENCES watchlist_memberships(id), membership_generation INTEGER, scope_id UUID NOT NULL,
 CHECK((membership_id IS NULL)=(membership_generation IS NULL)),
 CHECK(scope_id=coalesce(membership_id,'00000000-0000-0000-0000-000000000000'::UUID))
);
CREATE TABLE analysis_input_snapshots (
 id UUID PRIMARY KEY, request_id UUID NOT NULL UNIQUE REFERENCES analysis_requests(id),
 creating_execution_id UUID NOT NULL, review_id UUID NOT NULL REFERENCES fundamentals_input_reviews(id),
 membership_id UUID REFERENCES watchlist_memberships(id), membership_generation INTEGER,
 scope_id UUID NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(creating_execution_id,request_id) REFERENCES analysis_executions(id,request_id),
 UNIQUE(id,request_id),
 CHECK((membership_id IS NULL)=(membership_generation IS NULL)),
 CHECK(scope_id=coalesce(membership_id,'00000000-0000-0000-0000-000000000000'::UUID))
);
CREATE TABLE fundamentals_calculation_payloads (
 payload_hash TEXT PRIMARY KEY, dependency_hash TEXT NOT NULL UNIQUE,
 payload_text TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 CHECK(payload_hash=fundamentals_hash(payload_text)),
 CHECK(payload_text=fundamentals_canonical(payload_text::JSONB)),
 CHECK((payload_text::JSONB->>'dependency_hash') IS NOT DISTINCT FROM dependency_hash),
 CHECK((payload_text::JSONB->>'version') IS NOT DISTINCT FROM 's6-fundamentals-v1'),
 CHECK((payload_text::JSONB->>'evidence_mode') IS NOT DISTINCT FROM 'synthetic')
);
CREATE TABLE analysis_snapshots (
 id UUID PRIMARY KEY, request_id UUID NOT NULL UNIQUE REFERENCES analysis_requests(id),
 execution_id UUID NOT NULL UNIQUE, input_snapshot_id UUID NOT NULL UNIQUE,
 payload_hash TEXT NOT NULL REFERENCES fundamentals_calculation_payloads(payload_hash),
 lease_identity JSONB NOT NULL, stage_id UUID NOT NULL REFERENCES analysis_stage_attempts(id),
 outcome TEXT NOT NULL CHECK(outcome IN ('completed','completed_with_gaps')),
 generated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(execution_id,request_id) REFERENCES analysis_executions(id,request_id),
 FOREIGN KEY(input_snapshot_id,request_id) REFERENCES analysis_input_snapshots(id,request_id)
);
CREATE TABLE fundamentals_review_history (
 review_id UUID NOT NULL REFERENCES fundamentals_input_reviews(id), sample_index INTEGER NOT NULL CHECK(sample_index>=0),
 snapshot_id UUID NOT NULL REFERENCES analysis_snapshots(id),
 payload_hash TEXT NOT NULL REFERENCES fundamentals_calculation_payloads(payload_hash),
 quarter_end DATE NOT NULL, PRIMARY KEY(review_id,sample_index), UNIQUE(review_id,snapshot_id)
);
CREATE TABLE latest_fundamentals (
 workspace_id UUID NOT NULL REFERENCES workspaces(id), security_id UUID NOT NULL REFERENCES securities(id),
 compatibility_hash TEXT NOT NULL, scope_id UUID NOT NULL,
 latest_request_id UUID NOT NULL REFERENCES analysis_requests(id), latest_request_sequence BIGINT NOT NULL,
 snapshot_id UUID REFERENCES analysis_snapshots(id), snapshot_sequence BIGINT,
 PRIMARY KEY(workspace_id,security_id,compatibility_hash,scope_id),
 CHECK((snapshot_id IS NULL)=(snapshot_sequence IS NULL)),
 CHECK(snapshot_sequence<=latest_request_sequence)
);
CREATE FUNCTION fundamentals_review_child_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_temp AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM fundamentals_input_reviews WHERE id=NEW.review_id AND creation_transaction_id=txid_current()) THEN
 RAISE EXCEPTION 'review evidence must be sealed in its creation transaction' USING ERRCODE='55000'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION fundamentals_latest_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_temp AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM analysis_requests r JOIN fundamentals_request_intents i ON i.request_id=r.id
 JOIN fundamentals_input_reviews v ON v.id=i.review_id
 WHERE r.id=NEW.latest_request_id AND r.workspace_id=NEW.workspace_id AND r.security_id=NEW.security_id
 AND r.request_sequence=NEW.latest_request_sequence AND v.compatibility_hash=NEW.compatibility_hash AND i.scope_id=NEW.scope_id) THEN
 RAISE EXCEPTION 'latest request context mismatch' USING ERRCODE='23514'; END IF;
 IF NEW.snapshot_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM analysis_snapshots s JOIN analysis_requests r ON r.id=s.request_id
 JOIN analysis_input_snapshots i ON i.id=s.input_snapshot_id JOIN fundamentals_input_reviews v ON v.id=i.review_id
 WHERE s.id=NEW.snapshot_id AND r.workspace_id=NEW.workspace_id AND r.security_id=NEW.security_id
 AND r.request_sequence=NEW.snapshot_sequence AND v.compatibility_hash=NEW.compatibility_hash AND i.scope_id=NEW.scope_id) THEN
 RAISE EXCEPTION 'latest snapshot context mismatch' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' AND (NEW.latest_request_sequence<OLD.latest_request_sequence
 OR (OLD.snapshot_sequence IS NOT NULL AND (NEW.snapshot_sequence IS NULL OR NEW.snapshot_sequence<OLD.snapshot_sequence))
 OR ROW(NEW.workspace_id,NEW.security_id,NEW.compatibility_hash,NEW.scope_id) IS DISTINCT FROM ROW(OLD.workspace_id,OLD.security_id,OLD.compatibility_hash,OLD.scope_id)) THEN
 RAISE EXCEPTION 'latest projection cannot regress' USING ERRCODE='55000'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER fundamentals_latest_guard BEFORE INSERT OR UPDATE ON latest_fundamentals FOR EACH ROW EXECUTE FUNCTION fundamentals_latest_guard();
CREATE TRIGGER fundamentals_latest_delete BEFORE DELETE ON latest_fundamentals FOR EACH ROW EXECUTE FUNCTION evidence_immutable();
CREATE TRIGGER fundamentals_latest_truncate BEFORE TRUNCATE ON latest_fundamentals FOR EACH STATEMENT EXECUTE FUNCTION evidence_immutable();
CREATE FUNCTION fundamentals_enqueue(p_workspace UUID,p_watchlist UUID,p_review UUID,p_key TEXT,p_parent UUID,p_attempts INTEGER) RETURNS JSONB
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE v fundamentals_input_reviews; r analysis_requests; result JSONB; selector JSONB; options JSONB;
 context_id UUID; m watchlist_memberships; previous fundamentals_request_intents;
BEGIN
 SELECT * INTO v FROM fundamentals_input_reviews WHERE id=p_review;
 IF NOT FOUND OR v.workspace_id IS DISTINCT FROM p_workspace
 OR (p_watchlist IS NOT NULL AND NOT EXISTS(SELECT 1 FROM watchlists WHERE id=p_watchlist AND workspace_id=p_workspace)) THEN
 RAISE EXCEPTION 'review workspace mismatch' USING ERRCODE='23514'; END IF;
 selector:=v.manifest_text::JSONB->'selector';
 options:=jsonb_build_object('history_mode',selector->'history_mode','filed_cutoff',selector->'filed_cutoff',
 'retrieval_vintage',selector->'captured_before','max_attempts',p_attempts,
 'requested_periods',jsonb_build_array(jsonb_build_object('kind',CASE WHEN selector->>'period_basis'='instant' THEN 'instant' ELSE 'duration' END,'start',selector->'period_start','end',selector->'period_end')));
 result:=workflow_enqueue(CASE WHEN p_watchlist IS NULL THEN p_workspace ELSE NULL END,p_watchlist,
 v.security_id,v.quote_identifier_id,p_key,options,CASE WHEN p_watchlist IS NULL THEN 'manual_refresh' ELSE 'watchlist_add' END,p_parent);
 SELECT * INTO r FROM analysis_requests WHERE id=(result->>'request_id')::UUID;
 PERFORM 1 FROM analysis_request_state WHERE request_id=r.id FOR UPDATE;
 SELECT * INTO previous FROM fundamentals_request_intents WHERE request_id=r.id;
 IF FOUND THEN
 IF previous.review_id<>p_review THEN RAISE EXCEPTION 'idempotent request has different review intent' USING ERRCODE='23514'; END IF;
 RETURN result;
 END IF;
 -- A pre-existing ordinary request cannot be retrospectively relabelled as S6 work.
 IF EXISTS(SELECT 1 FROM analysis_executions WHERE request_id=r.id AND (attempt_no<>1 OR state<>'queued')) THEN
 RAISE EXCEPTION 'request has already started without S6 intent' USING ERRCODE='55000'; END IF;
 WITH RECURSIVE lineage AS (SELECT id,parent_request_id,membership_id,0 depth FROM analysis_requests WHERE id=r.id
 UNION ALL SELECT a.id,a.parent_request_id,a.membership_id,l.depth+1 FROM analysis_requests a JOIN lineage l ON a.id=l.parent_request_id)
 SELECT membership_id INTO context_id FROM lineage WHERE membership_id IS NOT NULL ORDER BY depth LIMIT 1;
 IF context_id IS NOT NULL THEN
 SELECT * INTO m FROM watchlist_memberships WHERE id=context_id FOR UPDATE;
 IF m.removed_at IS NOT NULL OR m.security_id<>r.security_id OR m.quote_identifier_id<>r.quote_identifier_id THEN
 RAISE EXCEPTION 'membership no longer eligible' USING ERRCODE='55000'; END IF;
 END IF;
 INSERT INTO fundamentals_request_intents VALUES(r.id,p_review,context_id,m.generation,coalesce(context_id,'00000000-0000-0000-0000-000000000000'::UUID));
 INSERT INTO latest_fundamentals(workspace_id,security_id,compatibility_hash,scope_id,latest_request_id,latest_request_sequence)
 VALUES(r.workspace_id,r.security_id,v.compatibility_hash,coalesce(context_id,'00000000-0000-0000-0000-000000000000'::UUID),r.id,r.request_sequence)
 ON CONFLICT(workspace_id,security_id,compatibility_hash,scope_id) DO UPDATE
 SET latest_request_id=excluded.latest_request_id,latest_request_sequence=excluded.latest_request_sequence
 WHERE latest_fundamentals.latest_request_sequence<excluded.latest_request_sequence;
 RETURN result;
END $$;
CREATE FUNCTION fundamentals_freeze(p_lease JSONB,p_stage UUID,p_review UUID) RETURNS UUID
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE e analysis_executions; r analysis_requests; v fundamentals_input_reviews; i analysis_input_snapshots;
 m watchlist_memberships; selector JSONB; new_id UUID:=gen_random_uuid(); context_id UUID;
BEGIN
 e:=workflow_locked_lease(p_lease);
 SELECT * INTO r FROM analysis_requests WHERE id=e.request_id;
 SELECT * INTO v FROM fundamentals_input_reviews WHERE id=p_review;
 IF NOT FOUND OR r.trigger NOT IN ('watchlist_add','manual_refresh') OR r.workspace_id<>v.workspace_id
 OR r.security_id<>v.security_id OR r.quote_identifier_id<>v.quote_identifier_id
 OR NOT EXISTS(SELECT 1 FROM securities WHERE id=r.security_id AND issuer_id=v.issuer_id) THEN
 RAISE EXCEPTION 'review/request identity mismatch' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT 1 FROM analysis_stage_attempts WHERE id=p_stage AND execution_id=e.id AND stage_key='fundamentals' AND state='running') THEN
 RAISE EXCEPTION 'active fundamentals stage required' USING ERRCODE='55000'; END IF;
 IF NOT EXISTS(SELECT 1 FROM fundamentals_request_intents WHERE request_id=r.id AND review_id=p_review) THEN
 RAISE EXCEPTION 'request review intent mismatch' USING ERRCODE='23514'; END IF;
 selector:=v.manifest_text::JSONB->'selector';
 IF r.history_mode IS DISTINCT FROM selector->>'history_mode'
 OR r.filed_cutoff IS DISTINCT FROM (selector->>'filed_cutoff')::DATE
 OR r.retrieval_vintage IS DISTINCT FROM (selector->>'captured_before')::TIMESTAMPTZ
 OR r.requested_periods IS DISTINCT FROM jsonb_build_array(jsonb_build_object('kind',CASE WHEN selector->>'period_basis'='instant' THEN 'instant' ELSE 'duration' END,'start',selector->'period_start','end',selector->'period_end')) THEN
 RAISE EXCEPTION 'explicit request selections differ' USING ERRCODE='23514'; END IF;
 WITH RECURSIVE lineage AS (SELECT id,parent_request_id,membership_id,0 depth FROM analysis_requests WHERE id=r.id
 UNION ALL SELECT a.id,a.parent_request_id,a.membership_id,l.depth+1 FROM analysis_requests a JOIN lineage l ON a.id=l.parent_request_id)
 SELECT membership_id INTO context_id FROM lineage WHERE membership_id IS NOT NULL ORDER BY depth LIMIT 1;
 IF context_id IS NOT NULL THEN
 SELECT * INTO m FROM watchlist_memberships WHERE id=context_id FOR UPDATE;
 IF m.removed_at IS NOT NULL OR m.security_id<>r.security_id OR m.quote_identifier_id<>r.quote_identifier_id THEN
 RAISE EXCEPTION 'membership no longer eligible' USING ERRCODE='55000'; END IF;
 END IF;
 SELECT * INTO i FROM analysis_input_snapshots WHERE request_id=r.id;
 IF FOUND THEN
 IF i.review_id<>p_review THEN RAISE EXCEPTION 'request inputs already frozen' USING ERRCODE='55000'; END IF;
 RETURN i.id;
 END IF;
 INSERT INTO analysis_input_snapshots(id,request_id,creating_execution_id,review_id,membership_id,membership_generation,scope_id)
 VALUES(new_id,r.id,e.id,v.id,context_id,m.generation,coalesce(context_id,'00000000-0000-0000-0000-000000000000'::UUID));
 INSERT INTO latest_fundamentals(workspace_id,security_id,compatibility_hash,scope_id,latest_request_id,latest_request_sequence)
 VALUES(r.workspace_id,r.security_id,v.compatibility_hash,coalesce(context_id,'00000000-0000-0000-0000-000000000000'::UUID),r.id,r.request_sequence)
 ON CONFLICT(workspace_id,security_id,compatibility_hash,scope_id) DO UPDATE
 SET latest_request_id=excluded.latest_request_id,latest_request_sequence=excluded.latest_request_sequence
 WHERE latest_fundamentals.latest_request_sequence<excluded.latest_request_sequence;
 PERFORM workflow_event(e.id,'fundamentals_frozen',jsonb_build_object('input_snapshot_id',new_id));
 RETURN new_id;
END $$;
CREATE FUNCTION fundamentals_publish(p_lease JSONB,p_stage UUID,p_input UUID,p_payload TEXT) RETURNS UUID
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE e analysis_executions; r analysis_requests; i analysis_input_snapshots; v fundamentals_input_reviews;
 old analysis_snapshots; m watchlist_memberships; p JSONB:=p_payload::JSONB; h TEXT:=fundamentals_hash(p_payload);
 saved TEXT; new_id UUID:=gen_random_uuid(); result_outcome TEXT;
BEGIN
 -- Serialize before checking replay, including concurrent crash-response retries.
 PERFORM 1 FROM analysis_request_state WHERE request_id=(p_lease->>'request_id')::UUID FOR UPDATE;
 SELECT * INTO old FROM analysis_snapshots WHERE request_id=(p_lease->>'request_id')::UUID;
 IF FOUND THEN
 IF old.lease_identity IS DISTINCT FROM p_lease OR old.stage_id IS DISTINCT FROM p_stage OR old.input_snapshot_id IS DISTINCT FROM p_input OR old.payload_hash IS DISTINCT FROM h THEN
 RAISE EXCEPTION 'conflicting publication replay' USING ERRCODE='55000'; END IF;
 RETURN old.id;
 END IF;
 e:=workflow_locked_lease(p_lease);
 SELECT * INTO r FROM analysis_requests WHERE id=e.request_id;
 SELECT * INTO i FROM analysis_input_snapshots WHERE id=p_input AND request_id=r.id;
 IF NOT FOUND THEN RAISE EXCEPTION 'frozen input ownership mismatch' USING ERRCODE='23514'; END IF;
 SELECT * INTO v FROM fundamentals_input_reviews WHERE id=i.review_id;
 IF i.membership_id IS NOT NULL THEN
 SELECT * INTO m FROM watchlist_memberships WHERE id=i.membership_id FOR UPDATE;
 IF m.removed_at IS NOT NULL OR m.generation<>i.membership_generation THEN
 RAISE EXCEPTION 'membership no longer eligible' USING ERRCODE='55000'; END IF;
 END IF;
 IF NOT EXISTS(SELECT 1 FROM analysis_stage_attempts WHERE id=p_stage AND execution_id=e.id AND stage_key='fundamentals' AND state='running')
 OR EXISTS(SELECT 1 FROM analysis_stage_attempts WHERE execution_id=e.id AND state='running' AND id<>p_stage) THEN
 RAISE EXCEPTION 'exclusive active fundamentals stage required' USING ERRCODE='55000'; END IF;
 IF p_payload IS NULL OR p_payload IS DISTINCT FROM fundamentals_canonical(p)
 OR h IS DISTINCT FROM v.expected_payload_hash OR p->>'dependency_hash' IS DISTINCT FROM v.manifest_hash
 OR p->'selector' IS DISTINCT FROM v.manifest_text::JSONB->'selector' THEN
 RAISE EXCEPTION 'payload differs from independently reviewed calculation' USING ERRCODE='23514'; END IF;
 INSERT INTO fundamentals_calculation_payloads(payload_hash,dependency_hash,payload_text) VALUES(h,v.manifest_hash,p_payload)
 ON CONFLICT(dependency_hash) DO NOTHING;
 SELECT payload_text INTO saved FROM fundamentals_calculation_payloads WHERE dependency_hash=v.manifest_hash;
 IF saved IS DISTINCT FROM p_payload THEN RAISE EXCEPTION 'non-deterministic payload' USING ERRCODE='23514'; END IF;
 result_outcome:=CASE WHEN EXISTS(SELECT 1 FROM jsonb_array_elements(p->'metrics') x WHERE x->>'status'<>'valid')
 OR (p->'accounting'<>'null'::JSONB AND p#>>'{accounting,matches}' IS DISTINCT FROM 'true')
 OR (jsonb_array_length(v.manifest_text::JSONB->'trend_inputs')>0 AND p#>>'{trend,relation}' IS NULL)
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(p->'history') history_item WHERE history_item->>'relation' IS NULL)
 OR EXISTS(SELECT 1 FROM analysis_stage_attempts WHERE execution_id=e.id AND state NOT IN ('running','completed'))
 THEN 'completed_with_gaps' ELSE 'completed' END;
 INSERT INTO analysis_snapshots(id,request_id,execution_id,input_snapshot_id,payload_hash,lease_identity,stage_id,outcome)
 VALUES(new_id,r.id,e.id,i.id,h,p_lease,p_stage,result_outcome);
 PERFORM workflow_finish_stage(p_lease,p_stage,'completed',NULL,ARRAY[]::UUID[]);
 PERFORM workflow_event(e.id,'fundamentals_published',jsonb_build_object('snapshot_id',new_id,'payload_hash',h));
 PERFORM workflow_finish(p_lease,result_outcome,NULL);
 UPDATE latest_fundamentals SET snapshot_id=new_id,snapshot_sequence=r.request_sequence
 WHERE workspace_id=r.workspace_id AND security_id=r.security_id AND compatibility_hash=v.compatibility_hash
 AND scope_id=i.scope_id AND latest_request_sequence=r.request_sequence;
 RETURN new_id;
END $$;
"""

BASE_TABLES = ["fundamentals_input_reviews", "fundamentals_review_inputs", "fundamentals_request_intents", "analysis_input_snapshots",
               "fundamentals_calculation_payloads", "analysis_snapshots", "fundamentals_review_history"]
FUNCTIONS = ["fundamentals_publish(jsonb,uuid,uuid,text)", "fundamentals_freeze(jsonb,uuid,uuid)",
             "fundamentals_enqueue(uuid,uuid,uuid,text,uuid,integer)",
             "fundamentals_latest_guard()", "fundamentals_review_child_guard()",
             "fundamentals_hash(text)", "fundamentals_canonical(jsonb)"]


def upgrade():
    op.execute(SQL)
    tables = list(BASE_TABLES)
    for name, target in REFERENCES.items():
        table = "fundamentals_review_" + name
        op.execute(f"""CREATE TABLE {table} (
          review_id UUID NOT NULL, input_index INTEGER NOT NULL, evidence_id UUID NOT NULL REFERENCES {target}(id),
          PRIMARY KEY(review_id,input_index,evidence_id), FOREIGN KEY(review_id,input_index)
          REFERENCES fundamentals_review_inputs(review_id,input_index))""")
        tables.append(table)
    for table in tables:
        op.execute(f"CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION evidence_immutable()")
        op.execute(f"CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION evidence_immutable()")
        if table.startswith("fundamentals_review_"):
            op.execute(f"CREATE TRIGGER seal_children BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION fundamentals_review_child_guard()")
    for table in [*tables, "latest_fundamentals"]:
        op.execute(f"REVOKE ALL ON {table} FROM PUBLIC,equity_runtime; GRANT SELECT ON {table} TO equity_runtime")
    for function in FUNCTIONS:
        op.execute(f"REVOKE ALL ON FUNCTION {function} FROM PUBLIC,equity_runtime")
    for function in FUNCTIONS[:3]:
        op.execute(f"GRANT EXECUTE ON FUNCTION {function} TO equity_runtime")


def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM fundamentals_input_reviews)
      OR EXISTS(SELECT 1 FROM analysis_input_snapshots) OR EXISTS(SELECT 1 FROM analysis_snapshots)
      THEN RAISE EXCEPTION 'cannot downgrade retained fundamentals history' USING ERRCODE='55000'; END IF; END $$""")
    for function in FUNCTIONS[:3]:
        op.execute(f"DROP FUNCTION {function}")
    op.execute("DROP TABLE latest_fundamentals")
    for name in REFERENCES:
        op.execute(f"DROP TABLE fundamentals_review_{name}")
    for table in reversed(BASE_TABLES):
        op.execute(f"DROP TABLE {table}")
    for function in FUNCTIONS[3:]:
        op.execute(f"DROP FUNCTION {function}")
