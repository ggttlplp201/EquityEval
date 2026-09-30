"""Export fictional S8a examples through the unchanged S7a core/public contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from equity_core.valuation_payload import calculate_payload
from equity_schema.valuation import ValuationManifest

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "scripts/fixtures/valuation-presentation.json"
OUTPUT = ROOT / "apps/web/src/features/valuation/fixture.json"


def build() -> dict[str, Any]:
    examples = []
    for row in json.loads(INPUT.read_text()):
        manifest = ValuationManifest.model_validate(row["manifest"])
        payload = calculate_payload(manifest)
        examples.append(
            {"id": row["id"], "label": row["label"], "payload": payload.model_dump(mode="json")}
        )
    examples.append({"id": "missing", "label": "Missing saved result", "payload": None})
    return {"fictional": True, "examples": examples}


def encoded(bundle: dict[str, Any]) -> bytes:
    return (json.dumps(bundle, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = encoded(build())
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != result:
            raise SystemExit(
                "Valuation presentation fixture differs; run scripts/export_valuation.py"
            )
    else:
        OUTPUT.write_bytes(result)


if __name__ == "__main__":
    main()
