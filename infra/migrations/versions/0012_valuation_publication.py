"""D038 synthetic reverse valuation, additive to approved S6a; no live activation."""

from alembic import op

revision = "0012_valuation_publication"
down_revision = "0011_fundamentals_publication"
branch_labels = None
depends_on = None

SQL = r"""
CREATE TABLE valuation_model_definitions (
 content_hash TEXT PRIMARY KEY CHECK(content_hash=fundamentals_hash(definition_text)),
 definition_text TEXT NOT NULL CHECK(definition_text=fundamentals_canonical(definition_text::JSONB)),
 CHECK(definition_text::JSONB->>'revision' IS NOT DISTINCT FROM 'reverse_fcff_operating_v1')
);
CREATE TABLE valuation_policy_revisions (
 content_hash TEXT PRIMARY KEY CHECK(content_hash=fundamentals_hash(policy_text)),
 policy_text TEXT NOT NULL CHECK(policy_text=fundamentals_canonical(policy_text::JSONB))
);

-- Persistence invokes this bounded helper with the fixed AssumptionContent shape
-- below, never a caller-supplied schema. Cross-field rules are checked separately.
CREATE FUNCTION valuation_shape_valid(p JSONB,s JSONB,root JSONB,depth INTEGER DEFAULT 0) RETURNS BOOLEAN
 LANGUAGE plpgsql IMMUTABLE SET search_path=public,pg_temp AS $$
DECLARE k TEXT; v JSONB; typ TEXT; txt TEXT; mant TEXT; coeff TEXT; spelling TEXT; sign TEXT; digits INTEGER; exponent INTEGER; adjusted INTEGER;
BEGIN
 IF p IS NULL OR s IS NULL OR depth>20 THEN RETURN false; END IF;
 IF s ? '$ref' THEN RETURN valuation_shape_valid(p,root#>string_to_array(substr(s->>'$ref',3),'/'),root,depth+1); END IF;
 IF s ? 'anyOf' OR s ? 'oneOf' THEN
 FOR v IN SELECT value FROM jsonb_array_elements(coalesce(s->'anyOf',s->'oneOf')) LOOP
 IF valuation_shape_valid(p,v,root,depth+1) THEN RETURN true; END IF; END LOOP; RETURN false; END IF;
 IF s ? 'const' AND p IS DISTINCT FROM s->'const' THEN RETURN false; END IF;
 IF s ? 'enum' AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(s->'enum') x WHERE x=p) THEN RETURN false; END IF;
 typ:=s->>'type';
 IF typ='integer' THEN
 IF jsonb_typeof(p)<>'number' OR p::TEXT !~ '^-?[0-9]+$' THEN RETURN false; END IF;
 ELSIF typ IS NOT NULL AND jsonb_typeof(p)<>typ THEN RETURN false; END IF;
 IF typ='object' THEN
 FOR k IN SELECT jsonb_array_elements_text(coalesce(s->'required','[]'::JSONB)) LOOP
 IF NOT p ? k THEN RETURN false; END IF; END LOOP;
 FOR k,v IN SELECT key,value FROM jsonb_each(p) LOOP
 IF NOT (s->'properties') ? k THEN RETURN false; END IF;
 IF NOT valuation_shape_valid(v,s->'properties'->k,root,depth+1) THEN RETURN false; END IF;
 END LOOP;
 ELSIF typ='array' THEN
 IF jsonb_array_length(p)<coalesce((s->>'minItems')::INTEGER,0)
 OR jsonb_array_length(p)>coalesce((s->>'maxItems')::INTEGER,10000) THEN RETURN false; END IF;
 FOR v IN SELECT value FROM jsonb_array_elements(p) LOOP
 IF NOT valuation_shape_valid(v,s->'items',root,depth+1) THEN RETURN false; END IF; END LOOP;
 ELSIF typ='string' THEN
 txt:=p#>>'{}';
 IF length(txt)<coalesce((s->>'minLength')::INTEGER,0) OR length(txt)>coalesce((s->>'maxLength')::INTEGER,10000)
 OR (s ? 'pattern' AND txt !~ (s->>'pattern')) THEN RETURN false; END IF;
 IF s->>'format'='date' THEN
 IF txt !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' OR NOT isfinite(txt::DATE) THEN RETURN false; END IF;
 ELSIF s->>'format'='date-time' THEN
 IF txt !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]\.[0-9]{6}Z$'
 OR NOT isfinite(txt::TIMESTAMPTZ) THEN RETURN false; END IF;
 ELSIF s->>'format'='decimal_dcf_input' THEN
 mant:=split_part(lower(txt),'e',1);
 digits:=length(ltrim(regexp_replace(mant,'[-.]','','g'),'0'));
 exponent:=coalesce(nullif(split_part(lower(txt),'e',2),''),'0')::INTEGER-length(split_part(mant,'.',2));
 IF digits>40 OR abs(exponent)>100 OR abs(exponent+greatest(digits,1)-1)>100 THEN RETURN false; END IF;
 -- Match Python Decimal.__str__ exactly, preserving scale and signed zero.
 coeff:=coalesce(nullif(ltrim(regexp_replace(mant,'[-.]','','g'),'0'),''),'0');
 sign:=CASE WHEN left(txt,1)='-' THEN '-' ELSE '' END;
 adjusted:=exponent+length(coeff)-1;
 IF exponent>0 OR adjusted < -6 THEN
 spelling:=left(coeff,1)||CASE WHEN length(coeff)>1 THEN '.'||substr(coeff,2) ELSE '' END
   ||'E'||CASE WHEN adjusted>=0 THEN '+' ELSE '' END||adjusted::TEXT;
 ELSIF exponent=0 THEN spelling:=coeff;
 ELSIF length(coeff)+exponent>0 THEN
 spelling:=left(coeff,length(coeff)+exponent)||'.'||substr(coeff,length(coeff)+exponent+1);
 ELSE spelling:='0.'||repeat('0',-exponent-length(coeff))||coeff;
 END IF;
 IF txt<>sign||spelling THEN RETURN false; END IF;
 END IF;
 ELSIF typ IN ('integer','number') THEN
 IF (s ? 'minimum' AND (p::TEXT)::NUMERIC<(s->>'minimum')::NUMERIC)
 OR (s ? 'maximum' AND (p::TEXT)::NUMERIC>(s->>'maximum')::NUMERIC) THEN RETURN false; END IF;
 END IF;
 RETURN true;
EXCEPTION WHEN data_exception THEN RETURN false;
END $$;
CREATE FUNCTION valuation_assumptions_valid(p JSONB) RETURNS BOOLEAN
 LANGUAGE plpgsql IMMUTABLE SET search_path=public,pg_temp AS $$
DECLARE shape JSONB:='{"$defs":{"Judgment":{"additionalProperties":false,"properties":{"scenario":{"maxLength":250,"minLength":1,"title":"Scenario","type":"string"},"parameter":{"maxLength":250,"minLength":1,"title":"Parameter","type":"string"},"binding":{"discriminator":{"mapping":{"scalar":"#/$defs/ScalarBinding","schedule":"#/$defs/ScheduleBinding","solved":"#/$defs/SolvedBinding","solver":"#/$defs/SolverBinding","vector":"#/$defs/VectorBinding"},"propertyName":"kind"},"oneOf":[{"$ref":"#/$defs/ScalarBinding"},{"$ref":"#/$defs/VectorBinding"},{"$ref":"#/$defs/SolvedBinding"},{"$ref":"#/$defs/ScheduleBinding"},{"$ref":"#/$defs/SolverBinding"}],"title":"Binding"},"origin":{"const":"user_judgment","title":"Origin","type":"string"},"author_id":{"maxLength":250,"minLength":1,"title":"Author Id","type":"string"},"authored_at":{"format":"date-time","title":"Authored At","type":"string"},"known_at":{"format":"date-time","title":"Known At","type":"string"},"unit":{"enum":["fraction","currency","years","schedule","solver_policy"],"title":"Unit","type":"string"},"rationale":{"maxLength":4000,"minLength":1,"title":"Rationale","type":"string"},"effective_from":{"format":"date","title":"Effective From","type":"string"},"effective_to":{"format":"date","title":"Effective To","type":"string"},"supporting_hashes":{"items":{"pattern":"^[a-f0-9]{64}$","type":"string"},"title":"Supporting Hashes","type":"array"}},"required":["scenario","parameter","binding","origin","author_id","authored_at","known_at","unit","rationale","effective_from","effective_to","supporting_hashes"],"title":"Judgment","type":"object"},"ScalarBinding":{"additionalProperties":false,"properties":{"kind":{"const":"scalar","title":"Kind","type":"string"},"value":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","title":"Value","type":"string"}},"required":["kind","value"],"title":"ScalarBinding","type":"object"},"Scenario":{"additionalProperties":false,"description":"Null is permitted only at a declared solved slot; no hidden fixed fallback.","properties":{"name":{"maxLength":250,"minLength":1,"title":"Name","type":"string"},"revenue_anchor":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","title":"Revenue Anchor","type":"string"},"growth":{"anyOf":[{"items":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},"type":"array"},{"type":"null"}],"title":"Growth"},"margins":{"anyOf":[{"items":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},"type":"array"},{"type":"null"}],"title":"Margins"},"taxes":{"items":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},"title":"Taxes","type":"array"},"reinvestment":{"anyOf":[{"items":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},"type":"array"},{"type":"null"}],"title":"Reinvestment"},"wacc":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","title":"Wacc","type":"string"},"risk_free":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","title":"Risk Free","type":"string"},"terminal_growth":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","title":"Terminal Growth","type":"string"},"terminal_margin":{"anyOf":[{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},{"type":"null"}],"title":"Terminal Margin"},"terminal_tax":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","title":"Terminal Tax","type":"string"},"terminal_roic":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","title":"Terminal Roic","type":"string"},"solve":{"$ref":"#/$defs/SolveSpec"}},"required":["name","revenue_anchor","growth","margins","taxes","reinvestment","wacc","risk_free","terminal_growth","terminal_margin","terminal_tax","terminal_roic","solve"],"title":"Scenario","type":"object"},"ScheduleBinding":{"additionalProperties":false,"properties":{"kind":{"const":"schedule","title":"Kind","type":"string"},"value":{"items":{"format":"date","type":"string"},"title":"Value","type":"array"}},"required":["kind","value"],"title":"ScheduleBinding","type":"object"},"SensitivityGrid":{"additionalProperties":false,"properties":{"name":{"maxLength":250,"minLength":1,"title":"Name","type":"string"},"reference_scenario":{"maxLength":250,"minLength":1,"title":"Reference Scenario","type":"string"},"output":{"enum":["reverse_implied_parameter","conditional_reprice"],"title":"Output","type":"string"},"x_parameter":{"enum":["wacc","terminal_growth","revenue_cagr","terminal_operating_margin","reinvestment_to_revenue"],"title":"X Parameter","type":"string"},"x_values":{"items":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},"title":"X Values","type":"array"},"y_parameter":{"enum":["wacc","terminal_growth","revenue_cagr","terminal_operating_margin","reinvestment_to_revenue"],"title":"Y Parameter","type":"string"},"y_values":{"items":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},"title":"Y Values","type":"array"},"conditional_parameter":{"anyOf":[{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},{"type":"null"}],"title":"Conditional Parameter"}},"required":["name","reference_scenario","output","x_parameter","x_values","y_parameter","y_values","conditional_parameter"],"title":"SensitivityGrid","type":"object"},"SolveSpec":{"additionalProperties":false,"properties":{"variable":{"enum":["revenue_cagr","terminal_operating_margin","reinvestment_to_revenue"],"title":"Variable","type":"string"},"lower":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","title":"Lower","type":"string"},"upper":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","title":"Upper","type":"string"},"absolute_tolerance":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","title":"Absolute Tolerance","type":"string"},"relative_tolerance":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","title":"Relative Tolerance","type":"string"},"width_tolerance":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","title":"Width Tolerance","type":"string"},"max_iterations":{"maximum":256,"minimum":1,"title":"Max Iterations","type":"integer"},"max_subdivisions":{"maximum":4096,"minimum":1,"title":"Max Subdivisions","type":"integer"},"max_evaluations":{"maximum":10000,"minimum":1,"title":"Max Evaluations","type":"integer"},"margin_weights":{"items":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},"title":"Margin Weights","type":"array"},"anchor_margin":{"anyOf":[{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},{"type":"null"}],"title":"Anchor Margin"}},"required":["variable","lower","upper","absolute_tolerance","relative_tolerance","width_tolerance","max_iterations","max_subdivisions","max_evaluations","margin_weights","anchor_margin"],"title":"SolveSpec","type":"object"},"SolvedBinding":{"additionalProperties":false,"properties":{"kind":{"const":"solved","title":"Kind","type":"string"},"variable":{"enum":["revenue_cagr","terminal_operating_margin","reinvestment_to_revenue"],"title":"Variable","type":"string"}},"required":["kind","variable"],"title":"SolvedBinding","type":"object"},"SolverBinding":{"additionalProperties":false,"properties":{"kind":{"const":"solver","title":"Kind","type":"string"},"value":{"$ref":"#/$defs/SolveSpec"}},"required":["kind","value"],"title":"SolverBinding","type":"object"},"VectorBinding":{"additionalProperties":false,"properties":{"kind":{"const":"vector","title":"Kind","type":"string"},"value":{"items":{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},"title":"Value","type":"array"}},"required":["kind","value"],"title":"VectorBinding","type":"object"}},"additionalProperties":false,"properties":{"authored_at":{"format":"date-time","title":"Authored At","type":"string"},"author_id":{"maxLength":250,"minLength":1,"title":"Author Id","type":"string"},"valuation_at":{"format":"date-time","title":"Valuation At","type":"string"},"retrospective":{"title":"Retrospective","type":"boolean"},"calendar":{"const":"calendar_year_equivalent","title":"Calendar","type":"string"},"leap_day":{"const":"february_28","title":"Leap Day","type":"string"},"forecast_dates":{"items":{"format":"date","type":"string"},"title":"Forecast Dates","type":"array"},"anchor_method":{"const":"explicit_carry_forward_annual_run_rate","title":"Anchor Method","type":"string"},"anchor_source_index":{"minimum":0,"title":"Anchor Source Index","type":"integer"},"scenarios":{"items":{"$ref":"#/$defs/Scenario"},"maxItems":12,"minItems":1,"title":"Scenarios","type":"array"},"sensitivities":{"items":{"$ref":"#/$defs/SensitivityGrid"},"maxItems":4,"title":"Sensitivities","type":"array"},"judgments":{"items":{"$ref":"#/$defs/Judgment"},"title":"Judgments","type":"array"}},"required":["authored_at","author_id","valuation_at","retrospective","calendar","leap_day","forecast_dates","anchor_method","anchor_source_index","scenarios","sensitivities","judgments"],"title":"AssumptionContent","type":"object"}'::JSONB; n INTEGER; i INTEGER; s JSONB; g JSONB; q JSONB; j JSONB;
 solve_variable TEXT; names TEXT[]; param TEXT; weights JSONB; w NUMERIC; prev NUMERIC;
 at_day DATE; expected_unit TEXT; expected_binding JSONB;
BEGIN
 IF NOT valuation_shape_valid(p,shape,shape) THEN RETURN false; END IF;
 n:=jsonb_array_length(p->'forecast_dates');
 IF n<5 OR n>10 THEN RETURN false; END IF;
 at_day:=((p->>'valuation_at')::TIMESTAMPTZ AT TIME ZONE 'UTC')::DATE;
 FOR i IN 1..n LOOP
 IF (p->'forecast_dates'->>(i-1))::DATE<>(at_day+make_interval(years=>i))::DATE THEN RETURN false; END IF;
 END LOOP;
 IF (p->>'retrospective')::BOOLEAN IS DISTINCT FROM ((p->>'authored_at')::TIMESTAMPTZ>(p->>'valuation_at')::TIMESTAMPTZ) THEN RETURN false; END IF;
 SELECT array_agg(x->>'name') INTO names FROM jsonb_array_elements(p->'scenarios') x;
 IF cardinality(names)<>(SELECT count(DISTINCT v) FROM unnest(names) v) THEN RETURN false; END IF;
 solve_variable:=p#>>'{scenarios,0,solve,variable}';
 FOR s IN SELECT value FROM jsonb_array_elements(p->'scenarios') LOOP
 q:=s->'solve'; param:=q->>'variable';
 IF param<>solve_variable OR jsonb_array_length(s->'taxes')<>n
 OR (s->'growth'='null'::JSONB) IS DISTINCT FROM (param='revenue_cagr')
 OR (s->'reinvestment'='null'::JSONB) IS DISTINCT FROM (param='reinvestment_to_revenue')
 OR (s->'margins'='null'::JSONB) IS DISTINCT FROM (param='terminal_operating_margin')
 OR (s->'terminal_margin'='null'::JSONB) IS DISTINCT FROM (param='terminal_operating_margin')
 OR (q->>'lower')::NUMERIC >= (q->>'upper')::NUMERIC
 OR (q->>'absolute_tolerance')::NUMERIC<=0 OR (q->>'width_tolerance')::NUMERIC<=0
 OR (q->>'relative_tolerance')::NUMERIC<0 THEN RETURN false; END IF;
 weights:=q->'margin_weights';
 IF param='terminal_operating_margin' THEN
 IF jsonb_array_length(weights)<>n OR q->'anchor_margin'='null'::JSONB
 OR (q->>'lower')::NUMERIC<=0 OR (q->>'upper')::NUMERIC>1
 OR (weights->>(n-1))::NUMERIC<>1 THEN RETURN false; END IF;
 prev:=0;
 FOR j IN SELECT value FROM jsonb_array_elements(weights) LOOP
 w:=(j#>>'{}')::NUMERIC; IF w<prev OR w>1 THEN RETURN false; END IF; prev:=w; END LOOP;
 ELSE
 IF jsonb_array_length(weights)<>0 OR q->'anchor_margin'<>'null'::JSONB THEN RETURN false; END IF;
 IF param='revenue_cagr' AND (q->>'lower')::NUMERIC<=-1 THEN RETURN false; END IF;
 IF param='reinvestment_to_revenue' AND (q->>'lower')::NUMERIC<0 THEN RETURN false; END IF;
 END IF;
 END LOOP;
 IF jsonb_array_length(p->'judgments')<>13*jsonb_array_length(p->'scenarios') THEN RETURN false; END IF;
 FOR s IN SELECT value FROM jsonb_array_elements(p->'scenarios') LOOP
 IF (SELECT array_agg(x->>'parameter' ORDER BY x->>'parameter') FROM jsonb_array_elements(p->'judgments') x WHERE x->>'scenario'=s->>'name')
 IS DISTINCT FROM ARRAY['growth','margins','reinvestment','revenue_anchor','risk_free','schedule','solver_policy','taxes','terminal_growth','terminal_margin','terminal_roic','terminal_tax','wacc']::TEXT[] THEN RETURN false; END IF;
 END LOOP;
 FOR j IN SELECT value FROM jsonb_array_elements(p->'judgments') LOOP
 SELECT value INTO s FROM jsonb_array_elements(p->'scenarios') WHERE value->>'name'=j->>'scenario';
 param:=j->>'parameter';
 expected_binding:=CASE WHEN param='schedule' THEN jsonb_build_object('kind','schedule','value',p->'forecast_dates')
 WHEN param='solver_policy' THEN jsonb_build_object('kind','solver','value',s->'solve')
 WHEN s->param='null'::JSONB THEN jsonb_build_object('kind','solved','variable',s#>>'{solve,variable}')
 WHEN jsonb_typeof(s->param)='array' THEN jsonb_build_object('kind','vector','value',s->param)
 ELSE jsonb_build_object('kind','scalar','value',s->param) END;
 IF j->'binding' IS DISTINCT FROM expected_binding OR j->'author_id' IS DISTINCT FROM p->'author_id'
 OR j->'authored_at' IS DISTINCT FROM p->'authored_at' OR j->'known_at' IS DISTINCT FROM p->'authored_at'
 THEN RETURN false; END IF;
 expected_unit:=CASE WHEN j->>'parameter'='revenue_anchor' THEN 'currency' WHEN j->>'parameter' IN ('schedule','solver_policy') THEN j->>'parameter' ELSE 'fraction' END;
 IF j->>'unit'<>expected_unit OR (j->>'effective_from')::DATE>(j->>'effective_to')::DATE THEN RETURN false; END IF; END LOOP;
 IF jsonb_array_length(p->'sensitivities')<>(SELECT count(DISTINCT x->>'name') FROM jsonb_array_elements(p->'sensitivities') x) THEN RETURN false; END IF;
 FOR g IN SELECT value FROM jsonb_array_elements(p->'sensitivities') LOOP
 IF NOT g->>'reference_scenario'=ANY(names) OR g->>'x_parameter'=g->>'y_parameter'
 OR jsonb_array_length(g->'x_values')=0 OR jsonb_array_length(g->'y_values')=0
 OR jsonb_array_length(g->'x_values')*jsonb_array_length(g->'y_values')>100
 OR jsonb_array_length(g->'x_values')<>(SELECT count(DISTINCT (x#>>'{}')::NUMERIC) FROM jsonb_array_elements(g->'x_values') x)
 OR jsonb_array_length(g->'y_values')<>(SELECT count(DISTINCT (x#>>'{}')::NUMERIC) FROM jsonb_array_elements(g->'y_values') x)
 OR (g->'conditional_parameter'='null'::JSONB) IS DISTINCT FROM (g->>'output'='reverse_implied_parameter')
 OR (g->>'output'='reverse_implied_parameter' AND solve_variable IN (g->>'x_parameter',g->>'y_parameter')) THEN RETURN false; END IF;
 END LOOP;
 RETURN true;
EXCEPTION WHEN data_exception THEN RETURN false;
END $$;

CREATE FUNCTION valuation_claim_valid(p JSONB) RETURNS BOOLEAN LANGUAGE plpgsql IMMUTABLE SET search_path=public,pg_temp AS $$ DECLARE shape JSONB:='{"$defs":{"ClaimCoverage":{"additionalProperties":false,"properties":{"component":{"enum":["cash","nonoperating_assets","debt","leases","preferred","nci","other"],"title":"Component","type":"string"},"disposition":{"enum":["included","excluded","unknown"],"title":"Disposition","type":"string"},"explanation":{"maxLength":250,"minLength":1,"title":"Explanation","type":"string"},"evidence_hash":{"anyOf":[{"pattern":"^[a-f0-9]{64}$","type":"string"},{"type":"null"}],"title":"Evidence Hash"}},"required":["component","disposition","explanation","evidence_hash"],"title":"ClaimCoverage","type":"object"}},"additionalProperties":false,"properties":{"kind":{"enum":["cash","nonoperating_assets","debt","leases","preferred","nci","other"],"title":"Kind","type":"string"},"coverage":{"anyOf":[{"items":{"$ref":"#/$defs/ClaimCoverage"},"type":"array"},{"type":"null"}],"title":"Coverage"},"economic_claim_ids":{"items":{"maxLength":250,"minLength":1,"type":"string"},"title":"Economic Claim Ids","type":"array"},"state":{"enum":["eligible_amount","evidenced_absence","unavailable"],"title":"State","type":"string"},"amount":{"anyOf":[{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},{"type":"null"}],"title":"Amount"},"currency":{"pattern":"^[A-Z]{3}$","title":"Currency","type":"string"},"as_of":{"format":"date","title":"As Of","type":"string"},"known_at":{"format":"date-time","title":"Known At","type":"string"},"captured_at":{"format":"date-time","title":"Captured At","type":"string"},"known_basis":{"enum":["owner_reviewed_instant","date_only","unproven"],"title":"Known Basis","type":"string"},"basis":{"enum":["economic_value","absence","unreviewed"],"title":"Basis","type":"string"},"evidence_hash":{"pattern":"^[a-f0-9]{64}$","title":"Evidence Hash","type":"string"},"fixture_url":{"pattern":"^https://example\\.invalid/","title":"Fixture Url","type":"string"},"reasons":{"items":{"maxLength":250,"minLength":1,"type":"string"},"title":"Reasons","type":"array"}},"required":["kind","coverage","economic_claim_ids","state","amount","currency","as_of","known_at","captured_at","known_basis","basis","evidence_hash","fixture_url","reasons"],"title":"Claim","type":"object"}'::JSONB; BEGIN RETURN valuation_shape_valid(p,shape,shape); END $$;
CREATE FUNCTION valuation_shares_valid(p JSONB) RETURNS BOOLEAN LANGUAGE plpgsql IMMUTABLE SET search_path=public,pg_temp AS $$ DECLARE shape JSONB:='{"additionalProperties":false,"properties":{"source_basic":{"anyOf":[{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},{"type":"null"}],"title":"Source Basic"},"source_diluted":{"anyOf":[{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},{"type":"null"}],"title":"Source Diluted"},"source_unit":{"anyOf":[{"enum":["shares","thousand_shares","million_shares"],"type":"string"},{"type":"null"}],"title":"Source Unit"},"source_multiplier":{"anyOf":[{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},{"type":"null"}],"title":"Source Multiplier"},"current_basic":{"anyOf":[{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},{"type":"null"}],"title":"Current Basic"},"current_diluted":{"anyOf":[{"format":"decimal_dcf_input","pattern":"^-?(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$","type":"string"},{"type":"null"}],"title":"Current Diluted"},"currency":{"pattern":"^[A-Z]{3}$","title":"Currency","type":"string"},"as_of":{"format":"date","title":"As Of","type":"string"},"known_at":{"format":"date-time","title":"Known At","type":"string"},"captured_at":{"format":"date-time","title":"Captured At","type":"string"},"known_basis":{"enum":["owner_reviewed_instant","date_only","unproven"],"title":"Known Basis","type":"string"},"action_basis":{"maxLength":250,"minLength":1,"title":"Action Basis","type":"string"},"evidence_hash":{"pattern":"^[a-f0-9]{64}$","title":"Evidence Hash","type":"string"},"fixture_url":{"pattern":"^https://example\\.invalid/","title":"Fixture Url","type":"string"},"complete_homogeneous_pool":{"title":"Complete Homogeneous Pool","type":"boolean"},"no_dilutive_claims":{"title":"No Dilutive Claims","type":"boolean"},"complete_action_coverage":{"title":"Complete Action Coverage","type":"boolean"},"operating_lease_basis_matches":{"title":"Operating Lease Basis Matches","type":"boolean"},"unrestricted_nonoperating_cash":{"title":"Unrestricted Nonoperating Cash","type":"boolean"},"no_crossholding_earnings_overlap":{"title":"No Crossholding Earnings Overlap","type":"boolean"},"reasons":{"items":{"maxLength":250,"minLength":1,"type":"string"},"title":"Reasons","type":"array"}},"required":["source_basic","source_diluted","source_unit","source_multiplier","current_basic","current_diluted","currency","as_of","known_at","captured_at","known_basis","action_basis","evidence_hash","fixture_url","complete_homogeneous_pool","no_dilutive_claims","complete_action_coverage","operating_lease_basis_matches","unrestricted_nonoperating_cash","no_crossholding_earnings_overlap","reasons"],"title":"SharePool","type":"object"}'::JSONB; BEGIN RETURN valuation_shape_valid(p,shape,shape); END $$;
CREATE TABLE valuation_assumption_sets (
 id UUID PRIMARY KEY, workspace_id UUID NOT NULL REFERENCES workspaces(id),
 parent_id UUID, idempotency_key TEXT NOT NULL CHECK(length(trim(idempotency_key))>0),
 content_text TEXT NOT NULL CHECK(content_text=fundamentals_canonical(content_text::JSONB))
 CHECK(valuation_assumptions_valid(content_text::JSONB)),
 content_hash TEXT NOT NULL CHECK(content_hash=fundamentals_hash(content_text)),
 authored_at TIMESTAMPTZ NOT NULL, retrospective BOOLEAN NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 creation_transaction_id BIGINT NOT NULL DEFAULT txid_current(),
 UNIQUE(id,workspace_id), UNIQUE(workspace_id,idempotency_key),
 FOREIGN KEY(parent_id,workspace_id) REFERENCES valuation_assumption_sets(id,workspace_id),
 CHECK(parent_id IS DISTINCT FROM id),
 CHECK((content_text::JSONB->>'authored_at')::TIMESTAMPTZ IS NOT DISTINCT FROM authored_at),
 CHECK((content_text::JSONB->>'retrospective')::BOOLEAN IS NOT DISTINCT FROM retrospective),
 CHECK(retrospective=(authored_at>(content_text::JSONB->>'valuation_at')::TIMESTAMPTZ))
);
CREATE TABLE valuation_assumption_entries (
 assumption_id UUID NOT NULL REFERENCES valuation_assumption_sets(id), scenario TEXT NOT NULL, parameter_key TEXT NOT NULL,
 unit TEXT NOT NULL, effective_from DATE NOT NULL, effective_to DATE NOT NULL,
 entry_text TEXT NOT NULL, PRIMARY KEY(assumption_id,scenario,parameter_key),
 CHECK(effective_from<=effective_to),
 CHECK(entry_text=fundamentals_canonical(entry_text::JSONB)),
 CHECK(entry_text::JSONB->>'parameter' IS NOT DISTINCT FROM parameter_key),
 CHECK(entry_text::JSONB->>'scenario' IS NOT DISTINCT FROM scenario),
 CHECK(entry_text::JSONB->>'unit' IS NOT DISTINCT FROM unit)
);
CREATE FUNCTION valuation_assumption_child_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_temp AS $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM valuation_assumption_sets s,
 jsonb_array_elements(s.content_text::JSONB->'judgments') j WHERE s.id=NEW.assumption_id
 AND s.creation_transaction_id=txid_current() AND j=NEW.entry_text::JSONB
 AND (j->>'effective_from')::DATE=NEW.effective_from AND (j->>'effective_to')::DATE=NEW.effective_to) THEN
 RAISE EXCEPTION 'immutable assumption entry mismatch' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER seal BEFORE INSERT ON valuation_assumption_entries FOR EACH ROW EXECUTE FUNCTION valuation_assumption_child_guard();
CREATE FUNCTION valuation_assumption_complete() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$ BEGIN
 IF (SELECT count(*) FROM valuation_assumption_entries WHERE assumption_id=NEW.id)<>jsonb_array_length(NEW.content_text::JSONB->'judgments') THEN
 RAISE EXCEPTION 'incomplete assumption bindings' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE CONSTRAINT TRIGGER assumption_complete AFTER INSERT ON valuation_assumption_sets DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION valuation_assumption_complete();
CREATE FUNCTION valuation_create_assumptions(p_workspace UUID,p_parent UUID,p_key TEXT,p_text TEXT) RETURNS UUID
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE old valuation_assumption_sets; new_id UUID:=gen_random_uuid(); p JSONB:=p_text::JSONB; stamp TIMESTAMPTZ;
BEGIN
 IF p_text IS NULL OR p_text IS DISTINCT FROM fundamentals_canonical(p) OR p_key IS NULL
 OR p_workspace IS NULL OR jsonb_typeof(p->'judgments') IS DISTINCT FROM 'array' THEN
 RAISE EXCEPTION 'invalid assumption envelope' USING ERRCODE='23514'; END IF;
 PERFORM pg_advisory_xact_lock(hashtextextended(p_workspace::TEXT||':'||p_key,0));
 SELECT * INTO old FROM valuation_assumption_sets WHERE workspace_id=p_workspace AND idempotency_key=p_key;
 IF FOUND THEN IF old.content_text IS DISTINCT FROM p_text OR old.parent_id IS DISTINCT FROM p_parent THEN
 RAISE EXCEPTION 'assumption idempotency conflict' USING ERRCODE='23505'; END IF; RETURN old.id; END IF;
 stamp:=(p->>'authored_at')::TIMESTAMPTZ;
 IF stamp IS NULL OR stamp<clock_timestamp()-interval '5 minutes' OR stamp>clock_timestamp()+interval '1 minute' THEN
 RAISE EXCEPTION 'local assumption authorship must be current' USING ERRCODE='23514'; END IF;
 INSERT INTO valuation_assumption_sets(id,workspace_id,parent_id,idempotency_key,content_text,content_hash,authored_at,retrospective)
 VALUES(new_id,p_workspace,p_parent,p_key,p_text,fundamentals_hash(p_text),stamp,(p->>'retrospective')::BOOLEAN);
 INSERT INTO valuation_assumption_entries SELECT new_id,j->>'scenario',j->>'parameter',j->>'unit',
 (j->>'effective_from')::DATE,(j->>'effective_to')::DATE,fundamentals_canonical(j)
 FROM jsonb_array_elements(p->'judgments') j;
 RETURN new_id;
END $$;
CREATE TABLE valuation_input_reviews (
 id UUID PRIMARY KEY, workspace_id UUID NOT NULL REFERENCES workspaces(id),
 issuer_id UUID NOT NULL REFERENCES issuers(id), security_id UUID NOT NULL REFERENCES securities(id),
 quote_identifier_id UUID NOT NULL, source_snapshot_id UUID NOT NULL REFERENCES analysis_snapshots(id),
 assumption_set_id UUID NOT NULL, model_hash TEXT NOT NULL REFERENCES valuation_model_definitions(content_hash),
 policy_hash TEXT NOT NULL REFERENCES valuation_policy_revisions(content_hash),
 manifest_text TEXT NOT NULL, manifest_hash TEXT NOT NULL, compatibility_text TEXT NOT NULL,
 compatibility_hash TEXT NOT NULL, expected_payload_hash TEXT NOT NULL CHECK(expected_payload_hash~'^[0-9a-f]{64}$'),
 reviewed_by TEXT NOT NULL CHECK(length(trim(reviewed_by))>0),reason TEXT NOT NULL CHECK(length(trim(reason))>0),
 reviewed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),creation_transaction_id BIGINT NOT NULL DEFAULT txid_current(),
 price_date DATE NOT NULL, price_id UUID, price_source_id UUID NOT NULL REFERENCES sources(id),
 price_batch_id UUID REFERENCES market_data_batches(id),
 FOREIGN KEY(price_date,price_id) REFERENCES price_daily(session_date,id),
 FOREIGN KEY(quote_identifier_id,security_id) REFERENCES security_identifiers(id,security_id),
 FOREIGN KEY(assumption_set_id,workspace_id) REFERENCES valuation_assumption_sets(id,workspace_id),
 UNIQUE(workspace_id,manifest_hash), CHECK(manifest_hash=fundamentals_hash(manifest_text)),
 CHECK(manifest_text=fundamentals_canonical(manifest_text::JSONB)),
 CHECK(compatibility_text=manifest_text),CHECK(compatibility_hash=manifest_hash),
 CHECK(manifest_text::JSONB->>'version' IS NOT DISTINCT FROM 's7-input-v1'),
 CHECK(manifest_text::JSONB->>'evidence_mode' IS NOT DISTINCT FROM 'synthetic'),
 CHECK(manifest_text::JSONB->>'fixture_label' IS NOT DISTINCT FROM 'Synthetic integration fixture — not company data'),
 CHECK(manifest_text::JSONB->>'source_snapshot_id' IS NOT DISTINCT FROM source_snapshot_id::TEXT),
 CHECK(manifest_text::JSONB->>'assumption_set_id' IS NOT DISTINCT FROM assumption_set_id::TEXT),
 CHECK(manifest_text::JSONB#>>'{selector,issuer_id}' IS NOT DISTINCT FROM issuer_id::TEXT),
 CHECK(manifest_text::JSONB#>>'{selector,security_id}' IS NOT DISTINCT FROM security_id::TEXT),
 CHECK(manifest_text::JSONB#>>'{selector,quote_identifier_id}' IS NOT DISTINCT FROM quote_identifier_id::TEXT),
 CHECK(manifest_text::JSONB#>>'{price,source_id}' IS NOT DISTINCT FROM price_source_id::TEXT),
 CHECK((manifest_text::JSONB#>>'{price,batch_id}')::UUID IS NOT DISTINCT FROM price_batch_id),
 CHECK((manifest_text::JSONB#>>'{price,observation_id}')::UUID IS NOT DISTINCT FROM price_id),
 CHECK((manifest_text::JSONB#>>'{price,reference_date}')::DATE IS NOT DISTINCT FROM price_date)
);
CREATE FUNCTION valuation_review_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM analysis_snapshots s JOIN analysis_requests r ON r.id=s.request_id
 JOIN analysis_input_snapshots i ON i.id=s.input_snapshot_id JOIN fundamentals_input_reviews v ON v.id=i.review_id
 WHERE s.id=NEW.source_snapshot_id AND r.workspace_id=NEW.workspace_id AND r.security_id=NEW.security_id
 AND r.quote_identifier_id=NEW.quote_identifier_id AND s.payload_hash=NEW.manifest_text::JSONB->>'source_payload_hash'
 AND v.manifest_hash=NEW.manifest_text::JSONB->>'source_input_hash'
 AND v.manifest_text::JSONB->'selector'=NEW.manifest_text::JSONB->'selector')
 OR NOT EXISTS(SELECT 1 FROM valuation_assumption_sets a WHERE a.id=NEW.assumption_set_id
 AND a.content_text::JSONB=NEW.manifest_text::JSONB->'assumptions')
 OR NOT valuation_shares_valid(NEW.manifest_text::JSONB->'shares')
 OR NEW.model_hash IS DISTINCT FROM fundamentals_hash(fundamentals_canonical(NEW.manifest_text::JSONB->'model'))
 OR NEW.policy_hash IS DISTINCT FROM fundamentals_hash(fundamentals_canonical(NEW.manifest_text::JSONB->'policy'))
 OR (NEW.price_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM price_daily p JOIN market_data_batches b ON b.id=p.batch_id
 WHERE p.id=NEW.price_id AND p.session_date=NEW.price_date AND p.batch_id=NEW.price_batch_id
 AND b.source_id=NEW.price_source_id AND p.quote_identifier_id=NEW.quote_identifier_id AND p.security_id=NEW.security_id)) THEN
 RAISE EXCEPTION 'valuation exact source ownership mismatch' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER review_guard BEFORE INSERT ON valuation_input_reviews FOR EACH ROW EXECUTE FUNCTION valuation_review_guard();
CREATE TABLE valuation_review_claims (
 review_id UUID NOT NULL REFERENCES valuation_input_reviews(id),kind TEXT NOT NULL
 CHECK(kind IN ('cash','nonoperating_assets','debt','leases','preferred','nci','other')),
 state TEXT NOT NULL CHECK(state IN ('eligible_amount','evidenced_absence','unavailable')),
 amount NUMERIC,currency TEXT NOT NULL CHECK(currency~'^[A-Z]{3}$'),as_of DATE NOT NULL,
 evidence_hash TEXT NOT NULL CHECK(evidence_hash~'^[0-9a-f]{64}$'),claim_text TEXT NOT NULL,
 PRIMARY KEY(review_id,kind),CHECK(claim_text=fundamentals_canonical(claim_text::JSONB)),
 CHECK(valuation_claim_valid(claim_text::JSONB)),
 CHECK((state='unavailable')=(amount IS NULL)),CHECK(amount>=0),
 CHECK(state<>'evidenced_absence' OR amount=0)
);
CREATE TABLE valuation_review_claim_ids (
 review_id UUID NOT NULL,kind TEXT NOT NULL,economic_id TEXT NOT NULL,
 PRIMARY KEY(review_id,economic_id), FOREIGN KEY(review_id,kind) REFERENCES valuation_review_claims(review_id,kind)
);
CREATE FUNCTION valuation_review_child_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM valuation_input_reviews WHERE id=NEW.review_id AND creation_transaction_id=txid_current()) THEN
 RAISE EXCEPTION 'review evidence is sealed' USING ERRCODE='55000'; END IF; RETURN NEW; END $$;
CREATE FUNCTION valuation_claim_consistency() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
 IF TG_TABLE_NAME='valuation_review_claims' THEN
 IF NOT EXISTS(SELECT 1 FROM valuation_input_reviews v,jsonb_array_elements(v.manifest_text::JSONB->'claims') c
 WHERE v.id=NEW.review_id AND c=NEW.claim_text::JSONB AND c->>'kind'=NEW.kind AND c->>'state'=NEW.state
 AND (c->>'amount')::NUMERIC IS NOT DISTINCT FROM NEW.amount AND c->>'currency'=NEW.currency
 AND (c->>'as_of')::DATE=NEW.as_of AND c->>'evidence_hash'=NEW.evidence_hash) THEN
 RAISE EXCEPTION 'claim differs from reviewed manifest' USING ERRCODE='23514'; END IF;
 ELSE
 IF NOT EXISTS(SELECT 1 FROM valuation_review_claims c WHERE c.review_id=NEW.review_id AND c.kind=NEW.kind
 AND c.claim_text::JSONB->'economic_claim_ids' ? NEW.economic_id) THEN
 RAISE EXCEPTION 'economic claim identity differs' USING ERRCODE='23514'; END IF;
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER consistency BEFORE INSERT ON valuation_review_claims FOR EACH ROW EXECUTE FUNCTION valuation_claim_consistency();
CREATE TRIGGER consistency BEFORE INSERT ON valuation_review_claim_ids FOR EACH ROW EXECUTE FUNCTION valuation_claim_consistency();
CREATE FUNCTION valuation_review_complete() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
BEGIN
 IF (SELECT count(*) FROM valuation_review_claims WHERE review_id=NEW.id)<>7
 OR EXISTS(SELECT 1 FROM valuation_review_claims c WHERE c.review_id=NEW.id AND
 jsonb_array_length(c.claim_text::JSONB->'economic_claim_ids')<>(SELECT count(*) FROM valuation_review_claim_ids i
 WHERE i.review_id=c.review_id AND i.kind=c.kind)) THEN
 RAISE EXCEPTION 'incomplete reviewed claim roster' USING ERRCODE='23514'; END IF; RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER review_complete AFTER INSERT ON valuation_input_reviews DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION valuation_review_complete();
CREATE TABLE valuation_request_intents (
 request_id UUID PRIMARY KEY REFERENCES analysis_requests(id),review_id UUID NOT NULL REFERENCES valuation_input_reviews(id),
 membership_id UUID REFERENCES watchlist_memberships(id),membership_generation INTEGER,scope_id UUID NOT NULL,
 CHECK((membership_id IS NULL)=(membership_generation IS NULL)),
 CHECK(scope_id=coalesce(membership_id,'00000000-0000-0000-0000-000000000000'::UUID))
);
CREATE TABLE valuation_input_snapshots (
 id UUID PRIMARY KEY,request_id UUID NOT NULL UNIQUE REFERENCES analysis_requests(id),
 creating_execution_id UUID NOT NULL,review_id UUID NOT NULL REFERENCES valuation_input_reviews(id),
 membership_id UUID REFERENCES watchlist_memberships(id),membership_generation INTEGER,scope_id UUID NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(creating_execution_id,request_id) REFERENCES analysis_executions(id,request_id),UNIQUE(id,request_id),
 CHECK((membership_id IS NULL)=(membership_generation IS NULL)),
 CHECK(scope_id=coalesce(membership_id,'00000000-0000-0000-0000-000000000000'::UUID))
);
CREATE TABLE valuation_payloads (
 workspace_id UUID NOT NULL REFERENCES workspaces(id),payload_hash TEXT NOT NULL,dependency_hash TEXT NOT NULL,
 payload_text TEXT NOT NULL,PRIMARY KEY(workspace_id,payload_hash),UNIQUE(workspace_id,dependency_hash),
 CHECK(payload_hash=fundamentals_hash(payload_text)),CHECK(payload_text=fundamentals_canonical(payload_text::JSONB)),
 CHECK(payload_text::JSONB->>'dependency_hash' IS NOT DISTINCT FROM dependency_hash),
 CHECK(payload_text::JSONB->>'version' IS NOT DISTINCT FROM 's7-result-v1'),
 CHECK(payload_text::JSONB->>'evidence_mode' IS NOT DISTINCT FROM 'synthetic')
);
CREATE TABLE valuation_model_runs (
 id UUID PRIMARY KEY,workspace_id UUID NOT NULL REFERENCES workspaces(id),
 request_id UUID NOT NULL UNIQUE REFERENCES analysis_requests(id),execution_id UUID NOT NULL UNIQUE,
 input_snapshot_id UUID NOT NULL UNIQUE,payload_hash TEXT NOT NULL,lease_identity JSONB NOT NULL,
 stage_id UUID NOT NULL REFERENCES analysis_stage_attempts(id),
 outcome TEXT NOT NULL CHECK(outcome IN ('completed','completed_with_gaps')),
 parent_run_id UUID REFERENCES valuation_model_runs(id),generated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
 creation_transaction_id BIGINT NOT NULL DEFAULT txid_current(),
 FOREIGN KEY(workspace_id,payload_hash) REFERENCES valuation_payloads(workspace_id,payload_hash),
 FOREIGN KEY(execution_id,request_id) REFERENCES analysis_executions(id,request_id),
 FOREIGN KEY(input_snapshot_id,request_id) REFERENCES valuation_input_snapshots(id,request_id)
);
CREATE TABLE valuation_scenario_results (
 run_id UUID NOT NULL REFERENCES valuation_model_runs(id),ordinal INTEGER NOT NULL CHECK(ordinal>0),
 name TEXT NOT NULL,state TEXT NOT NULL CHECK(state IN ('converged','no_solution_in_domain','non_unique','inconclusive','unavailable')),
 result_text TEXT NOT NULL,PRIMARY KEY(run_id,ordinal),UNIQUE(run_id,name)
);
CREATE TABLE valuation_sensitivity_results (
 run_id UUID NOT NULL REFERENCES valuation_model_runs(id),ordinal INTEGER NOT NULL CHECK(ordinal>0),
 name TEXT NOT NULL,result_text TEXT NOT NULL,PRIMARY KEY(run_id,ordinal),UNIQUE(run_id,name)
);
CREATE TABLE valuation_conclusions (
 run_id UUID NOT NULL REFERENCES valuation_model_runs(id),ordinal INTEGER NOT NULL CHECK(ordinal>0),
 conclusion TEXT NOT NULL,PRIMARY KEY(run_id,ordinal)
);

CREATE FUNCTION valuation_result_child_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE payload JSONB; expected JSONB;
BEGIN
 SELECT p.payload_text::JSONB INTO payload FROM valuation_model_runs r JOIN valuation_payloads p
 ON p.workspace_id=r.workspace_id AND p.payload_hash=r.payload_hash
 WHERE r.id=NEW.run_id AND r.creation_transaction_id=txid_current();
 IF NOT FOUND THEN RAISE EXCEPTION 'run children are sealed' USING ERRCODE='55000'; END IF;
 IF TG_TABLE_NAME='valuation_conclusions' THEN
 IF payload->'conclusions'->>(NEW.ordinal-1) IS DISTINCT FROM NEW.conclusion THEN
 RAISE EXCEPTION 'conclusion differs from saved payload' USING ERRCODE='23514'; END IF;
 ELSE
 expected:=payload->(CASE WHEN TG_TABLE_NAME='valuation_scenario_results' THEN 'scenarios' ELSE 'sensitivities' END)->(NEW.ordinal-1);
 IF expected IS NULL OR NEW.result_text IS DISTINCT FROM fundamentals_canonical(expected)
 OR NEW.name IS DISTINCT FROM expected->>'name' THEN
 RAISE EXCEPTION 'child differs from saved payload' USING ERRCODE='23514'; END IF;
 IF TG_TABLE_NAME='valuation_scenario_results' AND NEW.state IS DISTINCT FROM expected#>>'{solve,state}' THEN
 RAISE EXCEPTION 'solve state differs from payload' USING ERRCODE='23514'; END IF;
 END IF; RETURN NEW;
END $$;
CREATE FUNCTION valuation_run_complete() RETURNS trigger LANGUAGE plpgsql SET search_path=public,pg_temp AS $$
DECLARE p JSONB;
BEGIN
 SELECT payload_text::JSONB INTO p FROM valuation_payloads WHERE workspace_id=NEW.workspace_id AND payload_hash=NEW.payload_hash;
 IF (SELECT count(*) FROM valuation_scenario_results WHERE run_id=NEW.id)<>jsonb_array_length(p->'scenarios')
 OR (SELECT count(*) FROM valuation_sensitivity_results WHERE run_id=NEW.id)<>jsonb_array_length(p->'sensitivities')
 OR (SELECT count(*) FROM valuation_conclusions WHERE run_id=NEW.id)<>jsonb_array_length(p->'conclusions') THEN
 RAISE EXCEPTION 'incomplete saved result roster' USING ERRCODE='23514'; END IF; RETURN NEW;
END $$;
CREATE CONSTRAINT TRIGGER run_complete AFTER INSERT ON valuation_model_runs DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION valuation_run_complete();
CREATE TABLE latest_valuation (
 workspace_id UUID NOT NULL REFERENCES workspaces(id),security_id UUID NOT NULL REFERENCES securities(id),
 compatibility_hash TEXT NOT NULL,scope_id UUID NOT NULL,latest_request_id UUID NOT NULL REFERENCES analysis_requests(id),
 latest_request_sequence BIGINT NOT NULL,snapshot_id UUID REFERENCES valuation_model_runs(id),snapshot_sequence BIGINT,
 PRIMARY KEY(workspace_id,security_id,compatibility_hash,scope_id),
 CHECK((snapshot_id IS NULL)=(snapshot_sequence IS NULL)),CHECK(snapshot_sequence<=latest_request_sequence)
);
CREATE FUNCTION valuation_latest_guard() RETURNS trigger LANGUAGE plpgsql
 SET search_path=public,pg_temp AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM analysis_requests r JOIN valuation_request_intents i ON i.request_id=r.id
 JOIN valuation_input_reviews v ON v.id=i.review_id
 WHERE r.id=NEW.latest_request_id AND r.workspace_id=NEW.workspace_id AND r.security_id=NEW.security_id
 AND r.request_sequence=NEW.latest_request_sequence AND v.compatibility_hash=NEW.compatibility_hash AND i.scope_id=NEW.scope_id) THEN
 RAISE EXCEPTION 'latest request context mismatch' USING ERRCODE='23514'; END IF;
 IF NEW.snapshot_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM valuation_model_runs s JOIN analysis_requests r ON r.id=s.request_id
 JOIN valuation_input_snapshots i ON i.id=s.input_snapshot_id JOIN valuation_input_reviews v ON v.id=i.review_id
 WHERE s.id=NEW.snapshot_id AND r.workspace_id=NEW.workspace_id AND r.security_id=NEW.security_id
 AND r.request_sequence=NEW.snapshot_sequence AND v.compatibility_hash=NEW.compatibility_hash AND i.scope_id=NEW.scope_id) THEN
 RAISE EXCEPTION 'latest snapshot context mismatch' USING ERRCODE='23514'; END IF;
 IF TG_OP='UPDATE' AND (NEW.latest_request_sequence<OLD.latest_request_sequence
 OR (OLD.snapshot_sequence IS NOT NULL AND (NEW.snapshot_sequence IS NULL OR NEW.snapshot_sequence<OLD.snapshot_sequence))
 OR ROW(NEW.workspace_id,NEW.security_id,NEW.compatibility_hash,NEW.scope_id) IS DISTINCT FROM ROW(OLD.workspace_id,OLD.security_id,OLD.compatibility_hash,OLD.scope_id)) THEN
 RAISE EXCEPTION 'latest projection cannot regress' USING ERRCODE='55000'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER valuation_latest_guard BEFORE INSERT OR UPDATE ON latest_valuation FOR EACH ROW EXECUTE FUNCTION valuation_latest_guard();
CREATE TRIGGER valuation_latest_delete BEFORE DELETE ON latest_valuation FOR EACH ROW EXECUTE FUNCTION evidence_immutable();
CREATE TRIGGER valuation_latest_truncate BEFORE TRUNCATE ON latest_valuation FOR EACH STATEMENT EXECUTE FUNCTION evidence_immutable();
CREATE FUNCTION valuation_enqueue(p_workspace UUID,p_watchlist UUID,p_review UUID,p_key TEXT,p_parent UUID,p_attempts INTEGER) RETURNS JSONB
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE v valuation_input_reviews; r analysis_requests; result JSONB; selector JSONB; options JSONB;
 context_id UUID; m watchlist_memberships; previous valuation_request_intents;
BEGIN
 SELECT * INTO v FROM valuation_input_reviews WHERE id=p_review;
 IF NOT FOUND OR v.workspace_id IS DISTINCT FROM p_workspace
 OR (p_watchlist IS NOT NULL AND NOT EXISTS(SELECT 1 FROM watchlists WHERE id=p_watchlist AND workspace_id=p_workspace)) THEN
 RAISE EXCEPTION 'review workspace mismatch' USING ERRCODE='23514'; END IF;
 IF p_watchlist IS NOT NULL OR p_parent IS NULL OR NOT EXISTS(
 SELECT 1 FROM analysis_requests parent WHERE parent.id=p_parent
 AND parent.workspace_id=p_workspace AND parent.security_id=v.security_id
 AND parent.quote_identifier_id=v.quote_identifier_id AND (
 EXISTS(SELECT 1 FROM analysis_snapshots src WHERE src.id=v.source_snapshot_id AND src.request_id=parent.id)
 OR EXISTS(SELECT 1 FROM valuation_model_runs prior WHERE prior.request_id=parent.id))) THEN
 RAISE EXCEPTION 'saved fundamentals or valuation parent required' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*) FROM valuation_review_claims WHERE review_id=v.id)<>7 THEN
 RAISE EXCEPTION 'complete claim roster required' USING ERRCODE='23514'; END IF;
 selector:=v.manifest_text::JSONB->'selector';
 options:=jsonb_build_object('history_mode',selector->'history_mode','filed_cutoff',selector->'filed_cutoff',
 'retrieval_vintage',selector->'captured_before','max_attempts',p_attempts,
 'requested_periods',jsonb_build_array(jsonb_build_object('kind',CASE WHEN selector->>'period_basis'='instant' THEN 'instant' ELSE 'duration' END,'start',selector->'period_start','end',selector->'period_end')));
 result:=workflow_enqueue(CASE WHEN p_watchlist IS NULL THEN p_workspace ELSE NULL END,p_watchlist,
 v.security_id,v.quote_identifier_id,p_key,options,CASE WHEN p_watchlist IS NULL THEN 'manual_refresh' ELSE 'watchlist_add' END,p_parent);
 SELECT * INTO r FROM analysis_requests WHERE id=(result->>'request_id')::UUID;
 PERFORM 1 FROM analysis_request_state WHERE request_id=r.id FOR UPDATE;
 SELECT * INTO previous FROM valuation_request_intents WHERE request_id=r.id;
 IF FOUND THEN
 IF previous.review_id<>p_review THEN RAISE EXCEPTION 'idempotent request has different review intent' USING ERRCODE='23505'; END IF;
 RETURN result;
 END IF;
 -- A pre-existing ordinary request cannot be retrospectively relabelled as valuation work.
 IF EXISTS(SELECT 1 FROM analysis_executions WHERE request_id=r.id AND (attempt_no<>1 OR state<>'queued')) THEN
 RAISE EXCEPTION 'request has already started without valuation intent' USING ERRCODE='55000'; END IF;
 WITH RECURSIVE lineage AS (SELECT id,parent_request_id,membership_id,0 depth FROM analysis_requests WHERE id=r.id
 UNION ALL SELECT a.id,a.parent_request_id,a.membership_id,l.depth+1 FROM analysis_requests a JOIN lineage l ON a.id=l.parent_request_id)
 SELECT membership_id INTO context_id FROM lineage WHERE membership_id IS NOT NULL ORDER BY depth LIMIT 1;
 IF context_id IS NOT NULL THEN
 SELECT * INTO m FROM watchlist_memberships WHERE id=context_id FOR UPDATE;
 IF m.removed_at IS NOT NULL OR m.security_id<>r.security_id OR m.quote_identifier_id<>r.quote_identifier_id THEN
 RAISE EXCEPTION 'membership no longer eligible' USING ERRCODE='55000'; END IF;
 END IF;
 INSERT INTO valuation_request_intents VALUES(r.id,p_review,context_id,m.generation,coalesce(context_id,'00000000-0000-0000-0000-000000000000'::UUID));
 INSERT INTO latest_valuation(workspace_id,security_id,compatibility_hash,scope_id,latest_request_id,latest_request_sequence)
 VALUES(r.workspace_id,r.security_id,v.compatibility_hash,coalesce(context_id,'00000000-0000-0000-0000-000000000000'::UUID),r.id,r.request_sequence)
 ON CONFLICT(workspace_id,security_id,compatibility_hash,scope_id) DO UPDATE
 SET latest_request_id=excluded.latest_request_id,latest_request_sequence=excluded.latest_request_sequence
 WHERE latest_valuation.latest_request_sequence<excluded.latest_request_sequence;
 RETURN result;
END $$;
CREATE FUNCTION valuation_freeze(p_lease JSONB,p_stage UUID,p_review UUID) RETURNS UUID
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE e analysis_executions; r analysis_requests; v valuation_input_reviews; i valuation_input_snapshots;
 m watchlist_memberships; selector JSONB; new_id UUID:=gen_random_uuid(); context_id UUID;
BEGIN
 e:=workflow_locked_lease(p_lease);
 SELECT * INTO r FROM analysis_requests WHERE id=e.request_id;
 SELECT * INTO v FROM valuation_input_reviews WHERE id=p_review;
 IF NOT FOUND OR r.trigger NOT IN ('watchlist_add','manual_refresh') OR r.workspace_id<>v.workspace_id
 OR r.security_id<>v.security_id OR r.quote_identifier_id<>v.quote_identifier_id
 OR NOT EXISTS(SELECT 1 FROM securities WHERE id=r.security_id AND issuer_id=v.issuer_id) THEN
 RAISE EXCEPTION 'review/request identity mismatch' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT 1 FROM analysis_stage_attempts WHERE id=p_stage AND execution_id=e.id AND stage_key='valuation' AND state='running') THEN
 RAISE EXCEPTION 'active valuation stage required' USING ERRCODE='55000'; END IF;
 IF NOT EXISTS(SELECT 1 FROM valuation_request_intents WHERE request_id=r.id AND review_id=p_review) THEN
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
 SELECT * INTO i FROM valuation_input_snapshots WHERE request_id=r.id;
 IF FOUND THEN
 IF i.review_id<>p_review THEN RAISE EXCEPTION 'request inputs already frozen' USING ERRCODE='55000'; END IF;
 RETURN i.id;
 END IF;
 INSERT INTO valuation_input_snapshots(id,request_id,creating_execution_id,review_id,membership_id,membership_generation,scope_id)
 VALUES(new_id,r.id,e.id,v.id,context_id,m.generation,coalesce(context_id,'00000000-0000-0000-0000-000000000000'::UUID));
 INSERT INTO latest_valuation(workspace_id,security_id,compatibility_hash,scope_id,latest_request_id,latest_request_sequence)
 VALUES(r.workspace_id,r.security_id,v.compatibility_hash,coalesce(context_id,'00000000-0000-0000-0000-000000000000'::UUID),r.id,r.request_sequence)
 ON CONFLICT(workspace_id,security_id,compatibility_hash,scope_id) DO UPDATE
 SET latest_request_id=excluded.latest_request_id,latest_request_sequence=excluded.latest_request_sequence
 WHERE latest_valuation.latest_request_sequence<excluded.latest_request_sequence;
 PERFORM workflow_event(e.id,'valuation_frozen',jsonb_build_object('input_snapshot_id',new_id));
 RETURN new_id;
END $$;
CREATE FUNCTION valuation_publish(p_lease JSONB,p_stage UUID,p_input UUID,p_payload TEXT) RETURNS UUID
 LANGUAGE plpgsql SECURITY DEFINER SET search_path=public,pg_temp AS $$
DECLARE e analysis_executions; r analysis_requests; i valuation_input_snapshots; v valuation_input_reviews;
 old valuation_model_runs; m watchlist_memberships; p JSONB:=p_payload::JSONB; h TEXT:=fundamentals_hash(p_payload);
 saved TEXT; new_id UUID:=gen_random_uuid(); result_outcome TEXT;
BEGIN
 -- Serialize before checking replay, including concurrent crash-response retries.
 PERFORM 1 FROM analysis_request_state WHERE request_id=(p_lease->>'request_id')::UUID FOR UPDATE;
 SELECT * INTO old FROM valuation_model_runs WHERE request_id=(p_lease->>'request_id')::UUID;
 IF FOUND THEN
 IF old.lease_identity IS DISTINCT FROM p_lease OR old.stage_id IS DISTINCT FROM p_stage OR old.input_snapshot_id IS DISTINCT FROM p_input OR old.payload_hash IS DISTINCT FROM h THEN
 RAISE EXCEPTION 'conflicting publication replay' USING ERRCODE='55000'; END IF;
 RETURN old.id;
 END IF;
 e:=workflow_locked_lease(p_lease);
 SELECT * INTO r FROM analysis_requests WHERE id=e.request_id;
 SELECT * INTO i FROM valuation_input_snapshots WHERE id=p_input AND request_id=r.id;
 IF NOT FOUND THEN RAISE EXCEPTION 'frozen input ownership mismatch' USING ERRCODE='23514'; END IF;
 SELECT * INTO v FROM valuation_input_reviews WHERE id=i.review_id;
 IF i.membership_id IS NOT NULL THEN
 SELECT * INTO m FROM watchlist_memberships WHERE id=i.membership_id FOR UPDATE;
 IF m.removed_at IS NOT NULL OR m.generation<>i.membership_generation THEN
 RAISE EXCEPTION 'membership no longer eligible' USING ERRCODE='55000'; END IF;
 END IF;
 IF NOT EXISTS(SELECT 1 FROM analysis_stage_attempts WHERE id=p_stage AND execution_id=e.id AND stage_key='valuation' AND state='running')
 OR EXISTS(SELECT 1 FROM analysis_stage_attempts WHERE execution_id=e.id AND state='running' AND id<>p_stage) THEN
 RAISE EXCEPTION 'exclusive active valuation stage required' USING ERRCODE='55000'; END IF;
 IF p_payload IS NULL OR p_payload IS DISTINCT FROM fundamentals_canonical(p)
 OR h IS DISTINCT FROM v.expected_payload_hash OR p->>'dependency_hash' IS DISTINCT FROM v.manifest_hash
 OR p->>'source_snapshot_id' IS DISTINCT FROM v.source_snapshot_id::TEXT THEN
 RAISE EXCEPTION 'payload differs from independently reviewed calculation' USING ERRCODE='23514'; END IF;
 INSERT INTO valuation_payloads(workspace_id,payload_hash,dependency_hash,payload_text) VALUES(r.workspace_id,h,v.manifest_hash,p_payload)
 ON CONFLICT(workspace_id,dependency_hash) DO NOTHING;
 SELECT payload_text INTO saved FROM valuation_payloads WHERE workspace_id=r.workspace_id AND dependency_hash=v.manifest_hash;
 IF saved IS DISTINCT FROM p_payload THEN RAISE EXCEPTION 'non-deterministic payload' USING ERRCODE='23514'; END IF;
 result_outcome:=CASE WHEN p->'scenario_dispersion'='null'::JSONB
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(p->'scenarios') x WHERE x#>>'{solve,state}'<>'converged')
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(p->'sensitivities') g,
 jsonb_array_elements(g->'cells') c WHERE c->'value'='null'::JSONB)
 THEN 'completed_with_gaps' ELSE 'completed' END;
 INSERT INTO valuation_model_runs(id,workspace_id,request_id,execution_id,input_snapshot_id,payload_hash,lease_identity,stage_id,outcome,parent_run_id)
 VALUES(new_id,r.workspace_id,r.id,e.id,i.id,h,p_lease,p_stage,result_outcome,
 (SELECT id FROM valuation_model_runs WHERE request_id=r.parent_request_id));
 INSERT INTO valuation_scenario_results SELECT new_id,n::INTEGER,x->>'name',x#>>'{solve,state}',fundamentals_canonical(x)
 FROM jsonb_array_elements(p->'scenarios') WITH ORDINALITY s(x,n);
 INSERT INTO valuation_sensitivity_results SELECT new_id,n::INTEGER,x->>'name',fundamentals_canonical(x)
 FROM jsonb_array_elements(p->'sensitivities') WITH ORDINALITY s(x,n);
 INSERT INTO valuation_conclusions SELECT new_id,n::INTEGER,x FROM jsonb_array_elements_text(p->'conclusions') WITH ORDINALITY s(x,n);
 PERFORM workflow_finish_stage(p_lease,p_stage,'completed',NULL,ARRAY[]::UUID[]);
 PERFORM workflow_event(e.id,'valuation_published',jsonb_build_object('snapshot_id',new_id,'payload_hash',h));
 PERFORM workflow_finish(p_lease,result_outcome,NULL);
 UPDATE latest_valuation SET snapshot_id=new_id,snapshot_sequence=r.request_sequence
 WHERE workspace_id=r.workspace_id AND security_id=r.security_id AND compatibility_hash=v.compatibility_hash
 AND scope_id=i.scope_id AND latest_request_sequence=r.request_sequence;
 RETURN new_id;
END $$;
"""

