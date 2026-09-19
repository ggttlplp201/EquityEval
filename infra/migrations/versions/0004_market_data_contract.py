"""S4 typed market evidence, retained rights and immutable W1 source plans."""

from alembic import op

revision = "0004_market_data_contract"
down_revision = "0003_source_ingestion"
branch_labels = None
depends_on = None

PRICE_FIELDS = (
    "open", "high", "low", "close", "volume", "adj_open", "adj_high", "adj_low",
    "adj_close", "adj_volume", "div_cash", "split_factor",
)
TABLES = (
    "source_policy_capabilities", "provider_quote_bindings", "macro_series_definitions",
    "market_data_batches", "market_data_batch_inputs", "market_data_quality_flags",
    "price_daily", "macro_observations",
)

SQL = r"""
CREATE FUNCTION market_keys_valid(keys text[], empty_ok boolean) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
 SELECT keys IS NOT NULL AND (empty_ok OR cardinality(keys)>0)
 AND array_position(keys,NULL) IS NULL
 AND NOT EXISTS(SELECT FROM unnest(keys) k WHERE btrim(k)='' OR k<>btrim(k))
 AND cardinality(keys)=(SELECT count(DISTINCT k) FROM unnest(keys) k)
$$;
CREATE FUNCTION market_numeric_valid(value numeric,state text,lexical text,macro boolean) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
 SELECT coalesce(CASE WHEN state='observed' THEN value IS NOT NULL AND evidence_finite(value)
     AND lexical IS NOT NULL AND btrim(lexical)<>''
 WHEN state='unparseable' THEN value IS NULL
 WHEN macro AND state='source_missing' THEN value IS NULL
 WHEN NOT macro AND state='source_null' THEN value IS NULL AND lexical='null'
 WHEN NOT macro AND state='missing' THEN value IS NULL AND lexical IS NULL
 ELSE false END,false)
$$;
CREATE FUNCTION market_precision_valid(p_precision text,day date,instant timestamptz) RETURNS boolean
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
 SELECT coalesce((p_precision='unknown' AND day IS NULL AND instant IS NULL)
 OR (p_precision='date' AND day IS NOT NULL AND isfinite(day) AND instant IS NULL)
 OR (p_precision='instant' AND instant IS NOT NULL AND isfinite(instant)
     AND (day IS NULL OR isfinite(day))),false)
$$;
ALTER TABLE source_policy_revisions ADD CONSTRAINT market_policy_source UNIQUE(id,source_id);
CREATE TABLE source_policy_capabilities (
 policy_revision_id uuid PRIMARY KEY,source_id uuid NOT NULL REFERENCES sources(id),
 raw_scope_kind text NOT NULL CHECK(raw_scope_kind IN ('source','source_objects','macro_series')),
 raw_scope_keys text[] NOT NULL,normalized_scope_kind text NOT NULL
 CHECK(normalized_scope_kind IN ('source','source_objects','macro_series')),normalized_scope_keys text[] NOT NULL,
 raw_retention text NOT NULL CHECK(raw_retention IN ('indefinite_without_required_deletion','time_limited','forbidden','unreviewed')),
 normalized_retention text NOT NULL CHECK(normalized_retention IN ('indefinite_without_required_deletion','time_limited','forbidden','unreviewed')),
 internal_analysis_allowed boolean NOT NULL,review_valid_until timestamptz CHECK(isfinite(review_valid_until)),
 review_basis text NOT NULL CHECK(btrim(review_basis)<>''),activated_at timestamptz,activated_by text,activation_reason text,
 disabled_at timestamptz,disabled_by text,disable_reason text,
 FOREIGN KEY(policy_revision_id,source_id) REFERENCES source_policy_revisions(id,source_id),
 CHECK(market_keys_valid(raw_scope_keys,raw_scope_kind='source') AND ((raw_scope_kind='source')=(cardinality(raw_scope_keys)=0))),
 CHECK(market_keys_valid(normalized_scope_keys,normalized_scope_kind='source') AND ((normalized_scope_kind='source')=(cardinality(normalized_scope_keys)=0))),
 CHECK((activated_at IS NULL AND activated_by IS NULL AND activation_reason IS NULL) OR
 (activated_at IS NOT NULL AND isfinite(activated_at) AND btrim(activated_by)<>'' AND activated_by IS NOT NULL
 AND activation_reason IS NOT NULL AND btrim(activation_reason)<>'')),
 CHECK((disabled_at IS NULL AND disabled_by IS NULL AND disable_reason IS NULL) OR
 (disabled_at IS NOT NULL AND isfinite(disabled_at) AND activated_at IS NOT NULL AND disabled_at>=activated_at
 AND disabled_by IS NOT NULL AND btrim(disabled_by)<>'' AND disable_reason IS NOT NULL AND btrim(disable_reason)<>''))
);
CREATE UNIQUE INDEX market_one_active_policy ON source_policy_capabilities(source_id)
 WHERE activated_at IS NOT NULL AND disabled_at IS NULL;
CREATE INDEX market_capability_source ON source_policy_capabilities(source_id);
CREATE TABLE provider_quote_bindings (
 id uuid PRIMARY KEY,source_id uuid NOT NULL REFERENCES sources(id),quote_identifier_id uuid NOT NULL,security_id uuid NOT NULL,
 provider_symbol text NOT NULL CHECK(btrim(provider_symbol)<>''),provider_instrument_key text CHECK(btrim(provider_instrument_key)<>''),
 valid_from date NOT NULL CHECK(isfinite(valid_from)),valid_to date CHECK(isfinite(valid_to) AND valid_to>valid_from),
 identity_capture_id uuid NOT NULL REFERENCES source_captures(id),source_locator text NOT NULL CHECK(btrim(source_locator)<>''),
 identity_review_revision text NOT NULL CHECK(btrim(identity_review_revision)<>''),reviewed_at timestamptz NOT NULL CHECK(isfinite(reviewed_at)),
 reviewed_by text NOT NULL CHECK(btrim(reviewed_by)<>''),content_sha256 text NOT NULL CHECK(content_sha256 ~ '^[0-9a-f]{64}$'),
 FOREIGN KEY(quote_identifier_id,security_id) REFERENCES security_identifiers(id,security_id),
 UNIQUE(source_id,quote_identifier_id,content_sha256),UNIQUE(id,source_id,quote_identifier_id,security_id)
);
CREATE TABLE macro_series_definitions (
 id uuid PRIMARY KEY,source_id uuid NOT NULL REFERENCES sources(id),source_series_key text NOT NULL CHECK(btrim(source_series_key)<>''),
 metadata_capture_id uuid NOT NULL REFERENCES source_captures(id),source_locator text NOT NULL CHECK(btrim(source_locator)<>''),
 content_sha256 text NOT NULL CHECK(content_sha256 ~ '^[0-9a-f]{64}$'),definition_revision text NOT NULL CHECK(btrim(definition_revision)<>''),
 title text NOT NULL CHECK(btrim(title)<>''),units_text text NOT NULL CHECK(btrim(units_text)<>''),
 unit_code text NOT NULL CHECK(unit_code IN ('percent_per_year','percent','percentage_points','basis_points','index','count')),
 unit_multiplier numeric NOT NULL CHECK(evidence_finite(unit_multiplier) AND unit_multiplier>0),
 frequency text NOT NULL CHECK(frequency IN ('daily','business_day','weekly','monthly','quarterly','annual')),
 seasonal_adjustment text NOT NULL CHECK(seasonal_adjustment IN ('adjusted','not_adjusted','not_applicable','unknown')),
 geography text NOT NULL CHECK(btrim(geography)<>''),reference_date_convention text NOT NULL CHECK(btrim(reference_date_convention)<>''),
 source_release_key text,upstream_source_name text NOT NULL CHECK(btrim(upstream_source_name)<>''),
 upstream_rights_reference text NOT NULL CHECK(btrim(upstream_rights_reference)<>''),definition_as_of_date date CHECK(isfinite(definition_as_of_date)),
 definition_as_of_basis text NOT NULL CHECK(definition_as_of_basis IN ('source_supplied','capture_only','unknown')),
 CHECK((definition_as_of_basis='source_supplied')=(definition_as_of_date IS NOT NULL)),
 UNIQUE(source_id,source_series_key,metadata_capture_id,source_locator,definition_revision),UNIQUE(id,source_id,source_series_key)
);
CREATE TABLE market_data_batches (
 id uuid PRIMARY KEY,data_kind text NOT NULL CHECK(data_kind IN ('price','macro')),source_id uuid NOT NULL REFERENCES sources(id),
 policy_revision_id uuid NOT NULL REFERENCES source_policy_capabilities(policy_revision_id),
 quote_identifier_id uuid,security_id uuid,quote_binding_id uuid,source_series_key text,series_definition_id uuid,
 requested_start date NOT NULL CHECK(isfinite(requested_start)),requested_end date NOT NULL CHECK(isfinite(requested_end)),
 source_vintage_mode text NOT NULL CHECK(source_vintage_mode IN ('current_provider_history','source_as_of_date')),
 source_as_of_date date CHECK(isfinite(source_as_of_date)),retrieval_cutoff timestamptz CHECK(isfinite(retrieval_cutoff)),
 parser_revision text NOT NULL CHECK(btrim(parser_revision)<>''),normalizer_revision text NOT NULL CHECK(btrim(normalizer_revision)<>''),
 selection_policy_revision text NOT NULL CHECK(btrim(selection_policy_revision)<>''),
 input_manifest_hash text NOT NULL CHECK(input_manifest_hash ~ '^[0-9a-f]{64}$'),output_manifest_hash text NOT NULL CHECK(output_manifest_hash ~ '^[0-9a-f]{64}$'),
 manifest_blob_key text NOT NULL CHECK(btrim(manifest_blob_key)<>''),manifest_body_sha256 text NOT NULL CHECK(manifest_body_sha256 ~ '^[0-9a-f]{64}$'),
 manifest_byte_count bigint NOT NULL CHECK(manifest_byte_count>0),origin_stage_attempt_id uuid NOT NULL REFERENCES analysis_stage_attempts(id),
 created_at timestamptz NOT NULL CHECK(isfinite(created_at)),published_at timestamptz,
 state text NOT NULL CHECK(state IN ('building','published','failed')),
 coverage_state text NOT NULL CHECK(coverage_state IN ('complete','partial','unknown','unavailable')),
 FOREIGN KEY(quote_identifier_id,security_id) REFERENCES security_identifiers(id,security_id),
 FOREIGN KEY(quote_binding_id,source_id,quote_identifier_id,security_id) REFERENCES provider_quote_bindings(id,source_id,quote_identifier_id,security_id),
 FOREIGN KEY(series_definition_id,source_id,source_series_key) REFERENCES macro_series_definitions(id,source_id,source_series_key),
 CHECK(requested_start<=requested_end),CHECK((source_vintage_mode='source_as_of_date')=(source_as_of_date IS NOT NULL)),
 CHECK((data_kind='price' AND security_id IS NOT NULL AND quote_identifier_id IS NOT NULL AND source_series_key IS NULL AND series_definition_id IS NULL)
 OR(data_kind='macro' AND security_id IS NULL AND quote_identifier_id IS NULL AND quote_binding_id IS NULL AND source_series_key IS NOT NULL AND btrim(source_series_key)<>'')),
 CHECK((state='published' AND published_at IS NOT NULL AND isfinite(published_at) AND published_at>=created_at)
 OR(state<>'published' AND published_at IS NULL))
);
CREATE UNIQUE INDEX market_published_input ON market_data_batches(source_id,input_manifest_hash) WHERE state='published';
CREATE TABLE market_data_batch_inputs (
 id uuid PRIMARY KEY,batch_id uuid NOT NULL REFERENCES market_data_batches(id),capture_id uuid REFERENCES source_captures(id),
 attempt_id uuid REFERENCES source_fetch_attempts(id),role text NOT NULL
 CHECK(role IN ('observations','series_definition','quote_identity','calendar','corporate_action_evidence','fetch_outcome')),
 CHECK((capture_id IS NULL)<>(attempt_id IS NULL)),CHECK(attempt_id IS NULL OR role='fetch_outcome')
);
CREATE UNIQUE INDEX market_capture_input ON market_data_batch_inputs(batch_id,capture_id,role) WHERE capture_id IS NOT NULL;
CREATE UNIQUE INDEX market_attempt_input ON market_data_batch_inputs(batch_id,attempt_id,role) WHERE attempt_id IS NOT NULL;
CREATE TABLE market_data_quality_flags (
 id uuid PRIMARY KEY,batch_id uuid NOT NULL REFERENCES market_data_batches(id),reference_date date CHECK(isfinite(reference_date)),
 field_key text CHECK(field_key IN ('open','high','low','close','volume','adj_open','adj_high','adj_low','adj_close','adj_volume','div_cash','split_factor','value')),
 rule_key text NOT NULL CHECK(btrim(rule_key)<>''),severity text NOT NULL CHECK(severity IN ('info','warning','error','blocking')),
 message text NOT NULL CHECK(btrim(message)<>''),capture_id uuid REFERENCES source_captures(id),attempt_id uuid REFERENCES source_fetch_attempts(id),
 source_locator text CHECK(btrim(source_locator)<>''),raised_at timestamptz NOT NULL CHECK(isfinite(raised_at)),
 CHECK(source_locator IS NULL OR capture_id IS NOT NULL)
);
CREATE TABLE price_daily (
 id uuid NOT NULL,session_date date NOT NULL CHECK(isfinite(session_date)),PRIMARY KEY(session_date,id),
 batch_id uuid NOT NULL REFERENCES market_data_batches(id),source_capture_id uuid NOT NULL REFERENCES source_captures(id),
 source_locator text NOT NULL CHECK(btrim(source_locator)<>''),quote_binding_id uuid NOT NULL REFERENCES provider_quote_bindings(id),
 quote_identifier_id uuid NOT NULL,security_id uuid NOT NULL,quote_currency text NOT NULL CHECK(quote_currency ~ '^[A-Z]{3}$'),
 dividend_currency text CHECK(dividend_currency ~ '^[A-Z]{3}$'),source_date_text text NOT NULL CHECK(btrim(source_date_text)<>''),
 session_basis text NOT NULL CHECK(session_basis='provider_daily_label'),session_timezone text,
 source_published_date date,source_published_at timestamptz,publication_precision text NOT NULL,
 __PRICE_FIELDS__
 adjustment_basis text NOT NULL CHECK(adjustment_basis IN ('split_and_dividend','split_only','unadjusted','unknown')),
 adjustment_vintage_basis text NOT NULL CHECK(adjustment_vintage_basis IN ('provider_supplied','capture_only','unknown')),
 adjustment_vintage_date date CHECK(isfinite(adjustment_vintage_date)),transform_revision text NOT NULL CHECK(btrim(transform_revision)<>''),
 FOREIGN KEY(quote_identifier_id,security_id) REFERENCES security_identifiers(id,security_id),
 CHECK((adjustment_vintage_basis='provider_supplied')=(adjustment_vintage_date IS NOT NULL)),
 CHECK(market_precision_valid(publication_precision,source_published_date,source_published_at)),
 CHECK(volume IS NULL OR volume>=0),CHECK(adj_volume IS NULL OR adj_volume>=0),CHECK(split_factor IS NULL OR split_factor>0),
 UNIQUE(batch_id,source_capture_id,source_locator,session_date)
);
CREATE TABLE macro_observations (
 id uuid NOT NULL,reference_date date NOT NULL CHECK(isfinite(reference_date)),PRIMARY KEY(reference_date,id),
 batch_id uuid NOT NULL REFERENCES market_data_batches(id),series_definition_id uuid NOT NULL REFERENCES macro_series_definitions(id),
 source_capture_id uuid NOT NULL REFERENCES source_captures(id),source_locator text NOT NULL CHECK(btrim(source_locator)<>''),
 source_date_text text NOT NULL CHECK(btrim(source_date_text)<>''),value numeric,value_state text NOT NULL,original_value_text text,
 source_observation_status text,transform_revision text NOT NULL CHECK(btrim(transform_revision)<>''),
 reference_end_date date CHECK(isfinite(reference_end_date) AND reference_end_date>=reference_date),
 source_realtime_start date CHECK(isfinite(source_realtime_start)),source_realtime_end date CHECK(isfinite(source_realtime_end)),
 source_vintage_basis text NOT NULL CHECK(source_vintage_basis IN ('source_interval','requested_as_of','current_only','unknown')),
 requested_source_as_of date CHECK(isfinite(requested_source_as_of)),source_published_date date,source_published_at timestamptz,
 publication_precision text NOT NULL,CHECK(market_numeric_valid(value,value_state,original_value_text,true)),
 CHECK((source_realtime_start IS NULL)=(source_realtime_end IS NULL)),
 CHECK(source_realtime_end IS NULL OR source_realtime_end>=source_realtime_start),
 CHECK(source_vintage_basis<>'source_interval' OR source_realtime_start IS NOT NULL),
 CHECK(source_vintage_basis<>'requested_as_of' OR requested_source_as_of IS NOT NULL),
 CHECK(source_vintage_basis NOT IN ('current_only','unknown') OR requested_source_as_of IS NULL),
 CHECK(source_vintage_basis<>'unknown' OR source_realtime_start IS NULL),
 CHECK(market_precision_valid(publication_precision,source_published_date,source_published_at)),
 UNIQUE(batch_id,source_capture_id,source_locator,reference_date)
);
ALTER TABLE analysis_requests
 ADD COLUMN market_plan_revision text CHECK(market_plan_revision='s4-market-data-v1'),
 ADD COLUMN price_source_id uuid REFERENCES sources(id),ADD COLUMN price_start date,ADD COLUMN price_end date,
 ADD COLUMN macro_source_id uuid REFERENCES sources(id),ADD COLUMN macro_series_keys text[],
 ADD COLUMN macro_start date,ADD COLUMN macro_end date,ADD COLUMN macro_source_as_of_date date,
 ADD CONSTRAINT market_request_shape CHECK(
 ((market_plan_revision IS NOT NULL)=(price_source_id IS NOT NULL OR macro_source_id IS NOT NULL)) AND
 ((price_source_id IS NULL AND price_start IS NULL AND price_end IS NULL) OR
 (price_source_id IS NOT NULL AND price_start IS NOT NULL AND price_end IS NOT NULL AND isfinite(price_start) AND isfinite(price_end) AND price_start<=price_end)) AND
 ((macro_source_id IS NULL AND macro_start IS NULL AND macro_end IS NULL AND macro_source_as_of_date IS NULL AND coalesce(cardinality(macro_series_keys),0)=0) OR
 (macro_source_id IS NOT NULL AND macro_start IS NOT NULL AND macro_end IS NOT NULL AND isfinite(macro_start) AND isfinite(macro_end) AND macro_start<=macro_end
 AND market_keys_valid(macro_series_keys,false) AND (macro_source_as_of_date IS NULL OR isfinite(macro_source_as_of_date))))
 );
CREATE INDEX market_request_price_source ON analysis_requests(price_source_id);
CREATE INDEX market_request_macro_source ON analysis_requests(macro_source_id);
"""

