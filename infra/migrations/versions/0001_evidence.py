"""S2a immutable financial evidence and sealed normalization batches.

Frozen SQL deliberately does not import application models or live concept enums.
Observation semantic_scope_id and batch output_manifest_hash make the reviewed
scope and deterministic-publication requirements enforceable rather than implicit.
"""

from alembic import op

revision = "0001_evidence"
down_revision = None
branch_labels = None
depends_on = None

# Frozen from the accepted S1 catalogue; equality with Concept is regression-tested.
CONCEPT_VALUES = (
    "revenue", "cost_of_revenue", "gross_profit", "research_and_development_expense",
    "selling_general_and_administrative_expense", "operating_expenses", "operating_income",
    "interest_expense", "pretax_income", "income_tax_expense", "net_income_parent",
    "net_income_consolidated", "eps_basic", "eps_diluted", "weighted_average_shares_basic",
    "weighted_average_shares_diluted", "common_shares_outstanding", "cash_and_cash_equivalents",
    "short_term_investments", "accounts_receivable_net", "inventory_net", "current_assets",
    "property_plant_equipment_net", "goodwill", "intangible_assets_net_excluding_goodwill",
    "total_assets", "accounts_payable_current", "current_debt", "long_term_debt_noncurrent",
    "current_liabilities", "total_liabilities", "equity_parent",
    "equity_including_noncontrolling_interests", "noncontrolling_interests",
    "cash_from_operating_activities", "capital_expenditures_ppe", "depreciation_and_amortization",
    "share_based_compensation", "dividends_paid", "share_repurchases",
)

TABLES = (
    "issuers", "securities", "sources", "source_captures", "security_identifiers",
    "security_identifier_validity", "security_identifier_closures",
    "security_relationships", "filings", "filing_versions", "periods", "units",
    "semantic_scopes", "mapping_revisions", "normalization_batches", "normalization_inputs",
    "statement_coverage", "source_observations", "fact_resolutions", "resolution_candidates",
    "data_quality_flags", "quality_flag_acknowledgements", "filing_events", "filing_event_scopes",
    "fact_revision_links",
)