TABLES = [
    "valuation_model_definitions",
    "valuation_policy_revisions",
    "valuation_assumption_sets",
    "valuation_assumption_entries",
    "valuation_input_reviews",
    "valuation_review_claims",
    "valuation_review_claim_ids",
    "valuation_request_intents",
    "valuation_input_snapshots",
    "valuation_payloads",
    "valuation_model_runs",
    "valuation_scenario_results",
    "valuation_sensitivity_results",
    "valuation_conclusions",
]
FUNCTIONS = [
    "valuation_publish(jsonb,uuid,uuid,text)",
    "valuation_freeze(jsonb,uuid,uuid)",
    "valuation_enqueue(uuid,uuid,uuid,text,uuid,integer)",
    "valuation_create_assumptions(uuid,uuid,text,text)",
    "valuation_latest_guard()",
    "valuation_result_child_guard()",
    "valuation_review_child_guard()",
    "valuation_review_guard()",
    "valuation_assumption_child_guard()",
    "valuation_claim_consistency()",
    "valuation_review_complete()",
    "valuation_run_complete()",
    "valuation_shape_valid(jsonb,jsonb,jsonb,integer)",
    "valuation_assumptions_valid(jsonb)",
    "valuation_assumption_complete()",
    "valuation_claim_valid(jsonb)",
    "valuation_shares_valid(jsonb)",
]