POLICY_SQL = r"""
CREATE FUNCTION market_validate_policy(p_policy uuid,p_source uuid,p_object_key text,p_series_key text DEFAULT NULL,
 p_normalized boolean DEFAULT false,p_require_active boolean DEFAULT true) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE cap source_policy_capabilities%ROWTYPE; kind text; keys text[];
BEGIN
 IF EXISTS(SELECT FROM source_policy_revisions WHERE id=p_policy AND source_id<>p_source) THEN
  RAISE EXCEPTION 'market policy source mismatch' USING ERRCODE='23514'; END IF;
 SELECT * INTO cap FROM source_policy_capabilities WHERE policy_revision_id=p_policy AND source_id=p_source FOR SHARE;
 IF NOT FOUND OR cap.raw_retention<>'indefinite_without_required_deletion'
 OR cap.normalized_retention<>'indefinite_without_required_deletion' OR NOT cap.internal_analysis_allowed THEN
  RAISE EXCEPTION 'market policy has no compatible retained-content grant' USING ERRCODE='23514'; END IF;
 IF p_require_active AND (cap.activated_at IS NULL OR cap.activated_at>clock_timestamp() OR cap.disabled_at IS NOT NULL
 OR (cap.review_valid_until IS NOT NULL AND cap.review_valid_until<=clock_timestamp())) THEN
  RAISE EXCEPTION 'market source policy is inactive or expired' USING ERRCODE='55000'; END IF;
 kind:=CASE WHEN p_normalized THEN cap.normalized_scope_kind ELSE cap.raw_scope_kind END;
 keys:=CASE WHEN p_normalized THEN cap.normalized_scope_keys ELSE cap.raw_scope_keys END;
 IF kind<>'source' AND NOT coalesce(CASE WHEN kind='source_objects' THEN p_object_key=ANY(keys)
 ELSE p_series_key=ANY(keys) AND (p_normalized OR p_series_key=p_object_key) END,false) THEN
  RAISE EXCEPTION 'market resource is outside reviewed policy scope' USING ERRCODE='23514'; END IF;
 RETURN true;
END $$;
CREATE FUNCTION market_capability_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$ BEGIN
 IF TG_OP='DELETE' THEN RAISE EXCEPTION 'market capability history is immutable' USING ERRCODE='55000'; END IF;
 IF TG_OP='INSERT' THEN
  IF NEW.activated_at IS NOT NULL OR NEW.disabled_at IS NOT NULL THEN
   RAISE EXCEPTION 'capability must start inactive' USING ERRCODE='23514'; END IF;
 ELSE
  IF (to_jsonb(NEW)-ARRAY['activated_at','activated_by','activation_reason','disabled_at','disabled_by','disable_reason'])
    IS DISTINCT FROM (to_jsonb(OLD)-ARRAY['activated_at','activated_by','activation_reason','disabled_at','disabled_by','disable_reason'])
  OR (OLD.activated_at IS NOT NULL AND (NEW.activated_at IS DISTINCT FROM OLD.activated_at
    OR NEW.activated_by IS DISTINCT FROM OLD.activated_by OR NEW.activation_reason IS DISTINCT FROM OLD.activation_reason))
  OR OLD.disabled_at IS NOT NULL OR (OLD.activated_at IS NULL AND NEW.activated_at IS NULL)
  OR (OLD.activated_at IS NOT NULL AND NEW.disabled_at IS NULL) THEN
   RAISE EXCEPTION 'market capability only activates or disables once' USING ERRCODE='55000'; END IF;
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER market_capability_transition BEFORE INSERT OR UPDATE OR DELETE ON source_policy_capabilities
 FOR EACH ROW EXECUTE FUNCTION market_capability_guard();
CREATE FUNCTION market_activate_policy(p_policy uuid,p_actor text,p_reason text) RETURNS boolean
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE cap source_policy_capabilities%ROWTYPE;
BEGIN
 SELECT * INTO cap FROM source_policy_capabilities WHERE policy_revision_id=p_policy;
 IF NOT FOUND THEN RAISE EXCEPTION 'unknown market capability' USING ERRCODE='23503'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(cap.source_id::text,904));
 SELECT * INTO cap FROM source_policy_capabilities WHERE policy_revision_id=p_policy FOR UPDATE;
 IF cap.activated_at IS NOT NULL OR cap.disabled_at IS NOT NULL THEN RAISE EXCEPTION 'policy cannot reactivate' USING ERRCODE='55000'; END IF;
 IF p_actor IS NULL OR btrim(p_actor)='' OR p_reason IS NULL OR btrim(p_reason)='' OR
 cap.raw_retention<>'indefinite_without_required_deletion' OR cap.normalized_retention<>'indefinite_without_required_deletion'
 OR NOT cap.internal_analysis_allowed OR (cap.review_valid_until IS NOT NULL AND cap.review_valid_until<=clock_timestamp()) THEN
  RAISE EXCEPTION 'invalid activation or retention grant' USING ERRCODE='23514'; END IF;
 UPDATE source_policy_capabilities SET disabled_at=clock_timestamp(),disabled_by=p_actor,disable_reason='Replaced: '||p_reason
  WHERE source_id=cap.source_id AND activated_at IS NOT NULL AND disabled_at IS NULL;
 UPDATE source_policy_capabilities SET activated_at=clock_timestamp(),activated_by=p_actor,activation_reason=p_reason WHERE policy_revision_id=p_policy;
 RETURN true;
END $$;
CREATE FUNCTION market_disable_policy(p_policy uuid,p_actor text,p_reason text) RETURNS boolean
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE source uuid;
BEGIN
 SELECT source_id INTO source FROM source_policy_capabilities WHERE policy_revision_id=p_policy;
 IF source IS NULL THEN RAISE EXCEPTION 'unknown market capability' USING ERRCODE='23503'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(source::text,904));
 IF p_actor IS NULL OR btrim(p_actor)='' OR p_reason IS NULL OR btrim(p_reason)='' THEN
  RAISE EXCEPTION 'disable requires actor and reason' USING ERRCODE='23514'; END IF;
 UPDATE source_policy_capabilities SET disabled_at=clock_timestamp(),disabled_by=p_actor,disable_reason=p_reason
  WHERE policy_revision_id=p_policy AND activated_at IS NOT NULL AND disabled_at IS NULL;
 IF NOT FOUND THEN RAISE EXCEPTION 'policy is not active' USING ERRCODE='55000'; END IF;
 RETURN true;
END $$;
CREATE FUNCTION market_sec_resource(p_source uuid,p_policy uuid,p_url text,p_object text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
 SELECT EXISTS(SELECT FROM sources s JOIN source_policy_revisions p ON p.source_id=s.id
  WHERE s.id=p_source AND p.id=p_policy AND s.base_url IN ('https://data.sec.gov','https://www.sec.gov')
  AND split_part(p_object,'/',2) ~ '^[0-9]{10}$' AND split_part(p_object,'/',2)<>'0000000000'
  AND ((p_object ~ '^company_facts/[0-9]{10}$'
     AND p_url='https://data.sec.gov/api/xbrl/companyfacts/CIK'||split_part(p_object,'/',2)||'.json')
    OR(p_object ~ '^submissions/[0-9]{10}$'
     AND p_url='https://data.sec.gov/submissions/CIK'||split_part(p_object,'/',2)||'.json')
    OR(p_object ~ '^submissions_history/[0-9]{10}/CIK[0-9]{10}-submissions-[0-9]+[.]json$'
     AND split_part(p_object,'/',3) ~ ('^CIK'||split_part(p_object,'/',2)||'-submissions-[0-9]+[.]json$')
     AND p_url='https://data.sec.gov/submissions/'||split_part(p_object,'/',3))
    OR(p_object ~ '^filing_document/[0-9]{10}/[0-9]{10}-[0-9]{2}-[0-9]{6}/[A-Za-z0-9][A-Za-z0-9_.-]*[.](htm|html|xml|txt|xsd)$'
     AND position('..' in split_part(p_object,'/',4))=0
     AND p_url='https://www.sec.gov/Archives/edgar/data/'||ltrim(split_part(p_object,'/',2),'0')||'/'||
       replace(split_part(p_object,'/',3),'-','')||'/'||split_part(p_object,'/',4))))
$$;
CREATE FUNCTION market_validate_resource(p_source uuid,p_url text,p_object text) RETURNS boolean
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE base text; source_origin text; url_origin text; object_origin text; origin text; symbol text;
BEGIN
 SELECT rtrim(base_url,'/') INTO base FROM sources WHERE id=p_source;
 IF base IS NULL THEN RAISE EXCEPTION 'market resource source is unknown' USING ERRCODE='23514'; END IF;
 source_origin:=CASE
  WHEN base ~* '^https://home[.]treasury[.]gov([/:?#]|$)' THEN 'https://home.treasury.gov'
  WHEN base ~* '^https://api[.]tiingo[.]com([/:?#]|$)' THEN 'https://api.tiingo.com'
  WHEN base ~* '^https://api[.]stlouisfed[.]org([/:?#]|$)' THEN 'https://api.stlouisfed.org' END;
 url_origin:=CASE
  WHEN p_url ~* '^https://home[.]treasury[.]gov([/:?#]|$)' THEN 'https://home.treasury.gov'
  WHEN p_url ~* '^https://api[.]tiingo[.]com([/:?#]|$)' THEN 'https://api.tiingo.com'
  WHEN p_url ~* '^https://api[.]stlouisfed[.]org([/:?#]|$)' THEN 'https://api.stlouisfed.org' END;
 object_origin:=CASE
  WHEN p_object='daily_treasury_yield_curve' THEN 'https://home.treasury.gov'
  WHEN p_object='tiingo_eod' OR p_object LIKE 'tiingo_eod/%' THEN 'https://api.tiingo.com'
  WHEN p_object='fred_observations' OR p_object LIKE 'fred_observations/%' THEN 'https://api.stlouisfed.org' END;
 origin:=coalesce(source_origin,url_origin,object_origin);
 IF origin IS NULL THEN RETURN true; END IF;
 IF source_origin IS DISTINCT FROM origin OR url_origin IS DISTINCT FROM origin
 OR (object_origin IS NOT NULL AND object_origin<>origin)
 OR (base<>origin AND left(base,length(origin)+1)<>origin||'/')
 OR (p_url<>base AND left(p_url,length(base)+1)<>base||'/')
 OR p_url !~ '^https://[^/?#@[:space:]]+/[^?#[:space:]]*$'
 OR base ~ '[?#@[:space:]]' OR position('..' in p_url)>0
 OR position('%' in p_url)>0 OR position(chr(92) in p_url)>0 THEN
  RAISE EXCEPTION 'market resource URL differs from its registered provider' USING ERRCODE='23514'; END IF;
 -- A known observation endpoint cannot be relabelled as metadata. Metadata
 -- objects under the same reviewed source still require that canonical origin.
 IF origin='https://home.treasury.gov' AND
  (object_origin IS NOT NULL OR p_url ~ '^https://home[.]treasury[.]gov/resource-center/data-chart-center/interest-rates/pages/xml/?$') THEN
  IF p_object<>'daily_treasury_yield_curve'
   OR p_url<>'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml' THEN
   RAISE EXCEPTION 'market resource Treasury object and URL differ' USING ERRCODE='23514'; END IF;
 ELSIF origin='https://api.tiingo.com' AND
  (object_origin IS NOT NULL OR p_url ~ '^https://api[.]tiingo[.]com/tiingo/daily/[^/]+/prices/?$') THEN
  symbol:=split_part(p_object,'/',2);
  IF p_object !~ '^tiingo_eod/[A-Z0-9][A-Z0-9.-]{0,19}$' OR position('..' in symbol)>0
   OR p_url<>'https://api.tiingo.com/tiingo/daily/'||symbol||'/prices' THEN
   RAISE EXCEPTION 'market resource Tiingo symbol and URL differ' USING ERRCODE='23514'; END IF;
 ELSIF origin='https://api.stlouisfed.org' AND
  (object_origin IS NOT NULL OR p_url ~ '^https://api[.]stlouisfed[.]org/fred/series/observations/?$') THEN
  IF p_object !~ '^fred_observations/[A-Za-z0-9_]{1,80}$'
   OR p_url<>'https://api.stlouisfed.org/fred/series/observations' THEN
   RAISE EXCEPTION 'market resource FRED object and URL differ' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN true;
END $$;
CREATE FUNCTION market_attempt_policy_guard() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$ BEGIN
 IF market_sec_resource(NEW.source_id,NEW.policy_revision_id,NEW.request_url,NEW.source_object_key) THEN RETURN NEW; END IF;
 PERFORM market_validate_resource(NEW.source_id,NEW.request_url,NEW.source_object_key);
 IF TG_OP='INSERT' OR (TG_OP='UPDATE' AND OLD.state='prepared' AND NEW.state='in_progress') THEN
  PERFORM market_validate_policy(NEW.policy_revision_id,NEW.source_id,NEW.source_object_key,NULL,false,true);
 ELSIF NEW.completed_capture_id IS NOT NULL OR NEW.reused_capture_id IS NOT NULL THEN
  PERFORM market_validate_policy(NEW.policy_revision_id,NEW.source_id,NEW.source_object_key,NULL,false,false);
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER market_attempt_policy BEFORE INSERT OR UPDATE ON source_fetch_attempts
 FOR EACH ROW EXECUTE FUNCTION market_attempt_policy_guard();
CREATE FUNCTION market_capture_policy_guard() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE c source_captures%ROWTYPE; BEGIN
 SELECT * INTO c FROM source_captures WHERE id=NEW.capture_id;
 IF NOT market_sec_resource(c.source_id,NEW.policy_revision_id,c.request_url,c.source_object_key) THEN
  PERFORM market_validate_resource(c.source_id,c.request_url,c.source_object_key);
  PERFORM market_validate_policy(NEW.policy_revision_id,c.source_id,c.source_object_key,NULL,false,false);
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER market_capture_policy BEFORE INSERT ON capture_policy_links FOR EACH ROW EXECUTE FUNCTION market_capture_policy_guard();
"""

