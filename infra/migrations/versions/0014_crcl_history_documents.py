"""D050 exact CRCL history-document intent; no general PDF acquisition."""

from importlib import import_module

from alembic import op

revision = "0014_crcl_history_documents"
down_revision = "0013_real_fundamentals"
branch_labels = None
depends_on = None

# Frozen reviewed roster; migrations do not import mutable application contracts.
DOCUMENTS = (
    "filing_document/0001876042/0000000000-24-002161/filename1.pdf",
    "filing_document/0001876042/0000000000-24-007530/filename1.pdf",
    "filing_document/0001876042/0000000000-24-012208/filename1.pdf",
    "filing_document/0001876042/0000000000-25-000390/filename1.pdf",
    "filing_document/0001876042/0000000000-25-002262/filename1.pdf",
    "filing_document/0001876042/0000000000-25-003884/filename1.pdf",
    "filing_document/0001876042/0000000000-25-008270/filename1.pdf",
    "filing_document/0001876042/0000950103-24-005276/filename1.htm",
    "filing_document/0001876042/0000950103-25-003718/filename1.htm",
    "filing_document/0001876042/0000950103-25-004232/filename1.htm",
    "filing_document/0001876042/0000950103-25-006798/filename1.htm",
    "filing_document/0001876042/0000950103-25-006799/filename1.htm",
    "filing_document/0001876042/0000950103-25-007009/dp229827_s1mef.htm",
    "filing_document/0001876042/0000950123-23-011178/filename1.htm",
    "filing_document/0001876042/0000950123-24-003285/filename1.htm",
    "filing_document/0001876042/0000950123-24-007245/filename1.htm",
    "filing_document/0001876042/0000950123-24-007246/filename1.htm",
    "filing_document/0001876042/0000950123-24-012158/filename1.htm",
    "filing_document/0001876042/0000950123-24-012159/filename1.htm",
    "filing_document/0001876042/0000950123-25-000606/filename1.htm",
    "filing_document/0001876042/0000950123-25-001965/filename1.htm",
    "filing_document/0001876042/0000950123-25-001969/filename1.htm",
    "filing_document/0001876042/0000950123-25-006942/filename1.htm",
    "filing_document/0001876042/0001104659-21-101498/tm2123712-1_s4.htm",
    "filing_document/0001876042/0001104659-21-102122/tm2123712d3_425.htm",
    "filing_document/0001876042/0001104659-21-102322/tm2123712d4_425.htm",
    "filing_document/0001876042/0001104659-21-108632/tm2125702d1_425.htm",
    "filing_document/0001876042/0001104659-21-108633/tm2125702d2_425.htm",
    "filing_document/0001876042/0001104659-21-122565/tm2124445-1_s4a.htm",
    "filing_document/0001876042/0001104659-21-128323/tm2124445d5_425.htm",
    "filing_document/0001876042/0001104659-21-153174/tm2124445-4_s4a.htm",
    "filing_document/0001876042/0001104659-22-044857/tm2124445d11_425.htm",
    "filing_document/0001876042/0001104659-22-056979/tm2124445-8_s4a.htm",
    "filing_document/0001876042/0001104659-22-068177/tm2217643d1_425.htm",
    "filing_document/0001876042/0001104659-22-068962/tm2217643d2_425.htm",
    "filing_document/0001876042/0001104659-22-078873/tm2124445-12_s4a.htm",
    "filing_document/0001876042/0001104659-22-096202/tm2124445-15_s4a.htm",
    "filing_document/0001876042/0001104659-22-110332/tm2124445-18_s4a.htm",
    "filing_document/0001876042/0001104659-22-118597/tm2124445-21_s4a.htm",
    "filing_document/0001876042/0001104659-22-124570/tm2124445d25_rw.htm",
    "filing_document/0001876042/0001193125-25-084837/filename1.htm",
    "filing_document/0001876042/0001193125-25-098254/filename1.htm",
    "filing_document/0001876042/0001193125-25-179050/filename1.htm",
    "filing_document/0001876042/0001193125-25-179053/filename1.htm",
    "filing_document/0001876042/0001193125-26-335377/d149697ds3asr.htm",
    "filing_document/0001876042/0001213900-22-008149/ea155842-8k425_concord.htm",
    "filing_document/0001876042/0001876042-26-000116/a2025annualreport0331.pdf",
)


def frozen_function(module: str, name: str) -> str:
    frozen = import_module("infra.migrations.versions." + module)
    sql = frozen.POLICY_SQL if module == "0004_market_data_contract" else frozen.SQL
    start = sql.index("FUNCTION " + name + "(")
    return "CREATE OR REPLACE " + sql[start : sql.index("$$;", start) + 3]


