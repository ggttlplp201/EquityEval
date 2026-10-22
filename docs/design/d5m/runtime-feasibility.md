# D5m runtime feasibility — read-only observations, 2026-10-22

No cloud workload, release upload or SEC request has been executed.

- Canonical tree started clean at f618ce9130c7925ef7bfba075aefc06c390c9168.
- Vercel connector team list empty; this agent's project list contains only
  the-table, garderobe and do-mus-mat-v2, not EquityEval. Those projects were not
  modified. Another coordinator connection returned an empty project list;
  connection scope is not assumed interchangeable.
- No local gh/vercel/sandbox executable found on PATH or the checked usual gh paths.
- Existing Git uses osxkeychain. A private in-memory credential-helper read enabled
  read-only GitHub REST; no credential was printed or written.
- GET /repos/ggttlplp201/EquityEval: HTTP200, public, default main, active repository,
  credential permissions include admin/maintain/push/pull.
- GET /repos/ggttlplp201/EquityEval/actions/permissions: HTTP200, enabled true,
  allowed_actions all. The proposed workflow will pin actions despite account
  sha_pinning_required false.
- GET /repos/ggttlplp201/EquityEval/actions/workflows: HTTP200, one active checks
  workflow, ID365458842, .github/workflows/ci.yml; existing Ubuntu24.04 CI.
- GitHub docs require manual-dispatch workflow on default branch. The proposal
  instead uses two explicit execution-ref pushes, with no main change.
- Public-repository visibility is compatible with GitHub's documented artifact
  attestation availability; actual signing/execution entitlement remains unproved.
- SEC licence register explicitly allows retention/redistribution for defined
  SEC public-filing scope with attribution. Transfer excludes other sources/secrets.

Not yet established: working cloud execution, kernel/cgroup/process limits,
network denial, exact Poppler26.05.0 Linux build/digest, pypdf6.10.0 wheel digest,
complete dependency pins, input transfer, artifact signing/verification, or PDF
content. These require staged implementation review and a synthetic-only proof run
before any source retry or real-document interpretation.
