# Argus IRIS

See beyond the symptoms. An IRIS-hosted operational investigation portal.

## Implementation status

Under active implementation. See [implementation record](docs/IMPLEMENTATION_STATUS.md).
The specifications are in `spec/`; `spec/iris.agent.md` is the supplied engineering authority.

## Runtime

Browser → IRIS Community 2026.2 Web Gateway → `/argus` → `%SYS.Python.WSGI`
→ Flask/Jinja → Embedded Python → SysAdmin v2 / native IRIS / IRIS SQL.
Application namespace and database: `ARGUS`. No standalone Python web server.

## Local development

Docker Desktop with Linux containers is required.

```sh
docker compose build
docker compose up -d --wait
docker compose exec -T -e ARGUS_LLM_MODE=mock iris sh /opt/argus/scripts/test.sh
```

Open http://localhost:52773/argus/ using an IRIS account. The Community image's
initial development account is `_SYSTEM` with password `SYS`; passwords are
unexpired for this local development image. Only localhost is published.
This is a development setup; configure non-default accounts and TLS for deployment.
No role escalation is configured on the Argus web application.

## AI during development

Compose uses `ARGUS_LLM_MODE=auto`: with no key, explanations are deterministic
mock responses and make no external requests. `ARGUS_LLM_MODE=mock` forbids LLM
calls even if a key is present. Tests use fake transports; no real OpenAI or
embedding requests are made. The collector never invokes the LLM.

Open an incident, choose **Explain this incident**, and generate a simulated
explanation. The incident's classification and evidence remain independent of AI.

For the later live validation, copy `.env.example` to `.env`, fill in
`OPENAI_API_KEY`, and run `docker compose up -d --force-recreate --wait`.
With `auto`, adding the key selects the OpenAI adapter. The model is configurable
with `ARGUS_LLM_MODEL`. Only an explicit explanation request sends a restricted
incident summary to the [Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create).
Provider errors leave evidence accessible. No raw process variables, global
contents, credentials or action tools are supplied to the model.
The real API connection has only been tested with a fake HTTP transport; paid
validation is intentionally deferred. IRIS Wallet integration remains pending.

## Evidence and investigation

The overview links current collection state to preserved incidents. Process and
lock investigators use the official SysAdmin API; lock waiter enrichment uses
`%SYS.LockQuery.Detail`. Process detail is loaded on demand. Namespace/global
resolution uses `%SYS.Namespace.GetGlobalDest`; global sizing uses the verified
stochastic `GetGlobalSize(fast=2)` mode.

`ArgusCollection` runs once per minute under a generated local collector account.
It preserves process/lock snapshots and evaluates lock persistence and impact.
Database size collection is hourly. A configured global watchlist is bounded to
20 globals and defaults to empty. Collector configuration is stored as JSON in
`Argus.Configuration`, record `collector`, in namespace `ARGUS`.

Baselines compare the same weekday and 15-minute local time bucket over 30 days,
excluding the most recent 24 hours. Fewer than five observations is learning mode.
Verified impact or unusual volume must persist for 60 seconds; recovery has a
60-second grace period. Missing polls do not establish persistence or recovery.
These intervals and retention can be adjusted in the collector configuration.

Incidents retain their timeline after processes exit. Incident, lock, behavior and
growth reports support HTML, JSON and CSV. Growth needs actual historical samples
at the requested horizon; a new installation reports insufficient history.
Report bounds are shown on screen. Global estimates are not a complete database
inventory, and private-global blocks are not converted into unverified byte totals.

The `argus-evidence` Docker volume preserves the ARGUS database across container
recreation. `docker compose down` preserves this volume; removing the volume
discards evidence. Back it up before any intentional reset.

## Validation and demo

The test command above runs pytest **inside IRIS Embedded Python**, then exercises
live WSGI routes and exports over HTTP. It fails if the embedded success marker is
missing, even when an IRIS session exits with code zero. The HTTP test refuses to
submit an explanation if a real provider is active.

`tests/fixtures/ArgusLock.mac` provides bounded owner/waiter jobs for local lock
contention acceptance testing. It uses only `^ArgusDemo("acceptance")` and exits
automatically. Load the fixture in ARGUS and run `^ArgusLock` and
`Waiter^ArgusLock` as separate jobs. Follow Overview → Incident → preserved
timeline → reports after the fixture exits. The deterministic tests also cover
normal noon peaks, unusual night volume, normal-volume impact, missing polls,
resolution and timestamp-based growth.

## Scope and remaining work

The six management families have live read coverage. Application description
edits and task run/suspend/resume use explicit user-bound confirmation and record
action events. Process termination and lock deletion are not exposed.
Authorization comes from the requesting IRIS user; historical views require
`%Admin_Operate`. The collector has explicit table grants, not `%All`.
On IRIS 2026.2, the installed database API requires `%Admin_Manage:USE` even
for listing, contrary to the published Operate alternative. This broader
administrative resource is not granted automatically. Storage collection reports
unavailability when the collector lacks permission; process/lock collection
continues. An administrator must explicitly authorize any additional service
account privileges before scheduled storage collection can run on this version.

This is an implementation in progress, not a claim that every specification phase
is complete. Remaining items include full task behavior collection, broader
administrative editing, HTMX updates and visual acceptance, IRIS Wallet credentials,
optional vector retrieval, and a validated IPM package. Docker is the validated
deployment path; `module.xml` is currently metadata only.

## Contract

The official [SysAdmin v2 specification](https://github.com/intersystems-community/sysadmin-api-specification/blob/master/mainspec_v2.json)
is captured in `docs/contracts/mainspec_v2.json`. Endpoint contracts must be checked
against this source and real IRIS responses. Missing data must never be fabricated.
