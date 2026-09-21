"""Compare pinned SEC inventories without inferring accounting revisions or dispatching work."""

import json
from collections import Counter
from datetime import datetime
from typing import Any

from equity_ingest.sec_inventory import FilingInventory, InventoryFiling
from equity_schema.filing_monitor import FilingMonitorPlan, timestamp


def filing_metadata(filing: InventoryFiling) -> dict[str, Any]:
    raw = json.loads(filing.raw_metadata)
    return {
        "accession": filing.accession,
        "form": filing.form,
        "filed_date": filing.filed_date.isoformat(),
        "report_date": filing.report_period_end.isoformat() if filing.report_period_end else None,
        "primary_document": filing.primary_document,
        "acceptance_raw": raw.get("acceptanceDateTime"),
        "acceptance_at": timestamp(filing.acceptance_at) if filing.acceptance_at else None,
        "acceptance_time_basis": filing.acceptance_time_basis,
    }


def observation(filing: InventoryFiling) -> dict[str, Any]:
    return {
        **filing_metadata(filing),
        "capture_id": str(filing.source_capture_id),
        "source_locator": filing.source_locator,
    }


def compare_inventories(
    baseline: FilingInventory,
    current: FilingInventory,
    plan: FilingMonitorPlan,
) -> dict[str, Any]:
    flags: set[str] = set()
    excluded: dict[str, list[str]] = {"baseline": [], "current": []}

    def selected(
        inventory: FilingInventory, cutoff: datetime, label: str
    ) -> dict[str, InventoryFiling]:
        if (
            inventory.cik != plan.cik
            or inventory.boundary_start != plan.inventory_start
            or inventory.boundary_end != plan.inventory_end
        ):
            raise ValueError("Inventory differs from pinned issuer/window")
        if inventory.completeness != "complete":
            flags.add(label + "_inventory_incomplete")
        flags.update(label + ":" + flag for flag in inventory.flags)
        counts = Counter(f.accession for f in inventory.filings)
        if any(count > 1 for count in counts.values()):
            flags.add(label + "_duplicate_accession")
        result = {}
        for filing in inventory.filings:
            if filing.form not in plan.forms:
                continue
            if filing.acceptance_at is None or filing.acceptance_time_basis != "verified_timezone":
                flags.add(label + "_acceptance_unverified")
                continue
            if filing.acceptance_at > cutoff:
                excluded[label].append(filing.accession)
                continue
            if filing.report_period_end is None or filing.primary_document is None:
                flags.add(label + "_filing_metadata_incomplete")
            result[filing.accession] = filing
        return result

    old = selected(baseline, plan.baseline.cutoff, "baseline")
    new = selected(current, plan.cutoff, "current")
    disappeared = sorted(old.keys() - new.keys())
    changed = [
        {"accession": key, "before": observation(old[key]), "after": observation(new[key])}
        for key in sorted(old.keys() & new.keys())
        if filing_metadata(old[key]) != filing_metadata(new[key])
    ]
    if disappeared:
        flags.add("baseline_accession_missing")
    if changed:
        flags.add("existing_accession_metadata_changed")
    additions = [observation(new[key]) for key in sorted(new.keys() - old.keys())]
    originals = [row for row in additions if not row["form"].endswith("/A")]
    amendments = [row for row in additions if row["form"].endswith("/A")]
    outcome = (
        "incomplete"
        if flags
        else "mixed_changes"
        if originals and amendments
        else "new_filing"
        if originals
        else "amendment"
        if amendments
        else "no_change"
    )
    return {
        "outcome": outcome,
        "baseline_eligible": not flags,
        "flags": sorted(flags),
        "new_filings": originals,
        "amendments": amendments,
        "metadata_changes": changed,
        "missing_accessions": disappeared,
        "baseline_filings": [observation(old[key]) for key in sorted(old)],
        "current_filings": [observation(new[key]) for key in sorted(new)],
        "excluded_after_cutoff": {k: sorted(v) for k, v in excluded.items()},
        "amendment_meaning": "Separate filing edition; no restatement or non-reliance inference",
    }
