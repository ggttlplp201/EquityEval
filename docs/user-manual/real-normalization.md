# Read CRCL's real normalized financials

Open **Real-data pilot → Inspect CRCL’s application pipeline → Financial
normalization → Inspect normalized financials**. The direct local route is
`/development/pilot/normalization`.

The saved FY2025 view contains reported revenue and reserve income of
$2,746,642,000 and operating income (loss) of −$96,435,000, in USD. Select an amount
to see its exact value, accession, filed date, retrieval cutoff, original source
token and transform. Escape closes the source drawer and restores keyboard focus.

**History selection** controls which filed-date evidence can be selected:

- **Filed by Mar 9, 2026:** includes the original annual filing.
- **Filed by Mar 8, 2026:** displays N/A for both figures.
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

**Quality flags** record unresolved conditions. Use **View calculation status**
to inspect the retained inventory and event-history flags. They prevent valuation
eligibility. Financial analysis, prices, ratios and fair value stay N/A here.

If the saved artifact fails verification, the page shows N/A and a Retry button.
Retry reloads the local saved page; it neither acquires data nor publishes a batch.

## Local operator commands

Run from the canonical CloudDocs project with its existing Python launcher:

```sh
.venv/bin/python scripts/project_python.py -m scripts.publish_crcl_normalization preflight
.venv/bin/python scripts/project_python.py -m scripts.publish_crcl_normalization verify
.venv/bin/python scripts/project_python.py -m scripts.export_crcl_normalization --check --verify-application
```

Preflight and verify are read-only. `publish` is the explicit D039-approved bounded
write command; the first run registers the reviewed mapping and publishes the
batch, and subsequent identical runs reuse it. Mapping approval is a separate
transaction from publication. A failed command does not prove rollback of a batch
that already committed; use `verify` to inspect the actual state before retrying.

The command is pinned to D3c's five governed captures and two reviewed FY2025
concepts. It does not fetch new files or expand to a different stock, period or
mapping. Those require a new reviewed input set. The application remains on
migration 0010; D5a does not publish a real S5/S6 analysis.