PLAN_SQL = r"""
CREATE FUNCTION market_request_plan(p jsonb) RETURNS jsonb
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE price_source uuid; macro_source uuid; ps date; pe date; ms date; me date; vintage date; keys text[]; key text;
BEGIN
 IF p IS NULL OR p='null'::jsonb THEN RETURN NULL; END IF;
 IF jsonb_typeof(p)<>'object' OR p-ARRAY['market_plan_revision','price_source_id','price_start','price_end',
 'macro_source_id','macro_series_keys','macro_start','macro_end','macro_source_as_of_date']<>'{}'::jsonb
 OR p->>'market_plan_revision' IS DISTINCT FROM 's4-market-data-v1' THEN
  RAISE EXCEPTION 'unknown market request plan revision or field' USING ERRCODE='22023'; END IF;
 FOREACH key IN ARRAY ARRAY['price_start','price_end','macro_start','macro_end','macro_source_as_of_date'] LOOP
  IF p->>key IS NOT NULL AND (jsonb_typeof(p->key)<>'string' OR p->>key !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$') THEN
   RAISE EXCEPTION 'market request dates require exact finite dates' USING ERRCODE='22023'; END IF;
 END LOOP;
 price_source:=(p->>'price_source_id')::uuid;macro_source:=(p->>'macro_source_id')::uuid;
 ps:=(p->>'price_start')::date;pe:=(p->>'price_end')::date;
 ms:=(p->>'macro_start')::date;me:=(p->>'macro_end')::date;vintage:=(p->>'macro_source_as_of_date')::date;
 IF p->'macro_series_keys' IS NOT NULL AND p->'macro_series_keys'<>'null'::jsonb THEN
  IF jsonb_typeof(p->'macro_series_keys')<>'array' OR EXISTS(SELECT FROM jsonb_array_elements(p->'macro_series_keys') v WHERE jsonb_typeof(v)<>'string') THEN
   RAISE EXCEPTION 'macro series keys must be exact strings' USING ERRCODE='22023'; END IF;
  SELECT coalesce(array_agg(v ORDER BY v),ARRAY[]::text[]) INTO keys FROM jsonb_array_elements_text(p->'macro_series_keys') v;
 END IF;
 IF (price_source IS NULL AND macro_source IS NULL)
 OR (price_source IS NULL AND (ps IS NOT NULL OR pe IS NOT NULL))
 OR (price_source IS NOT NULL AND (ps IS NULL OR pe IS NULL OR ps>pe))
 OR (macro_source IS NULL AND (ms IS NOT NULL OR me IS NOT NULL OR vintage IS NOT NULL OR coalesce(cardinality(keys),0)<>0))
 OR (macro_source IS NOT NULL AND (ms IS NULL OR me IS NULL OR ms>me OR NOT market_keys_valid(keys,false))) THEN
  RAISE EXCEPTION 'market request plan source, dates or series are inconsistent' USING ERRCODE='22023'; END IF;
 IF (price_source IS NOT NULL AND NOT EXISTS(SELECT FROM sources WHERE id=price_source))
 OR (macro_source IS NOT NULL AND NOT EXISTS(SELECT FROM sources WHERE id=macro_source)) THEN
  RAISE EXCEPTION 'market request source must be provisioned' USING ERRCODE='23503'; END IF;
 RETURN jsonb_build_object('market_plan_revision','s4-market-data-v1','price_source_id',price_source,'price_start',ps,'price_end',pe,
  'macro_source_id',macro_source,'macro_series_keys',CASE WHEN macro_source IS NULL THEN NULL ELSE to_jsonb(keys) END,
  'macro_start',ms,'macro_end',me,'macro_source_as_of_date',vintage);
END $$;
"""

