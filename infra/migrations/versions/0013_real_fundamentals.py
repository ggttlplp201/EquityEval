"""D048 real source-only S6 companion records; preserve synthetic v1."""
from importlib import import_module

from alembic import op

revision = "0013_real_fundamentals"
down_revision = "0012_valuation_publication"
branch_labels = None
depends_on = None

REFERENCES = {
    "batches": "normalization_batches", "captures": "source_captures",
    "editions": "filing_versions", "coverage": "statement_coverage",
    "events": "filing_events", "quality": "data_quality_flags",
    "resolutions": "fact_resolutions", "observations": "source_observations",
}
TABLES = ["real_fundamentals_policy_reviews", "real_fundamentals_policy_evidence",
          "real_fundamentals_input_reviews", "real_fundamentals_review_inputs",
          "real_fundamentals_review_captures", "real_fundamentals_request_intents",
          "real_fundamentals_input_snapshots", "real_fundamentals_calculation_payloads",
          "real_fundamentals_snapshots", "real_fundamentals_review_history"]
SQL = r"""
CREATE FUNCTION real_fundamentals_compatibility(p JSONB) RETURNS TEXT LANGUAGE sql IMMUTABLE
 SET search_path=public,pg_temp AS $$ SELECT fundamentals_hash(fundamentals_canonical(
 jsonb_build_object('version','s6-fundamentals-v2','evidence_mode','real','selector',p))) $$;
CREATE TABLE real_fundamentals_policy_reviews (
 id UUID PRIMARY KEY, issuer_id UUID NOT NULL REFERENCES issuers(id),
 policy_text TEXT NOT NULL, policy_hash TEXT NOT NULL UNIQUE,
 effective_on DATE NOT NULL, known_on DATE NOT NULL,
 reviewed_by TEXT NOT NULL CHECK(length(trim(reviewed_by))>0),
 reason TEXT NOT NULL CHECK(length(trim(reason))>0),
 reviewed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 creation_transaction_id BIGINT NOT NULL DEFAULT txid_current(),
 CHECK(policy_text=fundamentals_canonical(policy_text::JSONB)),
 CHECK(policy_hash=fundamentals_hash(policy_text)),
 CHECK(policy_text::JSONB#>>'{context,profile,issuer_id}'=issuer_id::TEXT),
 CHECK((policy_text::JSONB#>>'{context,profile,effective_on}')::DATE=effective_on),
 CHECK((policy_text::JSONB#>>'{context,profile,known_on}')::DATE=known_on)
);
CREATE TABLE real_fundamentals_policy_evidence (
 policy_review_id UUID NOT NULL REFERENCES real_fundamentals_policy_reviews(id),
 evidence_index INTEGER NOT NULL CHECK(evidence_index>=0),
 capture_id UUID NOT NULL REFERENCES source_captures(id), body_sha256 TEXT NOT NULL,
 locator TEXT NOT NULL CHECK(length(trim(locator))>0), purpose TEXT NOT NULL CHECK(length(trim(purpose))>0),
 PRIMARY KEY(policy_review_id,evidence_index)
);
CREATE TABLE real_fundamentals_input_reviews (
 id UUID PRIMARY KEY, workspace_id UUID NOT NULL REFERENCES workspaces(id),
 issuer_id UUID NOT NULL REFERENCES issuers(id), security_id UUID NOT NULL REFERENCES securities(id),
 policy_review_id UUID NOT NULL REFERENCES real_fundamentals_policy_reviews(id),
 manifest_text TEXT NOT NULL, manifest_hash TEXT NOT NULL,
 compatibility_text TEXT NOT NULL, compatibility_hash TEXT NOT NULL,
 expected_payload_hash TEXT NOT NULL CHECK(expected_payload_hash ~ '^[a-f0-9]{64}$'),
 reviewed_by TEXT NOT NULL CHECK(length(trim(reviewed_by))>0), reason TEXT NOT NULL CHECK(length(trim(reason))>0),
 reviewed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(), creation_transaction_id BIGINT NOT NULL DEFAULT txid_current(),
 UNIQUE(workspace_id,manifest_hash), CHECK(manifest_hash=fundamentals_hash(manifest_text)),
 CHECK(manifest_text=fundamentals_canonical(manifest_text::JSONB)),
 CHECK(compatibility_text=fundamentals_canonical(manifest_text::JSONB->'selector')),
 CHECK(compatibility_hash=real_fundamentals_compatibility(manifest_text::JSONB->'selector')),
 CHECK(manifest_text::JSONB->>'version' IS NOT DISTINCT FROM 's6-input-v2'),
 CHECK(manifest_text::JSONB->>'evidence_mode' IS NOT DISTINCT FROM 'real'),
 CHECK(manifest_text::JSONB#>>'{selector,selection_kind}' IS NOT DISTINCT FROM 'issuer_fundamentals'),
 CHECK(NOT manifest_text::JSONB ? 'fixture_label' AND NOT (manifest_text::JSONB->'selector') ? 'quote_identifier_id'),
 CHECK(manifest_text::JSONB#>>'{selector,issuer_id}' IS NOT DISTINCT FROM issuer_id::TEXT),
 CHECK(manifest_text::JSONB#>>'{selector,security_id}' IS NOT DISTINCT FROM security_id::TEXT)
);
CREATE TABLE real_fundamentals_review_inputs (
 review_id UUID NOT NULL REFERENCES real_fundamentals_input_reviews(id), input_index INTEGER NOT NULL CHECK(input_index>=0),
 period_id UUID NOT NULL REFERENCES periods(id), unit_id UUID NOT NULL REFERENCES units(id),
 scope_id UUID NOT NULL REFERENCES semantic_scopes(id), mapping_id UUID NOT NULL REFERENCES mapping_revisions(id),
 selection_hash TEXT NOT NULL CHECK(selection_hash ~ '^[a-f0-9]{64}$'), PRIMARY KEY(review_id,input_index)
);
CREATE TABLE real_fundamentals_review_captures (
 review_id UUID NOT NULL REFERENCES real_fundamentals_input_reviews(id),
 capture_id UUID NOT NULL REFERENCES source_captures(id), body_sha256 TEXT NOT NULL,
 fetched_at TIMESTAMPTZ NOT NULL, PRIMARY KEY(review_id,capture_id)
);
CREATE TABLE real_fundamentals_request_intents (
 request_id UUID PRIMARY KEY REFERENCES analysis_requests(id),
 review_id UUID NOT NULL REFERENCES real_fundamentals_input_reviews(id), UNIQUE(request_id,review_id)
);
CREATE TABLE real_fundamentals_input_snapshots (
 id UUID PRIMARY KEY, request_id UUID NOT NULL UNIQUE REFERENCES analysis_requests(id),
 creating_execution_id UUID NOT NULL, review_id UUID NOT NULL REFERENCES real_fundamentals_input_reviews(id),
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(creating_execution_id,request_id) REFERENCES analysis_executions(id,request_id),
 FOREIGN KEY(request_id,review_id) REFERENCES real_fundamentals_request_intents(request_id,review_id),
 UNIQUE(id,request_id,review_id)
);
CREATE TABLE real_fundamentals_calculation_payloads (
 payload_hash TEXT PRIMARY KEY, dependency_hash TEXT NOT NULL UNIQUE,
 payload_text TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 CHECK(payload_hash=fundamentals_hash(payload_text)),
 CHECK(payload_text=fundamentals_canonical(payload_text::JSONB)),
 CHECK(payload_text::JSONB->>'dependency_hash' IS NOT DISTINCT FROM dependency_hash),
 CHECK(payload_text::JSONB->>'version' IS NOT DISTINCT FROM 's6-fundamentals-v2'),
 CHECK(payload_text::JSONB->>'evidence_mode' IS NOT DISTINCT FROM 'real'),
 CHECK(payload_text::JSONB#>>'{selector,selection_kind}' IS NOT DISTINCT FROM 'issuer_fundamentals'),
 CHECK(NOT payload_text::JSONB ? 'fixture_label' AND NOT (payload_text::JSONB->'selector') ? 'quote_identifier_id')
);
CREATE TABLE real_fundamentals_snapshots (
 id UUID PRIMARY KEY, request_id UUID NOT NULL UNIQUE REFERENCES analysis_requests(id),
 execution_id UUID NOT NULL UNIQUE, input_snapshot_id UUID NOT NULL UNIQUE,
 review_id UUID NOT NULL REFERENCES real_fundamentals_input_reviews(id),
 payload_hash TEXT NOT NULL REFERENCES real_fundamentals_calculation_payloads(payload_hash),
 lease_identity JSONB NOT NULL, stage_id UUID NOT NULL REFERENCES analysis_stage_attempts(id),
 outcome TEXT NOT NULL CHECK(outcome IN ('completed','completed_with_gaps')),
 generated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(execution_id,request_id) REFERENCES analysis_executions(id,request_id),
 FOREIGN KEY(input_snapshot_id,request_id,review_id) REFERENCES real_fundamentals_input_snapshots(id,request_id,review_id),
 FOREIGN KEY(request_id,review_id) REFERENCES real_fundamentals_request_intents(request_id,review_id)
);
CREATE TABLE real_fundamentals_review_history (
 review_id UUID NOT NULL REFERENCES real_fundamentals_input_reviews(id), sample_index INTEGER NOT NULL CHECK(sample_index>=0),
 snapshot_id UUID NOT NULL REFERENCES real_fundamentals_snapshots(id),
 payload_hash TEXT NOT NULL REFERENCES real_fundamentals_calculation_payloads(payload_hash),
 quarter_end DATE NOT NULL, PRIMARY KEY(review_id,sample_index), UNIQUE(review_id,snapshot_id)
);
CREATE TABLE latest_real_fundamentals (
 workspace_id UUID NOT NULL REFERENCES workspaces(id), issuer_id UUID NOT NULL REFERENCES issuers(id),
 security_id UUID NOT NULL REFERENCES securities(id), compatibility_hash TEXT NOT NULL,
 latest_request_id UUID NOT NULL REFERENCES analysis_requests(id), latest_request_sequence BIGINT NOT NULL,
 snapshot_id UUID REFERENCES real_fundamentals_snapshots(id), snapshot_sequence BIGINT,
 PRIMARY KEY(workspace_id,issuer_id,security_id,compatibility_hash),
 CHECK((snapshot_id IS NULL)=(snapshot_sequence IS NULL)), CHECK(snapshot_sequence<=latest_request_sequence)
);
ALTER TABLE analysis_requests DROP CONSTRAINT analysis_requests_trigger_check;
ALTER TABLE analysis_requests ADD CONSTRAINT analysis_requests_trigger_check
 CHECK(trigger IN ('watchlist_add','manual_refresh','source_bootstrap','sec_filing_monitor','real_fundamentals'));
ALTER TABLE analysis_requests DROP CONSTRAINT workflow_bootstrap_shape;
ALTER TABLE analysis_requests ADD CONSTRAINT workflow_bootstrap_shape CHECK(
 (trigger NOT IN ('source_bootstrap','sec_filing_monitor','real_fundamentals') AND quote_identifier_id IS NOT NULL) OR
 (trigger IN ('source_bootstrap','sec_filing_monitor','real_fundamentals') AND quote_identifier_id IS NULL AND membership_id IS NULL
 AND (trigger='real_fundamentals' OR parent_request_id IS NULL) AND market_plan_revision IS NULL
 AND price_source_id IS NULL AND price_start IS NULL AND price_end IS NULL
 AND macro_source_id IS NULL AND macro_series_keys IS NULL AND macro_start IS NULL
 AND macro_end IS NULL AND macro_source_as_of_date IS NULL));
ALTER TABLE analysis_requests ADD CONSTRAINT real_fundamentals_request_shape CHECK(
 trigger<>'real_fundamentals' OR (bootstrap_plan IS NULL AND filing_monitor_plan IS NULL
 AND retrieval_policy='pinned_vintage' AND retrieval_vintage IS NOT NULL));

CREATE FUNCTION real_fundamentals_child_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_temp AS $$
DECLARE transaction_id BIGINT;
BEGIN
 IF TG_TABLE_NAME='real_fundamentals_policy_evidence' THEN
 SELECT creation_transaction_id INTO transaction_id FROM real_fundamentals_policy_reviews WHERE id=NEW.policy_review_id;
 ELSE
 SELECT creation_transaction_id INTO transaction_id FROM real_fundamentals_input_reviews WHERE id=NEW.review_id;
 END IF;
 IF transaction_id IS DISTINCT FROM txid_current() THEN RAISE EXCEPTION 'review children are sealed' USING ERRCODE='55000'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION real_fundamentals_intent_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_temp AS $$
DECLARE r analysis_requests; v real_fundamentals_input_reviews; selector JSONB;
BEGIN
 IF TG_TABLE_NAME='analysis_requests' THEN r:=NEW;
 ELSE SELECT * INTO r FROM analysis_requests WHERE id=NEW.request_id; END IF;
 IF r.trigger<>'real_fundamentals' THEN
 IF TG_TABLE_NAME='real_fundamentals_request_intents' THEN RAISE EXCEPTION 'real intent requires real request' USING ERRCODE='23514'; END IF;
 RETURN NEW; END IF;
 SELECT v0.* INTO v FROM real_fundamentals_input_reviews v0 JOIN real_fundamentals_request_intents i ON i.review_id=v0.id WHERE i.request_id=r.id;
 selector:=v.manifest_text::JSONB->'selector';
 IF v.id IS NULL OR r.workspace_id<>v.workspace_id OR r.security_id<>v.security_id
 OR r.retrieval_vintage IS DISTINCT FROM (selector->>'captured_before')::TIMESTAMPTZ
 OR r.history_mode IS DISTINCT FROM selector->>'history_mode'
 OR r.filed_cutoff IS DISTINCT FROM (selector->>'filed_cutoff')::DATE
 OR r.requested_periods IS DISTINCT FROM jsonb_build_array(jsonb_build_object('kind',CASE WHEN selector->>'period_basis'='instant' THEN 'instant' ELSE 'duration' END,'start',selector->'period_start','end',selector->'period_end'))
 OR (r.parent_request_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM analysis_requests p WHERE p.id=r.parent_request_id AND p.trigger='real_fundamentals' AND p.workspace_id=r.workspace_id AND p.security_id=r.security_id))
 THEN RAISE EXCEPTION 'real request intent/identity/selection mismatch' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER real_request_intent AFTER INSERT ON analysis_requests
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION real_fundamentals_intent_guard();
CREATE CONSTRAINT TRIGGER real_intent_request AFTER INSERT ON real_fundamentals_request_intents
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION real_fundamentals_intent_guard();
CREATE FUNCTION real_fundamentals_stage_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_temp AS $$
BEGIN
 IF EXISTS(SELECT 1 FROM analysis_requests r JOIN analysis_executions e ON e.request_id=r.id
 WHERE e.id=NEW.execution_id AND r.trigger='real_fundamentals') AND NEW.stage_key<>'real_fundamentals'
 THEN RAISE EXCEPTION 'source-only real stage required' USING ERRCODE='23514'; END IF;
 IF NEW.stage_key='real_fundamentals' AND NOT EXISTS(SELECT 1 FROM analysis_requests r JOIN analysis_executions e ON e.request_id=r.id
 WHERE e.id=NEW.execution_id AND r.trigger='real_fundamentals')
 THEN RAISE EXCEPTION 'real stage cannot use another request kind' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER real_stage BEFORE INSERT ON analysis_stage_attempts FOR EACH ROW EXECUTE FUNCTION real_fundamentals_stage_guard();
CREATE FUNCTION real_fundamentals_success_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_temp AS $$
DECLARE real_kind BOOLEAN;
BEGIN
 IF TG_TABLE_NAME='analysis_executions' THEN
 SELECT trigger='real_fundamentals' INTO real_kind FROM analysis_requests WHERE id=NEW.request_id;
 IF real_kind AND NEW.state IN ('completed','completed_with_gaps') AND NOT EXISTS(
 SELECT 1 FROM real_fundamentals_snapshots WHERE execution_id=NEW.id AND request_id=NEW.request_id AND outcome=NEW.state)
 THEN RAISE EXCEPTION 'real success requires matching snapshot' USING ERRCODE='23514'; END IF;
 ELSE
 IF NEW.stage_key='real_fundamentals' AND NEW.state='completed' AND NOT EXISTS(
 SELECT 1 FROM real_fundamentals_snapshots WHERE execution_id=NEW.execution_id AND stage_id=NEW.id)
 THEN RAISE EXCEPTION 'real stage success requires snapshot' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER real_success BEFORE UPDATE ON analysis_executions FOR EACH ROW EXECUTE FUNCTION real_fundamentals_success_guard();
CREATE TRIGGER real_stage_success BEFORE UPDATE ON analysis_stage_attempts FOR EACH ROW EXECUTE FUNCTION real_fundamentals_success_guard();
CREATE FUNCTION real_fundamentals_latest_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_temp AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM analysis_requests r JOIN real_fundamentals_request_intents i ON i.request_id=r.id
 JOIN real_fundamentals_input_reviews v ON v.id=i.review_id WHERE r.id=NEW.latest_request_id
 AND r.workspace_id=NEW.workspace_id AND r.security_id=NEW.security_id AND r.request_sequence=NEW.latest_request_sequence
 AND v.issuer_id=NEW.issuer_id AND v.compatibility_hash=NEW.compatibility_hash)
 OR (NEW.snapshot_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM real_fundamentals_snapshots s
 JOIN analysis_requests r ON r.id=s.request_id JOIN real_fundamentals_input_reviews v ON v.id=s.review_id
 WHERE s.id=NEW.snapshot_id AND r.workspace_id=NEW.workspace_id AND r.security_id=NEW.security_id
 AND r.request_sequence=NEW.snapshot_sequence AND v.issuer_id=NEW.issuer_id AND v.compatibility_hash=NEW.compatibility_hash))
 OR (TG_OP='UPDATE' AND (NEW.latest_request_sequence<OLD.latest_request_sequence OR NEW.snapshot_sequence<OLD.snapshot_sequence))
 THEN RAISE EXCEPTION 'real latest identity/ordering mismatch' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER real_latest BEFORE INSERT OR UPDATE ON latest_real_fundamentals FOR EACH ROW EXECUTE FUNCTION real_fundamentals_latest_guard();
"""

