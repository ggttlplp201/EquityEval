# S2 design review

S1 was accepted on 2026-09-12 with the user's instruction to move to S2. The
proposal was then accepted for implementation by the instruction to continue with
the next part. The storage implementation and tests are now recorded below.

- [Implementation and validation](implementation.md): frozen migrations, runtime,
  source/vintage/PIT selection, queue operations and remaining milestones.
- [Schema proposal](schema-proposal.md): decisions S2-01–05, table fields/keys,
  missingness and time policies, watchlist jobs and later contract requirements.
- [Tests before implementation](test-plan.md): real KHC expected values plus
  source corrections, scope collisions, missingness and concurrent watchlist cases.
- [Domain glossary](../../../CONTEXT.md): consistent meanings for issuer, security,
  analysis request, execution, snapshot and model run.
- [W1 watchlist analysis](../../features/W1-watchlist-analysis.md).
- [U1 user manual](../../features/U1-user-manual.md).
- [N1 news/macro monitoring](../../features/N1-news-and-macro-agent.md), including
  [stock topic and assessment contracts](../../features/N1-stock-topic-monitoring.md)
  and the [CRCL example](../../features/N1-crcl-topic-example.md).

Recommended reading order: the five decisions at the top of the schema proposal,
then the point-in-time section and KHC expected pair. Detailed tables are there
for traceability; accepting S1 does not silently approve a schema not yet presented.
