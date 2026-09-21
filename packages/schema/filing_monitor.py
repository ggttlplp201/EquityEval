"""D035 internal filing-discovery intent; never a financial-analysis request."""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal
from uuid import UUID

MONITOR_VERSION = "sec-filing-monitor-v1"
MONITOR_RESULT_VERSION = "sec-filing-monitor-result-v1"
FORMS = frozenset({"10-Q", "10-K", "10-Q/A", "10-K/A"})
COMPLETE_OUTCOMES = frozenset({"no_change", "new_filing", "amendment", "mixed_changes"})


def timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("Monitor cutoffs require an explicit timezone")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class MonitorBaseline:
    kind: Literal["initial_seed", "prior_monitor_result"]
    request_id: UUID
    execution_id: UUID
    manifest_sha256: str
    cutoff: datetime
    seed_approval_id: UUID | None = None
    plan_sha256: str | None = None
    capture_id: UUID | None = None
    manifest_id: UUID | None = None
    version: str = MONITOR_VERSION

    def __post_init__(self) -> None:
        timestamp(self.cutoff)
        if self.version != MONITOR_VERSION:
            raise ValueError("A baseline version change requires reviewed rebase")
        if not re.fullmatch(r"[a-f0-9]{64}", self.manifest_sha256):
            raise ValueError("Baseline must pin the result manifest hash")
        if self.kind == "initial_seed":
            if (
                self.seed_approval_id is None
                or self.capture_id is None
                or self.manifest_id is not None
                or self.plan_sha256 is None
                or not re.fullmatch(r"[a-f0-9]{64}", self.plan_sha256)
            ):
                raise ValueError("Initial baseline requires approved exact seed lineage")
        elif self.kind == "prior_monitor_result":
            if self.manifest_id is None or any(
                x is not None for x in (self.seed_approval_id, self.plan_sha256, self.capture_id)
            ):
                raise ValueError("Prior baseline requires an exact monitor result")
        else:
            raise ValueError("Unknown monitor baseline kind")
        for value in (
            self.request_id,
            self.execution_id,
            self.seed_approval_id,
            self.capture_id,
            self.manifest_id,
        ):
            if value is not None and not isinstance(value, UUID):
                raise ValueError("Baseline identities must be UUIDs")

    def as_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "request_id": str(self.request_id),
            "execution_id": str(self.execution_id),
            "manifest_sha256": self.manifest_sha256,
            "cutoff": timestamp(self.cutoff),
            "version": self.version,
            "seed_approval_id": str(self.seed_approval_id) if self.seed_approval_id else None,
            "plan_sha256": self.plan_sha256,
            "capture_id": str(self.capture_id) if self.capture_id else None,
            "manifest_id": str(self.manifest_id) if self.manifest_id else None,
        }

    @classmethod
    def from_json(cls, value: dict[str, Any]) -> "MonitorBaseline":
        fields = dict(value)
        for key in ("request_id", "execution_id", "seed_approval_id", "capture_id", "manifest_id"):
            fields[key] = UUID(fields[key]) if fields[key] is not None else None
        fields["cutoff"] = datetime.fromisoformat(fields["cutoff"])
        return cls(**fields)


@dataclass(frozen=True)
class FilingMonitorPlan:
    issuer_id: UUID
    cik: str
    source_id: UUID
    policy_revision_id: UUID
    inventory_start: date
    inventory_end: date
    cutoff: datetime
    forms: tuple[str, ...]
    resources: tuple[str, ...]
    baseline: MonitorBaseline
    version: str = MONITOR_VERSION

    def __post_init__(self) -> None:
        timestamp(self.cutoff)
        if self.version != MONITOR_VERSION or not isinstance(self.baseline, MonitorBaseline):
            raise ValueError("Unsupported monitor contract or baseline")
        if any(
            not isinstance(x, UUID)
            for x in (self.issuer_id, self.source_id, self.policy_revision_id)
        ):
            raise ValueError("Monitor identities must be UUIDs")
        if not re.fullmatch(r"[0-9]{10}", self.cik) or int(self.cik) == 0:
            raise ValueError("Monitor requires a canonical positive CIK")
        if type(self.inventory_start) is not date or type(self.inventory_end) is not date:
            raise ValueError("Filed window requires explicit dates")
        if not 0 <= (self.inventory_end - self.inventory_start).days <= 730:
            raise ValueError("Monitor filed window is limited to 730 days")
        if not self.inventory_start <= self.cutoff.astimezone(UTC).date() <= self.inventory_end:
            raise ValueError("Acceptance cutoff must lie within the pinned filed window")
        if self.baseline.cutoff > self.cutoff:
            raise ValueError("Baseline cutoff cannot exceed current cutoff")
        if (
            not self.forms
            or not set(self.forms) <= FORMS
            or len(set(self.forms)) != len(self.forms)
        ):
            raise ValueError("Monitor forms must be unique supported financial forms")
        root = f"submissions/{self.cik}"
        if (
            root not in self.resources
            or not 1 <= len(self.resources) <= 11
            or len(set(self.resources)) != len(self.resources)
        ):
            raise ValueError("Monitor requires root and at most ten unique history resources")
        for key in self.resources:
            if key != root and not re.fullmatch(
                rf"submissions_history/{self.cik}/CIK{self.cik}-submissions-[0-9]{{3}}\.json", key
            ):
                raise ValueError("Monitor permits exact same-CIK Submissions resources only")
        object.__setattr__(self, "forms", tuple(sorted(self.forms)))
        object.__setattr__(self, "resources", tuple(sorted(self.resources)))

    def as_json(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "issuer_id": str(self.issuer_id),
            "cik": self.cik,
            "source_id": str(self.source_id),
            "policy_revision_id": str(self.policy_revision_id),
            "inventory_start": self.inventory_start.isoformat(),
            "inventory_end": self.inventory_end.isoformat(),
            "cutoff": timestamp(self.cutoff),
            "forms": list(self.forms),
            "resources": list(self.resources),
            "baseline": self.baseline.as_json(),
        }

    @classmethod
    def from_json(cls, value: dict[str, Any]) -> "FilingMonitorPlan":
        fields = dict(value)
        for key in ("issuer_id", "source_id", "policy_revision_id"):
            fields[key] = UUID(fields[key])
        for key in ("inventory_start", "inventory_end"):
            fields[key] = date.fromisoformat(fields[key])
        fields["cutoff"] = datetime.fromisoformat(fields["cutoff"])
        fields["forms"], fields["resources"] = tuple(fields["forms"]), tuple(fields["resources"])
        fields["baseline"] = MonitorBaseline.from_json(fields["baseline"])
        return cls(**fields)