SQL += r"""
CREATE FUNCTION real_fundamentals_review_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_temp AS $$
DECLARE v real_fundamentals_input_reviews; p real_fundamentals_policy_reviews; m JSONB;
 source JSONB; item JSONB; n INTEGER; i INTEGER; refs JSONB; key TEXT; actual TEXT[]; expected TEXT[];
BEGIN
 IF TG_TABLE_NAME='real_fundamentals_policy_reviews' THEN
 p:=NEW;
 IF (SELECT count(*) FROM real_fundamentals_policy_evidence WHERE policy_review_id=p.id)
 IS DISTINCT FROM jsonb_array_length(p.policy_text::JSONB->'evidence')
 OR NOT EXISTS(SELECT 1 FROM real_fundamentals_policy_evidence WHERE policy_review_id=p.id)
 OR EXISTS(SELECT 1 FROM real_fundamentals_policy_evidence e JOIN source_captures c ON c.id=e.capture_id
 WHERE e.policy_review_id=p.id AND (c.body_sha256 IS DISTINCT FROM e.body_sha256
 OR c.http_status<>200 OR (c.fetched_at AT TIME ZONE 'UTC')::DATE>p.known_on
 OR p.policy_text::JSONB->'evidence'->e.evidence_index IS DISTINCT FROM jsonb_build_object(
 'capture_id',e.capture_id,'body_sha256',e.body_sha256,'locator',e.locator,'purpose',e.purpose)))
 THEN RAISE EXCEPTION 'policy retained evidence mismatch' USING ERRCODE='23514'; END IF;
 RETURN NEW;
 END IF;
 v:=NEW; m:=v.manifest_text::JSONB;
 SELECT * INTO p FROM real_fundamentals_policy_reviews WHERE id=v.policy_review_id;
 IF p.issuer_id<>v.issuer_id OR NOT EXISTS(SELECT 1 FROM securities WHERE id=v.security_id AND issuer_id=v.issuer_id)
 OR p.policy_text::JSONB IS DISTINCT FROM jsonb_build_object('context',m->'context','history_policy',m->'history_policy','trend_policy',m->'trend_policy','evidence',m->'policy_evidence')
 OR (SELECT count(*) FROM real_fundamentals_review_inputs WHERE review_id=v.id) IS DISTINCT FROM jsonb_array_length(m->'sources')
 OR (SELECT count(*) FROM real_fundamentals_review_captures WHERE review_id=v.id) IS DISTINCT FROM jsonb_array_length(m->'captures')
 OR (SELECT count(*) FROM real_fundamentals_review_history WHERE review_id=v.id) IS DISTINCT FROM jsonb_array_length(m->'history_samples')
 THEN RAISE EXCEPTION 'review policy/issuer/manifest shape mismatch' USING ERRCODE='23514'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(m->'captures') LOOP
 IF NOT EXISTS(SELECT 1 FROM real_fundamentals_review_captures e JOIN source_captures c ON c.id=e.capture_id
 JOIN capture_policy_links l ON l.capture_id=c.id
 WHERE e.review_id=v.id AND e.capture_id=(item->>'capture_id')::UUID
 AND e.body_sha256=item->>'body_sha256' AND c.body_sha256=e.body_sha256 AND c.http_status=200
 AND e.fetched_at=(item->>'fetched_at')::TIMESTAMPTZ AND c.fetched_at=e.fetched_at
 AND e.fetched_at<=(m#>>'{selector,captured_before}')::TIMESTAMPTZ)
 THEN RAISE EXCEPTION 'review capture lineage differs' USING ERRCODE='23514'; END IF;
 END LOOP;
 n:=jsonb_array_length(m->'sources');
 FOR i IN 0..n-1 LOOP
 source:=m->'sources'->i;
 IF NOT EXISTS(SELECT 1 FROM real_fundamentals_review_inputs x JOIN semantic_scopes s ON s.id=x.scope_id
 WHERE x.review_id=v.id AND x.input_index=i AND x.period_id=(source#>>'{period,id}')::UUID
 AND x.unit_id=(source#>>'{unit,id}')::UUID AND x.scope_id=(source#>>'{scope,id}')::UUID
 AND s.issuer_id=v.issuer_id AND x.mapping_id=(source#>>'{selection,query,mapping_revision_id}')::UUID
 AND x.selection_hash=source#>>'{selection,input_hash}')
 OR source#>>'{selection,query,issuer_id}' IS DISTINCT FROM v.issuer_id::TEXT
 OR (source#>>'{selection,query,captured_before}')::TIMESTAMPTZ IS DISTINCT FROM (m#>>'{selector,captured_before}')::TIMESTAMPTZ
 THEN RAISE EXCEPTION 'review source scope/selection differs' USING ERRCODE='23514'; END IF;
 refs:=jsonb_build_object('batches',source#>'{selection,query,batch_ids}',
 'captures',source#>'{selection,query,capture_ids}','editions',source#>'{selection,filing_version_ids}',
 'coverage',source#>'{selection,coverage_ids}',
 'events',(source#>'{selection,query,filing_event_ids}')||(source#>'{selection,event_ids}'),
 'quality',(source#>'{selection,query,additional_quality_flag_ids}')||(source#>'{selection,quality_flag_ids}'),
 'resolutions',coalesce((SELECT jsonb_agg(id) FROM jsonb_array_elements(source#>'{selection,facts}') f CROSS JOIN LATERAL jsonb_array_elements(f->'resolution_ids') id),'[]'::JSONB),
 'observations',coalesce((SELECT jsonb_agg(id) FROM jsonb_array_elements(source#>'{selection,facts}') f CROSS JOIN LATERAL jsonb_array_elements(f->'observation_ids') id),'[]'::JSONB));
 FOR key IN SELECT jsonb_object_keys(refs) LOOP
 EXECUTE format('SELECT coalesce(array_agg(evidence_id::text ORDER BY evidence_id::text),ARRAY[]::text[]) FROM real_fundamentals_input_%I WHERE review_id=$1 AND input_index=$2',key) INTO actual USING v.id,i;
 SELECT coalesce(array_agg(x ORDER BY x),ARRAY[]::TEXT[]) INTO expected FROM (SELECT DISTINCT jsonb_array_elements_text(refs->key) x) q;
 IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION 'typed source evidence set mismatch: %',key USING ERRCODE='23514'; END IF;
 END LOOP;
 IF EXISTS(SELECT 1 FROM real_fundamentals_input_batches b JOIN normalization_batches nb ON nb.id=b.evidence_id
 WHERE b.review_id=v.id AND b.input_index=i AND nb.issuer_id<>v.issuer_id)
 THEN RAISE EXCEPTION 'batch issuer mismatch' USING ERRCODE='23514'; END IF;
 -- Independently bind every typed edge to the selected source, not just existing IDs.
 IF EXISTS(SELECT 1 FROM real_fundamentals_input_batches x JOIN normalization_batches b ON b.id=x.evidence_id
 WHERE x.review_id=v.id AND x.input_index=i AND (b.state<>'published'
 OR b.mapping_revision_id<>(source#>>'{selection,query,mapping_revision_id}')::UUID
 OR b.normalizer_revision<>source#>>'{selection,query,normalizer_revision}'
 OR b.source_authority_policy_revision<>source#>>'{selection,query,authority_policy_revision}'))
 OR EXISTS(SELECT 1 FROM real_fundamentals_input_coverage x JOIN statement_coverage c ON c.id=x.evidence_id
 WHERE x.review_id=v.id AND x.input_index=i AND (
 c.period_id<>(source#>>'{period,id}')::UUID OR c.scope_id<>(source#>>'{scope,id}')::UUID
 OR c.currency_unit_id IS DISTINCT FROM (source#>>'{selection,query,reporting_currency_unit_id}')::UUID
 OR c.statement_family<>source#>>'{selection,query,statement_family}'
 OR NOT EXISTS(SELECT 1 FROM real_fundamentals_input_batches b WHERE b.review_id=v.id AND b.input_index=i AND b.evidence_id=c.batch_id)
 OR NOT EXISTS(SELECT 1 FROM real_fundamentals_input_editions e WHERE e.review_id=v.id AND e.input_index=i AND e.evidence_id=c.filing_version_id)))
 OR EXISTS(SELECT 1 FROM real_fundamentals_input_editions x JOIN filing_versions e ON e.id=x.evidence_id JOIN filings f ON f.id=e.filing_id
 WHERE x.review_id=v.id AND x.input_index=i AND (f.issuer_id<>v.issuer_id
 OR NOT EXISTS(SELECT 1 FROM real_fundamentals_input_captures c WHERE c.review_id=v.id AND c.input_index=i AND c.evidence_id=e.metadata_capture_id)
 OR NOT EXISTS(SELECT 1 FROM real_fundamentals_input_coverage c JOIN statement_coverage sc ON sc.id=c.evidence_id WHERE c.review_id=v.id AND c.input_index=i AND sc.filing_version_id=e.id)))
 THEN RAISE EXCEPTION 'real source batch/coverage/edition ownership mismatch' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM real_fundamentals_input_resolutions x JOIN fact_resolutions r ON r.id=x.evidence_id
 WHERE x.review_id=v.id AND x.input_index=i AND (
 r.semantic_scope_id<>(source#>>'{scope,id}')::UUID OR r.unit_id<>(source#>>'{unit,id}')::UUID
 OR NOT (source#>'{selection,query,concepts}') ? r.concept_std
 OR NOT EXISTS(SELECT 1 FROM real_fundamentals_input_coverage c WHERE c.review_id=v.id AND c.input_index=i AND c.evidence_id=r.coverage_id)
 OR (r.selected_observation_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM real_fundamentals_input_observations o WHERE o.review_id=v.id AND o.input_index=i AND o.evidence_id=r.selected_observation_id))))
 OR EXISTS(SELECT 1 FROM real_fundamentals_input_observations x JOIN source_observations o ON o.id=x.evidence_id
 WHERE x.review_id=v.id AND x.input_index=i AND (
 o.period_id<>(source#>>'{period,id}')::UUID OR o.unit_id<>(source#>>'{unit,id}')::UUID
 OR o.semantic_scope_id IS DISTINCT FROM (source#>>'{scope,id}')::UUID
 OR NOT EXISTS(SELECT 1 FROM real_fundamentals_input_captures c WHERE c.review_id=v.id AND c.input_index=i AND c.evidence_id=o.source_capture_id)
 OR NOT EXISTS(SELECT 1 FROM real_fundamentals_input_resolutions r JOIN fact_resolutions fr ON fr.id=r.evidence_id
 JOIN statement_coverage c ON c.id=fr.coverage_id WHERE r.review_id=v.id AND r.input_index=i
 AND fr.selected_observation_id=o.id AND c.filing_version_id=o.filing_version_id)))
 THEN RAISE EXCEPTION 'real resolution/observation ownership mismatch' USING ERRCODE='23514'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(source#>'{selection,facts}') LOOP
 IF item->>'status'='observed' AND (
 coalesce(jsonb_array_length(item->'resolution_ids'),0)=0
 OR coalesce(jsonb_array_length(item->'observation_ids'),0)=0 OR item->>'value' IS NULL)
 THEN RAISE EXCEPTION 'observed real fact requires selected resolution and observation' USING ERRCODE='23514'; END IF;
 SELECT coalesce(array_agg(DISTINCT r.selected_observation_id::TEXT ORDER BY r.selected_observation_id::TEXT)
 FILTER(WHERE r.selected_observation_id IS NOT NULL),ARRAY[]::TEXT[]) INTO actual
 FROM jsonb_array_elements_text(item->'resolution_ids') AS selected_id(value)
 JOIN fact_resolutions r ON r.id=selected_id.value::UUID;
 SELECT coalesce(array_agg(DISTINCT value ORDER BY value),ARRAY[]::TEXT[]) INTO expected
 FROM jsonb_array_elements_text(item->'observation_ids');
 IF actual IS DISTINCT FROM expected THEN
 RAISE EXCEPTION 'real fact observations differ from exact selected resolutions' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT 1 FROM jsonb_array_elements_text(item->'resolution_ids') AS selected_id(value)
 JOIN fact_resolutions r ON r.id=selected_id.value::UUID JOIN statement_coverage c ON c.id=r.coverage_id
 JOIN filing_versions e ON e.id=c.filing_version_id JOIN filings f ON f.id=e.filing_id
 LEFT JOIN source_observations o ON o.id=r.selected_observation_id
 WHERE r.concept_std IS DISTINCT FROM item->>'concept' OR r.status IS DISTINCT FROM item->>'status'
 OR (r.selected_observation_id IS NOT NULL AND (NOT (item->'observation_ids') ? o.id::TEXT
 OR o.numeric_value IS DISTINCT FROM (item->>'value')::NUMERIC
 OR f.accession IS DISTINCT FROM item->>'accession' OR e.filed_date IS DISTINCT FROM (item->>'filed_date')::DATE)))
 THEN RAISE EXCEPTION 'real selected fact differs from owned resolution' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF EXISTS(SELECT 1 FROM real_fundamentals_input_events x JOIN filing_events e ON e.id=x.evidence_id WHERE x.review_id=v.id AND x.input_index=i AND e.issuer_id<>v.issuer_id)
 OR EXISTS(SELECT 1 FROM real_fundamentals_input_quality x JOIN data_quality_flags q ON q.id=x.evidence_id WHERE x.review_id=v.id AND x.input_index=i AND q.issuer_id<>v.issuer_id)
 THEN RAISE EXCEPTION 'real event/quality issuer mismatch' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF EXISTS(SELECT 1 FROM real_fundamentals_review_history h JOIN real_fundamentals_snapshots s ON s.id=h.snapshot_id
 JOIN real_fundamentals_input_reviews prior_review ON prior_review.id=s.review_id WHERE h.review_id=v.id AND
 (s.payload_hash<>h.payload_hash OR prior_review.workspace_id<>v.workspace_id OR prior_review.issuer_id<>v.issuer_id
 OR prior_review.security_id<>v.security_id OR m->'history_samples'->h.sample_index IS DISTINCT FROM jsonb_build_object('snapshot_id',h.snapshot_id,'payload_hash',h.payload_hash,'quarter_end',h.quarter_end)))
 THEN RAISE EXCEPTION 'history source identity mismatch' USING ERRCODE='23514'; END IF;
 RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER real_policy_review AFTER INSERT ON real_fundamentals_policy_reviews
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION real_fundamentals_review_guard();
CREATE CONSTRAINT TRIGGER real_input_review AFTER INSERT ON real_fundamentals_input_reviews
 DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION real_fundamentals_review_guard();

CREATE FUNCTION real_fundamentals_enqueue(p_workspace UUID,p_review UUID,p_key TEXT,p_parent UUID,p_attempts INTEGER) RETURNS JSONB
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE v real_fundamentals_input_reviews; selector JSONB; h TEXT; existing analysis_request_keys;
 request UUID:=gen_random_uuid(); execution UUID:=gen_random_uuid(); sequence BIGINT;
BEGIN
 IF p_key IS NULL OR length(p_key) NOT BETWEEN 1 AND 200 OR p_attempts IS NULL OR p_attempts NOT BETWEEN 1 AND 10
 THEN RAISE EXCEPTION 'invalid real request options' USING ERRCODE='22023'; END IF;
 PERFORM 1 FROM workspaces WHERE id=p_workspace FOR UPDATE;
 SELECT * INTO v FROM real_fundamentals_input_reviews WHERE id=p_review AND workspace_id=p_workspace;
 IF NOT FOUND THEN RAISE EXCEPTION 'real review workspace mismatch' USING ERRCODE='23514'; END IF;
 IF p_parent IS NOT NULL AND NOT EXISTS(SELECT 1 FROM analysis_requests WHERE id=p_parent AND workspace_id=p_workspace AND security_id=v.security_id AND trigger='real_fundamentals')
 THEN RAISE EXCEPTION 'real parent identity mismatch' USING ERRCODE='23514'; END IF;
 selector:=v.manifest_text::JSONB->'selector';
 h:=fundamentals_hash(fundamentals_canonical(jsonb_build_object('workspace',p_workspace,'review',p_review,'parent',p_parent,'max_attempts',p_attempts,'trigger','real_fundamentals')));
 SELECT * INTO existing FROM analysis_request_keys WHERE workspace_id=p_workspace AND idempotency_key=p_key;
 IF FOUND THEN
 IF existing.parameters_hash<>h THEN RAISE EXCEPTION 'idempotency key reused with different real intent' USING ERRCODE='22023'; END IF;
 RETURN workflow_request_result(existing.request_id); END IF;
 INSERT INTO analysis_requests(id,workspace_id,security_id,quote_identifier_id,trigger,membership_id,parent_request_id,
 idempotency_key,history_mode,filed_cutoff,requested_periods,retrieval_policy,retrieval_vintage,max_attempts,request_parameters_hash)
 VALUES(request,p_workspace,v.security_id,NULL,'real_fundamentals',NULL,p_parent,p_key,selector->>'history_mode',
 (selector->>'filed_cutoff')::DATE,jsonb_build_array(jsonb_build_object('kind',CASE WHEN selector->>'period_basis'='instant' THEN 'instant' ELSE 'duration' END,'start',selector->'period_start','end',selector->'period_end')),
 'pinned_vintage',(selector->>'captured_before')::TIMESTAMPTZ,p_attempts,h) RETURNING request_sequence INTO sequence;
 INSERT INTO analysis_request_keys(workspace_id,idempotency_key,request_id,parameters_hash) VALUES(p_workspace,p_key,request,h);
 INSERT INTO analysis_executions(id,request_id,attempt_no,state) VALUES(execution,request,1,'queued');
 INSERT INTO analysis_request_state(request_id,current_execution_id,attempt_epoch) VALUES(request,execution,1);
 INSERT INTO real_fundamentals_request_intents VALUES(request,p_review);
 INSERT INTO latest_real_fundamentals(workspace_id,issuer_id,security_id,compatibility_hash,latest_request_id,latest_request_sequence)
 VALUES(p_workspace,v.issuer_id,v.security_id,v.compatibility_hash,request,sequence)
 ON CONFLICT(workspace_id,issuer_id,security_id,compatibility_hash) DO UPDATE SET latest_request_id=excluded.latest_request_id,latest_request_sequence=excluded.latest_request_sequence
 WHERE latest_real_fundamentals.latest_request_sequence<excluded.latest_request_sequence;
 PERFORM workflow_event(execution,'queued',jsonb_build_object('trigger','real_fundamentals'));
 RETURN workflow_request_result(request);
END $$;
CREATE FUNCTION real_fundamentals_freeze(p_lease JSONB,p_stage UUID,p_review UUID) RETURNS UUID
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE e analysis_executions; r analysis_requests; v real_fundamentals_input_reviews; i real_fundamentals_input_snapshots; new_id UUID:=gen_random_uuid();
BEGIN
 e:=workflow_locked_lease(p_lease);
 SELECT * INTO r FROM analysis_requests WHERE id=e.request_id;
 SELECT * INTO v FROM real_fundamentals_input_reviews WHERE id=p_review;
 IF NOT FOUND OR r.trigger<>'real_fundamentals' OR r.workspace_id<>v.workspace_id OR r.security_id<>v.security_id
 OR NOT EXISTS(SELECT 1 FROM real_fundamentals_request_intents WHERE request_id=r.id AND review_id=v.id)
 THEN RAISE EXCEPTION 'real freeze identity mismatch' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT 1 FROM analysis_stage_attempts WHERE id=p_stage AND execution_id=e.id AND stage_key='real_fundamentals' AND state='running')
 THEN RAISE EXCEPTION 'active real stage required' USING ERRCODE='55000'; END IF;
 SELECT * INTO i FROM real_fundamentals_input_snapshots WHERE request_id=r.id;
 IF FOUND THEN
 IF i.review_id<>p_review THEN RAISE EXCEPTION 'real frozen review differs' USING ERRCODE='23514'; END IF;
 RETURN i.id; END IF;
 INSERT INTO real_fundamentals_input_snapshots(id,request_id,creating_execution_id,review_id) VALUES(new_id,r.id,e.id,v.id);
 PERFORM workflow_event(e.id,'real_fundamentals_frozen',jsonb_build_object('input_snapshot_id',new_id));
 RETURN new_id;
END $$;
CREATE FUNCTION real_fundamentals_publish(p_lease JSONB,p_stage UUID,p_input UUID,p_payload TEXT) RETURNS UUID
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE e analysis_executions; r analysis_requests; i real_fundamentals_input_snapshots; v real_fundamentals_input_reviews;
 old real_fundamentals_snapshots; p JSONB:=p_payload::JSONB; h TEXT:=fundamentals_hash(p_payload);
 saved TEXT; new_id UUID:=gen_random_uuid(); result_outcome TEXT;
BEGIN
 PERFORM 1 FROM analysis_request_state WHERE request_id=(p_lease->>'request_id')::UUID FOR UPDATE;
 SELECT * INTO old FROM real_fundamentals_snapshots WHERE request_id=(p_lease->>'request_id')::UUID;
 IF FOUND THEN
 IF old.lease_identity IS DISTINCT FROM p_lease OR old.stage_id IS DISTINCT FROM p_stage OR old.input_snapshot_id IS DISTINCT FROM p_input OR old.payload_hash IS DISTINCT FROM h
 THEN RAISE EXCEPTION 'conflicting real publication replay' USING ERRCODE='55000'; END IF;
 RETURN old.id; END IF;
 e:=workflow_locked_lease(p_lease);
 SELECT * INTO r FROM analysis_requests WHERE id=e.request_id;
 SELECT * INTO i FROM real_fundamentals_input_snapshots WHERE id=p_input AND request_id=r.id;
 IF NOT FOUND OR r.trigger<>'real_fundamentals' THEN RAISE EXCEPTION 'real frozen ownership mismatch' USING ERRCODE='23514'; END IF;
 SELECT * INTO v FROM real_fundamentals_input_reviews WHERE id=i.review_id;
 IF NOT EXISTS(SELECT 1 FROM real_fundamentals_request_intents WHERE request_id=r.id AND review_id=v.id)
 OR r.workspace_id<>v.workspace_id OR r.security_id<>v.security_id
 THEN RAISE EXCEPTION 'real publication intent mismatch' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT 1 FROM analysis_stage_attempts WHERE id=p_stage AND execution_id=e.id AND stage_key='real_fundamentals' AND state='running')
 OR EXISTS(SELECT 1 FROM analysis_stage_attempts WHERE execution_id=e.id AND state='running' AND id<>p_stage)
 THEN RAISE EXCEPTION 'exclusive active real stage required' USING ERRCODE='55000'; END IF;
 IF p_payload IS NULL OR p_payload IS DISTINCT FROM fundamentals_canonical(p)
 OR h IS DISTINCT FROM v.expected_payload_hash OR p->>'dependency_hash' IS DISTINCT FROM v.manifest_hash
 OR p->'selector' IS DISTINCT FROM v.manifest_text::JSONB->'selector'
 THEN RAISE EXCEPTION 'real payload differs from independently reviewed calculation' USING ERRCODE='23514'; END IF;
 INSERT INTO real_fundamentals_calculation_payloads(payload_hash,dependency_hash,payload_text) VALUES(h,v.manifest_hash,p_payload) ON CONFLICT(dependency_hash) DO NOTHING;
 SELECT payload_text INTO saved FROM real_fundamentals_calculation_payloads WHERE dependency_hash=v.manifest_hash;
 IF saved IS DISTINCT FROM p_payload THEN RAISE EXCEPTION 'non-deterministic real payload' USING ERRCODE='23514'; END IF;
 result_outcome:=CASE WHEN EXISTS(SELECT 1 FROM jsonb_array_elements(p->'metrics') x WHERE x->>'status'<>'valid')
 OR p->'accounting'='null'::JSONB OR p#>>'{accounting,matches}' IS DISTINCT FROM 'true'
 OR p#>>'{trend,relation}' IS NULL
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(p->'history') x WHERE x->>'relation' IS NULL)
 THEN 'completed_with_gaps' ELSE 'completed' END;
 INSERT INTO real_fundamentals_snapshots(id,request_id,execution_id,input_snapshot_id,review_id,payload_hash,lease_identity,stage_id,outcome)
 VALUES(new_id,r.id,e.id,i.id,v.id,h,p_lease,p_stage,result_outcome);
 PERFORM workflow_finish_stage(p_lease,p_stage,'completed',NULL,ARRAY[]::UUID[]);
 PERFORM workflow_event(e.id,'real_fundamentals_published',jsonb_build_object('snapshot_id',new_id,'payload_hash',h));
 PERFORM workflow_finish(p_lease,result_outcome,NULL);
 UPDATE latest_real_fundamentals SET snapshot_id=new_id,snapshot_sequence=r.request_sequence
 WHERE workspace_id=r.workspace_id AND issuer_id=v.issuer_id AND security_id=r.security_id
 AND compatibility_hash=v.compatibility_hash AND latest_request_sequence=r.request_sequence;
 RETURN new_id;
END $$;
"""

