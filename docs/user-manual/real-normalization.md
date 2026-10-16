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

## Safety review after normalization

The analysis page preserves D5c's saved pre-exhibit safety review. Expand a check and choose
**Inspect evidence** for its exact source and limits. Filing coverage lists every
scoped accession, capture time and body hash; outstanding exhibits and later
filings are linked separately.

**Historical application knowledge** asks what the app actually retained by the
September cutoff. October retrievals cannot change that answer. **Retrospective
content review** asks what later evidence establishes about the old annual pair.
The pair and amendment wording pass bounded checks, but at that saved checkpoint missing exhibits and
reclassification scope prevented complete safety proof. A current assessment also
requires the two later events and a new cutoff/batch.

Operating margin stays N/A. The descriptive stablecoin-issuer profile does not
turn reported margin into recurring cash profit or generic technology-sector
comparability. Holder reserves are not corporate excess cash. No real S6 metric,
price ratio or valuation was published. See the [D5c milestone](../milestones/D5c-crcl-safety.md).


## Latest exhibit review (D5d)

The latest panel on the analysis page lists all eleven acquired exhibit bodies.
Expand an exhibit to read its actual relevance, review scope and remaining limit.
**Inspect exhibit evidence** opens retained quotes, capture time, source hash,
parent accession and, for earnings statements, exact ordered columns and paired
periodic filing proof. Financial source amounts appear inside this provenance
view; no operating margin is calculated.

The annual reported operands match. Tested quarterly comparisons also match;
this does not prove every annual reclassification question resolved. Later
Adjusted EBITDA definition changes are non-GAAP changes, and cannot replace the
reported operating result. The certificate reclassifies share classes. The bylaws
corroborate the fiscal calendar. Tazapay agreement representations describe the
target under SFRS, with omitted schedules and unavailable target statements;
they do not certify Circle GAAP figures. The transaction announcement describes
an expected future closing, not completed acquisition accounting.

All new evidence was retrieved in October. September application knowledge stays
blocked. The latest inventory identifies later primary filings that were not
acquired in this exhibit batch; current eligibility requires their review and a
new cutoff, accounting scope resolution and the real S6 publication gate.

Archive-only verification:

```sh
.venv/bin/python scripts/project_python.py -m scripts.review_crcl_exhibits --check
.venv/bin/python scripts/project_python.py -m scripts.export_crcl_exhibits --check
.venv/bin/python scripts/project_python.py -m scripts.capture_crcl_exhibits verify
```

The last command also reads the current application to verify preservation.
Do not rerun `capture`: the saved attempt is immutable and rejects implicit retry.
Older fixed-count application acquisition audits describe their historical state;
use D5d's verification for current source-storage preservation.


## Current-window decision (D5e)

The saved D5e analysis panel asks whether a new evidence batch can proceed. It shows
the two later primary events, their full-body findings, the exact unreviewed
CFO-departure exhibit link, and affected-line/edition comparisons. Expand a row and
choose **Inspect evidence**; financial source amounts remain inside provenance.
Fresh annual Company Facts values match the original annual edition, and retained
Q2/H1 comparative values match. Those findings do not resolve the missing earlier
Q1 comparison or every affected-line reclassification question.

Read the three times separately: the old September cutoff, the current inventory
observation, and the time all new bodies were held. The last is a retrieval cutoff,
not an assertion that the inventory covers later public events. A matched scoped
inventory is not completed event-body review. The candidate batch remains blocked;
there is still one published normalization batch, two selected facts and no metric.
Older D5c/D5d panels remain saved checkpoints and are not rewritten.

Verification uses `scripts.review_crcl_current --check`,
`scripts.export_crcl_current --check` and `scripts.capture_crcl_current verify`
through the existing project Python runner. Capture is a saved immutable attempt;
do not rerun it. The current acquisition adds four source captures and preserves
all prior rows. No financial publication or quote/provider activation occurred.

### D5f leadership-exhibit checkpoint

The saved D5f analysis panel closes the named CFO-transition exhibit review and
shows the remaining accounting blocker. Open its disclosures to inspect the
full-body finding, all retained periodic-context/reclassification evidence,
fresh annual source rows and the exact unretained IPO prospectus candidate.
The prospectus link comes from inventory metadata; its content is not yet proved.
Older D5e/D5d/D5c panels remain saved checkpoints. Inventory observation and final
retrieval times stay separate. No new normalized batch or metric is published;
September application knowledge remains unchanged. Preview uses port 3103.


### D5g IPO-prospectus checkpoint

The latest analysis panel distinguishes proved statement matches from incomplete
source history. Expand **IPO statements versus later editions** to inspect the
reported Q1 and annual comparative operands, exact tables/contexts, periods,
signed literals, USD scale and source lineage. **Every retained Q1 Facts vintage**
shows all thirteen captures with filing attribution; these are not thirteen
independent statements. **Unreviewed registration history** names each of seven
exact missing bodies and explains why metadata cannot establish their content.

