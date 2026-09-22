"""Owner-reviewed synthetic S7 storage; runtime writes use narrow W1 fences."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC
from typing import Any
from uuid import UUID, uuid4

from equity_schema.fundamentals_canonical import canonical_json, content_hash, parse_canonical
from equity_schema.fundamentals_store import (
    _require_idle_autocommit,
    _verify_sources,
    engine_revision,
    get_snapshot,
)
from equity_schema.fundamentals_store import (
    frozen_manifest as source_manifest,
)
from equity_schema.market_selection import MarketSelection, select_price
from equity_schema.valuation import (
    AssumptionContent,
    AssumptionCreate,
    AssumptionSaved,
    LatestResponse,
    PriceEvidence,
    RequestCreate,
    RequestResponse,
    RunResponse,
    ValuationManifest,
    ValuationPayload,
    read_manifest,
)
from equity_schema.workflow import Database, Lease, RequestHandle, _invoke, _request
from psycopg.types.json import Jsonb


def engine_build() -> str:
    return engine_revision().split(":", 1)[1]


def selection_hash(selection: MarketSelection) -> str:
    values = asdict(selection)
    age = values.pop("capture_age")
    # S4's derived timedelta cannot be serialized as a binary-float second count.
    values["capture_age_microseconds"] = (
        None if age is None else (age.days * 86400 + age.seconds) * 1000000 + age.microseconds
    )
    return content_hash(values)


def price_evidence(selection: MarketSelection, *, action_basis: str) -> PriceEvidence:
    if (
        selection.quote_identifier_id is None
        or selection.security_id is None
        or selection.retrieval_cutoff is None
        or selection.source_known_at is None
        or selection.field != "close"
    ):
        raise ValueError("Explicit raw close identity and PIT selectors required")
    return PriceEvidence(
        source_id=selection.source_id,
        field="close",
        quote_identifier_id=selection.quote_identifier_id,
        security_id=selection.security_id,
        batch_id=selection.batch_id,
        observation_id=selection.observation_id,
        reference_date=selection.reference_date,
        retrieval_cutoff=selection.retrieval_cutoff,
        source_known_at=selection.source_known_at,
        selection_hash=selection_hash(selection),
        value=selection.value,
        currency=selection.currency,
        usable=selection.usable,
        adjustment_basis=selection.adjustment_basis,
        session_basis=selection.session_basis,
        action_basis=action_basis,
        reasons=selection.flags,
    )


def get_assumptions(
    db: Database, *, workspace_id: UUID, assumption_id: UUID
) -> AssumptionSaved | None:
    row = db.execute(
        "SELECT * FROM valuation_assumption_sets WHERE workspace_id=%s AND id=%s",
        (workspace_id, assumption_id),
    ).fetchone()
    if not row:
        return None
    parse_canonical(row["content_text"])
    content = AssumptionContent.model_validate_json(row["content_text"])
    if content_hash(content) != row["content_hash"]:
        raise ValueError("Saved assumption digest mismatch")
    return AssumptionSaved(
        id=row["id"], parent_id=row["parent_id"], content_hash=row["content_hash"], content=content
    )


def create_assumptions(
    db: Database, *, workspace_id: UUID, request: AssumptionCreate
) -> AssumptionSaved:
    _require_idle_autocommit(db)
    request = AssumptionCreate.model_validate(request.model_dump())
    saved = _invoke(
        db,
        "SELECT valuation_create_assumptions(%s,%s,%s,%s) AS result",
        (workspace_id, request.parent_id, request.idempotency_key, canonical_json(request.content)),
    )
    result = get_assumptions(db, workspace_id=workspace_id, assumption_id=UUID(str(saved)))
    assert result is not None
    return result


def save_fixture_assumptions(
    db: Database,
    *,
    workspace_id: UUID,
    content: AssumptionContent,
    idempotency_key: str,
    parent_id: UUID | None = None,
) -> AssumptionSaved:
    """Owner-only historical fictional authorship; runtime API enforces current authorship.

    The direct insert has no runtime grant. This fixture review boundary cannot
    turn a user's backdated assumption into an ex-ante historical record.
    """
    _require_idle_autocommit(db)
    content = AssumptionContent.model_validate(content.model_dump())
    new_id = uuid4()
    with db.transaction():
        db.execute(
            """INSERT INTO valuation_assumption_sets
        (id,workspace_id,parent_id,idempotency_key,content_text,content_hash,authored_at,retrospective)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                new_id,
                workspace_id,
                parent_id,
                idempotency_key,
                canonical_json(content),
                content_hash(content),
                content.authored_at,
                content.retrospective,
            ),
        )
        for entry in content.judgments:
            db.execute(
                "INSERT INTO valuation_assumption_entries VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (
                    new_id,
                    entry.scenario,
                    entry.parameter,
                    entry.unit,
                    entry.effective_from,
                    entry.effective_to,
                    canonical_json(entry),
                ),
            )
    result = get_assumptions(db, workspace_id=workspace_id, assumption_id=new_id)
    assert result is not None
    return result