FUNCTIONS = ["real_fundamentals_enqueue(uuid,uuid,text,uuid,integer)",
             "real_fundamentals_freeze(jsonb,uuid,uuid)", "real_fundamentals_publish(jsonb,uuid,uuid,text)",
             "workflow_claim_real_fundamentals(text,integer,uuid)",
             "real_fundamentals_compatibility(jsonb)", "real_fundamentals_child_guard()",
             "real_fundamentals_intent_guard()", "real_fundamentals_stage_guard()",
             "real_fundamentals_success_guard()", "real_fundamentals_latest_guard()",
             "real_fundamentals_review_guard()"]


def upgrade():
    op.execute(SQL)
    tables = list(TABLES)
    for name, target in REFERENCES.items():
        table = "real_fundamentals_input_" + name
        op.execute(f"""CREATE TABLE {table} (
        review_id UUID NOT NULL, input_index INTEGER NOT NULL, evidence_id UUID NOT NULL REFERENCES {target}(id),
        PRIMARY KEY(review_id,input_index,evidence_id), FOREIGN KEY(review_id,input_index)
        REFERENCES real_fundamentals_review_inputs(review_id,input_index))""")
        tables.append(table)
    for table in tables:
        op.execute(f"CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION evidence_immutable()")
        op.execute(f"CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION evidence_immutable()")
        if table in ("real_fundamentals_policy_evidence", "real_fundamentals_review_inputs", "real_fundamentals_review_captures", "real_fundamentals_review_history") or table.startswith("real_fundamentals_input_") and table not in ("real_fundamentals_input_reviews", "real_fundamentals_input_snapshots"):
            op.execute(f"CREATE TRIGGER seal_children BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION real_fundamentals_child_guard()")
    for table in [*tables, "latest_real_fundamentals"]:
        op.execute(f"REVOKE ALL ON {table} FROM PUBLIC,equity_runtime; GRANT SELECT ON {table} TO equity_runtime")
    frozen = import_module("infra.migrations.versions.0008_filing_monitor")._claim()
    generic = "CREATE OR REPLACE FUNCTION workflow_claim_kind" + frozen
    op.execute(generic.replace("WHERE (r.trigger='source_bootstrap')=p_bootstrap", "WHERE r.trigger NOT IN ('sec_filing_monitor','real_fundamentals') AND (r.trigger='source_bootstrap')=p_bootstrap"))
    real = ("CREATE FUNCTION workflow_claim_real_fundamentals" + frozen).replace("p_seconds INTEGER,p_bootstrap BOOLEAN,p_request UUID", "p_seconds INTEGER,p_request UUID").replace("p_bootstrap IS NULL OR ", "").replace("(r.trigger='source_bootstrap')=p_bootstrap", "r.trigger='real_fundamentals'")
    op.execute(real)
    for function in FUNCTIONS:
        op.execute(f"REVOKE ALL ON FUNCTION {function} FROM PUBLIC,equity_runtime")
    for function in FUNCTIONS[:4]:
        op.execute(f"GRANT EXECUTE ON FUNCTION {function} TO equity_runtime")