def upgrade():
    # Escape literal colons for SQLAlchemy text binding, including embedded JSON.
    op.execute(SQL.replace(":", r"\:"))
    for table in TABLES:
        op.execute(
            f"CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION evidence_immutable()"
        )
        op.execute(
            f"CREATE TRIGGER immutable_truncate BEFORE TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION evidence_immutable()"
        )
    for table in ("valuation_review_claims", "valuation_review_claim_ids"):
        op.execute(
            f"CREATE TRIGGER seal BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION valuation_review_child_guard()"
        )
    for table in (
        "valuation_scenario_results",
        "valuation_sensitivity_results",
        "valuation_conclusions",
    ):
        op.execute(
            f"CREATE TRIGGER seal BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION valuation_result_child_guard()"
        )
    for table in [*TABLES, "latest_valuation"]:
        op.execute(
            f"REVOKE ALL ON {table} FROM PUBLIC,equity_runtime; GRANT SELECT ON {table} TO equity_runtime"
        )
    for function in FUNCTIONS:
        op.execute(f"REVOKE ALL ON FUNCTION {function} FROM PUBLIC,equity_runtime")
    op.execute(
        "GRANT EXECUTE ON FUNCTION valuation_claim_valid(jsonb),valuation_shares_valid(jsonb),valuation_assumptions_valid(jsonb),valuation_shape_valid(jsonb,jsonb,jsonb,integer) TO equity_runtime"
    )
    for function in FUNCTIONS[:4]:
        op.execute(f"GRANT EXECUTE ON FUNCTION {function} TO equity_runtime")


def downgrade():
    op.execute("""DO $$ BEGIN IF EXISTS(SELECT 1 FROM valuation_assumption_sets)
    OR EXISTS(SELECT 1 FROM valuation_input_reviews) OR EXISTS(SELECT 1 FROM valuation_model_runs)
    THEN RAISE EXCEPTION 'cannot downgrade retained valuation history' USING ERRCODE='55000'; END IF; END $$""")
    for function in FUNCTIONS[:4]:
        op.execute(f"DROP FUNCTION {function}")
    op.execute("DROP TABLE latest_valuation")
    for table in reversed(TABLES):
        op.execute(f"DROP TABLE {table}")
    for function in FUNCTIONS[4:]:
        op.execute(f"DROP FUNCTION {function}")
