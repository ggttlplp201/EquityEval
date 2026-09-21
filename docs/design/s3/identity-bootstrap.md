# D031 bootstrap implementation

User authorization: continue from c314df9 and implement the reviewed D031
proposal, then attempt genuine CRCL capture using existing settings. Shared
contracts are changed sequentially on `codex/source-bootstrap`.

## Storage and execution

Migration `0006_source_bootstrap` adds the distinct `source_bootstrap` trigger.
Only that trigger permits (and requires) a NULL quote. Workspace and security stay
mandatory; membership, parent and every market-plan column must be absent.
The existing ordinary enqueue function and watchlist membership shape are unchanged.

`enqueue_source_bootstrap` uses the new narrow SECURITY DEFINER enqueue function.
It serializes on the workspace, hashes exact request options and returns the
existing RequestHandle. Reusing a key with different intent fails. No runtime
INSERT grant or fabricated identifier is added.

`claim_next` still calls the original two-argument SQL interface, now delegating
to the same frozen claim loop filtered to ordinary requests. The new
`claim_source_bootstrap` explicitly selects bootstrap requests and optionally one
request ID. This lets the CRCL command avoid taking unrelated work. The shared
claim implementation is not runtime-callable. All modes reuse existing lease,
fencing, renewal, expiry recovery, retry, cancellation and event functions.

Database stage guards permit only the existing SEC fetch/parse/inventory stages
and the bootstrap manifest stage. Normalization, market and valuation stages
fail even if requested directly. A transport-attempt guard restricts bootstrap
requests to canonical SEC resources for the registered issuer. Existing policy,
attempt commit-order and timestamp checks remain authoritative.

## Pipeline and manifest

The ordinary SEC function and explicit bootstrap entry point share the existing
fetch/inventory implementation. Ordinary, market and combined workers reject
bootstrap intent. The bootstrap branch never calls a financial input builder,
normalizer or publisher and never creates membership or a quote identifier.

The archived `sec-bootstrap-run-v1` manifest retains the request with actual NULL
quote, execution, source plan, exact FetchResults/captures, inventory and source
gaps. It explicitly sets `financial_result=false` and `event_review=not_performed`.
Its hash/path is recorded in the fenced manifest stage's audit reason, following
the existing S3 manifest convention. Failed responses remain source evidence;
they cannot supply facts. Retry exhaustion retains its source manifest.

A workflow `completed` outcome means source acquisition completed, not a completed
stock analysis. S6 must exclude source-bootstrap executions from financial latest
pointers. There is no public HTTP API or new financial missingness/status convention.

## CRCL operator command

Use the canonical repository and the separate application runtime:

```sh
make app-db-start app-db-migrate app-redis-start
.venv/bin/python scripts/project_python.py -m scripts.bootstrap_crcl register
.venv/bin/python scripts/project_python.py -m scripts.bootstrap_crcl capture --key crcl-first-source-20260921
```

Registration checks the existing configured SEC contact and owned runtimes. Its
owner-only transaction reuses or creates the reviewed source, immutable policy,
issuer/security and workspace; differing existing metadata or policy hash fails.
It never creates a capture, quote or invented listing date. An empty watchlist
created with the existing workspace function has no stock membership.

Capture uses the restricted application login, `SecTransport`,
`DatabaseAttemptStore`, `LocalArchive` under `var/raw`, and the shared SEC Redis
key/rate. It requests Company Facts, submissions/advertised history and the
reviewed FY2025 and Q2 2026 filing documents, with actual capture times. There is
no alternate downloader, fabricated legacy completion or rate-limit bypass.

Reuse the same explicit key for a transport retry. A terminal request or an
unavailable/leased retry is reported without another dispatch. Use a new explicit
key only for new user/operator intent. No scheduler or background polling is added.
The command prints JSON audit references; redirect to ignored `var/` if desired.

Registration uses [the scoped SEC policy](../../research/sec-application-policy-2026-09-21.md)
and [the dated identity packet](../../research/seven-company-pilot-identities.json).
It does not treat a filing date as a listing start or activate other providers.
If the network rejects a request, retain the exact failed attempt and obey its
cooldown. Do not change contact, clear coordinator state or substitute web-tool data.

## Review and next evidence boundary

Tests cover empty and populated upgrades, downgrade refusal once bootstrap history
exists, quote invariants, restricted function grants, concurrent idempotency,
specific claiming, expired/cancelled leases, genuine DB/Redis/archive transport
with deterministic HTTP, failed/exhausted capture evidence and idempotent setup.
Full suites and independent review are recorded in the D3b milestone.

After a successful capture, review identity validity, filing inventory,
non-reliance, periods, scope and original-filing precision before registering a
quote and publishing normalized evidence. Bootstrap completion does not clear any
of those prerequisites. Then continue real PIT → eligible S5 → reviewed minimal
S6. DCF, prices, monitoring, deployment and alerts stay outside this milestone.