ENQUEUE_SQL = r"""
CREATE OR REPLACE FUNCTION workflow_enqueue(
    p_workspace UUID,p_watchlist UUID,p_security UUID,p_quote UUID,p_key TEXT,
    p_options JSONB,p_trigger TEXT,p_parent UUID
) RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE workspace UUID; membership UUID; request UUID; execution UUID; generation INTEGER;
    options JSONB; params_hash TEXT; existing analysis_request_keys%ROWTYPE;
    existing_membership watchlist_memberships%ROWTYPE; vintage TIMESTAMPTZ; market_plan JSONB;
BEGIN
    IF p_trigger NOT IN ('watchlist_add','manual_refresh') OR p_trigger IS NULL
        OR p_key IS NULL OR length(p_key) NOT BETWEEN 1 AND 200
        OR p_options IS NULL OR jsonb_typeof(p_options)<>'object'
        OR p_options-'history_mode'-'filed_cutoff'-'requested_periods'-'retrieval_vintage'-'max_attempts'-'market_plan'
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
    market_plan:=market_request_plan(p_options->'market_plan');
    IF market_plan IS NOT NULL THEN options:=options||jsonb_build_object('market_plan',market_plan); END IF;
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
        retrieval_policy,retrieval_vintage,max_attempts,request_parameters_hash,
        market_plan_revision,price_source_id,price_start,price_end,macro_source_id,macro_series_keys,macro_start,macro_end,macro_source_as_of_date)
    VALUES(request,workspace,p_security,p_quote,p_trigger,membership,p_parent,p_key,
        options->>'history_mode',(options->>'filed_cutoff')::DATE,options->'requested_periods',
        CASE WHEN vintage IS NULL THEN 'refresh' ELSE 'pinned_vintage' END,vintage,
        (options->>'max_attempts')::INTEGER,params_hash,market_plan->>'market_plan_revision',
        (market_plan->>'price_source_id')::UUID,(market_plan->>'price_start')::DATE,(market_plan->>'price_end')::DATE,
        (market_plan->>'macro_source_id')::UUID,CASE WHEN market_plan->>'macro_source_id' IS NULL THEN NULL
        ELSE ARRAY(SELECT jsonb_array_elements_text(market_plan->'macro_series_keys')) END,
        (market_plan->>'macro_start')::DATE,(market_plan->>'macro_end')::DATE,(market_plan->>'macro_source_as_of_date')::DATE);
    INSERT INTO analysis_request_keys(workspace_id,idempotency_key,request_id,parameters_hash)
        VALUES(workspace,p_key,request,params_hash);
    INSERT INTO analysis_executions(id,request_id,attempt_no,state)
        VALUES(execution,request,1,'queued');
    INSERT INTO analysis_request_state(request_id,current_execution_id,attempt_epoch)
        VALUES(request,execution,1);
    PERFORM workflow_event(execution,'queued',jsonb_build_object('trigger',p_trigger));
    RETURN workflow_request_result(request);
END $$;

"""

