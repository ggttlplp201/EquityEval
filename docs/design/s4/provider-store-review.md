# S4 provider-store correctness review

Reviewed against the accepted D019 / S4-01–04 contract. Implementation date:
2026-09-19. This is the scoped provider-store implementation review, not the
independent final milestone review.

## Findings resolved

1. **SEC policy exemption could associate a response with the wrong issuer or
   filing.** The original SQL checked URL and object-key formats independently.
   Seven regression cases reproduced a mismatch being accepted. The exemption
   now binds exact CIK, accession, and filename, and retains the existing SEC
   transport behavior.

2. **Shared ingestion could misattribute a market response to another provider.**
   Calling the existing SQL preparation or capture entry point directly bypassed
   the Python descriptor check. Twenty-four regression cases reproduced
   acceptance of mismatched origins, symbols, observation objects, or
   credential-bearing public URLs. The shared guards now recognize Treasury,
   Tiingo, and FRED object keys, endpoint URLs, and registered source origins.
   Recognized observation objects require their canonical endpoint; metadata
   requires the same registered provider origin and reviewed raw scope.
   Alternate endpoint spellings cannot be relabelled as metadata. Unknown
   fictional source/URL/object triples remain supported by older generic tests.

3. **Retries could exceed a logical resource's three-attempt budget.** Provider
   preparation now counts every prepared attempt for the immutable W1 request,
   source, object, and parameter hash, across all stages and execution attempts.
   A new logical-fetch UUID, worker, or store does not erase reservations.

4. **Tiingo account consumption could disappear after coordinator restart.**
   Every preparation reserves one request and the maximum permitted wire bytes
   under a source advisory lock. Rolling one-hour, one-day, and 31-day counts,
   distinct symbol counts, and byte reservations use persisted attempts,
   including cancellations and interruptions. Concurrent connections cannot
   both consume the last available reservation. A reviewed quota is required.

5. **Naive evidence timestamps could acquire the database session's timezone.**
   Explicitly timezone-aware dispatch, response-header, and completion times are
   now required, matching the existing S3 evidence contract.

6. **Operational disable must not prevent retaining an authorized response.**
   New preparation and dispatch require current activation. Finalization and
   replay validate the exact historical grant with activation disabled; hashes,
   policy identity, and resource identity remain checked. This behavior is
   covered by an archive-backed completion and replay test.

## Scope and remaining integration checks

The provider store enforces concrete resource types, registered source identity,
immutable W1 source/date/series/quote intent, current FRED wire vintage anchored
to the request's UTC date, and pre-provisioned full-window quote bindings.
Prepared operations commit before HTTP; the store owns no transaction during
network work.

The SQL URL guard validates public source and resource identity. Request
parameter meaning is additionally checked by the typed resource/W1 adapter and
publication boundary. The parameter hash alone is not represented as decoded
request parameters in the existing attempt table.

Quotas are per configured source account identity. Review and provisioning must
use one source identity for an account; this implementation does not invent a
cross-account credential registry. It performs no live source activation or
network research.

Focused validation passed on the real Timescale profile: 112 provider-store,
market-storage, and existing SEC transport tests; then five additional tests
covering authenticated redirects, reflected header/body/compressed credentials,
conditional reuse, and replay. Ruff and mypy pass for the provider store. The
final milestone log records the complete suite. Coverage includes
actual Timescale migration, SQL entry-point bypass tests, existing SEC transport
regressions, concurrent reservations, retries, archives, disabled policies,
and timezone checks. All HTTP in these tests is fictional or absent.
