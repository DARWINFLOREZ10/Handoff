# ADR 001 Async boundary

## Context

A workflow step that runs inside the request is lost when the client disconnects, and it holds the database while waiting on the network. A tenant id in a header, without a membership row, is not isolation.

## Decision

`POST /workflows/{id}/runs` inserts the run, the job, and the audit row, then commits once. Only after that commit does the API ask Celery to deliver the job. The worker locks the job, POSTs `definition.url` with `Idempotency-Key` set to the job id, and commits the outcome. A failed attempt goes back to `queued` until `attempts` reaches `max_retries` (3). A succeeded or failed job is not sent again.

Every route that takes `X-Tenant-ID` loads a membership for that user. Missing organization is 404. An organization the user does not belong to is 403.

## Consequences

The request can return while the step is still queued. If the broker is down, the job stays queued and the error is logged; the run is not rolled back. A crash during the POST, before the worker commits, leaves the job `queued` and can send the HTTP call again. The idempotency key is how the receiver deals with that. The lock is held for the duration of the one HTTP call, which is acceptable for a single worker and the wrong shape for a pool of workers. There is one step type. There is no scheduler, OAuth, report, or API-key surface in this repository.
