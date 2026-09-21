# Local application storage

Verified 2026-09-21. Separate persistent application services; this is not a
production deployment or permission to activate a data provider.

| Service | Port | Storage | Control |
| --- | --- | --- | --- |
| Application PostgreSQL 16.14 / TimescaleDB 2.28.1 | 5433 | `var/application-postgres16/data` | `scripts/app_postgres.py` |
| Application Redis (installed host binary; verified 8.8.1) | 6380 | `var/application-redis` | `scripts/app_redis.py` |
| Disposable test PostgreSQL | 55432 / 55433 | Existing test directories | Existing test helpers |
| Disposable test Redis | 16380 | `var/test-redis` | Existing test helper |

## Run and inspect

After normal repository setup, configure `.env` with the existing application
DATABASE_URL and REDIS_URL. Never include credentials in a handover or commit.
The native helpers accept only loopback5433/6380; Redis uses database0, with the
existing local unauthenticated URL. Authenticated or remote Redis configurations
are explicitly refused by this bounded native helper rather than overwritten.
The database requires its own non-owner login and password.

```sh
make app-db-start
make app-db-migrate
make app-db-inspect
make app-redis-start
make app-redis-status
```

PostgreSQL copies only the previously built, pinned executable installation
referenced by `var/test-postgres16-timescale/installation.json`. If absent, run
`make test-db-setup-timescale` to build it first. No test data is copied, migrated,
claimed or deleted. The new cluster has a separate owner record, data directory,
private Unix socket and executable-copy provenance. It binds only 127.0.0.1.

This private PostgreSQL build has no TLS and is restricted to this local host.
Owner migrations use Unix peer authentication. The application login uses TCP
SCRAM and receives the existing restricted `equity_runtime` role; it is not the
cluster owner or a superuser. Migration reruns report the actual applied revision.
Failed command output redacts exception text that could contain credentials.

Redis binds only 127.0.0.1 and writes an append-only file with `appendfsync always`
and no eviction. This retains the shared SEC limiter's state and cooldowns across
restarts. It does not enable polling. All future SEC workers must use the existing
`RedisRateLimiter` identity/configuration, never independent per-worker budgets.

```sh
make app-db-stop
make app-redis-stop
```

Stop commands preserve data. No helper has a delete/reset/flush action. They check
ownership and runtime identity before controlling a service, and refuse occupied
foreign ports, mismatched records and symlinked controlled paths. Startup waits
for Redis to finish loading AOF; port probes tolerate a stopped server's TCP
TIME_WAIT sockets while still refusing active listeners.

Do not start Compose and native application services on the same ports. Compose
remains a separate alternative. There are no new background launch/login services.

## Data readiness

The initial application inspection found zero policy, issuer, security, mapping,
capture and normalization rows. Applying migrations creates structure, not
financial evidence. This checkpoint inserted no provider policies or domain rows.
The D2 pilot remains the existing archived observation view.

The [bootstrap review](s3/identity-bootstrap-proposal.md) explains the concrete
first-capture dependency and proposed W1/S3 extension. Old S1 archives retain their
actual metadata: unknown request/completion times cannot become invented values.
After that review, follow the existing SEC archive/publication/PIT path, complete
scope/precision/non-reliance checks, finish eligible S5, then review and build S6.
