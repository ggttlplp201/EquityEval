# D051 synthetic proof 4 — exercise the actual Flate boundary

Status: independent standards/spec review passed for canonical packet404db9….
Full checks and mandatory hooks precede the approved synthetic dispatch.
No execution intent/ref update, release, SEC retry, real PDF interpretation or publication yet.

Proof3 commit 08f4c58cbeaa92933acb543584f932f700739077 passed mandatory
1932/512/110 checks (two existing warnings). Run39860919258 attempt1 failed one
of13 independent checks. Artifact12462485747 ZIP SHA256
c23ee1f0ca8e5fa5ef89c0481c5a9bddb8d615b9420486efdcbaf707d60f1d71,
tar SHA256 afe84c3ca6b73392a2dc318bc764408c2988102ef4368d54c1f0231fac034522,
passed pinned gh attestation checks for exact repository/workflow/ref/commit,
hosted runner and invocation URL, plus exact packet/run/file-manifest verification.
All signed outputs, packet, intents, API receipts and losslessly gzipped raw log
are preserved in [proof3 evidence](../../research/crcl-d5m-runtime/proof-3).

The parser returned parsed/empty text for the compressed Contents fixture.
Inspection of hash-pinned pypdf6.10.0 shows that a page without Resources returns
empty text before reading Contents. This was a skipped test input, not proof of
safe decompression. The separate actual image decoder reported LimitReachedError;
Poppler stream/image probes terminated under limits, and its actual PNG output
reached8388608bytes. Those signed observations remain unchanged.

## Exact repair

Give the Contents fixture an explicit Resources dictionary with a standard
Helvetica font. The same bounded 1GiB synthetic whitespace stream must now be
read. Add pdf_parser_decompression_limit only for the exact pypdf.errors.
LimitReachedError class with a traceback code-object identity matching pinned
filters._decompress_with_limit or filters.decompress. Text matching alone, other
exception classes, and LimitReachedError from unrelated reader/cmap boundaries
are not accepted; they remain generic blocked parser errors. Parser version6.10.0
is checked before inspection. Existing memory/timeout/process-limit outcomes stay
accepted. No generic parser-error acceptance is introduced.

A tiny synthetic regression lowers only its isolated test process's Flate output
limit to64bytes, parses1024bytes of compressed whitespace through the actual
fixture/worker, and requires the precise blocked reason. Removing Resources or
skipping Contents fails this assertion. Same-message wrong exception classes and
the correct class outside the Flate traceback fail classification; an actual
Flate frame raising ValueError also fails classification. Production caps and
parser defaults are unchanged. Both new regressions were red before implementation;
focused parser/runtime/export tests now pass42; Ruff and strict mypy pass.

Bind the signed observed built-toolchain manifest SHA256
7a78dcefce1302d6da1974679abd4c9b3031765cc16d00e40cdb8087ff1e62b4.
The proof copies its manifest and verifies this exact digest before controls and
all probes. Any rebuild drift blocks execution; it cannot silently use a different
Poppler/Python/library/font toolchain. The packet records this identity as well.
Original toolchain recipe SHA ca89f7b1a1cfe05b06caf0984ae34b340a5d4b4f98d938c111d02593824bf11f
and all isolation/streaming/quiescence/output constraints remain unchanged.

New execution UUID 9675916e-0420-4334-b5de-c990d0d2fd86.
Packet SHA256 404db9bbe4f33ec7bc1d9b07377085ce7975fa9d1e268d9002eee9c7e189fd55.
Predecessor binds proof3 exact commit/run/attempt and immutable packet, intent,
and API run-receipt hashes. Only a separately reviewed hooked descendant may
advance the proof ref through the existing strict-ancestry/atomic expected-OID
lease and post-update verification. No rerun, unconditional force or default
branch change. Any failure remains failed with independent diagnostic aggregation.
Runtime success alone cannot clear source/accounting/history/publication gates.

Dispatch-readiness regression reproduced and fixed the trailing-newline rejection;
the staged packet uses exact canonical bytes and verifies every pinned file.
