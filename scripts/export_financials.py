"""Checked local S8c statement presentation; fictional source copies, never calculations."""

import argparse
import calendar
import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, Self
from uuid import NAMESPACE_URL, uuid5

from equity_ingest.sec_normalize import period_spec, unit_spec
from equity_schema.concepts import Concept
from equity_schema.fundamentals_canonical import canonical_json, content_hash
from pydantic import BaseModel, ConfigDict, model_validator

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "scripts/fixtures/financials-presentation.json"
OUTPUT = ROOT / "apps/web/src/features/financials/fixture.json"
REVISION = "s8c-source-copy-v1"
# Reviewed selected-line roster; absence must be explicit null, never inferred.
STATEMENTS = {
    "income": (
        (Concept.REVENUE, "Revenue"),
        (Concept.GROSS_PROFIT, "Gross profit"),
        (Concept.OPERATING_INCOME, "Operating income"),
        (Concept.NET_INCOME_CONSOLIDATED, "Net income · consolidated"),
    ),
    "balance_sheet": (
        (Concept.CASH_AND_CASH_EQUIVALENTS, "Cash and cash equivalents"),
        (Concept.TOTAL_ASSETS, "Total assets"),
        (Concept.TOTAL_LIABILITIES, "Total liabilities"),
        (Concept.EQUITY_INCLUDING_NONCONTROLLING_INTERESTS, "Equity · including NCI"),
    ),
    "cash_flow": (
        (Concept.CASH_FROM_OPERATING_ACTIVITIES, "Cash from operations"),
        (Concept.CAPITAL_EXPENDITURES_PPE, "Capital expenditures · PPE"),
        (Concept.DIVIDENDS_PAID, "Dividends paid"),
    ),
}


class Edition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    label: str
    basis: Literal["annual", "quarter"]
    period_start: date
    period_end: date
    filed_on: date
    known_on: date
    retrieved_at: datetime
    currency: Literal["USD"]
    scale: Literal["1"]
    scope: Literal["consolidated"]
    supersedes: str | None
    values: dict[Concept, str | None]

    @model_validator(mode="after")
    def validate_source(self) -> Self:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.id) or not self.label.strip():
            raise ValueError("Explicit fixture identity and label required")
        start, end = self.period_start, self.period_end
        if self.basis == "annual":
            valid = start == date(end.year, 1, 1) and end == date(end.year, 12, 31)
        else:
            valid = (
                end.month in {3, 6, 9, 12}
                and start == date(end.year, end.month - 2, 1)
                and end.day == calendar.monthrange(end.year, end.month)[1]
            )
        if not valid:
            raise ValueError("Only reviewed calendar-year and direct quarter durations supported")
        if not end < self.filed_on <= self.known_on <= self.retrieved_at.date():
            raise ValueError("Financial, filing, known and retrieval dates must be ordered")
        if self.retrieved_at.utcoffset() is None:
            raise ValueError("Retrieval timestamp must be timezone aware")
        expected = {concept for rows in STATEMENTS.values() for concept, _ in rows}
        if set(self.values) != expected:
            raise ValueError("Selected-line roster must be exact; missing inputs use explicit null")
        for value in self.values.values():
            if value is not None and not re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value):
                raise ValueError("A finite exact decimal source string is required")
        return self


class Recipe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    fictional: Literal[True]
    label: str
    editions: tuple[Edition, ...]

    @model_validator(mode="after")
    def validate_editions(self) -> Self:
        if not self.editions or len({e.id for e in self.editions}) != len(self.editions):
            raise ValueError("Exactly one saved edition per key required")
        seen: dict[str, Edition] = {}
        for edition in self.editions:
            if edition.supersedes is not None:
                old = seen.get(edition.supersedes)
                if old is None or (
                    old.period_start,
                    old.period_end,
                    old.basis,
                    old.currency,
                    old.scope,
                ) != (
                    edition.period_start,
                    edition.period_end,
                    edition.basis,
                    edition.currency,
                    edition.scope,
                ):
                    raise ValueError("Revision must reference an earlier compatible edition")
                if not (
                    old.filed_on < edition.filed_on
                    and old.known_on < edition.known_on
                    and old.retrieved_at < edition.retrieved_at
                ):
                    raise ValueError("A revision cannot precede its original evidence")
            seen[edition.id] = edition
        return self


