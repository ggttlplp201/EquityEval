# Kraft Heinz restatement candidate

Status: filing evidence verified; Company Facts mapping and fixtures pending.
CIK: 0001637459. Observation: FY2017 net income attributable to Kraft Heinz,
period ended 2017-12-30. All amounts below are USD millions as presented in filings.

| Version | Value | Accession | Filed | SEC-displayed acceptance |
| --- | --- | --- | --- | --- |
| Original FY2017 10-K | 10,999 | 0001637459-18-000015 | 2018-02-16 | 2018-02-16 12:39:26 |
| FY2017 comparative in FY2018 10-K | 10,941 | 0001637459-19-000049 | 2019-06-07 | 2019-06-07 17:07:36 |

Sources: [original index](https://www.sec.gov/Archives/edgar/data/1637459/000163745918000015/0001637459-18-000015-index.htm),
[revised index](https://www.sec.gov/Archives/edgar/data/1637459/000163745919000049/0001637459-19-000049-index.htm),
[original income statement](https://www.sec.gov/Archives/edgar/data/1637459/000163745918000015/R2.htm).

The reconciliation attributes a 58 reduction to error restatement and zero to
ASU adoption for this line. The errors included supplier-arrangement recognition
timing and other corrections. This is explicitly an ASC 250 error restatement.
Cost of products sold is a less clean fixture: 16,529 becomes 16,485 through error
correction, then 17,043 after a separate pension-presentation recast.
[Restatement note](https://www.sec.gov/Archives/edgar/data/1637459/000163745919000049/R9.htm)

A May 6, 2019 8-K reports non-reliance determined May 2 and preliminary unaudited
revisions. Preserve that event separately from the June audited comparative.
[Non-reliance filing](https://www.sec.gov/Archives/edgar/data/1637459/000163745919000033/may2019form8-k.htm)

## Proposed later regression

After verifying the exact API rows and any intermediate versions, pin both
amounts with their original units, intervals and accessions. Choose cutoffs that
exclude the later version in the earlier query, and verify the later query can
select the revised value. This is a proposed test design, not an executed test.

Pending: actual raw tag, unit scale, start date, fy/fp behavior, repeated values,
intermediate filings and the exact cutoff policy. Parent-attributable income
must not be confused with consolidated income including noncontrolling interests.
`us-gaap:NetIncomeLoss` is a candidate to inspect, not a confirmed mapping.
