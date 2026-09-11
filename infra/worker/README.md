# Worker reservation

Ingest scheduling is added after the S3/S4 source contracts are stable.
No idle container or pretend worker is started in S0. The eventual scheduler
must support idempotency, explicit backfills, retries, dead letters and shared
per-source rate limits (SPEC 1.4).