PUBLICATION_SQL = r"""
CREATE FUNCTION market_insert_exact(p_table text,p_values jsonb,p_insert boolean DEFAULT true) RETURNS void
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE normalized jsonb; existing jsonb;
BEGIN
 IF p_table NOT IN ('provider_quote_bindings','macro_series_definitions','market_data_batches','market_data_batch_inputs',
 'market_data_quality_flags','price_daily','macro_observations') OR jsonb_typeof(p_values)<>'object' THEN
  RAISE EXCEPTION 'invalid market publication record' USING ERRCODE='22023'; END IF;
 IF EXISTS(SELECT FROM jsonb_object_keys(p_values) k WHERE NOT EXISTS(
  SELECT FROM pg_attribute WHERE attrelid=p_table::regclass AND attnum>0 AND NOT attisdropped AND attname=k)) THEN
  RAISE EXCEPTION 'unknown market publication field' USING ERRCODE='22023'; END IF;
 EXECUTE format('SELECT to_jsonb(jsonb_populate_record(NULL::%I,$1))',p_table) INTO normalized USING p_values;
 IF p_insert THEN
  EXECUTE format('INSERT INTO %I SELECT (jsonb_populate_record(NULL::%I,$1)).* ON CONFLICT DO NOTHING',p_table,p_table) USING normalized;
 END IF;
 IF p_table='price_daily' THEN
  SELECT to_jsonb(t) INTO existing FROM price_daily t WHERE id=(normalized->>'id')::uuid AND session_date=(normalized->>'session_date')::date;
 ELSIF p_table='macro_observations' THEN
  SELECT to_jsonb(t) INTO existing FROM macro_observations t WHERE id=(normalized->>'id')::uuid AND reference_date=(normalized->>'reference_date')::date;
 ELSE EXECUTE format('SELECT to_jsonb(t) FROM %I t WHERE id=($1->>''id'')::uuid',p_table) INTO existing USING normalized;
 END IF;
 IF existing IS DISTINCT FROM normalized THEN
  RAISE EXCEPTION 'immutable market record conflicts with existing identity' USING ERRCODE='23514'; END IF;
END $$;
CREATE FUNCTION market_batch_transition() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$ BEGIN
 IF TG_OP='DELETE' OR (TG_OP='INSERT' AND NEW.state<>'building') THEN
  RAISE EXCEPTION 'market batch begins building and cannot be deleted' USING ERRCODE='55000'; END IF;
 IF TG_OP='UPDATE' AND (OLD.state<>'building' OR NEW.state NOT IN ('published','failed')
 OR(to_jsonb(NEW)-ARRAY['state','published_at']) IS DISTINCT FROM(to_jsonb(OLD)-ARRAY['state','published_at'])) THEN
  RAISE EXCEPTION 'market batch publication is immutable' USING ERRCODE='55000'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER market_batch_state BEFORE INSERT OR UPDATE OR DELETE ON market_data_batches FOR EACH ROW EXECUTE FUNCTION market_batch_transition();
CREATE FUNCTION market_child_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE state text; BEGIN
 SELECT b.state INTO state FROM market_data_batches b WHERE id=NEW.batch_id FOR UPDATE;
 IF state IS DISTINCT FROM 'building' THEN RAISE EXCEPTION 'market child requires building batch' USING ERRCODE='55000'; END IF;
 RETURN NEW;
END $$;
CREATE FUNCTION market_require_capture(p_capture uuid,p_cutoff timestamptz,p_numeric boolean) RETURNS source_captures
LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE c source_captures%ROWTYPE; policy uuid;
BEGIN
 SELECT * INTO c FROM source_captures WHERE id=p_capture;
 SELECT policy_revision_id INTO policy FROM capture_policy_links WHERE capture_id=p_capture;
 IF c.id IS NULL OR policy IS NULL OR c.body_sha256 IS NULL OR c.completed_at IS NULL OR
 (p_cutoff IS NOT NULL AND c.completed_at>p_cutoff) OR(p_numeric AND (c.http_status IS NULL OR c.http_status NOT BETWEEN 200 AND 299)) THEN
  RAISE EXCEPTION 'market capture is incomplete, unreviewed, unsuccessful or after cutoff' USING ERRCODE='23514'; END IF;
 IF NOT market_sec_resource(c.source_id,policy,c.request_url,c.source_object_key) THEN
  PERFORM market_validate_policy(policy,c.source_id,c.source_object_key,NULL,false,false);
 END IF;
 RETURN c;
END $$;
CREATE FUNCTION market_publish(p_lease jsonb,p_stage uuid,p_bundle jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE execution analysis_executions%ROWTYPE; req analysis_requests%ROWTYPE; batch market_data_batches%ROWTYPE;
 existing market_data_batches%ROWTYPE; c source_captures%ROWTYPE; binding provider_quote_bindings%ROWTYPE;
 definition macro_series_definitions%ROWTYPE; quote security_identifiers%ROWTYPE; item jsonb; row_data jsonb;
 field text; table_name text; kind text; day date; cut date; has_problem boolean; capture_ids uuid[]; stage_key text; row_count bigint;
BEGIN
 execution:=ingestion_locked_stage(p_lease,p_stage);
 SELECT * INTO req FROM analysis_requests WHERE id=execution.request_id;
 SELECT s.stage_key INTO stage_key FROM analysis_stage_attempts s WHERE id=p_stage;
 IF p_bundle IS NULL OR jsonb_typeof(p_bundle)<>'object' OR p_bundle-ARRAY['batch','inputs','flags','prices','macros','definitions','bindings']<>'{}'::jsonb
 OR NOT(p_bundle ?& ARRAY['batch','inputs','flags','prices','macros']) THEN
  RAISE EXCEPTION 'invalid market publication bundle' USING ERRCODE='22023'; END IF;
 FOREACH kind IN ARRAY ARRAY['inputs','flags','prices','macros','definitions','bindings'] LOOP
  IF jsonb_typeof(coalesce(p_bundle->kind,'[]'::jsonb)) IS DISTINCT FROM 'array' THEN
   RAISE EXCEPTION 'market publication children must be arrays' USING ERRCODE='22023'; END IF;
 END LOOP;
 IF jsonb_typeof(p_bundle->'batch')<>'object' OR (p_bundle->'batch') ?| ARRAY['state','published_at','created_at','origin_stage_attempt_id']
 OR EXISTS(SELECT FROM jsonb_object_keys(p_bundle->'batch') k WHERE NOT EXISTS(SELECT FROM pg_attribute
 WHERE attrelid='market_data_batches'::regclass AND attnum>0 AND NOT attisdropped AND attname=k)) THEN
  RAISE EXCEPTION 'publication owns batch state and provenance' USING ERRCODE='22023'; END IF;
 row_data:=(p_bundle->'batch')||jsonb_build_object('origin_stage_attempt_id',p_stage,'created_at',clock_timestamp(),'state','building');
 SELECT * INTO batch FROM jsonb_populate_record(NULL::market_data_batches,row_data);
 IF req.market_plan_revision IS NULL THEN RAISE EXCEPTION 'request has no immutable market plan' USING ERRCODE='23514'; END IF;
 IF batch.retrieval_cutoff IS DISTINCT FROM req.retrieval_vintage THEN RAISE EXCEPTION 'market retrieval cutoff differs from request' USING ERRCODE='23514'; END IF;
 IF batch.data_kind='price' THEN
  IF stage_key<>'price_normalization' OR batch.source_id IS DISTINCT FROM req.price_source_id
  OR batch.security_id IS DISTINCT FROM req.security_id OR batch.quote_identifier_id IS DISTINCT FROM req.quote_identifier_id
  OR batch.requested_start IS DISTINCT FROM req.price_start OR batch.requested_end IS DISTINCT FROM req.price_end
  OR batch.source_as_of_date IS NOT NULL OR batch.source_vintage_mode<>'current_provider_history'
  OR jsonb_array_length(p_bundle->'macros')<>0 THEN
   RAISE EXCEPTION 'price batch does not match immutable request scope' USING ERRCODE='23514'; END IF;
 ELSIF batch.data_kind='macro' THEN
  IF stage_key !~ '^macro_normalization_[a-f0-9]{16}$' OR batch.source_id IS DISTINCT FROM req.macro_source_id
  OR NOT coalesce(batch.source_series_key=ANY(req.macro_series_keys),false)
  OR batch.requested_start<req.macro_start OR batch.requested_end>req.macro_end
  OR batch.source_as_of_date IS DISTINCT FROM req.macro_source_as_of_date
  OR jsonb_array_length(p_bundle->'prices')<>0 THEN
   RAISE EXCEPTION 'macro batch does not match immutable request scope' USING ERRCODE='23514'; END IF;
 ELSE RAISE EXCEPTION 'unknown market batch kind' USING ERRCODE='23514'; END IF;
 IF batch.parser_revision IS DISTINCT FROM 'parser-v1' OR batch.normalizer_revision IS DISTINCT FROM 'normalizer-v1'
 OR batch.selection_policy_revision IS DISTINCT FROM 'selection-v1' THEN
  RAISE EXCEPTION 'market parser or selection revision differs from pinned plan' USING ERRCODE='23514'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(batch.source_id::text||batch.input_manifest_hash,905));
 PERFORM ingestion_locked_stage(p_lease,p_stage);
 SELECT * INTO existing FROM market_data_batches WHERE source_id=batch.source_id AND input_manifest_hash=batch.input_manifest_hash AND state='published';
 IF FOUND THEN
  IF (to_jsonb(existing)-ARRAY['id','origin_stage_attempt_id','created_at','published_at','state'])
    IS DISTINCT FROM(to_jsonb(batch)-ARRAY['id','origin_stage_attempt_id','created_at','published_at','state']) THEN
   RAISE EXCEPTION 'same market input has conflicting output or manifest' USING ERRCODE='23514'; END IF;
  -- Publication body is revalidated below before reusing its immutable result.
 END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(coalesce(p_bundle->'bindings','[]'::jsonb)) LOOP
  PERFORM market_insert_exact('provider_quote_bindings',item);
 END LOOP;
 FOR item IN SELECT value FROM jsonb_array_elements(coalesce(p_bundle->'definitions','[]'::jsonb)) LOOP
  PERFORM market_insert_exact('macro_series_definitions',item);
 END LOOP;
 IF batch.data_kind='price' AND batch.quote_binding_id IS NOT NULL THEN
  SELECT * INTO binding FROM provider_quote_bindings WHERE id=batch.quote_binding_id;
  SELECT * INTO quote FROM security_identifiers WHERE id=batch.quote_identifier_id;
  SELECT min(cl.valid_to) INTO cut FROM security_identifier_closures cl JOIN source_captures cc ON cc.id=cl.source_capture_id
   WHERE cl.quote_identifier_id=batch.quote_identifier_id AND (batch.retrieval_cutoff IS NULL OR cc.completed_at<=batch.retrieval_cutoff);
  cut:=least(cut,quote.valid_to);
  IF binding.id IS NULL OR binding.source_id<>batch.source_id OR binding.quote_identifier_id<>batch.quote_identifier_id OR binding.security_id<>batch.security_id
  OR binding.valid_from>batch.requested_start OR(binding.valid_to IS NOT NULL AND binding.valid_to<=batch.requested_end)
  OR quote.valid_from>batch.requested_start OR(cut IS NOT NULL AND cut<=batch.requested_end) THEN
   RAISE EXCEPTION 'price binding or quote validity does not cover requested interval' USING ERRCODE='23514'; END IF;
  PERFORM market_require_capture(binding.identity_capture_id,batch.retrieval_cutoff,true);
  IF NOT EXISTS(SELECT FROM jsonb_array_elements(p_bundle->'inputs') v WHERE v->>'capture_id'=binding.identity_capture_id::text AND v->>'role'='quote_identity') THEN
   RAISE EXCEPTION 'price identity capture is not pinned' USING ERRCODE='23514'; END IF;
 ELSIF batch.data_kind='macro' AND batch.series_definition_id IS NOT NULL THEN
  SELECT * INTO definition FROM macro_series_definitions WHERE id=batch.series_definition_id;
  IF definition.id IS NULL OR definition.source_id<>batch.source_id OR definition.source_series_key<>batch.source_series_key THEN
   RAISE EXCEPTION 'macro definition does not match requested source series' USING ERRCODE='23514'; END IF;
  PERFORM market_require_capture(definition.metadata_capture_id,batch.retrieval_cutoff,true);
  IF NOT EXISTS(SELECT FROM jsonb_array_elements(p_bundle->'inputs') v WHERE v->>'capture_id'=definition.metadata_capture_id::text AND v->>'role'='series_definition') THEN
   RAISE EXCEPTION 'macro definition capture is not pinned' USING ERRCODE='23514'; END IF;
 END IF;
 IF (jsonb_array_length(p_bundle->'prices')>0 AND binding.id IS NULL) OR(jsonb_array_length(p_bundle->'macros')>0 AND definition.id IS NULL) THEN
  RAISE EXCEPTION 'market observations require reviewed identity or definition' USING ERRCODE='23514'; END IF;
 IF batch.policy_revision_id IS NULL OR NOT EXISTS(SELECT FROM source_policy_capabilities WHERE policy_revision_id=batch.policy_revision_id AND source_id=batch.source_id
 AND raw_retention='indefinite_without_required_deletion' AND normalized_retention='indefinite_without_required_deletion' AND internal_analysis_allowed) THEN
  RAISE EXCEPTION 'market batch policy source mismatch' USING ERRCODE='23514'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(p_bundle->'inputs') LOOP
  IF item->>'capture_id' IS NOT NULL THEN
   c:=market_require_capture((item->>'capture_id')::uuid,batch.retrieval_cutoff,item->>'role'<>'fetch_outcome');
   IF item->>'role'='observations' THEN
    IF c.source_id<>batch.source_id OR NOT EXISTS(SELECT FROM capture_policy_links WHERE capture_id=c.id AND policy_revision_id=batch.policy_revision_id) THEN
     RAISE EXCEPTION 'observation capture source or policy mismatch' USING ERRCODE='23514'; END IF;
    PERFORM market_validate_policy(batch.policy_revision_id,batch.source_id,c.source_object_key,batch.source_series_key,true,false);
   END IF;
  ELSIF item->>'attempt_id' IS NOT NULL THEN
   IF NOT EXISTS(
    SELECT FROM source_fetch_attempts a JOIN analysis_stage_attempts st ON st.id=a.stage_attempt_id
    JOIN analysis_executions ae ON ae.id=st.execution_id JOIN analysis_requests ar ON ar.id=ae.request_id
    WHERE a.id=(item->>'attempt_id')::uuid AND a.source_id=batch.source_id
    AND a.policy_revision_id=batch.policy_revision_id AND a.state NOT IN ('prepared','in_progress')
    AND a.finished_at IS NOT NULL AND(batch.retrieval_cutoff IS NULL OR a.finished_at<=batch.retrieval_cutoff)
    AND ar.market_plan_revision='s4-market-data-v1'
    AND ((batch.data_kind='price' AND ar.price_source_id=batch.source_id
      AND ar.quote_identifier_id=batch.quote_identifier_id AND ar.security_id=batch.security_id
      AND ar.price_start=batch.requested_start AND ar.price_end=batch.requested_end
      AND a.source_object_key='tiingo_eod/'||binding.provider_symbol)
     OR (batch.data_kind='macro' AND ar.macro_source_id=batch.source_id
      AND batch.source_series_key=ANY(ar.macro_series_keys)
      AND ar.macro_start<=batch.requested_start AND ar.macro_end>=batch.requested_end
      AND ar.macro_source_as_of_date IS NOT DISTINCT FROM batch.source_as_of_date
      AND a.source_object_key IN ('daily_treasury_yield_curve','fred_observations/'||batch.source_series_key)))
   ) THEN
    RAISE EXCEPTION 'attempt is unresolved or outside market request, policy or cutoff' USING ERRCODE='23514'; END IF;
  END IF;
 END LOOP;
 IF batch.data_kind='price' AND (SELECT count(DISTINCT v->>'capture_id') FROM jsonb_array_elements(p_bundle->'inputs') v WHERE v->>'role'='observations')>1 THEN
  RAISE EXCEPTION 'price history requires one coherent response' USING ERRCODE='23514'; END IF;
 IF existing.id IS NULL THEN PERFORM market_insert_exact('market_data_batches',row_data); END IF;
 FOREACH kind IN ARRAY ARRAY['inputs','flags','prices','macros'] LOOP
  table_name:=CASE kind WHEN 'inputs' THEN 'market_data_batch_inputs' WHEN 'flags' THEN 'market_data_quality_flags'
   WHEN 'prices' THEN 'price_daily' ELSE 'macro_observations' END;
  FOR item IN SELECT value FROM jsonb_array_elements(p_bundle->kind) LOOP
   IF item ? 'batch_id' THEN RAISE EXCEPTION 'child batch identity is publication-owned' USING ERRCODE='22023'; END IF;
   day:=CASE WHEN kind='prices' THEN(item->>'session_date')::date ELSE(item->>'reference_date')::date END;
   IF day IS NOT NULL AND(day<batch.requested_start OR day>batch.requested_end) THEN
    RAISE EXCEPTION 'market row is outside requested interval' USING ERRCODE='23514'; END IF;
   IF kind IN ('prices','macros') THEN
    IF NOT EXISTS(SELECT FROM jsonb_array_elements(p_bundle->'inputs') v WHERE v->>'capture_id'=item->>'source_capture_id' AND v->>'role'='observations') THEN
     RAISE EXCEPTION 'numeric row capture is not a pinned observation input' USING ERRCODE='23514'; END IF;
    IF kind='prices' AND ((item->>'quote_binding_id')::uuid IS DISTINCT FROM binding.id OR(item->>'quote_identifier_id')::uuid IS DISTINCT FROM batch.quote_identifier_id
      OR(item->>'security_id')::uuid IS DISTINCT FROM batch.security_id OR item->>'quote_currency' IS DISTINCT FROM quote.quote_currency) THEN
     RAISE EXCEPTION 'price row identity or currency mismatch' USING ERRCODE='23514'; END IF;
    IF kind='macros' AND ((item->>'series_definition_id')::uuid IS DISTINCT FROM definition.id
      OR(item->>'requested_source_as_of')::date IS DISTINCT FROM batch.source_as_of_date
      OR(batch.source_as_of_date IS NOT NULL AND (item->>'source_vintage_basis' NOT IN ('source_interval','requested_as_of')
        OR(item->>'source_realtime_start')::date>batch.source_as_of_date OR(item->>'source_realtime_end')::date<batch.source_as_of_date))) THEN
     RAISE EXCEPTION 'macro row definition or source vintage mismatch' USING ERRCODE='23514'; END IF;
    FOREACH field IN ARRAY CASE WHEN kind='prices' THEN ARRAY['open','high','low','close','volume','adj_open','adj_high','adj_low','adj_close','adj_volume','div_cash','split_factor'] ELSE ARRAY['value'] END LOOP
     has_problem:=item->>(CASE WHEN kind='prices' THEN field||'_state' ELSE 'value_state' END) IS DISTINCT FROM 'observed';
     IF kind='prices' AND field='div_cash' AND item->>'div_cash' IS NOT NULL AND item->>'dividend_currency' IS NULL THEN has_problem:=true; END IF;
     IF has_problem AND NOT EXISTS(SELECT FROM jsonb_array_elements(p_bundle->'flags') f WHERE
      (f->>'reference_date')::date=day AND(f->>'field_key'=field OR f->>'field_key' IS NULL) AND f->>'severity' IN ('error','blocking')) THEN
      RAISE EXCEPTION 'unusable market value lacks explicit field quality flag' USING ERRCODE='23514'; END IF;
    END LOOP;
   ELSIF kind='flags' THEN
    IF (item->>'field_key' IS NOT NULL AND ((batch.data_kind='macro')<>(item->>'field_key'='value')))
    OR(item->>'capture_id' IS NOT NULL AND NOT EXISTS(SELECT FROM jsonb_array_elements(p_bundle->'inputs') v WHERE v->>'capture_id'=item->>'capture_id'))
    OR(item->>'attempt_id' IS NOT NULL AND NOT EXISTS(SELECT FROM jsonb_array_elements(p_bundle->'inputs') v WHERE v->>'attempt_id'=item->>'attempt_id')) THEN
     RAISE EXCEPTION 'market quality flag has wrong field or unpinned evidence' USING ERRCODE='23514'; END IF;
   END IF;
   PERFORM market_insert_exact(table_name,item||jsonb_build_object('batch_id',coalesce(existing.id,batch.id)),existing.id IS NULL);
  END LOOP;
  EXECUTE format('SELECT count(*) FROM %I WHERE batch_id=$1',table_name) INTO row_count USING coalesce(existing.id,batch.id);
  IF row_count<>jsonb_array_length(p_bundle->kind) THEN
   RAISE EXCEPTION 'market bundle repeats or omits child records' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF (batch.coverage_state<>'complete' OR (jsonb_array_length(p_bundle->'prices')=0 AND jsonb_array_length(p_bundle->'macros')=0))
 AND jsonb_array_length(p_bundle->'flags')=0 THEN
  RAISE EXCEPTION 'incomplete or empty market batch needs explicit quality flag' USING ERRCODE='23514'; END IF;
 PERFORM ingestion_locked_stage(p_lease,p_stage);
 IF existing.id IS NULL THEN
  UPDATE market_data_batches SET state='published',published_at=clock_timestamp() WHERE id=batch.id;
 ELSE batch:=existing; END IF;
 SELECT coalesce(array_agg(DISTINCT successful_capture.id),ARRAY[]::uuid[]) INTO capture_ids
  FROM jsonb_array_elements(p_bundle->'inputs') v JOIN source_captures successful_capture
   ON successful_capture.id=(v->>'capture_id')::uuid
  WHERE successful_capture.http_status BETWEEN 200 AND 299;
 PERFORM workflow_finish_stage(p_lease,p_stage,'completed',jsonb_build_object('batch_id',batch.id,
  'manifest_blob_key',batch.manifest_blob_key,'manifest_body_sha256',batch.manifest_body_sha256,'manifest_byte_count',batch.manifest_byte_count)::text,capture_ids);
 RETURN jsonb_build_object('batch_id',batch.id,'reused',existing.id IS NOT NULL);
END $$;
"""

