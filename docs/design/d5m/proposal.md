# D5m — Complete the bounded D5l CRCL history review

Status: proposed 2026-10-22; independent review required before implementation,
cloud proof execution, retry acquisition or any live publication. Baseline
`f618ce9130c7925ef7bfba075aefc06c390c9168`, canonical iCloud checkout, existing
`codex/d5a-crcl-normalization` branch. D051. The user explicitly resumed to finish
this section. D5m is the separately reviewed amendment that completes D5l, not a
multi-company or price-data milestone. All D050 artifacts and timestamps remain
immutable. A genuine unresolved evidence/contract gate still returns null.

## Exact local acquisition amendment

Reuse the existing V2 BootstrapPlan and exact resource
`filing_document/0001876042/0001876042-26-000116/a2025annualreport0331.pdf`.
Only this resource gets a maximum of 33,554,432 wire bytes and 33,554,432 decoded
entity bytes (32 MiB), further reduced by any lower configured document limit.
Apply the same exact-resource cap to `pdf_review.py` independently: its current
8 MiB input gate must accept up to 32 MiB only when the input is bound to the
exact ARS resource and verified capture manifest. A caller boolean or filename
alone cannot grant the larger cap. Parse/render staging, archive replay and
remote input validation enforce the identical identity-bound limit. Test an ARS
above 8 MiB below 32 MiB, an ARS above 32 MiB, and a correspondence PDF above
8 MiB; wrong-resource/cross-issuer/renamed inputs never inherit the ARS allowance.
The seven correspondence PDFs keep 8 MiB; JSON/HTML limits and all other source
contracts remain unchanged. This is a bounded retry candidate, not a claim that
32 MiB is sufficient. No other bodies, URLs, accessions or CIKs are authorized.

One new V2 request retains the mandatory `company_facts/0001876042` and
`submissions/0001876042` plus the exact ARS. Only after ARS and all other original
bodies are verified retained, a separate pair-only V2 request obtains a new final
Facts/Submissions observation. Total five logical resources, at most fifteen
transport dispatches, one execution per request, ten-minute combined acquisition
wall budget. No automatic new run or cap increase after failure. Keep the original
failed attempt and withheld group 11 unchanged. Pin the request interval as
2025-01-01 through 2026-10-22; crossing that date does not silently rebase it.
Fresh inventory is reviewed for the entire D050 financial-history form scope;
new required bodies or advertised history files become exact blockers requiring
a separately reviewed finite extension, never unbounded follow-link acquisition.

Retain local source/policy/lease/Redis/contact/redirect/archive governance. No SEC
fetch occurs in a remote interpretation runtime. Persist before mutation an
immutable intent with resource list, limits, implementation hash and prior row
hashes. Recovery only reconstructs the exact intent from retained attempts and
verified archives; it never redispatches implicitly. Missing or contradictory audit
state is blocked. Source observation is the exact minimum supported timestamp of
the final pair, completed after all bodies; it is not September knowledge or
whole-day October coverage. A changed inventory cannot inherit D5i completeness.

## Byte evidence without changing the public/database contract

Use the existing optional `ingestion_finalize(... failure_detail ...)` text field
for a compact canonical JSON transfer-evidence record (at most 2,048 UTF-8 bytes),
including resource/attempt identity, cap revision, declared Content-Length or null,
wire bytes observed, decoded bytes emitted, archive-complete boolean and stop
reason. Counts are nonnegative observations, not inferred total server size.
Record whether EOF was reached and whether the last chunk crossed the limit;
wire count may exceed the cap by the actually observed bounded chunk, while
archived/decoded output must never exceed its enforced cap. Stream chunks are
bounded to 64 KiB. Reject overlong/malformed Content-Length and record its invalid
state without retaining arbitrary header content. Keep ordinary failure codes.

Before consuming body bytes, fsync an exclusive attempt-bound local evidence
header containing Content-Length, encoding, limit and response time. Finalize a
hash-bound audit after terminal completion with counters and the database outcome.
On process death, a surviving header is not a complete byte counter: recovery
reports counters unknown unless a terminal evidence record exists. Never invent
counts for D5l's original failed attempt. A missing/changed sidecar cannot become
complete audit evidence. Successful captures still require matching archive
SHA/byte count. Reuse/304 validates the applicable exact-resource limit and body.
No migration, new table/column, public API or missingness status is expected.
Any discovered need for one stops at a separately concrete reviewed boundary.