def approve_fixture_manifest(
    db: Database, *, workspace_id: UUID, manifest: ValuationManifest, reviewed_by: str, reason: str
) -> UUID:
    from equity_core.valuation_payload import calculate_payload, resolved
    from equity_core.valuation_source import anchor_reasons

    _require_idle_autocommit(db)
    manifest = read_manifest(canonical_json(manifest))
    if (
        not reviewed_by.strip()
        or not reason.strip()
        or manifest.model.engine_build != engine_build()
    ):
        raise ValueError("Reviewed current engine and explicit owner rationale required")
    source = get_snapshot(db, workspace_id=workspace_id, snapshot_id=manifest.source_snapshot_id)
    if source is None or source.payload_hash != manifest.source_payload_hash:
        raise ValueError("Exact source snapshot missing")
    source_workspace, inputs = source_manifest(db, source.input_snapshot_id)
    if (
        source_workspace != workspace_id
        or manifest.source_input_hash != content_hash(inputs)
        or manifest.selector != inputs.selector
    ):
        raise ValueError("Exact source selections differ")
    _verify_sources(db, inputs)
    anchor_index = manifest.assumptions.anchor_source_index
    if anchor_index >= len(inputs.sources):
        raise ValueError("Anchor source index absent")
    anchor = inputs.sources[anchor_index]
    if str(anchor.concept.value) != "revenue" or anchor.fact is None or anchor.fact.value is None:
        raise ValueError("Reviewed annual revenue source required")
    actual_reasons = anchor_reasons(anchor, inputs.selector, manifest.assumptions.valuation_at)
    if manifest.source_eligibility_reasons != actual_reasons:
        raise ValueError("Frozen source eligibility differs from S5 evidence")
    actual_uncertainty = (
        ("revenue_anchor", anchor.precision.absolute_error if anchor.precision else None),
    )
    if manifest.source_measurement_uncertainty != actual_uncertainty:
        raise ValueError("Source uncertainty differs from retained precision evidence")
    for scenario in manifest.assumptions.scenarios:
        if scenario.revenue_anchor != anchor.fact.value:
            raise ValueError("Carry-forward anchor differs from selected source; no hidden rebase")
        resolved(scenario, scenario.solve.lower)
        resolved(scenario, scenario.solve.upper)
    saved = get_assumptions(db, workspace_id=workspace_id, assumption_id=manifest.assumption_set_id)
    if saved is None or saved.content != manifest.assumptions:
        raise ValueError("Immutable assumption contents differ")
    price = manifest.price
    selection = select_price(
        db,
        price.source_id,
        price.quote_identifier_id,
        price.reference_date,
        field="close",
        retrieval_cutoff=price.retrieval_cutoff,
        batch_id=price.batch_id,
        source_known_at=price.source_known_at,
    )
    if price_evidence(selection, action_basis=price.action_basis) != price:
        raise ValueError("Price selection differs from exact retained S4 evidence")
    for capture in selection.provenance:
        row = db.execute(
            "SELECT content_scope FROM sources WHERE id=%s", (capture.source_id,)
        ).fetchone()
        if (
            not row
            or row["content_scope"] != "test fixture"
            or not capture.request_url.startswith("https://example.invalid/")
        ):
            raise ValueError("Only fictional S4 evidence may be reviewed")
    expected = calculate_payload(manifest)
    new_id = uuid4()
    body = canonical_json(manifest)
    digest = content_hash(manifest)
    with db.transaction():
        prior = db.execute(
            "SELECT id FROM valuation_input_reviews WHERE workspace_id=%s AND manifest_hash=%s",
            (workspace_id, digest),
        ).fetchone()
        if prior:
            return UUID(str(prior["id"]))
        db.execute(
            "INSERT INTO valuation_model_definitions VALUES(%s,%s) ON CONFLICT DO NOTHING",
            (content_hash(manifest.model), canonical_json(manifest.model)),
        )
        db.execute(
            "INSERT INTO valuation_policy_revisions VALUES(%s,%s) ON CONFLICT DO NOTHING",
            (content_hash(manifest.policy), canonical_json(manifest.policy)),
        )
        db.execute(
            """INSERT INTO valuation_input_reviews
        (id,workspace_id,issuer_id,security_id,quote_identifier_id,source_snapshot_id,assumption_set_id,
        model_hash,policy_hash,manifest_text,manifest_hash,compatibility_text,compatibility_hash,
        expected_payload_hash,reviewed_by,reason,price_date,price_id,price_source_id,price_batch_id)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                new_id,
                workspace_id,
                manifest.selector.issuer_id,
                manifest.selector.security_id,
                manifest.selector.quote_identifier_id,
                manifest.source_snapshot_id,
                manifest.assumption_set_id,
                content_hash(manifest.model),
                content_hash(manifest.policy),
                body,
                digest,
                body,
                digest,
                content_hash(expected),
                reviewed_by,
                reason,
                price.reference_date,
                price.observation_id,
                price.source_id,
                price.batch_id,
            ),
        )
        for claim in manifest.claims:
            db.execute(
                "INSERT INTO valuation_review_claims VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    new_id,
                    claim.kind,
                    claim.state,
                    claim.amount,
                    claim.currency,
                    claim.as_of,
                    claim.evidence_hash,
                    canonical_json(claim),
                ),
            )
            for economic_id in claim.economic_claim_ids:
                db.execute(
                    "INSERT INTO valuation_review_claim_ids VALUES(%s,%s,%s)",
                    (new_id, claim.kind, economic_id),
                )
    return new_id


def enqueue_valuation(db: Database, *, workspace_id: UUID, request: RequestCreate) -> RequestHandle:
    _require_idle_autocommit(db)
    request = RequestCreate.model_validate(request.model_dump())
    return _request(
        _invoke(
            db,
            "SELECT valuation_enqueue(%s,NULL,%s,%s,%s,%s) AS result",
            (
                workspace_id,
                request.review_id,
                request.idempotency_key,
                request.parent_request_id,
                request.max_attempts,
            ),
        )
    )


def freeze_inputs(db: Database, lease: Lease, *, stage_id: UUID, review_id: UUID) -> UUID:
    _require_idle_autocommit(db)
    return UUID(
        str(
            _invoke(
                db,
                "SELECT valuation_freeze(%s,%s,%s) AS result",
                (Jsonb(lease.as_json()), stage_id, review_id),
            )
        )
    )


def frozen_manifest(db: Database, input_snapshot_id: UUID) -> ValuationManifest:
    row = db.execute(
        """SELECT v.manifest_text,v.manifest_hash FROM valuation_input_snapshots i
    JOIN valuation_input_reviews v ON v.id=i.review_id WHERE i.id=%s""",
        (input_snapshot_id,),
    ).fetchone()
    if not row:
        raise ValueError("Frozen valuation input not found")
    result = read_manifest(row["manifest_text"])
    if content_hash(result) != row["manifest_hash"]:
        raise ValueError("Frozen valuation input digest differs")
    return result


RUN_SQL = """SELECT s.*,p.payload_text,v.compatibility_hash FROM valuation_model_runs s
JOIN analysis_requests r ON r.id=s.request_id
JOIN valuation_input_snapshots i ON i.id=s.input_snapshot_id
JOIN valuation_input_reviews v ON v.id=i.review_id
JOIN valuation_payloads p ON p.workspace_id=s.workspace_id AND p.payload_hash=s.payload_hash"""


def _run(row: dict[str, Any]) -> RunResponse:
    parse_canonical(row["payload_text"])
    payload = ValuationPayload.model_validate_json(row["payload_text"])
    if (
        canonical_json(payload) != row["payload_text"]
        or content_hash(payload) != row["payload_hash"]
    ):
        raise ValueError("Saved valuation bytes or digest differ")
    return RunResponse(
        run_id=row["id"],
        parent_run_id=row["parent_run_id"],
        request_id=row["request_id"],
        execution_id=row["execution_id"],
        input_snapshot_id=row["input_snapshot_id"],
        generated_at=row["generated_at"].astimezone(UTC),
        compatibility_key=row["compatibility_hash"],
        payload_hash=row["payload_hash"],
        outcome=row["outcome"],
        result=payload,
    )


def get_run(db: Database, *, workspace_id: UUID, run_id: UUID) -> RunResponse | None:
    row = db.execute(
        RUN_SQL + " WHERE s.workspace_id=%s AND s.id=%s", (workspace_id, run_id)
    ).fetchone()
    return _run(row) if row else None


def saved_payload(db: Database, lease: Lease) -> str | None:
    row = db.execute(RUN_SQL + " WHERE r.id=%s", (lease.request_id,)).fetchone()
    if not row:
        return None
    _run(row)
    return str(row["payload_text"])


def publish(
    db: Database, lease: Lease, *, stage_id: UUID, input_snapshot_id: UUID, payload_text: str
) -> UUID:
    _require_idle_autocommit(db)
    return UUID(
        str(
            _invoke(
                db,
                "SELECT valuation_publish(%s,%s,%s,%s) AS result",
                (Jsonb(lease.as_json()), stage_id, input_snapshot_id, payload_text),
            )
        )
    )


def get_request(db: Database, *, workspace_id: UUID, request_id: UUID) -> RequestResponse | None:
    row = db.execute(
        """SELECT r.id,e.id execution_id,e.state,v.id run_id,st.state stage_state,
    CASE WHEN st.id IS NOT NULL THEN 'valuation' END stage_key,
    CASE WHEN e.state='running' AND e.lease_expires_at<=clock_timestamp() THEN 'lease_expired'
      WHEN e.state='failed' THEN 'worker_failure'
      WHEN e.state IN ('cancelled','waiting_for_input','retry_scheduled') THEN e.state
      WHEN st.state IN ('blocked','unsupported','failed') THEN 'stage_'||st.state
      ELSE NULL END public_error
    FROM analysis_requests r
    JOIN valuation_request_intents i ON i.request_id=r.id
    JOIN analysis_request_state c ON c.request_id=r.id
    JOIN analysis_executions e ON e.id=c.current_execution_id
    LEFT JOIN valuation_model_runs v ON v.request_id=r.id
    LEFT JOIN LATERAL (SELECT id,state FROM analysis_stage_attempts WHERE execution_id=e.id
      AND stage_key='valuation' ORDER BY attempt_no DESC LIMIT 1) st ON true
    WHERE r.workspace_id=%s AND r.id=%s""",
        (workspace_id, request_id),
    ).fetchone()
    return (
        RequestResponse(
            request_id=row["id"],
            execution_id=row["execution_id"],
            state=row["state"],
            stage_key=row["stage_key"],
            stage_state=row["stage_state"],
            error_code=row["public_error"],
            run_id=row["run_id"],
        )
        if row
        else None
    )


def get_latest(
    db: Database,
    *,
    workspace_id: UUID,
    issuer_id: UUID,
    security_id: UUID,
    quote_identifier_id: UUID,
    scope_id: UUID,
    compatibility_key: str,
) -> LatestResponse | None:
    row = db.execute(
        """SELECT l.snapshot_id,l.latest_request_id,e.state FROM latest_valuation l
    JOIN analysis_requests r ON r.id=l.latest_request_id JOIN securities s ON s.id=l.security_id
    JOIN analysis_request_state c ON c.request_id=r.id
    JOIN analysis_executions e ON e.id=c.current_execution_id
    WHERE l.workspace_id=%s AND s.issuer_id=%s AND l.security_id=%s AND r.quote_identifier_id=%s
    AND l.scope_id=%s AND l.compatibility_hash=%s
    AND (l.scope_id='00000000-0000-0000-0000-000000000000'::UUID
    OR EXISTS(SELECT 1 FROM watchlist_memberships m
    WHERE m.id=l.scope_id AND m.removed_at IS NULL))""",
        (workspace_id, issuer_id, security_id, quote_identifier_id, scope_id, compatibility_key),
    ).fetchone()
    if not row:
        return None
    return LatestResponse(
        run=get_run(db, workspace_id=workspace_id, run_id=row["snapshot_id"])
        if row["snapshot_id"]
        else None,
        latest_request_id=row["latest_request_id"],
        latest_request_state=row["state"],
    )