def upgrade() -> None:
    original_plan = frozen_function("0007_bootstrap_intent", "workflow_valid_bootstrap_plan")
    original_resource = frozen_function("0004_market_data_contract", "market_sec_resource")
    op.execute(
        original_plan.replace("workflow_valid_bootstrap_plan(", "workflow_valid_bootstrap_plan_v1(")
    )
    op.execute(original_resource.replace("market_sec_resource(", "market_sec_resource_v1("))
    allowed = ",".join("'" + key + "'" for key in DOCUMENTS)
    pdfs = ",".join("'" + key + "'" for key in DOCUMENTS if key.endswith(".pdf"))
    op.execute(
        """
CREATE OR REPLACE FUNCTION workflow_valid_bootstrap_plan(p JSONB) RETURNS BOOLEAN
LANGUAGE plpgsql IMMUTABLE SET search_path=public,pg_temp AS $$
DECLARE k TEXT; n INTEGER; common JSONB;
BEGIN
 IF p->>'version'='sec-identity-bootstrap-v1' THEN
  RETURN workflow_valid_bootstrap_plan_v1(p);
 END IF;
 IF p->>'version' IS DISTINCT FROM 'sec-crcl-history-bootstrap-v2'
 OR p->>'cik' IS DISTINCT FROM '0001876042'
 OR jsonb_typeof(p->'resources') IS DISTINCT FROM 'array' THEN RETURN FALSE; END IF;
 common:=jsonb_set(jsonb_set(p,'{version}','"sec-identity-bootstrap-v1"'),'{resources}',
  '["company_facts/0001876042","submissions/0001876042"]');
 IF NOT workflow_valid_bootstrap_plan_v1(common) THEN RETURN FALSE; END IF;
 n:=jsonb_array_length(p->'resources');
 IF n NOT BETWEEN 2 AND 7
 OR NOT (p->'resources') ?& ARRAY['company_facts/0001876042','submissions/0001876042']
 OR (SELECT count(DISTINCT value) FROM jsonb_array_elements(p->'resources'))<>n
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(p->'resources') WHERE jsonb_typeof(value)<>'string')
 THEN RETURN FALSE; END IF;
 FOR k IN SELECT jsonb_array_elements_text(p->'resources') LOOP
  IF k IN ('company_facts/0001876042','submissions/0001876042') THEN CONTINUE; END IF;
  IF k NOT IN ("""
        + allowed
        + """) THEN RETURN FALSE; END IF;
 END LOOP;
 RETURN TRUE;
END $$;
CREATE OR REPLACE FUNCTION market_sec_resource(p_source uuid,p_policy uuid,p_url text,p_object text)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
 SELECT market_sec_resource_v1(p_source,p_policy,p_url,p_object) OR (
  p_object IN ("""
        + pdfs
        + """)
  AND p_url='https://www.sec.gov/Archives/edgar/data/1876042/'||
   replace(split_part(p_object,'/',3),'-','')||'/'||split_part(p_object,'/',4)
  AND EXISTS(SELECT FROM sources s JOIN source_policy_revisions p ON p.source_id=s.id
   WHERE s.id=p_source AND p.id=p_policy
   AND s.base_url IN ('https://data.sec.gov','https://www.sec.gov')));
$$;
REVOKE ALL ON FUNCTION workflow_valid_bootstrap_plan_v1(JSONB),
 market_sec_resource_v1(UUID,UUID,TEXT,TEXT) FROM PUBLIC,equity_runtime;
"""
    )
    guard = frozen_function("0007_bootstrap_intent", "workflow_bootstrap_attempt_guard")
    guard = guard.replace(
        " RETURN NEW;",
        """
 IF right(NEW.source_object_key,4)='.pdf' AND (
  kind IS DISTINCT FROM 'source_bootstrap'
  OR plan->>'version' IS DISTINCT FROM 'sec-crcl-history-bootstrap-v2'
  OR NOT workflow_valid_bootstrap_plan(plan)) THEN
  RAISE EXCEPTION 'PDF requires exact V2 bootstrap intent' USING ERRCODE='23514';
 END IF;
 RETURN NEW;""",
    )
    op.execute(guard)


def downgrade() -> None:
    op.execute("""
DO $$ BEGIN
 IF EXISTS(SELECT 1 FROM analysis_requests
  WHERE bootstrap_plan->>'version'='sec-crcl-history-bootstrap-v2') THEN
  RAISE EXCEPTION 'refusing to discard retained V2 acquisition intent' USING ERRCODE='55000';
 END IF;
END $$;
""")
    for module, name in (
        ("0007_bootstrap_intent", "workflow_valid_bootstrap_plan"),
        ("0007_bootstrap_intent", "workflow_bootstrap_attempt_guard"),
        ("0004_market_data_contract", "market_sec_resource"),
    ):
        op.execute(frozen_function(module, name))
    op.execute("""
DROP FUNCTION workflow_valid_bootstrap_plan_v1(JSONB);
DROP FUNCTION market_sec_resource_v1(UUID,UUID,TEXT,TEXT);
""")
