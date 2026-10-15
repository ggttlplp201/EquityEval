# D5i handoff

Canonical iCloud repo, branch codex/d5a-crcl-normalization. Proposal c55c2cf,
baseline 07c53d69. Acquire the exact pair only once: saved capture times are
2026-10-15T21:59:05.128575Z and 21:59:05.195192Z. Do not repeat acquisition or
rewrite prior audits. Review and preparation artifacts pin exact observation
semantics and the explicit three-acceptance-time metadata-vintage delta.

Run project Python with explicit PYTHONPATH to the existing editable build plus
repo root; this prevents the known iCloud hidden-pointer subprocess import issue.
Replay `scripts.review_crcl_observation --check`, `scripts.prepare_crcl_observation
--check`, and checked exporter. All three independent reviews cleared the exact pinned live publication. Batch
`b49859b5-9f27-455a-87a4-e6fe776f5314` is now published and replay/readback/preservation
verified. Use `scripts.publish_crcl_observation verify`; do not republish or replace
its immutable audit. The capture-only verifier predates the new normalization rows;
the publication verifier checks preservation across both boundaries.

Next main gate is real S6 contract review: synthetic-only input/result types and
SQL constraints, plus required quote identity, cannot honestly represent a real
unpriced CRCL operating-margin snapshot. Do not change those contracts silently,
mislabel real data synthetic, fabricate a quote, or calculate in the frontend.
Keep historical D5a and saved D5b–h panels distinct. Preview 3103; never touch 3101.

Validation: full make check 1,799/505/110, 14 focused observation tests, production
build, all 51 browser checks and independent standards/spec/numeric reviews pass.
Final hooked commit runs the added publication regression in the full suite too.
Only new D5i research artifacts were added; all prior research bytes are unchanged.

D5i committed and pushed as f42222682892e8602b884e5aaf64c44af9b85d63; remote HEAD
verified and tree clean. Hooks passed 1,800/505/110. Continue only from the separate
[D5j contract proposal](../design/d5j/proposal.md) after explicit shared-contract
approval. Its review does not itself authorize source/API/schema mutations.

D048 was subsequently approved by the coordinator under the user’s continuation,
after independent design reviews. Proceed with that exact companion-table/v2
contract; review SQL/Pydantic/API before applying migration and numeric candidate
before publishing. No other expansion is approved.
