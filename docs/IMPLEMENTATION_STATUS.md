# Argus IRIS implementation record

Authority: `spec/iris.agent.md` (the supplied AGENT document), `spec/SPEC.md`,
the official SysAdmin contract, `spec/IMPLEMENTATION_PLAN.md`, `spec/PRODUCT_UX.md`.

## Plan and boundaries

1. Remove sample application and establish IRIS Community 2026.2, namespace/database
   ARGUS, `/argus` native WSGI, Flask and Embedded Python. Validate real HTTP first.
2. Centralize official SysAdmin v2 access, with per-user authorization; implement
   the six administrative areas, then lazy Process and Lock Investigators.
3. Persist bounded snapshots, baselines, incidents and evidence in ARGUS IRIS SQL.
   Schedule Python collection with IRIS Task Manager. Add deterministic lifecycle tests.
4. Resolve storage topology, estimate global growth, add reports and operational UX.
5. Add optional evidence-only explanation with mocked LLM responses by default.
   No OpenAI calls or paid embeddings during implementation/testing. Real provider
   activation is deferred until credentials are supplied and validation is requested.
6. Validate packaging, build, startup, live integration, logs and document limitations.

Runtime: Browser → IRIS Web Gateway → %SYS.Python.WSGI → Flask/Jinja →
Embedded Python → SysAdmin HTTP/native IRIS APIs/IRIS SQL. No external app backend.
Dependencies: Flask, requests, pytest for tests; HTMX for progressive UI updates.
Secrets: never committed; LLM credentials remain server-side. Default AI mode is mock.

## Validation

2026-09-19: All four supplied specifications read. Repository is the unmodified
development template, apart from user-supplied `spec/`. Docker Desktop Linux engine
27.2.0 accessible; IRIS Community 2026.2 image downloaded. Official SysAdmin
`mainspec_v2.json` captured under `docs/contracts/` for contract tests.
No phase is yet accepted. Real runtime validation is required before advancement.

## Phase 0/1: COMPLETE

Sample classes/tests and unused deployment workflows removed. ARGUS database and
namespace configured. Native WSGI properties validated on 2026.2: WSGIType is 1
(the older article's 0 is invalid). Docker build and startup pass. Container healthy.
`python3 -m pytest -q`: 1 passed. Real authenticated HTTP `/argus/` and `/argus/health`:
200; health reports Embedded Python and IRIS 2026.2 Build 221U. `/api/admin/info`,
`/v2/processes`, `/v2/locks`: 200 with live data. messages.log/WSGI log inspected.
No external Python server. Phase 2 now in progress.

Contract findings: `/v2/lock` has DELETE only (detail comes from list);
audit records uses POST and returns 202 with Location; task identifiers use `id`,
history uses `taskId`; SQL privileges require grantee and namespace.

## Phase 2: COMPLETE (minimum scope)

Six live areas exercised through `/argus/view/`: applications, users/roles/resources,
Wallet metadata, tasks, system and logs/audit. All return 200. Application detail,
task detail and SQL privilege query return 200. Description edit of `/argus` was
confirmed and read back successfully. Adapter/auth/confirmation tests: 10 passed.
System resource endpoint returns a list (not an object); renderer corrected and
retested. Optional certificates/OAuth and unsupported REST discovery are omitted.
No shared administrative service credentials; SysAdmin uses the requesting user's
Authorization header. Empty Wallet returns an explicit empty state.

## Phases 3/4: COMPLETE (read-first investigators)

Real bounded ArgusLock fixture loaded and executed. SysAdmin /v2/locks returned
^ArgusDemo and its owner. Both lock and process detail routes returned 200.
%SYS.LockQuery.Detail was verified to return the actual waiter PID; matching requires
physical reference, owner and local ownership. No inferred transaction age or fake
blocking graph. Destructive process/lock actions intentionally remain unexposed.

## Phase 5: COMPLETE (core lock lifecycle)

21 tests passed inside Embedded Python, including real SQL lifecycle with rollback.
Task Manager ArgusCollection ran as ArgusCollector and returned Success. Explicit
SQL grants fixed its initial permission error; no %All role was added. Real contention
created one HIGH incident for a verified waiter after >60 seconds. It resolved after
the condition cleared and the grace period passed. Four timeline entries remained;
JSON, CSV and HTML reports returned 200. An IRIS numeric timestamp conversion in
HTML was corrected. Evidence survived container recreation through argus-evidence.

## Phase 6: core storage integration validated; extensions in progress

Namespace/global root resolution and Config.MapGlobals listing returned 200 on
ARGUS. %Library.GlobalEdit.GetGlobalSize(fast=2) was exercised on ^ArgusDemo;
allocated/used MB persisted. Database size source is /v2/database-dirs (not the
configuration-only /v2/database-dir). Hourly database and configured global watchlist
collection added. Growth and IRISTEMP routes return 200. Subscript-level resolution
is explicitly outside the root-global form; no bytes inferred from PPG block counts.

## Continuation validation — 2026-09-20

- Optional mock incident explanation implemented. Auto mode uses mock without a
  key; explicit mock ignores any key. OpenAI Responses adapter tested only with
  fake transport. No real API request or embedding call was made.
- Overview displays actual active incidents, recent history and stale collection.
  Active incident recovery no longer depends on the latest-100 history limit.
- Lock, behavior and growth reports added in HTML/JSON/CSV; export bounds are
  explicit. CSV formula-like cells are escaped. Human action events are recorded.
- Final restart validated: 35 tests passed inside Embedded Python, followed by
  29 HTTP route/export checks and preserved incident exports plus a mock
  explanation. Includes task snapshots and storage status changes. Container
  health and ARGUS_INSTALL_OK confirmed; existing incident evidence survived.
- Fixed empty SQL aggregate handling and case-sensitive global history. Regression
  tests exercise both: IRIS returns empty string for a missing aggregate and
  default SQL string collation can uppercase DISTINCT projections.
- Actual scheduled storage collection revealed an authorization mismatch:
  `%Api.Admin.Endpoints.Database.ConfigCRUD.ResourcesOR` on 2026.2 returns only
  `%Admin_Manage`. Published specification also advertises `%Admin_Operate`.
- Automatic approval review rejected adding `%Admin_Manage:USE` to the collector.
  The privilege change was removed. User approval is pending. Storage status is
  now recorded separately; a storage 403 does not fail successful process/lock
  collection. Do not claim automated database collection is validated yet.
- `.env` and variants excluded from Git/Docker context. Added portable LF rules
  and a single `scripts/test.sh` entry point used by CI.
- Visual browser acceptance remains unverified: authenticated URL was rejected
  for credential exposure; normal URL failed in the integrated browser. HTTP
  authenticated checks succeeded. No browser security restriction was bypassed.

## Remaining scope

IPM packaging remains metadata only; Docker is the tested path. Full task behavior
baselines, HTMX/visual acceptance, Wallet-backed LLM credentials and optional
IRIS vector retrieval remain incomplete. Live OpenAI validation is intentionally
deferred by the user. Do not describe the complete specification as delivered.