INDEXES = {
    "provider_quote_bindings": ["quote_identifier_id", "security_id", "identity_capture_id"],
    "macro_series_definitions": ["metadata_capture_id"],
    "market_data_batches": ["policy_revision_id", "quote_identifier_id", "security_id", "quote_binding_id", "series_definition_id", "origin_stage_attempt_id", "source_id, data_kind, requested_start, requested_end, published_at"],
    "market_data_batch_inputs": ["capture_id", "attempt_id"],
    "market_data_quality_flags": ["batch_id, reference_date", "capture_id", "attempt_id"],
    "price_daily": ["quote_identifier_id, session_date, batch_id", "source_capture_id", "quote_binding_id", "security_id"],
    "macro_observations": ["series_definition_id, reference_date, batch_id", "source_capture_id"],
}


def upgrade() -> None:
    columns = ",\n".join(
        f'"{field}" numeric, {field}_state text NOT NULL, {field}_text text, '
        f'CHECK(market_numeric_valid("{field}",{field}_state,{field}_text,false))'
        for field in PRICE_FIELDS
    ) + ","
    op.execute(SQL.replace("__PRICE_FIELDS__", columns))
    op.execute(POLICY_SQL)
    op.execute(PLAN_SQL)
    op.execute(ENQUEUE_SQL)
    op.execute(PUBLICATION_SQL)
    for table in TABLES:
        op.execute(f"REVOKE ALL ON {table} FROM PUBLIC, equity_runtime")
        op.execute(f"GRANT SELECT ON {table} TO equity_runtime")
        op.execute(f"CREATE TRIGGER {table}_no_truncate BEFORE TRUNCATE ON {table} "
                   "FOR EACH STATEMENT EXECUTE FUNCTION evidence_immutable()")
        if table not in {"source_policy_capabilities", "market_data_batches"}:
            op.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                       "FOR EACH ROW EXECUTE FUNCTION evidence_immutable()")
        if table in {"market_data_batch_inputs", "market_data_quality_flags", "price_daily", "macro_observations"}:
            op.execute(f"CREATE TRIGGER {table}_building BEFORE INSERT ON {table} "
                       "FOR EACH ROW EXECUTE FUNCTION market_child_guard()")
    for table, indexes in INDEXES.items():
        for number, columns in enumerate(indexes):
            op.execute(f"CREATE INDEX {table}_market_fk_{number} ON {table} ({columns})")
    op.execute(r"""
    DO $$ DECLARE f record; BEGIN
      FOR f IN SELECT oid::regprocedure AS signature,proname FROM pg_proc
        WHERE pronamespace='public'::regnamespace AND proname LIKE 'market\_%' ESCAPE '\' LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC',f.signature);
        IF f.proname IN ('market_validate_policy','market_publish','market_numeric_valid') THEN
          EXECUTE format('GRANT EXECUTE ON FUNCTION %s TO equity_runtime',f.signature);
        END IF;
      END LOOP;
    END $$;
    """)


