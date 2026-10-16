"""Real-v2 projection fixtures never write an application publication."""

import json
from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from scripts.normalize_crcl import ROOT
from scripts.publish_crcl_fundamentals import (
    MANIFEST_HASH,
    PAYLOAD_HASH,
    PREPARATION,
    checked_candidate,
)
from scripts.publish_crcl_observation import PUBLICATION as OBSERVATION


def fixture():
    from equity_schema.real_fundamentals_store import compatibility_key

    manifest, payload = checked_candidate()
    preparation = json.loads((ROOT / PREPARATION).read_text())
    snapshot = {
        "snapshot_id": str(uuid4()),
        "request_id": str(uuid4()),
        "execution_id": str(uuid4()),
        "input_snapshot_id": str(uuid4()),
        "generated_at": datetime.now(UTC).isoformat(),
        "compatibility_key": compatibility_key(manifest),
        "payload_hash": PAYLOAD_HASH,
        "outcome": "completed_with_gaps",
        "result": payload.model_dump(mode="json"),
    }
    publication = {
        "snapshot": snapshot,
        "manifestHash": MANIFEST_HASH,
        "priorRowsPreserved": True,
        "exactReplay": True,
        "sourceObservation": preparation["sourceObservation"],
        "evaluatedAt": preparation["evaluatedAt"],
    }
    return preparation, publication, json.loads((ROOT / OBSERVATION).read_text())


def test_published_projection_uses_signed_result_and_complete_operand_provenance():
    from scripts.export_crcl_fundamentals import project

    data = project(*fixture())
    assert data["marginDisplay"] == "-3.51%"
    assert len(data["operands"]) == 2 and len(data["unresolved"]) == 9
    for key in ("operating_margin", "operating_income", "revenue", "policy"):
        assert data["details"][key]["sources"]
        assert all(
            s["url"].startswith("https://") and s["capturedAt"]
            for s in data["details"][key]["sources"]
        )
    assert (
        "PPE purchases"
        in next(m for m in data["unresolved"] if m["id"] == "free_cash_flow_ppe")["requirement"]
    )


@pytest.mark.parametrize("change", ["value", "missing_proof", "wrong_mode"])
def test_unverified_publication_cannot_render_numeric_result(change):
    from scripts.export_crcl_fundamentals import project

    preparation, publication, observation = fixture()
    publication = deepcopy(publication)
    if change == "value":
        publication["snapshot"]["result"]["metrics"][0]["value"] = "100"
    elif change == "missing_proof":
        publication["exactReplay"] = False
    else:
        publication["snapshot"]["result"]["evidence_mode"] = "synthetic"
    with pytest.raises(ValueError):
        project(preparation, publication, observation)