def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM real_fundamentals_policy_reviews)
    OR EXISTS(SELECT 1 FROM analysis_requests WHERE trigger='real_fundamentals')
    THEN RAISE EXCEPTION 'cannot discard retained real fundamentals history' USING ERRCODE='55000'; END IF; END $$;
    DROP TRIGGER real_request_intent ON analysis_requests;
    DROP TRIGGER real_stage ON analysis_stage_attempts;
    DROP TRIGGER real_success ON analysis_executions;
    DROP TRIGGER real_stage_success ON analysis_stage_attempts;
    ALTER TABLE analysis_requests DROP CONSTRAINT real_fundamentals_request_shape;
    ALTER TABLE analysis_requests DROP CONSTRAINT analysis_requests_trigger_check;
    ALTER TABLE analysis_requests ADD CONSTRAINT analysis_requests_trigger_check CHECK(trigger IN ('watchlist_add','manual_refresh','source_bootstrap','sec_filing_monitor'));
    ALTER TABLE analysis_requests DROP CONSTRAINT workflow_bootstrap_shape;
    ALTER TABLE analysis_requests ADD CONSTRAINT workflow_bootstrap_shape CHECK(
    (trigger NOT IN ('source_bootstrap','sec_filing_monitor') AND quote_identifier_id IS NOT NULL) OR
    (trigger IN ('source_bootstrap','sec_filing_monitor') AND quote_identifier_id IS NULL AND membership_id IS NULL
    AND parent_request_id IS NULL AND market_plan_revision IS NULL AND price_source_id IS NULL AND price_start IS NULL AND price_end IS NULL
    AND macro_source_id IS NULL AND macro_series_keys IS NULL AND macro_start IS NULL AND macro_end IS NULL AND macro_source_as_of_date IS NULL));
    """)
    op.execute("DROP TABLE latest_real_fundamentals")
    for name in REFERENCES:
        op.execute(f"DROP TABLE real_fundamentals_input_{name}")
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE {table}")
    for function in FUNCTIONS:
        op.execute(f"DROP FUNCTION {function}")
    frozen = import_module("infra.migrations.versions.0008_filing_monitor")._claim()
    op.execute(("CREATE OR REPLACE FUNCTION workflow_claim_kind"+frozen).replace("WHERE (r.trigger='source_bootstrap')=p_bootstrap", "WHERE r.trigger<>'sec_filing_monitor' AND (r.trigger='source_bootstrap')=p_bootstrap"))
