# D051 synthetic proof 3 — bounded live diagnostics

Status: independent standards/spec review passed; mandatory hooks precede dispatch.
No third execution intent/ref update,
release, SEC retry, real PDF processing or financial publication.

Proof2 commit e0046e9bae40378ab6bddcc3f1d899993819ed34 passed1926/512/110 hooks
(two existing warnings), was pushed, and executed as run39856955079 attempt1.
The pinned CA bootstrap and tool build succeeded. The synthetic worker then failed
at runtime_compressed_stream_not_bounded. The signed diagnostic package contained
only supervisor container/process receipts; Docker cp omitted the live tmpfs files.
The parser's actual reason was therefore not retained. No assertion relaxation is
justified by that evidence.

Artifact12459797527 (crcl-pdf-proof-39856955079-1), ZIP1930bytes SHA256
cbd09bfa7c1e902c1c689ee9063b302693ebf32aa4554a8c6f55654c8293b715,
contains tar SHA256 ff65c18bbf3e70643c30b7347c40f1fac62ec18dc6ceef36784aacfe71d0c3bf.
Pinned gh2.80.0 verified its GitHub attestation against the exact repository,
workflow, source ref and commit, rejecting self-hosted runners. Exact packet,
execution UUID, run/attempt and file-manifest checks also passed. This proves the
origin/integrity of the failed diagnostic, not runtime safety. All packet/intent/
dispatch/run/job/artifact/log/signature/output evidence is preserved under
[proof-2](../../research/crcl-d5m-runtime/proof-2); the raw log is losslessly gzipped.

## Repair and unchanged acceptance

Replace docker cp with trusted tar executed inside the still-live container mount
namespace. The host reads stdout incrementally with a120second deadline and
744MiB hard byte ceiling; failure kills the export process and discards its partial
archive. Tar traversal rejects more than3000members, absolute/traversal paths,
links/nonregular entries, duplicate names, supervisor receipt collisions,
files above32MiB and aggregate payload above736MiB. Files are written exclusively.
The container's read-only filesystem, network denial, CPU/memory/PID/tmpfs limits
remain unchanged. The resident sleep is3600seconds (job remains45minutes), keeping
tmpfs alive beyond the1500second proof supervisor timeout; cleanup always removes
the container. Export is attempted after ordinary worker exit/failure. A host interpreter timeout
cannot establish quiescence merely by killing the Docker exec client: it records
worker_timeout_no_quiescence, skips export and removes the entire container/process
tree in finally. Mutable tmpfs data is never exported after that timeout.
If the container itself dies or its tmpfs is lost, export fails closed and records
an explicit blocked receipt; no missing output can be promoted to a proof.

The built-toolchain manifest is copied into tmpfs before tests. Each intermediate
result is atomically checkpointed before its assertion, and an exception writes a
bounded failure record. Unexpected results remain failed while independent bounded probes continue.
Dependent checks are explicitly skipped when prerequisites failed, and any failure
or skip makes the overall proof fail. All intermediate values/check dispositions
are retained. Effective isolation failure still stops every subsequent probe.
The compressed-stream assertion still accepts only the
original precise memory/timeout/process-failure codes. Generic parser errors are
not accepted. Proof3 is a diagnostic run and may fail at that same assertion; its
observed exact parser result will determine any separately reviewed mapping or
fixture repair. No claim that the unknown parser result is an internal limit.

New execution UUID7dae5905-a544-4124-8af9-f50a5d388d03.
Packet SHA256 39227c2e915788a41e4990cf389e10becfb47ab20169ce48ad0dd35be6c92a64.
Toolchain remains ca89f7b1a1cfe05b06caf0984ae34b340a5d4b4f98d938c111d02593824bf11f.
Predecessor is exact failed proof2 commit/run/attempt and retained receipt hashes.
The already reviewed strict-ancestry plus atomic expected-OID lease and post-push
verification apply. A new hooked descendant commit and explicit clearance are
required before dispatch; no rerun API or unconditional force.

Four new red export/checkpoint regressions reproduced the missing implementation;
focused runtime/export tests pass21. Full exact-tree mandatory hooks precede any
approved dispatch. No source retry follows automatically from diagnostic success.
