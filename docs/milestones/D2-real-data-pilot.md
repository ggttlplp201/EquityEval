# D2 — Seven-company real-source pilot

Status: bounded archived-observation slice complete and verified, 2026-09-20.
Live publication and core eligibility remain blocked by the prerequisites below.
Recovery checkpoint: `milestone/d2-observed-pilot`.
Branch: `codex/seven-company-pilot`.
Recovery base: `3342595`, annotated tag `milestone/d1b-redesign`.
Dependencies: S1 archived evidence, accepted S3 source readers and reviewed mappings,
S5 source eligibility, D026 seven-company scope, D029 reviewed visual system.

## Scope and order

The owner authorized the reviewed redesign checkpoint followed by the small
real-data pilot in order **CRCL, MSTR, COIN, HOOD, USAR, MP, GOOGL**. Preserve the
existing MSFT/RBLX regression evidence. Keep all seven in the pilot even when only
an identity/business/coverage report is possible. These seven are neither an
industry universe nor a sector/market benchmark.

This bounded implementation puts archived CRCL FY2025 observations into the
redesigned Company workspace, with all seven names retained in the real-source
roster. It does not call the observations a published PIT result. Financial
calculation eligibility and business applicability remain separate.

## Artifacts and reuse

- `scripts/export_real_pilot.py`: verified S1 gzip archives through
  `LocalArchive.read_blob`, exact existing `reviewed_cohort_rules`,
  `normalize_verified_bytes`, and `extract_inline_filing/select_filing_fact`.
  No transport, alternate parser, independent financial arithmetic, fake
  StatementSelection, or test seed is imported.
- `apps/web/src/features/pilot/evidence.json`: deterministic internal display
  artifact, hash identified, separate from the fictional Company/Sector fixtures.
  It is not the S6 public contract, a live cache, or normalized database storage.
- `/development/pilot?company=CRCL`: real-source route in the supplied dark visual
  system, source drawer, explicit gaps, and retained 3/5/10-year history controls.
- [Seven-company research](../research/seven-company-pilot-2026-09-20.md) and
  [dated identity catalog](../research/seven-company-pilot-identities.json).
- `tests/test_real_pilot_presentation.py`: independent source expectations,
  corrupted-archive/scope failures, seven-company order and artifact reproduction.

## Concrete source boundary

The observed accession is `0001876042-26-000062`, 2025-01-01 through 2025-12-31,
filed 2026-03-09. The original document was captured
2026-09-11T14:27:04.146547+00:00; Company Facts has its own original capture time.
The later Q2 2026 filing in the research roster is explicitly a different record.

Two exact original-filing selections agree with Company Facts:

| Concept | Original literal | Scale/sign | Observed USD amount |
| --- | --- | --- | --- |
| Total revenue and reserve income | 2,746,642 | scale 3 | 2,746,642,000 |
| Operating income (loss) | 96,435 | scale 3; negative | -96,435,000 |

Both use `{http://fasb.org/us-gaap/2025}`, context `c-1`, unit `usd`,
empty dimensions and reported decimals `-3`. Equal revenue repetitions remain
in the source chain. Whole-document extraction is incomplete (249 local issues);
the two supported facts do not imply complete financial-statement extraction.
No rounding precision is inferred from Company Facts digits.

Existing normalization raises `inventory_history_incomplete` and
`event_history_incomplete`. These flags are preserved. The UI shows observed
amounts, while derived metrics remain null. No core invocation is manufactured
without a real published PIT selection. No prior-period mapping is extrapolated
from the reviewed FY2025 accession.

## Decisions and reviews

D030 bounds this internal source-observation projection. Existing schema, concept
vocabulary, missing-value representation and public API remain unchanged.
Independent source/numeric review confirmed sign, scale, context and archive
agreement, and identified the application runtime and publication prerequisites.
Implementation source/number review found no blocking defects. It required an
explicit caveat that legacy S1 completion time is unknown; the artifact now
retains that flag and a source-detail note. Internal normalization references
must never be published as authentic capture records.

