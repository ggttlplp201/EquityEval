"""Reproduce fictional S8b fundamentals through the unchanged S6a public contract."""

from __future__ import annotations

import argparse
import json
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Literal, Self

from equity_core.fundamentals import calculate_payload
from equity_schema.fundamentals import (
    DecimalString,
    FundamentalsPayload,
    HistorySampleRef,
    read_manifest,
)
from equity_schema.fundamentals_canonical import canonical_json, content_hash
from pydantic import BaseModel, ConfigDict, model_validator

from scripts.fundamentals_presentation_inputs import identity, manifest

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "scripts/fixtures/fundamentals-presentation.json"
OUTPUT = ROOT / "apps/web/src/features/fundamentals/fixture.json"


class Example(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    label: str
    basis: Literal["annual", "instant"]
    dates: tuple[date, ...]
    case: Literal["valid", "not_meaningful", "missing", "invalid", "stale", "inapplicable"]


class Recipe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    fictional: Literal[True]
    label: str
    sources: dict[str, DecimalString]
    history_operating_income: tuple[DecimalString, ...]
    examples: tuple[Example, ...]

    @model_validator(mode="after")
    def unique_selections(self) -> Self:
        ids = [example.id for example in self.examples]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate example ID")
        for example in self.examples:
            if len(set(example.dates)) != len(example.dates):
                raise ValueError("Duplicate example date")
            if not example.dates:
                raise ValueError("Example requires a saved date")
        return self


def chart_positions(payload: FundamentalsPayload) -> dict[str, list[str]]:
    """Chart coordinates only; the core supplies every percentile value."""
    charts = {}
    for history in payload.history:
        if history.p25 is None or history.p50 is None or history.p75 is None:
            continue
        values = [Decimal(history.p25), Decimal(history.p50), Decimal(history.p75)]
        with localcontext() as context:
            context.prec = 50
            span = values[2] - values[0]
            charts[history.metric_id] = [
                str(Decimal(50) if not span else 10 + (value - values[0]) / span * 80)
                for value in values
            ]
    return charts


def validate_selection_keys(snapshots: list[dict[str, Any]]) -> None:
    keys = [
        (row["example"], row["payload"]["selector"]["as_of"], row["years"]) for row in snapshots
    ]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate saved selection key")


def build() -> dict[str, Any]:
    recipe = Recipe.model_validate_json(INPUT.read_text())
    if len(recipe.history_operating_income) != 12:
        raise ValueError("Twelve explicit historical operating-income observations required")
    snapshots = []
    for example in recipe.examples:
        for as_of in example.dates:
            for years in (3, 5, 10):
                window: Literal[3, 5, 10] = 3 if years == 3 else 5 if years == 5 else 10
                draft = manifest(
                    recipe.sources,
                    basis=example.basis,
                    as_of=as_of,
                    years=window,
                    case=example.case,
                )
                history_payloads = {}
                references = []
                # Twelve source-backed quarterly evaluations, plus a future sample
                # that the unchanged core must exclude. No history values go to UI.
                quarters = [
                    date(year, month, day)
                    for year in (2023, 2024, 2025, 2026)
                    for month, day in ((3, 31), (6, 30), (9, 30), (12, 31))
                    if date(2023, 6, 30) < date(year, month, day) <= date(2026, 6, 30)
                ]
                for index, day in enumerate((*quarters, date(2026, 9, 30))):
                    amounts = dict(recipe.sources)
                    if index < 12:
                        amounts["operating_income"] = recipe.history_operating_income[index]
                    if day > as_of:
                        amounts["revenue"] = "987654321"
                    old = manifest(
                        amounts, basis=example.basis, as_of=day, years=window, case=example.case
                    )
                    payload = FundamentalsPayload.model_validate(
                        calculate_payload(old, history_payloads={}).model_dump()
                    )
                    sid = identity("history:" + content_hash(payload))
                    history_payloads[sid] = payload
                    references.append(
                        HistorySampleRef(
                            snapshot_id=sid, payload_hash=content_hash(payload), quarter_end=day
                        )
                    )
                frozen = read_manifest(
                    canonical_json(draft.model_copy(update={"history_samples": tuple(references)}))
                )
                payload = FundamentalsPayload.model_validate(
                    calculate_payload(frozen, history_payloads=history_payloads).model_dump()
                )
                snapshots.append(
                    {
                        "example": example.id,
                        "years": years,
                        "snapshot_id": str(identity("snapshot:" + content_hash(frozen))),
                        "input_snapshot_id": str(identity("inputs:" + content_hash(frozen))),
                        "payload_hash": content_hash(payload),
                        "payload": payload.model_dump(mode="json"),
                        "chart_positions": chart_positions(payload),
                    }
                )
    validate_selection_keys(snapshots)
    return {
        "fictional": True,
        "label": recipe.label,
        "examples": [e.model_dump(mode="json") for e in recipe.examples],
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
            raise SystemExit("Fundamentals fixture differs; run scripts/export_fundamentals.py")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(result)


if __name__ == "__main__":
    main()
