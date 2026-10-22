> Historical second proof: executed as run39856955079 attempt1. Tool build passed;
> synthetic assertion failed. See [diagnostic repair](proof-3-diagnostic-export.md).

# D051 synthetic proof 2 — CA bootstrap repair

Status: independent standards/spec review passed; second execution remains behind
mandatory hooked commit. No second execution intent, commit, proof-ref update,
draft release, SEC retry or real PDF interpretation has occurred.

The first approved proof commit e54d6774acb99d8ba688b4e7ae52f27f6527c82f passed
mandatory1918/512/110 checks (two existing warnings) and production build. It was
pushed to the development branch and proof ref. GitHub run39854492748 attempt1
failed during trusted Docker tool staging: the minimal pinned Ubuntu base lacks
CA certificates, and the HTTP snapshot URL redirects to HTTPS. Certificate
verification correctly failed. No PDF worker ran and no output artifact or
attestation exists. The real-review job was skipped. This is not runtime proof.

The complete first packet, local intent/dispatch receipt, run/job/artifact metadata
and exact job log are preserved under docs/research/crcl-d5m-runtime/proof-1.
The log SHA256 is fe39a8cec9d04cd1349a1250e827dc6127011fc23c895514b0098f3949a316a0.
The local var archive remains authoritative for dispatch recovery.

## Exact repair

Use ca-certificates20240203 from the already pinned noble snapshot:
https://snapshot.ubuntu.com/ubuntu/20261022T000000Z/pool/main/c/ca-certificates/ca-certificates_20240203_all.deb

Package159378bytes SHA256
641de77d8f142cfd62a1a6f964ba67b20754d3337c480efb529d086075a06c9a.
Its package identity was resolved through the pinned noble InRelease SHA and its
SHA256-bound main/binary-amd64/Packages.xz. The local trusted interpreter downloaded
with HTTPS verification and checked exact bytes/hash. It read only the package's
146 usr/share/ca-certificates/mozilla/*.crt members, ordered lexically, concatenating
each with one terminal newline. Result219342bytes SHA256
6d84ab71cb726c0641b0af84303c316e3fa50db941dc8507d09045eb2fa5d238.
The public certificate bundle is committed and included in the exact file roster
and Docker context allowlist. Docker copies it to the initial CA bundle location
and checks its SHA before apt. Sources explicitly use HTTPS. Package TLS
verification, Ubuntu signature verification and all pinned InRelease checks remain
mandatory; no insecure transport, trust override or arbitrary certificate source.
The installed snapshot ca-certificates package subsequently maintains the normal
runtime bundle; observed runtime identities remain exported and reviewed.

## Single descendant execution

New UUID3a8fbc9a-d2b5-41f8-8b55-91be73f68559.
Packet SHA256 b4a219fbeee1e6e4400647f254e12e43db80ea160c88dddec303785df9d109fe.
Toolchain SHA256 ca89f7b1a1cfe05b06caf0984ae34b340a5d4b4f98d938c111d02593824bf11f.
The packet pins prior UUID, commit, packet/intent/run-receipt hashes, run39854492748
attempt1 and failed conclusion. The first intent is never edited or reused.

After independent clearance, a hooked descendant commit may be pushed to the
existing development branch. A new immutable execution intent binds that exact
commit and packet. Before any proof-ref update, the dispatcher verifies retained
prior intent/receipt hashes, live exact run identity/status/attempt, remote ref
still at e54d6774acb99d8ba688b4e7ae52f27f6527c82f, and strict Git ancestry.
It then uses an atomic explicit expected-OID lease
(`--force-with-lease=<exact-ref>:<exact-predecessor>`) after the independent strict
ancestry check, and verifies the post-push remote head. No unconditional force or
history rewrite is permitted. A concurrent deletion or move, even to another
ancestor of the candidate, rejects the update. Initial ref creation likewise uses
an explicit empty expected-OID lease. The branch must only fast-forward to the new
reviewed descendant. Missing/mismatched ref, different run/attempt/outcome, changed
receipt or non-descendant blocks. Any existing new intent invokes read-only
recovery instead of redispatch, including after a crash before/after push.
No GitHub rerun API is used. This creates a new logical proof run, not attempt2.
The workflow/ref/limits/fixtures/output signature requirements otherwise remain
unchanged. A failed or unverified second run still blocks source acquisition.

Red ref-update regression was observed; focused runtime tests pass15 with strict
mypy and Ruff checks. Commit and the exact atomic descendant ref update were independently cleared;
mandatory final-tree hooks precede dispatch.