Independent standards/spec review found no application blocker. Its missing
research-note link was resolved by the completed seven-company research packet.
Dated-security and reference-only wording was corrected before the final build.
Only the selected issuer's financial details go to the pilot client. Shared
navigation avoids preloading the large fictional demonstration payload.

## Validation evidence

- Red phase: new presentation tests failed collection before exporter existed.
- Seven new source-presentation tests pass, including exact reproduction of the
  shipped artifact, source corruption, unsupported cross-checks, negative sign,
  unknown completion metadata and seven-company identity guards.
- `make lint typecheck`: pass; 53 Python source files pass strict typing.
- `make test`: **970 passed** in 169.33 seconds.
- `make test-core`: **225 passed**; `make test-golden`: **110 passed**.
  Existing MSFT/RBLX and all other baseline regressions remain intact.
- Optimized Next.js build: pass, including the new dynamic pilot route.
- **54 browser checks pass** in isolated headless Chrome via bundled Playwright:
  all seven selections; 3/5/10-year coverage; two exact source drawers; repeated
  Escape and restored focus; 320/390/768/1440 widths; invalid/duplicate links;
  actual selector navigation; separate fictional Company/drawer; Help and the
  opening-screen pilot link. Desktop/mobile screenshots visually inspected.
- No page/runtime JavaScript errors. The only console resource warning was
  independently identified as the pre-existing missing `/favicon.ico`.
- Earlier agent-browser runs verified desktop interactions but repeatedly lost
  their isolated tab at the second Escape interaction. Explicit scrolling and
  bounded polling clarified the tool issue; the independent runner then passed
  the complete flow, including repeated Escape, without application changes.
- Local logs/artifacts: `var/d2-static-checks.log`, `var/d2-tests.log`,
  `var/d2-build.log`, `var/d2-browser-checks.json`,
  `var/d2-browser-network.json`, `var/d2-real-pilot*.png`.
  These runtime artifacts are ignored; the reproducible source/tests and this
  result record are committed.

Preview: `http://127.0.0.1:3101/development/pilot`.
Reproduce the artifact with
`.venv/bin/python scripts/project_python.py -m scripts.export_real_pilot --check`.

## Concrete blockers and next action

A read-only connection probe on 2026-09-20 found the configured application
PostgreSQL endpoint on loopback port 5433 refusing connections. Credentials were
not printed. The Docker CLI was also unavailable on the current PATH, so the
configured Compose runtime could not be started through the documented command.
The repository's working Timescale runtime on port 55433 is explicitly
test-only; it is not substituted as application evidence storage.

Legacy S1 captures are research archives. Existing S3 publication requires reviewed
application source-policy/capture links and registered mappings. Those were not
invented or self-approved. Filing inventory/non-reliance evidence is incomplete.
SEC contact configuration alone does not supply these prerequisites.

Continue in this order:

1. Restore/provision the separate application runtime, inspect existing approved
   policy/identity rows, and register the exact accepted archive/mapping evidence
   through the reviewed S3 path; retain original capture times.
2. Complete actual filing and non-reliance coverage, review period/scope/precision
   and business applicability for the next issuer/accession.
3. Publish and read actual PIT selections using `read_statements`; pass eligible
   `FinancialInput` operands to the existing pure core. Do not clear flags merely
   to produce a ratio. Remaining six issuers keep their explicit gaps meanwhile.
4. Advance remaining S5 definitions/interpretation and then S6 public
   result/publication/cache contracts in their dedicated sequential review.
5. Only then implement the first eligible, tested D027 deterministic attribution
   pair. No eligible annual comparison pair or activated attribution convention
   is supplied by this pilot. Business-cause claims remain separate.

Live prices, driver feeds, alert delivery, deployment and subscriptions are not
activated. Price/share/calendar/action prerequisites stay in S4b and the provider
rights register. This checkpoint does not complete S5, S6, W1, N1 or production F1.