def validate_recipe(data: Any) -> Recipe:
    return Recipe.model_validate(data)


def identity(kind: str, value: Any) -> str:
    return str(uuid5(NAMESPACE_URL, f"equityeval:s8c:{kind}:{content_hash(value)}"))


def build(data: Any = None) -> dict[str, Any]:
    recipe = validate_recipe(json.loads(RECIPE.read_text()) if data is None else data)
    snapshots: list[dict[str, Any]] = []
    prior_rows: dict[str, dict[str, dict[str, Any]]] = {}
    for edition_index, edition in enumerate(recipe.editions):
        source_hash = content_hash(edition)
        source_id = identity("source", edition)
        source_path = f"scripts/fixtures/financials-presentation.json#/editions/{edition_index}"
        old_rows = prior_rows.get(edition.supersedes or "", {})
        statements = []
        rows_by_concept = {}
        for family, roster in STATEMENTS.items():
            period = period_spec(
                None if family == "balance_sheet" else edition.period_start, edition.period_end
            )
            period_data = json.loads(canonical_json(period))
            rows = []
            for concept, label in roster:
                value = edition.values[concept]
                old = old_rows.get(concept.value)
                restatement = (
                    "unavailable"
                    if value is None
                    else "original"
                    if old is None
                    else "repeated"
                    if old["value"] is not None and Decimal(value) == Decimal(old["value"])
                    else "restated"
                )
                evidence = {
                    "source_id": source_id,
                    "source_hash": source_hash,
                    "fixture_source": source_path,
                    "source_locator": f"{source_path}/values/{concept.value}",
                    "source_tag": f"fictional:{concept.value}",
                    "accession": None,
                    "original_numeric_text": value,
                    "filed_on": edition.filed_on.isoformat(),
                    "known_on": edition.known_on.isoformat(),
                    "retrieved_at": edition.retrieved_at.isoformat(),
                    "period": period_data,
                    "unit": json.loads(canonical_json(unit_spec(edition.currency))),
                    "currency": edition.currency,
                    "scale": edition.scale,
                    "scope": edition.scope,
                    "statement": family,
                    "reporting_basis": "us_gaap",
                    "restatement_status": restatement,
                    "prior_evidence_id": None if old is None else old["evidence"]["evidence_id"],
                    "prior_value": None if old is None else old["value"],
                    "transform": {"operation": "identity_decimal", "revision": REVISION},
                }
                evidence["evidence_id"] = identity("evidence", evidence)
                row = {
                    "concept": concept.value,
                    "label": label,
                    "value": value,
                    "status": "missing" if value is None else "reported",
                    "quality_flags": ["source_not_supplied"] if value is None else [],
                    "evidence": evidence,
                }
                rows.append(row)
                rows_by_concept[concept.value] = row
            statements.append(
                {
                    "family": family,
                    "period": period_data,
                    "rows": rows,
                    "coverage": {
                        "available": sum(r["value"] is not None for r in rows),
                        "requested": len(rows),
                        "scope": "selected_lines",
                    },
                }
            )
        payload = {
            "edition": edition.id,
            "label": edition.label,
            "basis": edition.basis,
            "issuer_id": identity("issuer", "Fictional Statement Co."),
            "company": recipe.label,
            "source_id": source_id,
            "input_hash": source_hash,
            "currency": edition.currency,
            "scale": edition.scale,
            "scope": edition.scope,
            "filed_on": edition.filed_on.isoformat(),
            "known_on": edition.known_on.isoformat(),
            "retrieved_at": edition.retrieved_at.isoformat(),
            "history_mode": "latest_reported" if old_rows else "original_as_filed",
            "supersedes": edition.supersedes,
            "statements": statements,
            "revision": REVISION,
        }
        snapshots.append(
            {
                **payload,
                "payload_hash": content_hash(payload),
                "snapshot_id": identity("snapshot", payload),
            }
        )
        prior_rows[edition.id] = rows_by_concept
    return {
        "fictional": True,
        "label": recipe.label,
        "choices": [{"edition": e.id, "label": e.label, "basis": e.basis} for e in recipe.editions],
        "snapshots": snapshots,
    }


def encoded(bundle: dict[str, Any]) -> bytes:
    return (json.dumps(bundle, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = encoded(build())
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != result:
            raise SystemExit("Financials fixture differs; run python -m scripts.export_financials")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(result)


if __name__ == "__main__":
    main()