DDL = r"""
CREATE EXTENSION IF NOT EXISTS btree_gist;
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'equity_runtime') THEN
        CREATE ROLE equity_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
    ELSIF EXISTS (SELECT FROM pg_roles WHERE rolname = 'equity_runtime'
                 AND (rolcanlogin OR rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)) THEN
        RAISE EXCEPTION 'Existing equity_runtime role is privileged; use an isolated migration role';
    END IF;
END $$;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO equity_runtime;

CREATE FUNCTION evidence_finite(value numeric) RETURNS boolean
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT value NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric) $$;

CREATE TABLE issuers (
    id uuid PRIMARY KEY, cik text UNIQUE CHECK (cik ~ '^[0-9]{10}$'),
    legal_name text NOT NULL CHECK (btrim(legal_name) <> ''), first_seen_at timestamptz NOT NULL
);
CREATE TABLE securities (
    id uuid PRIMARY KEY, issuer_id uuid NOT NULL REFERENCES issuers(id),
    instrument_kind text NOT NULL CHECK (btrim(instrument_kind) <> ''), share_class_label text,
    underlying_security_id uuid, active boolean NOT NULL DEFAULT true,
    UNIQUE (id, issuer_id), CHECK (underlying_security_id <> id),
    FOREIGN KEY (underlying_security_id, issuer_id) REFERENCES securities(id, issuer_id)
);
CREATE TABLE sources (
    id uuid PRIMARY KEY, source_key text NOT NULL UNIQUE CHECK (btrim(source_key) <> ''),
    name text NOT NULL CHECK (btrim(name) <> ''), base_url text NOT NULL,
    terms_review_reference text NOT NULL CHECK (btrim(terms_review_reference) <> ''),
    content_scope text NOT NULL CHECK (btrim(content_scope) <> '')
);
CREATE TABLE source_captures (
    id uuid PRIMARY KEY, source_id uuid NOT NULL REFERENCES sources(id),
    source_object_key text NOT NULL CHECK (btrim(source_object_key) <> ''), request_url text NOT NULL,
    request_params_hash text NOT NULL CHECK (request_params_hash ~ '^[a-f0-9]{64}$'),
    requested_at timestamptz NOT NULL, completed_at timestamptz, fetched_at timestamptz,
    http_status integer CHECK (http_status BETWEEN 100 AND 599),
    body_sha256 text CHECK (body_sha256 ~ '^[a-f0-9]{64}$'), blob_key text,
    byte_count bigint CHECK (byte_count >= 0), content_type text,
    terms_review_reference text NOT NULL CHECK (btrim(terms_review_reference) <> ''),
    CHECK (completed_at IS NULL OR completed_at >= requested_at),
    CHECK (fetched_at IS NULL OR (completed_at IS NOT NULL AND fetched_at >= requested_at
                                 AND fetched_at <= completed_at)),
    CHECK ((body_sha256 IS NULL AND blob_key IS NULL AND byte_count IS NULL) OR
           (body_sha256 IS NOT NULL AND blob_key IS NOT NULL AND btrim(blob_key) <> ''
            AND byte_count IS NOT NULL AND fetched_at IS NOT NULL)),
    CHECK (http_status IS NULL OR http_status NOT BETWEEN 200 AND 299 OR
           (completed_at IS NOT NULL AND fetched_at IS NOT NULL AND body_sha256 IS NOT NULL))
);
CREATE TABLE security_identifiers (
    id uuid PRIMARY KEY, security_id uuid NOT NULL REFERENCES securities(id),
    symbol text NOT NULL CHECK (btrim(symbol) <> ''), exchange_code text NOT NULL CHECK (btrim(exchange_code) <> ''),
    quote_currency text NOT NULL CHECK (quote_currency ~ '^[A-Z]{3}$'), valid_from date NOT NULL,
    valid_to date, source_capture_id uuid NOT NULL REFERENCES source_captures(id),
    CHECK (isfinite(valid_from) AND (valid_to IS NULL OR (isfinite(valid_to) AND valid_to > valid_from))),
    UNIQUE (id, security_id)
);
-- Original identity rows remain immutable. This constrained projection answers
-- current validity; historical reads pin the original row plus closure IDs.
CREATE TABLE security_identifier_validity (
    quote_identifier_id uuid PRIMARY KEY REFERENCES security_identifiers(id),
    security_id uuid NOT NULL REFERENCES securities(id), symbol text NOT NULL,
    exchange_code text NOT NULL, valid_from date NOT NULL, current_valid_to date,
    CHECK (isfinite(valid_from) AND (current_valid_to IS NULL OR
           (isfinite(current_valid_to) AND current_valid_to > valid_from))),
    EXCLUDE USING gist (exchange_code WITH =, symbol WITH =,
                       daterange(valid_from, current_valid_to, '[)') WITH &&)
);
CREATE TABLE security_identifier_closures (
    id uuid PRIMARY KEY, quote_identifier_id uuid NOT NULL UNIQUE REFERENCES security_identifiers(id),
    valid_to date NOT NULL CHECK (isfinite(valid_to)),
    source_capture_id uuid NOT NULL REFERENCES source_captures(id),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE security_relationships (
    id uuid PRIMARY KEY, security_id uuid NOT NULL REFERENCES securities(id),
    underlying_security_id uuid NOT NULL REFERENCES securities(id), valid_from date NOT NULL,
    valid_to date, underlying_units numeric NOT NULL, instrument_units numeric NOT NULL,
    source_capture_id uuid NOT NULL REFERENCES source_captures(id),
    CHECK (security_id <> underlying_security_id), CHECK (valid_to IS NULL OR valid_to > valid_from),
    CHECK (evidence_finite(underlying_units) AND underlying_units > 0),
    CHECK (evidence_finite(instrument_units) AND instrument_units > 0),
    EXCLUDE USING gist (security_id WITH =, underlying_security_id WITH =,
                       daterange(valid_from, valid_to, '[)') WITH &&)
);
CREATE TABLE filings (
    id uuid PRIMARY KEY, issuer_id uuid NOT NULL REFERENCES issuers(id),
    accession text NOT NULL CHECK (btrim(accession) <> ''), UNIQUE (issuer_id, accession)
);
CREATE TABLE filing_versions (
    id uuid PRIMARY KEY, filing_id uuid NOT NULL REFERENCES filings(id),
    metadata_capture_id uuid NOT NULL REFERENCES source_captures(id), filed_date date NOT NULL,
    acceptance_at timestamptz, acceptance_time_basis text,
    form text NOT NULL CHECK (btrim(form) <> ''), report_period_end date, source_url text NOT NULL,
    metadata_hash text NOT NULL CHECK (metadata_hash ~ '^[a-f0-9]{64}$'),
    CHECK ((acceptance_at IS NULL AND acceptance_time_basis IS NULL) OR
           (acceptance_at IS NOT NULL AND acceptance_time_basis IN ('verified_timezone', 'unverified'))),
    UNIQUE (filing_id, metadata_capture_id, metadata_hash)
);
CREATE TABLE periods (
    id uuid PRIMARY KEY, period_kind text NOT NULL CHECK (period_kind IN ('instant', 'duration')),
    start_date date, end_date date NOT NULL,
    CHECK ((period_kind = 'instant' AND start_date IS NULL) OR
           (period_kind = 'duration' AND start_date IS NOT NULL AND start_date <= end_date)),
    UNIQUE NULLS NOT DISTINCT (period_kind, start_date, end_date)
);
CREATE TABLE units (
    id uuid PRIMARY KEY, unit_key text NOT NULL UNIQUE CHECK (btrim(unit_key) <> ''),
    numerator_measures text[] NOT NULL, denominator_measures text[] NOT NULL,
    CHECK (cardinality(numerator_measures) > 0),
    CHECK (array_position(numerator_measures, NULL) IS NULL AND array_position(denominator_measures, NULL) IS NULL),
    UNIQUE (numerator_measures, denominator_measures)
);
CREATE TABLE semantic_scopes (
    id uuid PRIMARY KEY, issuer_id uuid NOT NULL REFERENCES issuers(id), instrument_id uuid,
    scope_kind text NOT NULL CHECK (btrim(scope_kind) <> ''), descriptor_schema_version integer NOT NULL CHECK (descriptor_schema_version > 0),
    descriptor_json jsonb NOT NULL CHECK (jsonb_typeof(descriptor_json) = 'object'),
    content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[a-f0-9]{64}$'),
    FOREIGN KEY (instrument_id, issuer_id) REFERENCES securities(id, issuer_id),
    UNIQUE (issuer_id, descriptor_schema_version, content_sha256)
);
CREATE TABLE mapping_revisions (
    id uuid PRIMARY KEY, revision_key text NOT NULL UNIQUE CHECK (btrim(revision_key) <> ''),
    content_sha256 text NOT NULL UNIQUE CHECK (content_sha256 ~ '^[a-f0-9]{64}$'),
    code_revision text NOT NULL CHECK (btrim(code_revision) <> ''), approved_at timestamptz NOT NULL,
    approved_by text NOT NULL CHECK (btrim(approved_by) <> ''),
    reviewed_scope text NOT NULL CHECK (btrim(reviewed_scope) <> '')
);
CREATE TABLE normalization_batches (
    id uuid PRIMARY KEY, issuer_id uuid NOT NULL REFERENCES issuers(id),
    mapping_revision_id uuid NOT NULL REFERENCES mapping_revisions(id),
    normalizer_revision text NOT NULL CHECK (btrim(normalizer_revision) <> ''),
    source_authority_policy_revision text NOT NULL CHECK (btrim(source_authority_policy_revision) <> ''),
    created_at timestamptz NOT NULL, published_at timestamptz,
    state text NOT NULL DEFAULT 'building' CHECK (state IN ('building', 'published', 'failed')),
    input_manifest_hash text CHECK (input_manifest_hash ~ '^[a-f0-9]{64}$'),
    output_manifest_hash text CHECK (output_manifest_hash ~ '^[a-f0-9]{64}$'),
    CHECK ((state = 'published' AND published_at IS NOT NULL AND published_at >= created_at
            AND input_manifest_hash IS NOT NULL AND output_manifest_hash IS NOT NULL) OR
           (state <> 'published' AND published_at IS NULL))
);
CREATE TABLE normalization_inputs (
    batch_id uuid NOT NULL REFERENCES normalization_batches(id),
    source_capture_id uuid NOT NULL REFERENCES source_captures(id), role text NOT NULL CHECK (btrim(role) <> ''),
    PRIMARY KEY (batch_id, source_capture_id, role)
);
CREATE TABLE statement_coverage (
    id uuid PRIMARY KEY, batch_id uuid NOT NULL REFERENCES normalization_batches(id),
    filing_version_id uuid NOT NULL REFERENCES filing_versions(id), period_id uuid NOT NULL REFERENCES periods(id),
    statement_family text NOT NULL CHECK (statement_family IN ('income', 'balance_sheet', 'cash_flow', 'other')),
    period_label text, reporting_basis text NOT NULL CHECK (btrim(reporting_basis) <> ''),
    scope_id uuid NOT NULL REFERENCES semantic_scopes(id), currency_unit_id uuid REFERENCES units(id),
    authority_class text NOT NULL CHECK (authority_class IN ('periodic_complete', 'reviewed_equivalent', 'preliminary', 'unknown')),
    assurance text NOT NULL CHECK (assurance IN ('audited', 'unaudited', 'unknown')),
    coverage_state text NOT NULL CHECK (coverage_state IN ('covered', 'source_missing', 'unresolved')),
    evidence_locator text NOT NULL CHECK (btrim(evidence_locator) <> ''),
    CHECK (currency_unit_id IS NOT NULL OR coverage_state = 'unresolved'),
    UNIQUE NULLS NOT DISTINCT (batch_id, filing_version_id, period_id, statement_family, reporting_basis, scope_id, currency_unit_id)
);
CREATE TABLE source_observations (
    id uuid PRIMARY KEY, source_capture_id uuid NOT NULL REFERENCES source_captures(id),
    filing_version_id uuid NOT NULL REFERENCES filing_versions(id), source_locator text NOT NULL CHECK (btrim(source_locator) <> ''),
    namespace text NOT NULL CHECK (btrim(namespace) <> ''), tag text NOT NULL CHECK (btrim(tag) <> ''),
    period_id uuid NOT NULL REFERENCES periods(id), unit_id uuid NOT NULL REFERENCES units(id),
    semantic_scope_id uuid REFERENCES semantic_scopes(id), numeric_value numeric,
    value_state text NOT NULL CHECK (value_state IN ('numeric', 'source_nil', 'unparseable')),
    original_numeric_text text, context_id text, raw_dimensions jsonb,
    context_knowledge text NOT NULL CHECK (context_knowledge IN ('unknown', 'known_empty', 'known_dimensions')),
    parser_revision text NOT NULL CHECK (btrim(parser_revision) <> ''),
    transform_metadata jsonb NOT NULL, raw_metadata jsonb NOT NULL,
    CHECK ((value_state = 'numeric' AND numeric_value IS NOT NULL AND evidence_finite(numeric_value)
            AND original_numeric_text IS NOT NULL AND btrim(original_numeric_text) <> '') OR
           (value_state <> 'numeric' AND numeric_value IS NULL)),
    CHECK ((context_knowledge = 'unknown' AND raw_dimensions IS NULL) OR
           (context_knowledge = 'known_empty' AND raw_dimensions = '{}'::jsonb) OR
           (context_knowledge = 'known_dimensions' AND jsonb_typeof(raw_dimensions) = 'object'
            AND raw_dimensions <> '{}'::jsonb)),
    UNIQUE (source_capture_id, source_locator)
);
CREATE TABLE fact_resolutions (
    id uuid PRIMARY KEY, coverage_id uuid NOT NULL REFERENCES statement_coverage(id),
    concept_std text NOT NULL CONSTRAINT fact_resolutions_concept_std_check CHECK (concept_std IN (__CONCEPTS__)),
    semantic_scope_id uuid NOT NULL REFERENCES semantic_scopes(id), instrument_id uuid REFERENCES securities(id),
    unit_id uuid NOT NULL REFERENCES units(id),
    status text NOT NULL CHECK (status IN ('observed', 'source_nil', 'missing', 'ambiguous', 'unsupported_scope', 'stale_source')),
    selected_observation_id uuid REFERENCES source_observations(id), reason text,
    CHECK ((status IN ('observed', 'source_nil') AND selected_observation_id IS NOT NULL) OR
           (status NOT IN ('observed', 'source_nil') AND selected_observation_id IS NULL)),
    CHECK (status = 'observed' OR (reason IS NOT NULL AND btrim(reason) <> '')),
    UNIQUE NULLS NOT DISTINCT (coverage_id, concept_std, semantic_scope_id, instrument_id, unit_id)
);
CREATE TABLE resolution_candidates (
    resolution_id uuid NOT NULL REFERENCES fact_resolutions(id), observation_id uuid NOT NULL REFERENCES source_observations(id),
    rule_reference text NOT NULL CHECK (btrim(rule_reference) <> ''),
    disposition text NOT NULL CHECK (disposition IN ('selected', 'rejected', 'conflicting')),
    explanation text NOT NULL CHECK (btrim(explanation) <> ''), PRIMARY KEY (resolution_id, observation_id)
);
CREATE TABLE data_quality_flags (
    id uuid PRIMARY KEY, batch_id uuid REFERENCES normalization_batches(id), resolution_id uuid REFERENCES fact_resolutions(id),
    issuer_id uuid NOT NULL REFERENCES issuers(id), security_id uuid, period_id uuid REFERENCES periods(id),
    rule_key text NOT NULL CHECK (btrim(rule_key) <> ''), severity text NOT NULL CHECK (severity IN ('info', 'warning', 'error', 'blocking')),
    message text NOT NULL CHECK (btrim(message) <> ''), evidence_references jsonb NOT NULL,
    raised_at timestamptz NOT NULL, FOREIGN KEY (security_id, issuer_id) REFERENCES securities(id, issuer_id),
    CHECK (jsonb_typeof(evidence_references) = 'array' AND jsonb_array_length(evidence_references) > 0)
);
CREATE TABLE quality_flag_acknowledgements (
    id uuid PRIMARY KEY, flag_id uuid NOT NULL REFERENCES data_quality_flags(id),
    acknowledged_by text NOT NULL CHECK (btrim(acknowledged_by) <> ''), acknowledged_at timestamptz NOT NULL,
    note text NOT NULL CHECK (btrim(note) <> '')
);
CREATE TABLE filing_events (
    id uuid PRIMARY KEY, issuer_id uuid NOT NULL REFERENCES issuers(id),
    creation_transaction_id xid8 NOT NULL DEFAULT pg_current_xact_id(),
    event_kind text NOT NULL CHECK (event_kind IN ('non_reliance', 'withdrawal', 'formal_correction', 'accounting_recast', 'source_correction', 'reinstatement')),
    announced_date date NOT NULL, announced_at timestamptz, effective_date date,
    source_filing_version_id uuid NOT NULL REFERENCES filing_versions(id),
    evidence_locator text NOT NULL CHECK (btrim(evidence_locator) <> ''), description text NOT NULL CHECK (btrim(description) <> '')
);
CREATE TABLE filing_event_scopes (
    event_id uuid NOT NULL REFERENCES filing_events(id), filing_id uuid REFERENCES filings(id),
    period_id uuid REFERENCES periods(id),
    concept_std text CONSTRAINT filing_event_scopes_concept_std_check CHECK (concept_std IN (__CONCEPTS__)),
    CHECK (filing_id IS NOT NULL OR period_id IS NOT NULL),
    UNIQUE NULLS NOT DISTINCT (event_id, filing_id, period_id, concept_std)
);
CREATE TABLE fact_revision_links (
    earlier_resolution_id uuid NOT NULL REFERENCES fact_resolutions(id), later_resolution_id uuid NOT NULL REFERENCES fact_resolutions(id),
    relation_kind text NOT NULL CHECK (relation_kind IN ('error_restatement', 'accounting_recast', 'source_correction', 'comparative_revision')),
    filing_event_id uuid REFERENCES filing_events(id), rationale text NOT NULL CHECK (btrim(rationale) <> ''),
    evidence_reference text NOT NULL CHECK (btrim(evidence_reference) <> ''),
    CHECK (earlier_resolution_id <> later_resolution_id),
    CHECK (relation_kind <> 'error_restatement' OR filing_event_id IS NOT NULL),
    PRIMARY KEY (earlier_resolution_id, later_resolution_id)
);
"""

