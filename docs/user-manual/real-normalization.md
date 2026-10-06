# Read CRCL's real normalized financials

Open **Real-data pilot → Inspect CRCL’s application pipeline → Financial
normalization → Inspect normalized financials**. The direct local route is
`/development/pilot/normalization`.

The saved FY2025 view contains reported revenue and reserve income of
$2,746,642,000 and operating income (loss) of −$96,435,000, in USD. Select an amount
to see its exact value, accession, filed date, retrieval cutoff, original source
token and transform. Its Source chain distinguishes the selected Company Facts
observation, the original 10-K's independent precision cross-check and Submissions
filing metadata. Only Company Facts supplies the mapped numeric observation.
The amendment and quarterly filing appear separately under **Review context
(not PIT-selected)**, with their own review roles. Escape closes the source drawer and restores keyboard focus.

**History selection** controls which filed-date evidence can be selected:

- **Filed by Mar 9, 2026:** includes the original annual filing.
- **Filed by Mar 8, 2026:** displays N/A for both figures. Their drawers contain
  only the unavailable selection, with no later literals, scales, contexts or
  filing links. Later material is available separately through **Publication &
  source records**, explicitly as non-PIT review context.
- **Earliest available:** selects the earliest eligible retained original. This
  does not claim the financial or event history is complete.

These are retrospective filed-date reconstructions using files captured on
September 21. The application did not hold those files in March. Publication on
September 30 is a separate event; click the date panel to inspect all exact times.

A **source capture** is retained source bytes with their hash, URL and capture
identity. A **normalization batch** is an immutable conversion of reviewed source
observations into standard concepts. Repeating the exact inputs reuses the same
batch. This batch references five captures, retains nine Company Facts candidate
observations and selects two facts. Three filing editions remain distinct; the
annual amendment adds separate Circle Reserve Fund statements and is not treated
as a restatement of Circle's original annual figures.

**Precision** describes what the source reports, not certainty about the business.
The original filing uses scale 3 and decimals −3. The source reader preserves the
literal, sign and transform. Company Facts does not supply original XBRL context
or precision, so those fields remain unknown in that observation; the original
filing's evidence is shown separately. Whole-document extraction has unresolved
items; these two checked facts do not imply complete statement extraction.

**Quality flags** record unresolved conditions. Use **Quality flags** for the
source rows or **Inspect analysis readiness** for the downstream gate view. The
retained inventory and event-history flags prevent valuation eligibility.
Financial analysis, prices, ratios and fair value stay N/A here.

## Read analysis readiness

Open **Financial normalization → Inspect analysis readiness**, or use
`/development/pilot/analysis`. The page keeps three ideas separate:

- **Normalized inputs:** the two exact source amounts passed D5a normalization.
- **Analysis values:** both remain unavailable because the reviewed point-in-time
  selections retain blocking quality flags.
- **Published metrics:** zero. Operating margin shows its intended formula and
  N/A, with an explicit statement that no ratio was calculated.

Expand the five publication gates to inspect the remaining history,
business/metric applicability, accounting coverage, quote identity and real
fundamentals-publication work. A blocked gate describes missing evidence or an
unfinished contract. It is not a positive or negative judgment about the stock.

The page reads a hash-checked artifact derived from D5a. It does not query the
application database, fetch a source, update a watchlist or calculate finance in
the browser. The two source amounts are abbreviated for display. Select either
amount to inspect its exact decimal string, accession, retrieval date, transform
and three-link source chain.

If the saved artifact fails verification, the page shows N/A and a Retry button.
Retry reloads the local saved page; it neither acquires data nor publishes a batch.

## Local operator commands

Run from the canonical CloudDocs project with its existing Python launcher:

```sh
.venv/bin/python scripts/project_python.py -m scripts.publish_crcl_normalization preflight
.venv/bin/python scripts/project_python.py -m scripts.publish_crcl_normalization verify
.venv/bin/python scripts/project_python.py -m scripts.export_crcl_normalization --check --verify-application
.venv/bin/python scripts/project_python.py -m scripts.export_crcl_analysis_readiness --check
```

Preflight and verify are read-only. Replay and standalone verify both require the
exact reviewed mapping ID, revision, rule hash, code revision, approver and scope. `publish` is the explicit D039-approved bounded
write command; the first run registers the reviewed mapping and publishes the
batch, and subsequent identical runs reuse it. Mapping approval is a separate
transaction from publication. A failed command does not prove rollback of a batch
that already committed; use `verify` to inspect the actual state before retrying.

The command is pinned to D3c's five governed captures and two reviewed FY2025
concepts. It does not fetch new files or expand to a different stock, period or
mapping. Those require a new reviewed input set. The application remains on
migration 0010; D5a does not publish a real S5/S6 analysis.
