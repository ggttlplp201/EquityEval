# API contract status

D037 approves narrow **S6a fundamentals publication and read-only retrieval**.
The implementation and generated contract cover governed synthetic S5 outputs.
D038 now approves synthetic **S6b/S7a assumptions and reverse valuation** as a
separate trusted-local app. Its [implementation](design/s7/implementation.md)
reuses saved S6a evidence and W1; the S6a generated routes remain unchanged.
No production source or application financial result was activated.

| Endpoint | Contract |
| --- | --- |
| `GET /analysis-snapshots/{snapshot_id}` | Exact immutable snapshot; no selector query parameters. Unknown/out-of-workspace ID returns `snapshot_not_found` 404. |
| `GET /companies/{issuer_id}/fundamentals` | Requires security ID, full-selector compatibility hash and explicit membership/independent scope ID. No nearest fallback; no exact saved result returns `no_compatible_snapshot` 404. |

Both endpoints preserve Decimal strings, nulls, all seven S5 statuses, dated
provenance, formula/coefficient lineage, full coverage and selected 3/5/10-year
history. Latest response separates the saved result from the latest declared W1
request and its state. Reads do not calculate, acquire data or age stored labels.
Invalid selectors produce the generated validation-error shape (422).

The app factory requires a trusted workspace and connection factory; it enables
no default credentials or network listener. Query parameters cannot change the
workspace. The API uses read-only transactions. Multi-user authentication and UI
integration remain later boundaries; S6a itself has no mutation HTTP route.

Source: `apps/api/fundamentals.py` and `packages/schema/fundamentals.py`.
Generated artifacts: `packages/schema/openapi/fundamentals.json` and
`packages/schema/types/fundamentals.ts`. Run
`scripts/generate_fundamentals_api.py --check` through `scripts/project_python.py`;
`make lint` and CI enforce no-diff regeneration.

The [implementation record](design/s6/implementation.md),
[milestone](milestones/S6a-fundamentals-publication.md) and
[manual](user-manual/saved-fundamentals.md) describe private input reviews, typed
source links, immutable request/result identities, exact cache reuse, fenced
publication and remaining real-data/valuation prerequisites.

## S6b/S7a valuation app

| Endpoint | Contract |
| --- | --- |
| `POST /assumption-sets` | 201 immutable current-authored content, optional parent and idempotency key; same-key changed content is 409. |
| `GET /assumption-sets/{assumption_id}` | Exact same-workspace assumptions including private author/rationale. |
| `POST /valuation-requests` | 202 for reviewed synthetic inputs, explicit parent, idempotency key and attempt budget; enqueue only. |
| `GET /valuation-requests/{request_id}` | Current execution, valuation stage, fixed safe error and saved run ID. |
| `GET /model-runs/{run_id}` | Exact immutable envelope and sanitized valuation payload, without recalculation. |
| `GET /companies/{issuer_id}/valuation` | Exact security/quote/scope/compatibility key; saved run and latest requested state are separate. |

All exact-ID routes reject extra selectors with 422; inaccessible IDs return 404.
The app factory requires the trusted workspace and connection factory explicitly;
there is no default listener, auth identity, provider or worker. Mutation handlers
only create assumptions or enqueue owner-reviewed work. Reads use read-only
transactions. Public runs omit private authorship/rationale and all raw worker
error text. Decimal strings, nulls, ordered scenarios/cells, five solve states,
three separate uncertainty fields and signed evaluation diagnostics are retained.

Sources: `apps/api/valuation.py`, `packages/schema/valuation.py` and
`packages/schema/valuation_store.py`. Generated files are
`packages/schema/openapi/valuation.json` and `packages/schema/types/valuation.ts`.
`make lint` runs `scripts/generate_valuation_api.py --check` through the project
Python wrapper. The [saved-valuation manual](user-manual/saved-valuations.md)
explains creating a reviewed fixture run, reading it and changing assumptions.
