# Filing schedules (development preview)

Open **Real-data pilot → Inspect CRCL’s application pipeline → Filing schedule**.
This is a saved manual scheduler check. **Background service not configured** is
literal: a stored active configuration does not mean a worker is running, and
opening the page never polls SEC. The bounded acceptance schedule is paused after
its one check. The older D4a filing check remains separately dated below it.

Read configuration state, saved-as-of time and health together. Expand the slot
for its cutoff, actual completion, outcome, coverage, prior baseline and manifest
hashes. Expand schedule history for immutable revisions and response evidence.
The scheduled-check totals and older D4a/D3f checkpoint totals have separate labels.

| Term | Meaning |
| --- | --- |
| Schedule / revision | A stable issuer/security/source-policy identity and an immutable version of its settings, actor and reason. |
| Active / paused | Active permits a due manual tick; paused blocks new claims/dispatches. Neither state proves a background service exists. A request already dispatched can still finish. |
| Slot | One scheduled check with a stable request key. Its identity does not change when execution is late or retried. |
| Cadence / jitter | The UTC interval and bounded deterministic delay used to spread due work. There is no local-time or daylight-saving shift. |
| Acceptance cutoff | The nominal slot time. Filings accepted after it are outside this comparison, even if retrieved later. It is separate from the actual HTTP request/completion. |
| Last eligible success | The latest complete filing comparison. An intervening error/incomplete check stays visible and does not replace the successful baseline. |
| Ready | Configuration readiness only; it does not mean live coverage or an installed worker. |
| Lag / missed interval | Work is overdue / a slot was not checked. Late recovery records missed ranges and makes one current check, not a burst of invented historical checks. |
| Attempt budget | Conservative reserved allowance for all transport/workflow retries; retained for 24 hours after resolution. Unused units are not refunded early. This differs from recorded dispatch attempts and the shared SEC rate cap. A dispatch record without a response can remain cancelled or unknown. |
| Backoff | An explicit wait after failures or rate limiting. Provider cooldowns are never shortened. |
| Rebase required | The approved scope has expired or a structural scope/history change needs review. No automatic window, form, resource or policy expansion is permitted. |
| Saved status | A timestamped audit, not a live worker heartbeat. Old source captures retain their original timestamps. |

A terminal incomplete/error poll is resolved for scheduling, retaining the last
eligible baseline. An ordinary transient incomplete result may be checked by a
later slot after backoff; newly required history resources or an expired window
require review. Unknown crash outcomes remain recorded. Repeating an ordinary
completed slot makes no HTTP call, but recovering a lost response can require
another bounded call; remote HTTP is not guaranteed exactly once across crashes.

The approved CRCL scope ends **September 21, 2026 UTC**. New dispatch after that
day is blocked, even for an older queued slot. There is no rebase writer in D4b.
Old manifests/captures remain available while a replacement scope awaits review.

## Operator: an explicit manual lifecycle

Use the canonical repository and configured application PostgreSQL/Redis stores.
All commands have this prefix:

```sh
.venv/bin/python scripts/project_python.py -m scripts.schedule_crcl_filings
```

1. `history --output var/d4b-before.json` saves preexisting row hashes, including
   D4a seed approvals and retained response descriptors.
2. `prepare --anchor <explicit-UTC-instant> --output var/d4b-config.json` writes
   the reviewed CRCL config. Anchor must be no earlier than its baseline. For
   the bounded tracer choose the next whole UTC minute and record it before
   execution. The configuration retains D4a's exact filed window and prior result.
3. `create --config var/d4b-config.json --key <stable-key> --output var/d4b-created.json`
   is an owner-only operation. It validates the exact approved CRCL config and
   writes schedule/revision history. Save the returned schedule UUID.
4. `tick --schedule <UUID> --output var/d4b-tick.json` reconciles prior work and
   materializes at most one due slot. Early, paused, blocked and repeated ticks
   cannot enqueue duplicate work. Save a returned request UUID when pending.
5. `run-slot --schedule <UUID> --request <UUID> --output var/d4b-run.json`
   executes that exact D4a request through W1 and the shared SEC limiter, then
   reconciles the result. It cannot force early, paused, expired or over-budget
   work. If a request remains queued/running, inspect its durable state rather
   than changing its key.
6. `pause --schedule <UUID> --epoch <current-revision-number> --key <stable-pause-key>
   --output var/d4b-paused.json` appends a revision. `resume` has the same arguments,
   remains subject to backoff/budget/scope, and does not itself fetch.
7. `inspect --schedule <UUID> --before var/d4b-before.json --output <audit.json>`
   uses a read-only transaction to verify retained evidence and export sanitized
   health, history and completed monitor audits.

Creation and pause/resume use the configured owner connection. Tick, execution
and inspection use the runtime role; runtime cannot edit configurations or
baselines directly. Repeating a revision operation key returns that original
transition; it does not apply it again after a later change. Changed contents
under an old key are rejected. Always inspect the current revision afterward.

A lost/expired execution lease follows W1 recovery with a bounded backoff and
attempt limit. Successful captured resources are replayed. A paused slot keeps
its exact request; resume does not change its plan. New cadence/anchor/scope/policy
requires a separately reviewed replacement/rebase; this tracer only revises
active state, jitter, budget and lag threshold for future slots.

The UI exporter reads a pinned audit without database/network access. Optional
current application verification is explicit and read-only:

```sh
.venv/bin/python scripts/project_python.py -m scripts.export_scheduler_snapshot --check --verify-application
```

Filing discovery does not register a quote, normalize financial statements,
refresh valuations, publish results, manage production watchlists, monitor stock
news/CPI/PPI/Fed events, or send in-app/desktop/email notifications. Those retain
their separate reviewed prerequisites in the operational roadmap.