## Runtime decision and access feasibility

Vercel Sandbox was investigated via the installed skill and connector. Team
listing returned no teams; this agent's project listing returned three unrelated
projects and no EquityEval project. No local `vercel`/`sandbox` command is available.
There is no verified appropriate project scope. Do not create an arbitrary project
or use another application's project. Firecracker remains a technically suitable
alternative, but is not selected or claimed available for this execution.

Choose an **explicitly triggered GitHub Actions Ubuntu Linux job in the existing
EquityEval repository**, with a Docker process sandbox inside the ephemeral runner.
This is not a Firecracker-equivalent claim: GitHub owns the runner VM isolation;
Docker provides the additional process/network/filesystem/cgroup boundary.
The existing repository already declares ubuntu-24.04 CI. Read-only GitHub REST confirms the repository is public, the existing credential
has push/admin permission, and Actions is enabled. Artifact/signature generation
and actual runtime remain unproved. No credential value was printed or persisted.
Because `workflow_dispatch` requires the workflow on default branch `main`, do not
modify main just to enable this job. Instead use a push-only workflow restricted
to two new execution refs: `codex/d5m-runtime-proof` and
`codex/d5m-runtime-review`. Explicit non-force creation of either ref at the exact
reviewed commit is the dispatch boundary; ordinary development pushes do not run
the PDF workflow. Proof ref accepts synthetic inputs only; review ref additionally
requires a checked-in sentinel packet containing the exact reviewed input manifest
SHA, toolchain manifest SHA, workflow/worker hashes, release/asset IDs, allowed
mode and bounded expiry. The job fails before loading documents if any binding
differs; the local dispatcher verifies the exact reviewed Git commit and ref
before push and accepts output only from that commit. Tests reject missing sentinel,
wrong ref/mode/hash, expired packet, changed asset and altered worker/toolchain.
Never use pull-request
triggers or a general arbitrary-command input. Remove transient execution refs
after accepted output retention; no merge or default-branch change. The existing
CI may independently run its ordinary push checks.

No token, application database, SEC credentials or local environment files enter
the parser container. Existing CI is not edited into an automatic PDF job.

The dedicated workflow has two separately reviewed modes: synthetic runtime proof
(no SEC bodies), then exact-manifest document review. Checkout/actions use immutable
commit SHAs; runner label `ubuntu-24.04`, image digest, OS/kernel/runner-image build,
Python version, source tarball/wheel hashes, complete tool/dependency/binary manifest
are pinned in the execution packet before any real PDF is loaded. Build/install
trusted tools in a separate staging job with no document input. Preserve pypdf
6.10.0 and Poppler 26.05.0; do not substitute distro Poppler. If exact tools cannot
be built and pinned, report toolchain unavailable. The initial proposal does not
invent unobserved image/tool hashes: staged implementation review must freeze them.

The interpretation container runs non-root, read-only root, no Docker socket or
host mounts except exact read-only input/tool directories and a bounded output
directory, dropped capabilities, no-new-privileges, default seccomp, PID limit 64,
`--network none --cpus 1 --memory 2g --memory-swap 2g`. Verify effective cgroup v2
memory.max=2147483648, memory.swap.max=0 and CPU quota corresponding to one CPU;
unsupported/readback-mismatched controls block. Use a 768 MiB output tmpfs and
64 MiB temporary tmpfs, both counted within the 2 GiB cgroup. No inbound ports,
network devices except loopback, inherited proxy/token environment or persistence.
One document and one render process at a time. Stop and remove the container in
all exit paths; workflow timeout 45 minutes, interpretation phase at most 25 minutes.
No privileged fallback or RSS-sampling substitute.