GUARDS = r"""
CREATE FUNCTION evidence_quote_projection_guard() RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE original security_identifiers%ROWTYPE; closure security_identifier_closures%ROWTYPE;
BEGIN
    IF TG_OP='DELETE' THEN RAISE EXCEPTION 'quote projection cannot be deleted' USING ERRCODE='23514'; END IF;
    SELECT * INTO original FROM security_identifiers WHERE id=NEW.quote_identifier_id;
    SELECT * INTO closure FROM security_identifier_closures WHERE quote_identifier_id=NEW.quote_identifier_id;
    IF NOT FOUND AND TG_OP='UPDATE' THEN
        RAISE EXCEPTION 'quote projection update requires immutable closure evidence' USING ERRCODE='23514';
    END IF;
    IF NEW.security_id IS DISTINCT FROM original.security_id OR NEW.symbol IS DISTINCT FROM original.symbol
       OR NEW.exchange_code IS DISTINCT FROM original.exchange_code OR NEW.valid_from IS DISTINCT FROM original.valid_from
       OR NEW.current_valid_to IS DISTINCT FROM coalesce(closure.valid_to, original.valid_to) THEN
        RAISE EXCEPTION 'quote projection must match immutable identity and closure evidence' USING ERRCODE='23514';
    END IF;
    IF TG_OP='UPDATE' AND ((to_jsonb(NEW)-'current_valid_to') IS DISTINCT FROM
                          (to_jsonb(OLD)-'current_valid_to') OR OLD.current_valid_to IS NOT NULL) THEN
        RAISE EXCEPTION 'quote projection can only close its original open interval once' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION evidence_quote_projection_seed() RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, pg_temp AS $$ BEGIN
    -- Serialize one listing key before GiST checks to avoid mutual exclusion-check
    -- waits when two ingestion workers discover the same symbol simultaneously.
    PERFORM pg_advisory_xact_lock(hashtextextended(jsonb_build_array(NEW.exchange_code,NEW.symbol)::text,422));
    INSERT INTO security_identifier_validity(quote_identifier_id,security_id,symbol,exchange_code,valid_from,current_valid_to)
    VALUES(NEW.id,NEW.security_id,NEW.symbol,NEW.exchange_code,NEW.valid_from,NEW.valid_to);
    RETURN NEW;
END $$;

CREATE FUNCTION close_security_identifier(p_quote uuid, p_valid_to date, p_capture uuid) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE current_interval security_identifier_validity%ROWTYPE; closure_id uuid := gen_random_uuid();
BEGIN
    SELECT * INTO current_interval FROM security_identifier_validity WHERE quote_identifier_id=p_quote;
    IF NOT FOUND THEN RAISE EXCEPTION 'unknown quote identifier' USING ERRCODE='23503'; END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(
        jsonb_build_array(current_interval.exchange_code,current_interval.symbol)::text,422));
    SELECT * INTO current_interval FROM security_identifier_validity WHERE quote_identifier_id=p_quote FOR UPDATE;
    IF current_interval.current_valid_to IS NOT NULL OR EXISTS (
        SELECT FROM security_identifier_closures WHERE quote_identifier_id=p_quote) THEN
        RAISE EXCEPTION 'quote interval is already closed' USING ERRCODE='23514';
    END IF;
    IF p_valid_to IS NULL OR NOT isfinite(p_valid_to) OR p_valid_to <= current_interval.valid_from THEN
        RAISE EXCEPTION 'closure end must be finite and strictly after the original start' USING ERRCODE='23514';
    END IF;
    IF NOT EXISTS (SELECT FROM source_captures WHERE id=p_capture AND completed_at IS NOT NULL
                   AND fetched_at IS NOT NULL AND http_status BETWEEN 200 AND 299
                   AND body_sha256 IS NOT NULL AND blob_key IS NOT NULL AND byte_count IS NOT NULL) THEN
        RAISE EXCEPTION 'closure requires a successful archived source capture' USING ERRCODE='23514';
    END IF;
    INSERT INTO security_identifier_closures(id,quote_identifier_id,valid_to,source_capture_id)
    VALUES(closure_id,p_quote,p_valid_to,p_capture);
    UPDATE security_identifier_validity SET current_valid_to=p_valid_to WHERE quote_identifier_id=p_quote;
    RETURN closure_id;
END $$;

CREATE FUNCTION evidence_immutable() RETURNS trigger LANGUAGE plpgsql
SET search_path = public, pg_temp AS $$ BEGIN
    RAISE EXCEPTION '% evidence is immutable', TG_TABLE_NAME USING ERRCODE = '23514';
END $$;

CREATE FUNCTION evidence_lock_building(batch uuid) RETURNS void LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE status text;
BEGIN
    SELECT state INTO status FROM normalization_batches WHERE id = batch FOR UPDATE;
    IF status IS DISTINCT FROM 'building' THEN
        RAISE EXCEPTION 'normalization batch is sealed or missing' USING ERRCODE = '23514';
    END IF;
END $$;

CREATE FUNCTION evidence_integrity() RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE c statement_coverage%ROWTYPE; r fact_resolutions%ROWTYPE; o source_observations%ROWTYPE;
        s semantic_scopes%ROWTYPE; b normalization_batches%ROWTYPE; e filing_events%ROWTYPE;
        issuer uuid; other_issuer uuid; batch uuid; currency units%ROWTYPE; observed_unit units%ROWTYPE;
BEGIN
    IF TG_TABLE_NAME = 'security_relationships' THEN
        SELECT issuer_id INTO issuer FROM securities WHERE id = NEW.security_id;
        SELECT issuer_id INTO other_issuer FROM securities WHERE id = NEW.underlying_security_id;
        IF issuer IS DISTINCT FROM other_issuer THEN RAISE EXCEPTION 'relationship issuer mismatch' USING ERRCODE='23514'; END IF;
    ELSIF TG_TABLE_NAME = 'semantic_scopes' THEN
        IF EXISTS (SELECT FROM semantic_scopes x WHERE x.issuer_id=NEW.issuer_id
                   AND x.descriptor_schema_version=NEW.descriptor_schema_version AND x.content_sha256=NEW.content_sha256
                   AND (x.descriptor_json <> NEW.descriptor_json OR x.instrument_id IS DISTINCT FROM NEW.instrument_id
                        OR x.scope_kind <> NEW.scope_kind)) THEN
            RAISE EXCEPTION 'scope hash collision: different full descriptors' USING ERRCODE='23514';
        END IF;
    ELSIF TG_TABLE_NAME = 'normalization_inputs' THEN
        PERFORM evidence_lock_building(NEW.batch_id);
    ELSIF TG_TABLE_NAME = 'statement_coverage' THEN
        PERFORM evidence_lock_building(NEW.batch_id);
        SELECT * INTO b FROM normalization_batches WHERE id=NEW.batch_id;
        SELECT f.issuer_id INTO issuer FROM filing_versions fv JOIN filings f ON f.id=fv.filing_id WHERE fv.id=NEW.filing_version_id;
        SELECT * INTO s FROM semantic_scopes WHERE id=NEW.scope_id;
        IF b.issuer_id IS DISTINCT FROM issuer OR b.issuer_id IS DISTINCT FROM s.issuer_id THEN
            RAISE EXCEPTION 'coverage filing/scope issuer mismatch' USING ERRCODE='23514';
        END IF;
        IF NEW.currency_unit_id IS NOT NULL THEN
            SELECT * INTO currency FROM units WHERE id=NEW.currency_unit_id;
            IF cardinality(currency.numerator_measures) <> 1 OR cardinality(currency.denominator_measures) <> 0
               OR currency.numerator_measures[1] !~ '^iso4217:[A-Z]{3}$' THEN
                RAISE EXCEPTION 'coverage currency must be a currency unit' USING ERRCODE='23514';
            END IF;
        END IF;
    ELSIF TG_TABLE_NAME = 'source_observations' THEN
        IF NEW.semantic_scope_id IS NOT NULL THEN
            SELECT f.issuer_id INTO issuer FROM filing_versions fv JOIN filings f ON f.id=fv.filing_id WHERE fv.id=NEW.filing_version_id;
            SELECT issuer_id INTO other_issuer FROM semantic_scopes WHERE id=NEW.semantic_scope_id;
            IF issuer IS DISTINCT FROM other_issuer THEN RAISE EXCEPTION 'observation scope issuer mismatch' USING ERRCODE='23514'; END IF;
        END IF;
    ELSIF TG_TABLE_NAME = 'fact_resolutions' THEN
        SELECT * INTO c FROM statement_coverage WHERE id=NEW.coverage_id;
        PERFORM evidence_lock_building(c.batch_id);
        SELECT * INTO s FROM semantic_scopes WHERE id=NEW.semantic_scope_id;
        IF NEW.semantic_scope_id IS DISTINCT FROM c.scope_id OR NEW.instrument_id IS DISTINCT FROM s.instrument_id THEN
            RAISE EXCEPTION 'resolution scope/instrument mismatch' USING ERRCODE='23514';
        END IF;
        IF NEW.selected_observation_id IS NOT NULL THEN
            SELECT * INTO o FROM source_observations WHERE id=NEW.selected_observation_id;
            IF o.filing_version_id IS DISTINCT FROM c.filing_version_id OR o.period_id IS DISTINCT FROM c.period_id
               OR o.unit_id IS DISTINCT FROM NEW.unit_id OR o.semantic_scope_id IS DISTINCT FROM NEW.semantic_scope_id
               OR (NEW.status='observed' AND o.value_state IS DISTINCT FROM 'numeric')
               OR (NEW.status='source_nil' AND o.value_state IS DISTINCT FROM 'source_nil')
               OR c.currency_unit_id IS NULL OR c.coverage_state <> 'covered' THEN
                RAISE EXCEPTION 'selected observation filing/period/unit/scope/state mismatch' USING ERRCODE='23514';
            END IF;
            SELECT * INTO currency FROM units WHERE id=c.currency_unit_id;
            SELECT * INTO observed_unit FROM units WHERE id=NEW.unit_id;
            IF EXISTS (SELECT FROM unnest(observed_unit.numerator_measures) m
                       WHERE m LIKE 'iso4217:%' AND NOT (m=ANY(currency.numerator_measures))) THEN
                RAISE EXCEPTION 'selected observation currency mismatch' USING ERRCODE='23514';
            END IF;
        END IF;
    ELSIF TG_TABLE_NAME = 'resolution_candidates' THEN
        SELECT * INTO r FROM fact_resolutions WHERE id=NEW.resolution_id;
        SELECT * INTO c FROM statement_coverage WHERE id=r.coverage_id;
        PERFORM evidence_lock_building(c.batch_id);
        SELECT b1.issuer_id INTO issuer FROM normalization_batches b1 WHERE b1.id=c.batch_id;
        SELECT f.issuer_id INTO other_issuer FROM source_observations o1 JOIN filing_versions fv ON fv.id=o1.filing_version_id
            JOIN filings f ON f.id=fv.filing_id WHERE o1.id=NEW.observation_id;
        IF issuer IS DISTINCT FROM other_issuer THEN RAISE EXCEPTION 'candidate issuer mismatch' USING ERRCODE='23514'; END IF;
        IF (NEW.disposition='selected') IS DISTINCT FROM (r.selected_observation_id IS NOT DISTINCT FROM NEW.observation_id) THEN
            RAISE EXCEPTION 'selected candidate does not match resolution' USING ERRCODE='23514';
        END IF;
    ELSIF TG_TABLE_NAME = 'data_quality_flags' THEN
        IF NEW.resolution_id IS NOT NULL THEN
            SELECT sc.* INTO c FROM fact_resolutions fr JOIN statement_coverage sc ON sc.id=fr.coverage_id WHERE fr.id=NEW.resolution_id;
            IF NEW.batch_id IS DISTINCT FROM c.batch_id OR (NEW.period_id IS NOT NULL AND NEW.period_id <> c.period_id) THEN
                RAISE EXCEPTION 'flag resolution scope mismatch' USING ERRCODE='23514';
            END IF;
        END IF;
        IF NEW.batch_id IS NOT NULL THEN
            PERFORM evidence_lock_building(NEW.batch_id);
            SELECT issuer_id INTO issuer FROM normalization_batches WHERE id=NEW.batch_id;
            IF NEW.issuer_id IS DISTINCT FROM issuer THEN RAISE EXCEPTION 'flag issuer mismatch' USING ERRCODE='23514'; END IF;
        END IF;
    ELSIF TG_TABLE_NAME = 'filing_events' THEN
        IF NEW.creation_transaction_id IS DISTINCT FROM pg_current_xact_id() THEN
            RAISE EXCEPTION 'event creation transaction must be current' USING ERRCODE='23514';
        END IF;
        SELECT f.issuer_id INTO issuer FROM filing_versions fv JOIN filings f ON f.id=fv.filing_id WHERE fv.id=NEW.source_filing_version_id;
        IF NEW.issuer_id IS DISTINCT FROM issuer THEN RAISE EXCEPTION 'event issuer mismatch' USING ERRCODE='23514'; END IF;
    ELSIF TG_TABLE_NAME = 'filing_event_scopes' THEN
        SELECT * INTO e FROM filing_events WHERE id=NEW.event_id;
        IF e.creation_transaction_id IS DISTINCT FROM pg_current_xact_id() THEN
            RAISE EXCEPTION 'event scope set is sealed after its creation transaction' USING ERRCODE='23514';
        END IF;
        IF e.event_kind IN ('non_reliance', 'withdrawal') AND NEW.filing_id IS NULL THEN
            RAISE EXCEPTION 'non-reliance/withdrawal requires explicit affected filing' USING ERRCODE='23514';
        END IF;
        IF NEW.filing_id IS NOT NULL THEN
            SELECT issuer_id INTO issuer FROM filings WHERE id=NEW.filing_id;
            IF e.issuer_id IS DISTINCT FROM issuer THEN RAISE EXCEPTION 'event scope issuer mismatch' USING ERRCODE='23514'; END IF;
        END IF;
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION evidence_batch_transition() RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE manifest_count integer;
BEGIN
    IF TG_OP='INSERT' THEN
        IF NEW.state <> 'building' THEN RAISE EXCEPTION 'new batch must start building' USING ERRCODE='23514'; END IF;
        RETURN NEW;
    END IF;
    IF TG_OP='DELETE' OR OLD.state <> 'building' THEN
        RAISE EXCEPTION 'completed normalization batch is immutable' USING ERRCODE='23514';
    END IF;
    IF (to_jsonb(NEW) - ARRAY['state','published_at','input_manifest_hash','output_manifest_hash']) <>
       (to_jsonb(OLD) - ARRAY['state','published_at','input_manifest_hash','output_manifest_hash']) THEN
        RAISE EXCEPTION 'batch identity and revisions are immutable' USING ERRCODE='23514';
    END IF;
    IF NEW.state='published' THEN
        SELECT count(*) INTO manifest_count FROM normalization_inputs WHERE batch_id=NEW.id;
        IF manifest_count=0 OR EXISTS (
            SELECT FROM normalization_inputs i JOIN source_captures sc ON sc.id=i.source_capture_id
            WHERE i.batch_id=NEW.id AND (sc.completed_at IS NULL OR sc.fetched_at IS NULL OR
                sc.http_status IS NULL OR sc.http_status NOT BETWEEN 200 AND 299 OR sc.body_sha256 IS NULL
                OR sc.blob_key IS NULL OR sc.byte_count IS NULL)) THEN
            RAISE EXCEPTION 'publication requires successful archived input captures' USING ERRCODE='23514';
        END IF;
        IF EXISTS (
            SELECT FROM statement_coverage c JOIN filing_versions fv ON fv.id=c.filing_version_id
            WHERE c.batch_id=NEW.id AND NOT EXISTS (SELECT FROM normalization_inputs i
                WHERE i.batch_id=NEW.id AND i.source_capture_id=fv.metadata_capture_id)) THEN
            RAISE EXCEPTION 'filing metadata capture is missing from input manifest' USING ERRCODE='23514';
        END IF;
        IF EXISTS (
            SELECT FROM fact_resolutions r JOIN statement_coverage c ON c.id=r.coverage_id
            JOIN source_observations o ON o.id=r.selected_observation_id
            WHERE c.batch_id=NEW.id AND NOT EXISTS (SELECT FROM normalization_inputs i
                WHERE i.batch_id=NEW.id AND i.source_capture_id=o.source_capture_id)) OR EXISTS (
            SELECT FROM resolution_candidates rc JOIN fact_resolutions r ON r.id=rc.resolution_id
            JOIN statement_coverage c ON c.id=r.coverage_id JOIN source_observations o ON o.id=rc.observation_id
            WHERE c.batch_id=NEW.id AND NOT EXISTS (SELECT FROM normalization_inputs i
                WHERE i.batch_id=NEW.id AND i.source_capture_id=o.source_capture_id)) THEN
            RAISE EXCEPTION 'observation capture is missing from input manifest' USING ERRCODE='23514';
        END IF;
        IF EXISTS (SELECT FROM fact_resolutions r JOIN statement_coverage c ON c.id=r.coverage_id
                   WHERE c.batch_id=NEW.id AND r.status <> 'observed' AND NOT EXISTS (
                     SELECT FROM data_quality_flags f WHERE f.resolution_id=r.id AND f.batch_id=NEW.id)) THEN
            RAISE EXCEPTION 'unresolved resolution requires linked quality flag' USING ERRCODE='23514';
        END IF;
        IF NOT EXISTS (SELECT FROM statement_coverage WHERE batch_id=NEW.id) THEN
            RAISE EXCEPTION 'publication requires explicit statement coverage' USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION evidence_event_complete() RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, pg_temp AS $$ BEGIN
    IF NOT EXISTS (SELECT FROM filing_event_scopes WHERE event_id=NEW.id) THEN
        RAISE EXCEPTION 'event requires an explicit affected scope' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE FUNCTION evidence_revision_integrity() RETURNS trigger LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE earlier record; later record; event filing_events%ROWTYPE;
BEGIN
    -- Advisory locks serialize graph writes, but an established fixed snapshot
    -- could otherwise miss an edge committed while this writer waited.
    IF current_setting('transaction_isolation') <> 'read committed' THEN
        RAISE EXCEPTION 'revision graph writes require READ COMMITTED' USING ERRCODE='55000';
    END IF;
    SELECT r.*, c.period_id, c.statement_family, c.reporting_basis, b.issuer_id, fv.filing_id
      INTO earlier FROM fact_resolutions r JOIN statement_coverage c ON c.id=r.coverage_id
      JOIN normalization_batches b ON b.id=c.batch_id JOIN filing_versions fv ON fv.id=c.filing_version_id
      WHERE r.id=NEW.earlier_resolution_id;
    SELECT r.*, c.period_id, c.statement_family, c.reporting_basis, b.issuer_id, fv.filing_id
      INTO later FROM fact_resolutions r JOIN statement_coverage c ON c.id=r.coverage_id
      JOIN normalization_batches b ON b.id=c.batch_id JOIN filing_versions fv ON fv.id=c.filing_version_id
      WHERE r.id=NEW.later_resolution_id;
    IF earlier.issuer_id IS DISTINCT FROM later.issuer_id OR earlier.concept_std IS DISTINCT FROM later.concept_std
       OR earlier.period_id IS DISTINCT FROM later.period_id OR earlier.unit_id IS DISTINCT FROM later.unit_id
       OR earlier.semantic_scope_id IS DISTINCT FROM later.semantic_scope_id
       OR earlier.instrument_id IS DISTINCT FROM later.instrument_id
       OR earlier.statement_family IS DISTINCT FROM later.statement_family
       OR earlier.reporting_basis IS DISTINCT FROM later.reporting_basis THEN
        RAISE EXCEPTION 'revision link must retain entity/concept/period/unit/scope/basis' USING ERRCODE='23514';
    END IF;
    -- Serialize per issuer so concurrent individually acyclic edges cannot make a cycle together.
    PERFORM pg_advisory_xact_lock(hashtextextended(earlier.issuer_id::text, 421));
    IF EXISTS (WITH RECURSIVE reachable(id) AS (
        SELECT NEW.later_resolution_id UNION
        SELECT l.later_resolution_id FROM fact_revision_links l JOIN reachable p ON p.id=l.earlier_resolution_id)
        SELECT FROM reachable WHERE id=NEW.earlier_resolution_id) THEN
        RAISE EXCEPTION 'revision link cycle' USING ERRCODE='23514';
    END IF;
    IF NEW.filing_event_id IS NOT NULL THEN
        SELECT * INTO event FROM filing_events WHERE id=NEW.filing_event_id;
        IF event.issuer_id IS DISTINCT FROM earlier.issuer_id OR
           (NEW.relation_kind='error_restatement' AND event.event_kind <> 'formal_correction') THEN
            RAISE EXCEPTION 'revision event must evidence this issuer and correction type' USING ERRCODE='23514';
        END IF;
        IF NOT EXISTS (SELECT FROM filing_event_scopes s WHERE s.event_id=event.id
                       AND (s.filing_id IS NULL OR s.filing_id=earlier.filing_id)
                       AND (s.period_id IS NULL OR s.period_id=earlier.period_id)
                       AND (s.concept_std IS NULL OR s.concept_std=earlier.concept_std)) THEN
            RAISE EXCEPTION 'revision event does not cover the original resolution' USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END $$;
"""