def downgrade() -> None:
    op.execute(r"""
    DO $$ BEGIN
      IF EXISTS(SELECT FROM market_data_batches) OR EXISTS(SELECT FROM provider_quote_bindings)
       OR EXISTS(SELECT FROM macro_series_definitions) OR EXISTS(SELECT FROM source_policy_capabilities)
       OR EXISTS(SELECT FROM analysis_requests WHERE market_plan_revision IS NOT NULL) THEN
       RAISE EXCEPTION 'refusing to discard S4 evidence or request plans' USING ERRCODE='55000';
      END IF;
    END $$;
    DROP TRIGGER market_attempt_policy ON source_fetch_attempts;
    DROP TRIGGER market_capture_policy ON capture_policy_links;
    """)
    op.execute(LEGACY_ENQUEUE_SQL)
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE {table} CASCADE")
    op.execute("ALTER TABLE analysis_requests DROP COLUMN market_plan_revision, DROP COLUMN price_source_id, "
               "DROP COLUMN price_start, DROP COLUMN price_end, DROP COLUMN macro_source_id, "
               "DROP COLUMN macro_series_keys, DROP COLUMN macro_start, DROP COLUMN macro_end, "
               "DROP COLUMN macro_source_as_of_date")
    op.execute("ALTER TABLE source_policy_revisions DROP CONSTRAINT market_policy_source")
    op.execute(r"""
    DO $$ DECLARE f record; BEGIN
      FOR f IN SELECT oid::regprocedure AS signature FROM pg_proc
       WHERE pronamespace='public'::regnamespace AND proname LIKE 'market\_%' ESCAPE '\' LOOP
       EXECUTE format('DROP FUNCTION IF EXISTS %s CASCADE',f.signature);
      END LOOP;
    END $$;
    """)

LEGACY_ENQUEUE_SQL = r"""
CREATE OR REPLACE FUNCTION workflow_enqueue(
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

"""