Original D050 process limits/settings remain mandatory: parser RLIMIT_AS 512 MiB,
CPU 25 seconds, file 32 MiB, wall 30 seconds; renderer RLIMIT_AS 512 MiB, CPU
5 seconds, file 8 MiB, wall 15 seconds per page. PNG 100 DPI RGB MediaBox with
original anti-aliasing; locale C/timezone UTC; at most 2000 pixels per dimension,
4 million pixels/page. Correspondence 100 pages/2 MiB text/120 seconds render/
64 MiB PNG; exact ARS 400 pages/8 MiB text/300 seconds render/256 MiB PNG.
All eight total at most 704 MiB PNG/1140 seconds render. All original structural,
active-content, encryption and visual-coverage rejection rules remain unchanged.
The 2 GiB cgroup is an additional process-tree limit, not a replacement for the
512 MiB per-process address-space cap.

## Proof, transfer and output trust

Before real documents, prove actual Linux RLIMIT_AS enforcement with bounded
allocation failure; RLIMIT_CPU termination; RLIMIT_FSIZE refusal; cgroup settings;
network denial; worker timeout; compressed-image and oversized-page/PNG fixtures;
valid small PDF parse/render/replay; process cleanup and corrupt-output rejection.
Record actual exit codes, versions, hashes, timing and completed-page roster.
A configuration string or simulated error alone does not establish enforcement.
If access prevents running the proof, record that external limitation; never label
runtime proven. No source retry is cleared before the enforcing runtime proof.

Transfer only locally verified retained PDF entity bytes, exact worker/tool bundle
and a manifest of capture ID/resource/URL/fetched/completed time/entity SHA/bytes.
The input transport is a checksum-pinned transient asset on a dedicated draft
GitHub release in the existing repository, with existing repository visibility;
no new public release announcement. Pin release ID, asset ID, asset byte length
and SHA in the reviewed execution packet; forbid replace/clobber or asset-name-only
resolution. A draft asset is mutable transport, not immutable source evidence.
The verified local archive remains authoritative. Changed/missing asset identity,
bytes or metadata blocks; never overwrite an asset to make a retry match.
It contains only public SEC bodies and code,
no application dump/keys/headers containing credentials. Access and redistribution
policy must be checked against the existing SEC policy before upload. If draft
asset transport is unavailable, stop; do not fetch SEC from the runner or silently
commit a different source copy. The staging job downloads through authenticated
GitHub transport, verifies the expected manifest SHA and every input SHA, then
passes only those files read-only to the network-disabled container. Do not trust
filenames, extraction paths, symlinks or advertised archive sizes. Reject duplicate,
unlisted, changed, oversized or non-regular entries before parsing.

Export per-page text/PNG hashes, exact commands, binary/tool versions, limits,
completed-page roster, input manifest hash and structured failures. The runner
outside the parser container verifies output paths/types/counts/limits and computes
a checksum manifest. Upload the bounded output archive as an immutable Actions
artifact; generate a GitHub OIDC artifact attestation for its digest with the
exact repository/workflow/commit/run identity. Pin action commits, least workflow
permissions (contents read, id-token write, attestations write); the download job
alone gets draft-asset read authority. No signing token/key goes into the parser.
Local acceptance verifies authenticated run/commit, artifact digest, attestation
identity, every output hash, original input hashes and effective runtime proof.
A checksum alone is not called a signature. Missing attestation entitlement is an
explicit blocker until a separately reviewed signing alternative exists.
Cloud crash/recovery has two ordered, immutable intents. Before release creation,
fsync a transport intent containing a transport UUID, expected repository, unique
release/asset names, local content hashes/lengths and tool/input manifest hashes;
it cannot contain future server IDs or a future execution commit. Persist exclusive
append-only upload receipts with returned release/asset IDs, linked to the transport
intent hash. Recover upload by unique UUID/name plus verified bytes/hash/metadata
before any new upload; ambiguous or missing outcome stays blocked, never clobbered.
After IDs are known, write the sentinel with those IDs, transport-intent/receipt
hashes and an execution UUID, then commit it. The sentinel does not contain its
own commit hash. Before pushing an execution ref, fsync a separate execution
intent binding that exact finalized Git commit, sentinel/packet SHA, execution UUID,
mode/ref, repository and transport-intent/receipt hashes. Neither intent nor any
receipt is edited to add later knowledge; subsequent observations are new linked
records. Thus transport upload precedes sentinel finalization, which precedes the
execution intent and ref push. Bind workflow
run ID, run attempt, head SHA and generated artifact IDs/digests in the completion
audit; each output manifest repeats the logical execution UUID and packet hash.
On execution interruption, discover by exact repository/ref/head SHA and workflow
identity, then verify the execution UUID/packet from the run output before accepting
it. On pre-execution interruption, reconstruct transport receipts first and never
infer that a workflow was authorized from an upload alone. Inspect
existing release/assets and Actions runs/artifacts before any possible redispatch.
No match remains unknown, not evidence that execution never happened; multiple
matching executions are a conflict requiring review, not latest-run selection.
A running run is awaited, a completed run is recovered without another execution,
and a failed/cancelled/expired-artifact run remains an immutable blocked attempt.
GitHub rerun and ref delete/recreate are not automatic recovery actions. A reviewed
explicit rerun must create a new logical execution intent referencing the old run
and failure, pin the new run-attempt/artifact identity and repeat proof/validation;
old outputs are preserved and cannot be relabeled as the new attempt. A proof run
cannot satisfy a real-document run. Tests cover death after asset upload, after
ref push but before run ID persistence, after completed output but before local
audit, duplicate run, wrong run-attempt, expired artifact and corrupt recovered
output. Recovery never obtains SEC source or changes application financial rows.

