# API contract status

D037 approves narrow **S6a fundamentals publication and read-only retrieval**.
The implementation and generated contract cover governed synthetic S5 outputs.
S6b assumptions/DCF/model contracts remain unimplemented, with D004/D005 open.
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
integration remain later boundaries; no mutation HTTP route was added.

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
