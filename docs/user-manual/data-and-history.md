# Understanding source data and history

Draft for the implemented S2/S3 data layer. The product screens and their
walkthroughs are still being built; these definitions describe the current
stored evidence and testable behavior.

| Term | Meaning in EquityEval |
| --- | --- |
| Ticker | An exchange's symbol for a security. It can change or be reused, so the symbol alone is insufficient identity. |
| Issuer / CIK | The reporting company and its SEC identifier. An issuer can have several securities. |
| Ordinary share / ADS | Different instruments. An American depositary share represents underlying shares under its own terms; their reported share counts and per-share values cannot simply be substituted. |
| Reporting period | The dates a financial fact describes. Revenue covers an interval; cash is measured at a particular date. |
| Filing date | When the company filed the document. It is separate from the period described. |
| Accession | The SEC identifier of a particular filing. It helps distinguish original filings and later amendments. |
| Retrieval time / vintage | When the application obtained source data. A historical retrieval cutoff restricts the analysis to evidence already captured by that time. |
| Capture | A complete archived source response with its URL, retrieval times, hash and byte count. A failed transfer is an attempt, not a complete capture. |
| Provenance | The trail from a displayed fact back to its archived source, filing, exact location and recorded transformation. |
| Unit and scale | What the number measures and how its written amount expands. A filing displaying `12` in millions represents `12,000,000` of the stated unit. |
| Semantic scope | What a fact includes: for example, the consolidated group, income attributable to the parent, or one share class. Equal amounts do not prove equal scope. |
| Missing / source nil | Missing means no usable fact was selected. Source nil means the source explicitly declares an absent value. Neither means zero. An actually reported zero remains zero. |
| Ambiguous | More than one incompatible candidate remains. The application retains the evidence instead of choosing an amount without a reviewed basis. |
| Quality flag | A recorded issue affecting interpretation or readiness. A blocking flag prevents an affected result from being used for valuation. |
| Restatement | A later correction of previously reported financial information. EquityEval preserves both versions and their filing dates. |
| Non-reliance event | A statement that specified prior financial information should no longer be relied upon. Its public date matters for historical interpretation. |
| As filed by date | Select eligible evidence filed by the chosen date. Later revisions cannot silently replace what was available then. |
| Original as filed | Request the original reporting version. A complete history review is needed before the application claims it found the original. |
| Latest reported | Select the eligible latest reporting version under the pinned evidence and review policy. This does not mean the underlying sources were fetched today. |
| Rerun / retry | A rerun is a new user request with preserved history. A retry is another worker attempt to finish the same request after a temporary failure. |
| Completed with gaps | Implemented stages finished, but some required evidence or capabilities remain unavailable. At S3, valuation is explicitly still pending. |

A number can be preserved and inspectable while still being unsuitable for a
valuation. For example, the archive may contain a revenue fact, but incomplete
filing or event history prevents a confident historical selection. Inspect the
quality flags, selected history mode and retrieval date together.

Adding a resolved stock currently creates a durable request through the internal
worker interface. The SEC worker archives and normalizes only reviewed mappings;
new or unsupported coverage requests stop with an explicit gap. The future
watchlist UI, full financial analysis, alert settings and illustrated instructions
will be added and verified before release.
