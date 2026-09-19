# S4a correctness review

Reviewed implementation baseline: `014351d` (`milestone/s4-contract-review`).
Review date: 2026-09-19. Scope: the accepted D019 / S4-01–04 source, storage,
selection and W1 contracts. Review emphasized plausible incorrect values and
incorrect claims about historical knowledge, not just exceptions or syntax.

Independent implementation agents inspected each other's source boundaries and
normalization/selection interactions; the primary agent reconciled findings and
reviewed the shared publication, pipeline and historical-selection paths. All
identified actionable findings below were resolved before the checkpoint.

| Finding | Resolution and regression |
| --- | --- |
| Inconsistent OHLC bars flagged only close, leaving other affected price fields apparently usable. | Flag all four fields in the inconsistent raw or adjusted group. Preserve independent volume/dividend evidence. Normalizer and selector regressions cover both groups. |
| Equivalent timestamps in different time zones changed S4 hashes and replay identities. | S4-only canonical UTC serialization covers bundle hashes and manifests; fresh captures and database-reloaded captures replay identically. S3 hashes stay unchanged. |
| New failed fetches left older numeric batches looking current. | Publish an unavailable batch with complete retained error bodies and terminal attempt history. A later 503 or malformed 200 supersedes the older current selection; explicit older batch inspection remains possible. |
| Successful retry runs omitted earlier error evidence. | Pin original logical-fetch attempt lineage and all complete error responses in the manifest and typed batch inputs. Replay reconstructs only the original sequence, never later attempts. |
| Error captures were incorrectly passed as successful workflow reuse evidence. | Keep errors in the market batch, while the stage completion's successful-capture list contains only 2xx captures. |
| Authenticated redirects failed the real DB finalization constraint. | Record the explicit refusal failure code; do not follow or persist a credential-bearing Location. Real-store HTTP tests cover the boundary. |
| HTTP client diagnostics could expose a FRED query credential. | Suppress HTTP-library logs in the authenticated retrieval context, restore unrelated diagnostics afterward, and retain safe durable attempt metadata. Reflected header/body/compressed-body credentials fail before archive publication. |
| A replay capture beyond the local cutoff escaped before stage completion. | Record a source-specific blocked gap without live fallback or leaving that stage running. |
| Legacy requests had no explicit market-stage audit outcome. | Record unsupported market work when no immutable S4 plan exists; no defaults are retroactively applied. |
| Backward macro selection could let an unrelated older backfill displace a newer reference date. | Determine the latest eligible actual reference date, then rank relevant responses before usability; retain newer missing/empty coverage and the explicit age bound. |
| Historical values could remain usable with capture-only metadata history. | Preserve raw value and metadata for inspection, but make `definition_history_unavailable` block numeric usability for source-as-of selection. A source-supplied eligible definition is the positive control. |
| Generic SQL source entry points could bypass provider identity checks. | Bind registered origin, public URL and exact observation object, including SEC CIK/accession identity. Direct-call bypass regressions exercise both attempt preparation and capture registration. |

See the [provider-store review](provider-store-review.md) for durable account
reservations, request-wide attempt budgets, operational disable/replay,
concurrent reservation and timestamp checks. See the [test plan](test-plan.md)
and [milestone record](../../milestones/S4-prices-macro.md) for acceptance evidence.

Two full-suite fixture problems were also corrected without weakening product
rules. The legacy policy-migration test now creates genuine pre-policy evidence
before upgrading; it no longer tries to delete immutable S4 capabilities. Log
privacy tests explicitly enable the HTTP logger because Alembic's global logging
configuration otherwise disabled it and made isolated/full-suite behavior differ.

## Deliberate limits

Source normalization preserves native values and flags unknown calendar coverage;
it does not claim complete exchange/release history. FRED W1 attempt publication
uses the documented bounded plan of 20 pages × 100,000 rows. Pending or unresolved
attempts cannot be published as an immutable historical outcome. Exact reviewed
metadata and provider-symbol bindings remain provisioning prerequisites.

No live-provider permissions, production deployment, complete corporate-action/ADS
lifecycle, valuation engine, product UI or news delivery is claimed by this review.