# Each FK has a leading-key index (including joins whose PK covers the first FK).
INDEXES = {
    "securities": ["issuer_id", "underlying_security_id"],
    "source_captures": ["source_id, source_object_key, fetched_at"],
    "security_identifiers": ["security_id", "source_capture_id"],
    "security_identifier_validity": ["security_id"],
    "security_identifier_closures": ["source_capture_id"],
    "security_relationships": ["security_id", "underlying_security_id", "source_capture_id"],
    "filing_versions": ["filing_id, filed_date", "metadata_capture_id"],
    "semantic_scopes": ["instrument_id"],
    "normalization_batches": ["issuer_id, state", "mapping_revision_id"],
    "normalization_inputs": ["source_capture_id"],
    "statement_coverage": ["filing_version_id", "period_id", "scope_id", "currency_unit_id"],
    "source_observations": ["filing_version_id", "period_id", "unit_id", "semantic_scope_id"],
    "fact_resolutions": ["semantic_scope_id", "instrument_id", "unit_id", "selected_observation_id"],
    "resolution_candidates": ["observation_id"],
    "data_quality_flags": ["batch_id", "resolution_id", "issuer_id", "security_id", "period_id"],
    "quality_flag_acknowledgements": ["flag_id"],
    "filing_events": ["issuer_id, announced_date", "source_filing_version_id"],
    "filing_event_scopes": ["filing_id", "period_id"],
    "fact_revision_links": ["later_resolution_id", "filing_event_id"],
}