Retain accepted local copies before removing transient input transport assets;
cleanup failure is reported. Do not remove original local archives/audits.

## Substantive review and publication boundary

Read every successfully bounded PDF in full, visually inspect every rendered page,
and reconcile text/visual ambiguity with exact page references. No OCR values or
keyword-only absence conclusions. Complete per-body accounting/affected-concept
and reference dispositions across all 47 D050 bodies and retained periodic/
registration/exhibit editions. Resolve Reserve Fund fair-value treatment, SAB122
opening assets, corporate-held USDC flows, NCI/entity boundaries, temporary equity
and draft/pro-forma vs reported editions. Redactions or necessary unretained
references remain exact blockers. No mathematical identity is repaired.

Reassess FY2025 growth/ROA, eligible reported annual history and gross-margin
applicability under existing concepts/formula/period/status contracts. Gross
margin must not substitute RLDC or incomplete distribution costs. Annual growth
is not a quarterly trend. Requested 3/5/10 years is not evidence of coverage.
Freeze each eligible S3 preparation for independent standards/spec/numeric review
before any live source publication, then separately freeze period-specific S6
candidates for the same review. Preserve all prior batches and snapshots. New
concept/API/history shape or unsupported scope becomes a concrete contract blocker.
No price/provider/valuation/sector/scheduler or multi-company expansion.

## Acceptance and sequence

1. Review/commit this proposal; implement red-first transport/audit and runtime
   harness tests. Pin and review the workflow/toolchain and synthetic proof packet
   before dispatch. No live retry/migration is part of proposal approval alone.
2. Run synthetic runtime proof, inspect signed outputs, review exact source retry
   packet and prior-row baseline. Only explicit clearance permits local acquisition.
3. Review all bodies, final pair and accounting reconciliation, then clear exact
   S3/S6 candidates separately. Fail closed on any incomplete source/runtime gate.
4. Extend the analysis UI with current evidence/cutoff/history and provenance;
   no frontend finance math. Update roadmap/manual/milestone/handoff. Full checks,
   build, desktop/mobile/keyboard/GET-only/corruption acceptance, staged independent
   reviews, hooked commits, non-force push, clean remote/preview verification.
5. Stop after the complete D5l CRCL section or a genuine evidenced external/contract
   blocker. No multi-company rollout.

Official runtime references checked 2026-10-22:
[Vercel Sandbox](https://vercel.com/docs/sandbox),
[Docker resource controls](https://docs.docker.com/engine/containers/resource_constraints/),
[GitHub workflow execution](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
[GitHub attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations).
These establish documented capabilities, not proof of this account's runtime access.
