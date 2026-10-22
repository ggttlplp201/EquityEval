> Historical first proof gate: executed as run39854492748 attempt1 and failed
> at CA bootstrap before any PDF operation. See [second proof repair](proof-2-ca-bootstrap.md).

# D5m synthetic Linux proof — staged execution gate

No execution ref, draft release, live acquisition or financial publication has
been created. The proposed first cloud boundary is synthetic proof only. The
review branch job deliberately exits before any document operation. Real PDF
transport/review and the local ARS retry require later independent packets.

`infra/pdf-runtime/execution-packet.json` binds the complete required file roster,
exact official source/wheel/base-image/signed Ubuntu snapshot and action commits.
It contains a unique execution UUID, proof ref and expiration, with input null.
The final committed Git SHA is bound by a separate fsynced local execution intent
before a non-force ref push; the sentinel contains no circular own-commit hash.
The reviewed development-branch commit/push alone cannot run this workflow.

After explicit clearance and a clean hooked commit, the only dispatch command is:

```
python -m scripts.crcl_pdf_cloud dispatch-proof --commit <reviewed-committed-SHA>
```

Use the project Python environment. This creates only
`refs/heads/codex/d5m-runtime-proof` at that SHA in the existing repository. It
never changes main, uploads a release, fetches SEC or writes application rows.
An existing local intent makes all subsequent invocations recover-only; unknown,
duplicate, failed and unapproved-rerun outcomes stay blocked. Recovery uses
`recover --commit <original-SHA> --execution-id <retained-UUID>` and reads the
immutable saved intent without depending on packet expiry or the current checkout.
No force push.

The workflow first verifies the canonical packet, expiry, mode/ref/repository and
all required file/toolchain hashes. The Docker build receives only an explicit
allowlist of tool sources via Dockerfile.dockerignore; no financial PDFs, local
environment or database files. Ubuntu package indexes are signed and hash-pinned
at a fixed snapshot. Poppler26.05.0 and pypdf6.10.0 archives are hash-checked before
build/install. All observed binary/runtime library/font/interpreter source hashes
and package versions are exported. Bytecode caches are excluded from deterministic
source identity; Python sources and interpreter are included.

The trusted runner creates the declared 1CPU/2GiB/no-swap/read-only/nonroot container
with no network, dropped capabilities, seccomp, no-new-privileges, 64PIDs and bounded
tmpfs. A resident sleep process keeps tmpfs available until Docker copies the
bounded outputs; finally removal releases it even on error. The synthetic worker
independently checks effective kernel/cgroup settings, proves allocation/CPU/file/
network limits, valid PDF rendering/replay, oversized page rejection, compressed
stream and image decoder limits (including actual Poppler rendering of drawn
XObjects/content streams), a deterministic incompressible 1800×1800 RGB image
whose real PNG write must reach the 8MiB file cap and terminate unsuccessfully,
encrypted/page limits, actual wall timeout and
corrupt-page refusal. Parsed/rendered output never means human visual clearance.

Proof failure still exports checksum-bound signed diagnostic output where the
container supervisor produced a report; the job ultimately fails. Tool-build or
preflight failure cannot establish a runtime and remains a named/logged blocker.
The output tar is signed by GitHub OIDC outside the container and uploaded under
run-ID/attempt-specific artifact name with overwrite false and seven-day retention.

Before acceptance: retrieve the artifact by exact run/attempt/artifact ID, verify
its digest and GitHub attestation with the pinned local gh2.80.0 binary, exact
repository/workflow and source commit, deny self-hosted runners, retain verification
JSON/attestation and hashes locally. Then call `verify_output_tree` for exact file,
execution UUID, packet SHA, commit/run/attempt identity and require all synthetic
proofs successful. Hash verification alone is not a signature. The local verifier
archive pin is in toolchain.json. Actual signing/runner access remains unproved.
No source retry follows automatically after proof success.

The later real-document packet must pin the successful built-toolchain identity,
exact eight input captures/bytes and transient release/asset IDs. A reconstructed
build whose observed runtime identities differ cannot interpret financial bodies
until separately reviewed/proven. No current code claims this later step complete.

Validation before staged review: red transport/runtime/output/recovery regressions
recorded in /tmp/d5m-red-*.log; focused suite and disposable SQL counter-audit test
pass. Full checks passed 1915 tests (two existing warnings), 512 core and 110
golden tests; after the final recovery/encoding/render-fixture fixes, 58 focused
checks including the SQL audit passed. Production build passed. The mandatory
commit hook reruns the full final staged tree. No Linux runtime proof has run yet.
