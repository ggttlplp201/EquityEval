"""Versioned, bounded SEC identity acquisition intent; no financial request options."""

import re
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class BootstrapPlan:
    issuer_id: UUID
    cik: str
    source_id: UUID
    policy_revision_id: UUID
    inventory_start: date
    inventory_end: date
    resources: tuple[str, ...]
    version: str = "sec-identity-bootstrap-v1"

    def __post_init__(self) -> None:
        if self.version != "sec-identity-bootstrap-v1":
            raise ValueError("Unsupported bootstrap plan version")
        if not re.fullmatch(r"[0-9]{10}", self.cik) or int(self.cik) == 0:
            raise ValueError("Bootstrap needs a canonical positive CIK")
        if not 0 <= (self.inventory_end - self.inventory_start).days <= 730:
            raise ValueError("Bootstrap inventory window is limited to 730 days")
        required = {f"company_facts/{self.cik}", f"submissions/{self.cik}"}
        keys = set(self.resources)
        if len(keys) != len(self.resources) or not required.issubset(keys):
            raise ValueError("Bootstrap requires unique Company Facts and Submissions resources")
        filings = history = 0
        for key in keys - required:
            if (
                re.fullmatch(
                    rf"filing_document/{self.cik}/[0-9]{{10}}-[0-9]{{2}}-[0-9]{{6}}/"
                    r"[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:htm|html|xml|txt|xsd)",
                    key,
                )
                and ".." not in key
            ):
                filings += 1
            elif re.fullmatch(
                rf"submissions_history/{self.cik}/CIK{self.cik}-submissions-[0-9]{{3}}\.json", key
            ):
                history += 1
            else:
                raise ValueError("Invalid bootstrap resource")
        if filings > 5 or history > 10:
            raise ValueError("Bootstrap allows at most five filings and ten explicit history files")
        object.__setattr__(self, "resources", tuple(sorted(keys)))

    def as_json(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "issuer_id": str(self.issuer_id),
            "cik": self.cik,
            "source_id": str(self.source_id),
            "policy_revision_id": str(self.policy_revision_id),
            "inventory_start": self.inventory_start.isoformat(),
            "inventory_end": self.inventory_end.isoformat(),
            "resources": list(self.resources),
        }