def upgrade() -> None:
    concepts = ", ".join("'" + concept + "'" for concept in CONCEPT_VALUES)
    op.execute(DDL.replace("__CONCEPTS__", concepts))
    op.execute(GUARDS)
    for table in TABLES:
        if table not in {"normalization_batches", "security_identifier_validity"}:
            op.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                       "FOR EACH ROW EXECUTE FUNCTION evidence_immutable()")
        op.execute(f"GRANT SELECT ON {table} TO equity_runtime")
        if table not in {"sources", "mapping_revisions", "security_identifier_validity", "security_identifier_closures"}:
            op.execute(f"GRANT INSERT ON {table} TO equity_runtime")
    op.execute("CREATE TRIGGER security_identifiers_seed_validity AFTER INSERT ON security_identifiers "
               "FOR EACH ROW EXECUTE FUNCTION evidence_quote_projection_seed()")
    op.execute("CREATE TRIGGER security_identifier_validity_guard BEFORE INSERT OR UPDATE OR DELETE "
               "ON security_identifier_validity FOR EACH ROW EXECUTE FUNCTION evidence_quote_projection_guard()")
    op.execute("REVOKE ALL ON FUNCTION close_security_identifier(uuid,date,uuid) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION close_security_identifier(uuid,date,uuid) TO equity_runtime")
    for table in (
        "security_relationships", "semantic_scopes", "normalization_inputs", "statement_coverage",
        "source_observations", "fact_resolutions", "resolution_candidates", "data_quality_flags",
        "filing_events", "filing_event_scopes",
    ):
        op.execute(f"CREATE TRIGGER {table}_integrity BEFORE INSERT ON {table} "
                   "FOR EACH ROW EXECUTE FUNCTION evidence_integrity()")
    op.execute("CREATE TRIGGER normalization_batches_transition BEFORE INSERT OR UPDATE OR DELETE "
               "ON normalization_batches FOR EACH ROW EXECUTE FUNCTION evidence_batch_transition()")
    op.execute("CREATE CONSTRAINT TRIGGER filing_events_complete AFTER INSERT ON filing_events "
               "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION evidence_event_complete()")
    op.execute("CREATE TRIGGER fact_revision_links_integrity BEFORE INSERT ON fact_revision_links "
               "FOR EACH ROW EXECUTE FUNCTION evidence_revision_integrity()")
    op.execute("GRANT UPDATE (state, published_at, input_manifest_hash, output_manifest_hash) "
               "ON normalization_batches TO equity_runtime")
    for table, columns in INDEXES.items():
        for index, names in enumerate(columns):
            op.execute(f"CREATE INDEX {table}_fk_{index} ON {table} ({names})")
    # Trigger functions are invoked by triggers; they are not public RPC endpoints.
    for signature in (
        "evidence_quote_projection_guard()", "evidence_quote_projection_seed()",
        "evidence_immutable()", "evidence_lock_building(uuid)", "evidence_integrity()",
        "evidence_batch_transition()", "evidence_revision_integrity()", "evidence_event_complete()",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")


def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE {table}")
    for signature in (
        "close_security_identifier(uuid,date,uuid)", "evidence_quote_projection_guard()",
        "evidence_quote_projection_seed()",
        "evidence_revision_integrity()", "evidence_event_complete()", "evidence_batch_transition()", "evidence_integrity()",
        "evidence_lock_building(uuid)", "evidence_immutable()", "evidence_finite(numeric)",
    ):
        op.execute(f"DROP FUNCTION {signature}")
    # The cluster-scoped role and possibly pre-existing extension are deliberately retained.
