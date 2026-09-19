# S4 — Prices and macro sources

Status: S4a complete for the accepted scope; S4b and live-source readiness remain open
Implementation dates: 2026-09-16 and 2026-09-19
Task: EquityEval — milestone build log
Task ID: 01a08f8c-85c8-7bb0-9e60-6eb24809d8de
Branch: `codex/s4-market-data`
Dependency: S3 `b71e308`, tag `milestone/s3`
Review checkpoint: `014351d`, tag `milestone/s4-contract-review`
Implementation checkpoint: tag `milestone/s4a` (exact commit available via `git show milestone/s4a`)

## Authorization and trace

The original ZIP documents remain unchanged. The September 12 review packet
specified D019 / S4-01–04 and the macro portion of D009. The user authorized
implementation with “you can implement it” on September 16 and asked to continue
on September 19. This accepted the eight market tables, additive immutable W1 plan,
typed provider boundary, source adapters, historical selection and real Timescale
verification. It did not supply missing provider retention rights or decide S4b.

The earlier contract/research state is preserved at `014351d`. Implementation is
recorded here and in the [S4 guide](../design/s4/implementation.md), with the
[accepted contract](../design/s4/source-contract.md), [storage design](../design/s4/storage-review.md)
and [correctness review](../design/s4/correctness-review.md).

## Delivered behavior

- Eight typed market-data tables, immutable reviewed policies and exact source
  identity guards; atomic fenced publication with verified archived manifests.
- PostgreSQL 16/Timescale 2.28.1 date hypertables, without retention/deletion jobs.
  Native PostgreSQL remains an explicit narrower test profile.
- Treasury nominal two-/ten-year yields, Tiingo daily raw/adjusted price fields,
  and native FRED observations with complete bounded pagination. Vendor fixtures
  are fictional; the separately labelled permitted Treasury capture is a golden.
- Credential-isolated, bounded transport, durable attempts and conservative
  Tiingo account quotas. Provider activation, raw retention and normalized scope
  are checked independently; operational disable preserves authorized history.
- Exact-date and explicitly age-bounded historical selectors. Source-as-of dates,
  local capture cutoffs and release precision remain independent. Missing data
  stays missing; newer failed/malformed responses cannot revive older current values.
- Watchlist request plans and independent SEC/price/macro stages, shared exact
  monthly Treasury captures, fresh reruns and deterministic archive replay.
  Source work can complete with gaps while later valuation remains unsupported.
- Draft [prices and macro manual](../user-manual/prices-and-macro.md), plus updated
  setup, feature status and operator instructions.

## Validation

Validation on 2026-09-19:

| Gate | Result |
| --- | --- |
| `make check`, default real Timescale profile | **717 passed**, no skips; Ruff, import policy, generated concepts, ESLint, strict mypy and TypeScript pass |
| `EQUITY_TEST_DB_PROFILE=native-pg16 make test` | **716 passed, 1 explicit Timescale-only skip**; target 0004 |
| Separate `make test-golden` | **110 passed**, including the permitted Treasury capture |
| `make test-core` | Intentionally empty until S5/S7; no valuation tests claimed |
| Alembic history/full-head offline SQL, documentation links and whitespace | Pass |

Focused verification covers real Timescale publication, populated
hypertable conversion, FKs/uniqueness, policy bypasses, concurrent quota
reservations, retries, timezone-stable replay, missing/invalid latest responses,
quote identity, source-vintage boundaries and the combined watchlist source flow.

Independent review found and resolved OHLC flag scope, timestamp identity,
failed-fetch lineage, redirect finalization, secret diagnostics, source URL
attribution and historical-selection problems. See the [review record](../design/s4/correctness-review.md)
and [provider-store details](../design/s4/provider-store-review.md).
The mandatory pre-commit hook runs full checks and is not bypassed.

Tests use repository-owned disposable databases and fictional HTTP. No application
`.env`, application database, live API key, source subscription or user data was
changed. The local [Timescale runtime](../design/s4/runtime.md) was built privately
because Docker/Podman/Colima were unavailable; no global installation or login
service was created. Hosted CI and the pinned Compose image were not executed
locally. The runtime profile is explicit, with no silent fallback.

## Remaining scope and next handoff

S4a is not the entire original S4. S4b still requires the corporate-action/ADS
lifecycle contract. Tiingo/FRED live retained-content permissions remain
unresolved; no provider was activated. Direct Treasury's reviewed CC0 research
scope does not itself create an application policy. Bulk H.15 stays quarantined
because unused third-party series have unresolved raw retention rights.

Complete calendars and macro coverage remain explicit gaps. CPI/PPI/Fed release
monitoring, continuous discovery of relevant company/competitor/product/regulatory
news, conditional impact assessments and in-app/desktop/email alerts remain N1.
The CRCL examples remain examples rather than a fixed topic list.

S5 financial ratios, S6 public API, S7 valuation and S8 watchlist/product UI remain
required. W1's source stages are implemented, but full applicable financial
reanalysis and the user-facing add/rerun flow still depend on those milestones.
U1's final manual, searchable Help, screenshots and end-to-end user walkthrough
must be verified against the finished product before release.

## Subsequent planning checkpoint — 2026-09-19

After S4a was committed at `5eeec7e` and the working tree was clean, the user
requested incorporation of a fundamentals DOCX into the plan. [F1](../features/F1-fundamentals-guide.md)
and the [S5 milestone](S5-ratios.md) record conflicts, reuse and dependencies.
The user retained optional 5/10-year history alongside the proposed 3-year view.
No fundamentals implementation began. Existing S4b action/ADS review and the
calendar/coverage gaps are now explicit prerequisites for affected fundamentals
metrics; source-only S5 work can proceed under its own reviewed contract.