The candidate batch remains blocked and operating margin remains N/A. This does
not discard the statement matches: it prevents them being mistaken for complete
financial history. Inventory observation, final retrieval and historical cutoff
have distinct meanings. Earlier panels are saved decisions at their own checkpoint.
Verify with `scripts.review_crcl_prospectus --check`,
`scripts.export_crcl_prospectus --check`, and `scripts.capture_crcl_prospectus verify`.
Do not rerun the immutable acquisition. The next source batch requires its own
pinned proposal; no further source or publication was included here.

## D5h saved registration review

The saved D5h panel reviews all seven remaining registration bodies. Open
each disclosure for statement rows and accounting passages, or the comparison
drawer for exact periodic contexts and every retained Facts vintage. Every source
shows its URL, accession, retrieval time and transform/hash lineage. Blank preliminary
tables and derived quarters are not financial inputs.

The selected statements reconcile, but a new batch stays blocked: the last
Submissions observation precedes the final filing-body capture. Sharing a calendar
date does not prove coverage through a later instant or through the full day.
The next bounded step is a fresh mandatory `company_facts/0001876042` and
`submissions/0001876042` pair, both captured after all retained bodies, followed by
inventory review. September knowledge and the original batch do not change.
Operating margin remains N/A; real publication has separate gates. Earlier panels
are saved checkpoints and retain their then-current blockers.

## D5i archived source checkpoint

The D5i archived panel shows an eligible published normalization batch. Click either
source amount to open the original filing context, scale/sign/precision, current
Company Facts locator and retained source URL/hash/time. The evidence drawer shows
the exact inventory observation and the three explicitly reviewed acceptance-time
metadata differences. No explanation for those source-vintage differences is inferred.

Eligibility applies at 2026-10-15T21:59:05.195192Z. It does not repair September
knowledge or promise coverage later that day. The earlier panels remain saved
checkpoints. At D5i, operating margin remained N/A pending the separate real S6
contract completed in D5j. Reporting
USD is a source unit, not proof of quote currency. No ratio is computed in the browser.

Read-only checks: `scripts.review_crcl_observation --check`,
`scripts.prepare_crcl_observation --check`, `scripts.export_crcl_observation --check`
and `scripts.publish_crcl_observation verify`. Do not rerun the acquisition or
rewrite either normalization batch. Publication replay was already proved.

## Published real operating margin (D5j)

Open `/development/pilot/analysis`. The preserved D5j panel displays the saved real FY2025
reported operating margin, **−3.51%**. Select the percentage to inspect the exact
core result, signed operands, formula, snapshot identity, filing URLs, accession,
retrieval times, hashes and transformation evidence. Both USD operand amounts
open their own source drawers. Escape closes the drawer and restores focus.

This descriptive ratio divides reported operating income (loss) by total revenue
including reserve income. It is not adjusted earnings or a recurring-profit claim.
The policy drawer explains stablecoin/reserve-income applicability, annual
freshness, precision and accounting-review limits. Source knowledge ends exactly
at 2026-10-15T21:59:05.195192Z. Frozen evaluation and publication are separate times.

Within this preserved earlier snapshot, expand any of the nine unavailable metrics for its exact missing operands and
classification/applicability work. Accounting identity, comparison history and
quarterly trends remain unavailable. No price, valuation or sector conclusion is
implied. The older checkpoints below preserve their original blocked decisions;
the October review does not repair September knowledge. Synthetic development
pages remain separate. The preview uses port 3103.

After D5k, verify preservation with `scripts.verify_crcl_broader_completion --check`
and the original display with `scripts.export_crcl_fundamentals --check`. The display is a hash-checked export
of the immutable real-v2 snapshot, not a live recalculation. If it is damaged,
values disappear and Retry can recover after the original bytes are restored.

## Broader reported fundamentals (D5k)

The first analysis panel now presents two distinct published results. The annual
FY2025 section contains operating margin, consolidated net margin, free cash flow
after cash PPE purchases and its revenue margin. The December 31 closing section
contains current ratio and net working capital. Select any amount or ratio for its
exact formula, source operands, filing accession, retrieval time, hash and snapshot.
Expand Exact source operands for each normalized amount. The balance-identity
button opens the published assets/liabilities/permanent-equity check.

Net income includes noncontrolling interests. FCF excludes capitalized software
and acquisitions and must not be interpreted as discretionary cash. Current
assets/liabilities include holder reserves and obligations; their ratio and
difference are gross reported totals, not available corporate liquidity. The
metric-specific scope text travels with the result.

Each result keeps other-period metrics explicitly unavailable in that result.
Gross margins, growth and ROA remain globally unsupported. The comparative source
rows disclosure shows earlier reported amounts with provenance, labelled not
analysis eligible. It does not create full comparison history. Exact missing
draft/correspondence resources and unsupported PDF acquisition requirements are
listed beside the review. The same October 15 source observation applies; later
evaluation/publication does not extend coverage or repair September knowledge.

The older D5j and earlier audit panels remain preserved below. Their unavailable
slots describe those original snapshots, not a reversal of the newer publication.
The new display is a checked immutable export with no frontend finance math. A
damaged artifact hides values; restore its exact bytes and use Retry. Read-only
verification uses `scripts.verify_crcl_broader_completion --check`,
`scripts.publish_crcl_broader_fundamentals verify annual`,
`verify instant`, and `scripts.export_crcl_broader --check`.
