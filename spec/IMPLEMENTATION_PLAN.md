# OPORD ARGUS-IRIS-001 — Implementation Plan

**Classification:** DEVELOPMENT / INTERNAL  
**Project:** Argus IRIS  
**Execution model:** Sequential milestones with mandatory exit criteria  
**Primary executor:** Claude Code / Codex / engineering agent  
**Authoritative engineering doctrine:** `AGENT.md`  
**Authoritative product contract:** `SPEC.md`  
**Supporting UX contract:** `PRODUCT_UX.md`

---

# 1. SITUATION

## 1.1 Operational environment

Argus IRIS is being built for the InterSystems Programming Contest: **Build Your Own Management Portal**.

The official task requires a GUI powered by InterSystems IRIS management APIs for:

1. Web Applications / REST APIs;
2. Permission Management;
3. Security and Secrets;
4. Task Management;
5. Operating System / runtime management;
6. Logs.

The contest announcement also allows additional screens/actions.

An official contest-team response states that an alternative application is valid **“as long as it implements these calls”**, followed by the six areas above.

**Operational consequence:** all six areas receive functional coverage. Engineering depth is concentrated on runtime investigation.

Official reference:

- https://community.intersystems.com/post/intersystems-programming-contest-build-your-own-management-portal

SysAdmin contract:

- https://github.com/intersystems-community/sysadmin-api-specification/blob/master/mainspec_v2.json
- https://raw.githubusercontent.com/intersystems-community/sysadmin-api-specification/master/mainspec_v2.json

## 1.2 Friendly capabilities

Available and approved capabilities:

- InterSystems IRIS Community Edition 2026.2;
- InterSystems SysAdmin API v2;
- Embedded Python;
- `%SYS.Python.WSGI`;
- Flask/Jinja/HTMX;
- `iris.cls()` / `iris.gref()` / IRIS SQL;
- IRIS Task Manager;
- IRIS Wallet;
- IRIS Vector Search in optional phase;
- Docker;
- ZPM/IPM.

Source template:

- https://github.com/intersystems-community/intersystems-iris-dev-template

## 1.3 Primary threats

Treat the following as engineering threats:

### THREAT A — Scope expansion

Symptoms:

- building a full replacement Management Portal;
- adding every SysAdmin endpoint;
- spending time on visual polish before live IRIS integration;
- adding SQL Doctor/AI/vector features before Process/Lock flow works.

Countermeasure:

> Execute P0 before P1. Execute P1 before P2.

### THREAT B — Unsupported capability invention

Symptoms:

- invented SysAdmin path;
- assumed IRIS class/method;
- fabricated lock waiter relationship;
- unsupported log access.

Countermeasure:

> Verify against `mainspec_v2.json`, official docs or target runtime before coding the capability.

### THREAT C — Architecture drift

Symptoms:

- standalone Flask server;
- Java/Quarkus service;
- external database;
- Redis/background worker;
- custom ObjectScript business logic.

Countermeasure:

> Follow `AGENT.md` and `SPEC.md`: IRIS-hosted WSGI + Embedded Python.

### THREAT D — False completion

Symptoms:

- scaffold exists but was never run;
- endpoint written but never exercised;
- Docker builds but runtime fails;
- host Python imports succeed but IRIS Embedded Python imports fail.

Countermeasure:

> No phase is complete until its exit criteria and smoke tests pass on the actual runtime.

### THREAT E — Alert noise

Symptoms:

- static thresholds classify normal peaks as incidents;
- every anomalous sample creates an incident;
- one incident per polling cycle.

Countermeasure:

> Implement baseline + persistence + impact + deduplication before claiming incident intelligence.

---

# 2. MISSION

The engineering agent will build **Argus IRIS**, a functional IRIS-hosted Management Portal with minimum coverage of all six contest task families and deep runtime troubleshooting capabilities, using **100% Embedded Python for custom server-side logic**, the official SysAdmin API v2 as the administrative contract, and native IRIS APIs only for verified diagnostic enrichment.

The mission is complete when:

- the project builds from a clean repository;
- Docker starts IRIS Community Edition reproducibly;
- `/argus` runs through `%SYS.Python.WSGI`;
- all six contest areas have real IRIS-backed functionality;
- Process Investigator and Lock Investigator work end-to-end;
- Argus can preserve selected evidence as incidents;
- temporal context can distinguish normal from abnormal workload;
- reports remain understandable after live evidence disappears;
- P0/P1 tests and smoke checks pass;
- README accurately documents the finished product.

---

# 3. EXECUTION

## 3.1 Commander's intent

### Purpose

Deliver a Management Portal that is contest-compliant but differentiated by operational investigation, not by the quantity of CRUD forms.

### Key tasks

1. establish a reproducible IRIS/Embedded Python/WSGI runtime;
2. centralize SysAdmin API access;
3. cover all six official Management Portal areas at minimum usable depth;
4. build Process Investigator;
5. build Lock Investigator;
6. preserve historical evidence;
7. implement temporal baseline/anomaly/incident logic;
8. implement namespace/storage/growth investigation;
9. implement reports;
10. harden packaging, tests and documentation;
11. execute Vector Search / AI only after the core is stable.

### End state

An evaluator can start Argus, generate or observe a runtime condition, trace it through IRIS context, preserve it as an incident, and review a report without external backend infrastructure or an LLM.

---

## 3.2 Rules of engagement

These instructions apply to every phase.

### ROE-1 — Source hierarchy

Use:

```text
AGENT.md
  > SPEC.md
  > current mainspec_v2.json
  > IMPLEMENTATION_PLAN.md
  > PRODUCT_UX.md
```

### ROE-2 — No invented IRIS behavior

If not verified:

```text
mark UNVERIFIED
spike/test it
or omit it
```

Do not simulate a primary production capability merely to complete a screen.

### ROE-3 — No phase skipping

A later phase may perform a limited spike only when required to unblock an earlier phase.

Do not implement P2 intelligence while P0 runtime paths are broken.

### ROE-4 — Live integration first

Use mocks only in unit tests.

Milestone acceptance requires real IRIS-backed smoke tests.

### ROE-5 — Destructive actions

No destructive action without:

```text
privilege check
+ target display
+ explicit human confirmation
+ result verification where possible
```

### ROE-6 — No autonomous AI actions

LLM output is advisory only.

### ROE-7 — Keep the repository clean

At every phase:

- remove obsolete template artifacts;
- do not leave dead implementations;
- do not create duplicate clients/services for the same responsibility;
- update tests and docs with behavior changes.

---

# 4. CONCEPT OF OPERATIONS

Operations proceed in ten phases.

```text
PHASE 0  Reconnaissance and template sanitation
PHASE 1  Establish IRIS/WSGI foothold
PHASE 2  Establish SysAdmin control plane + contest minimum
PHASE 3  Runtime intelligence — Processes
PHASE 4  Runtime intelligence — Locks
PHASE 5  Historical intelligence — Baselines and Incidents
PHASE 6  Storage intelligence — Topology, Growth, IRISTEMP
PHASE 7  Reports and operational UX
PHASE 8  Bonus intelligence — Vector Search and DPI-I-574
PHASE 9  Packaging, hardening, final validation
```

No phase advances without exit criteria unless a documented blocker forces controlled parallel work.

---

# 5. PHASE 0 — RECONNAISSANCE AND TEMPLATE SANITATION

## Objective

Understand the clean IRIS template and remove assumptions before product code is introduced.

## Tasks

1. clone a clean copy of `intersystems-iris-dev-template`;
2. read completely:
   - `AGENT.md`;
   - `SPEC.md`;
   - `PRODUCT_UX.md`;
   - this OPORD;
3. inspect template infrastructure listed by `AGENT.md`;
4. identify:
   - image/version;
   - namespace/database;
   - existing Web Applications;
   - Docker ports;
   - installation flow;
   - sample packages/classes/tests;
5. choose intentional Argus names:
   - module;
   - namespace;
   - Python package;
   - Web Application path `/argus`;
6. remove sample code that does not belong;
7. document repository structure before implementation.

## Technical references

- Template: https://github.com/intersystems-community/intersystems-iris-dev-template
- Agent repository inspection doctrine: `AGENT.md`, sections 1, 5, 6, 7, 8.

## Exit criteria

- [ ] no accidental sample application remains;
- [ ] target namespace/database is explicit;
- [ ] `/argus` is reserved as application path;
- [ ] Docker/runtime architecture matches `SPEC.md`;
- [ ] no Java/external backend was introduced;
- [ ] repository names are Argus-specific.

## No-go conditions

Do not proceed if:

- template runtime cannot build/start;
- target IRIS version is unresolved;
- package/namespace naming is still ambiguous.

---

# 6. PHASE 1 — ESTABLISH IRIS/WSGI FOOTHOLD

## Objective

Prove that Argus Python executes inside the actual IRIS Embedded Python runtime through `%SYS.Python.WSGI`.

## Tasks

1. add the minimal Python package;
2. create WSGI entry point;
3. add Flask/Jinja dependency only to IRIS Embedded Python environment;
4. configure `/argus` Web Application;
5. configure:
   - `DispatchClass = %SYS.Python.WSGI`;
   - WSGI application location;
   - module/callable;
6. add `/argus/health` or equivalent;
7. expose diagnostic build/runtime version information without secrets;
8. verify startup and import logs;
9. add first HTTP integration test.

## Technical references

- WSGI Support Introduction: https://community.intersystems.com/post/wsgi-support-introduction
- Running WSGI Applications with IPM: https://community.intersystems.com/post/running-wsgi-applications-ipm
- Embedded Python core: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GEPYTHON_reference_core
- Run Embedded Python: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GEPYTHON_runpython
- `%SYS.Python`: https://docs.intersystems.com/irisforhealthlatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.Python&LIBRARY=%25SYS
- Agent WSGI doctrine: `AGENT.md`, section 2.6.

## Mandatory smoke test

```text
HTTP request
→ IRIS Web Application /argus
→ %SYS.Python.WSGI
→ Flask callable
→ Embedded Python code executes
→ HTTP 200
```

## Exit criteria

- [ ] Docker build succeeds;
- [ ] IRIS starts and remains healthy;
- [ ] `/argus` responds through IRIS WSGI;
- [ ] Flask imports from Embedded Python environment;
- [ ] no standalone Flask/Gunicorn/Uvicorn process exists;
- [ ] startup logs contain no unresolved Python import/dispatch errors.

## No-go conditions

Do not proceed if `/argus` works only through host Python or a separate Python server.

---

# 7. PHASE 2 — ESTABLISH SYSADMIN CONTROL PLANE AND CONTEST MINIMUM

## Objective

Create one tested SysAdmin adapter and achieve real functional coverage of all six official contest areas.

## Tasks — Control plane

1. implement `SysAdminClient` or equivalent;
2. centralize:
   - base path `/api/admin`;
   - authentication/session handling;
   - timeouts;
   - error normalization;
   - privilege errors;
   - JSON parsing;
3. add adapter tests for:
   - 200;
   - 400;
   - 401;
   - 403;
   - 404;
   - timeout/unavailable server;
4. verify target paths against current `mainspec_v2.json`.

## Tasks — Six contest areas

### Applications & REST

Implement minimum usable flow:

- list;
- details;
- safe edit where supported;
- REST/OpenAPI information when discoverable.

Relevant SysAdmin paths:

- `/v2/web-apps`
- `/v2/web-app`

### Permissions

Implement:

- users;
- roles;
- resources;
- SQL privileges.

Relevant paths:

- `/v2/security/users`
- `/v2/security/roles`
- `/v2/security/resources`
- `/v2/security/sql-privileges`

### Security & Secrets

Implement:

- Wallet collection/secret metadata;
- audit;
- only verified certificate/OAuth functions needed for reasonable contest coverage.

Relevant paths:

- `/v2/wallet/collections`
- `/v2/wallet/secret`
- `/v2/wallet/secrets`
- `/v2/security/audit/records`
- other `/v2/security/*` paths only after direct verification.

### Tasks

Implement:

- task list;
- task details;
- history;
- run/suspend/resume if supported and authorized.

Relevant paths:

- `/v2/tasks`
- `/v2/task`
- `/v2/task/history`
- `/v2/task/run`
- `/v2/task/suspend`
- `/v2/task/resume`

### System / Runtime

Implement:

- Overview resource summary;
- processes navigation;
- database/storage state;
- memory/shared memory;
- license/system state where useful.

Relevant paths:

- `/v2/monitor/dashboard/main`
- `/v2/monitor/dashboard/system-resources`
- `/v2/monitor/dashboard/globals-and-routines`
- `/v2/monitor/system-usage`
- `/v2/monitor/system-usage/shared-memory`
- `/v2/monitor/license-usage`
- `/v2/databases`
- `/v2/database-dir`
- `/v2/processes`

### Logs

Implement initial unified evidence view using sources verified in the runtime:

- audit records;
- task errors/history;
- WSGI/Argus errors where safely accessible.

Relevant path:

- `/v2/security/audit/records`

## Technical references

Primary contract:

- https://github.com/intersystems-community/sysadmin-api-specification/blob/master/mainspec_v2.json
- https://raw.githubusercontent.com/intersystems-community/sysadmin-api-specification/master/mainspec_v2.json

Contest requirement:

- https://community.intersystems.com/post/intersystems-programming-contest-build-your-own-management-portal

Audit:

- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=AAUDIT
- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ITECHREF_auditing

Tasks:

- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSA_manage_taskmgr
- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ITECHREF_task

## Exit criteria

- [ ] single SysAdmin adapter used by all six areas;
- [ ] no mocked primary data in user-facing paths;
- [ ] each official contest area has at least one usable, real IRIS-backed screen/flow;
- [ ] unauthorized states are explicit and safe;
- [ ] no flagship-level overengineering of Applications/Permissions/Security;
- [ ] Overview renders real monitor data.

## No-go conditions

Do not start bonus intelligence while any official task family has no working IRIS-backed path.

---

# 8. PHASE 3 — RUNTIME INTELLIGENCE: PROCESSES

## Objective

Turn the process list into an investigation surface.

## Tasks

1. build process list with filtering/sorting;
2. build Process Investigator;
3. retrieve deep detail lazily;
4. normalize optional/missing fields;
5. correlate process to:
   - namespace;
   - routine/current line;
   - transaction context;
   - last global reference;
   - global references/updates;
   - process-private global usage;
   - related locks;
6. implement suspend/resume/terminate only after privilege and safety validation;
7. add process-specific integration tests.

## Primary SysAdmin paths

- `/v2/processes`
- `/v2/process`
- `/v2/process/suspend`
- `/v2/process/resume`
- `/v2/process/terminate`

## Native enrichment

- `%SYS.ProcessQuery`

## Technical references

- mainspec: https://raw.githubusercontent.com/intersystems-community/sysadmin-api-specification/master/mainspec_v2.json
- `%SYS.ProcessQuery`: https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.ProcessQuery&LIBRARY=%25SYS
- Community performance investigation: https://community.intersystems.com/post/whats-taking-so-long-process-sampling-performance-analysis

## Exit criteria

- [ ] user selects a real PID and sees available process context;
- [ ] expensive detail is not polled for every PID by default;
- [ ] missing data degrades visibly, not silently;
- [ ] related-lock navigation is possible when lock data exists;
- [ ] process actions require explicit confirmation;
- [ ] at least one process integration path is exercised against the container.

## No-go conditions

Do not claim transaction/routine/global context if it was not actually returned or enriched by a verified native API.

---

# 9. PHASE 4 — RUNTIME INTELLIGENCE: LOCKS

## Objective

Turn the current lock table into an investigation surface and establish the primary Argus troubleshooting chain.

## Tasks

1. implement live lock list;
2. implement Lock Investigator;
3. correlate lock → owner process;
4. expose verified:
   - reference;
   - PID;
   - mode/count;
   - routine info;
   - directory;
   - process/transaction context;
5. link to:
   - Process Investigator;
   - Global/Database context where resolvable;
6. implement a blocking graph only if waiter relationships are actually derivable;
7. implement lock deletion only if official endpoint semantics are verified and safety protections remain intact;
8. create a deterministic local scenario for lock contention where safe.

## Primary SysAdmin paths

- `/v2/locks`
- `/v2/lock`

## Native enrichment

- `%SYS.LockQuery`

## Technical references

- mainspec: https://raw.githubusercontent.com/intersystems-community/sysadmin-api-specification/master/mainspec_v2.json
- `%SYS.LockQuery`: https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.LockQuery&LIBRARY=%25SYS
- Community historical-lock discussion: https://community.intersystems.com/post/how-do-i-trace-low-level-deadlocks-between-globals-sql-tables-and-object-transactions-across

## Exit criteria

- [ ] live lock data displays from real IRIS;
- [ ] selecting a lock identifies the owner process when available;
- [ ] lock → process navigation works;
- [ ] routine/directory/resource context is displayed only when verified;
- [ ] deterministic scenario can reproduce a meaningful lock condition in development;
- [ ] no fabricated blocking tree exists.

## No-go conditions

Do not promote a current lock count into “incident intelligence” before Phase 5 baseline/incident logic exists.

---

# 10. PHASE 5 — HISTORICAL INTELLIGENCE: BASELINES AND INCIDENTS

## Objective

Preserve selected operational evidence and distinguish unusual behavior from normal workload patterns.

## Tasks — Persistence

Create IRIS SQL schema for:

- `ArgusConfiguration`;
- `ArgusProcessSnapshot`;
- `ArgusLockSnapshot`;
- `ArgusTaskSnapshot`;
- `ArgusBehaviorBaseline`;
- `ArgusIncident`;
- `ArgusIncidentEvidence`.

## Tasks — Collection

1. implement selective snapshots;
2. use IRIS Task Manager to invoke Embedded Python collectors;
3. do not create permanent Flask worker threads;
4. implement retention configuration.

## Tasks — Baseline

Implement:

```text
entity/resource
+ namespace
+ day-of-week
+ local time bucket
```

Default:

- 15-minute bucket;
- 30-day rolling history.

Compute:

- sample count;
- min/max;
- average;
- median;
- p90;
- p95;
- standard deviation;
- confidence.

Persist capture time in UTC. Use configured environment timezone for behavior buckets.

## Tasks — Incident engine

Implement:

- Observation;
- Anomaly;
- Incident promotion;
- impact evaluation;
- persistence evaluation;
- correlation;
- deterministic reason list;
- severity;
- confidence;
- fingerprint/deduplication;
- grace-period resolution.

Required logic examples:

### Case A

```text
Noon lock volume high
but inside normal p95
and no wait impact
→ no incident
```

### Case B

```text
Same volume at 03:00
far beyond historical p95
persists
and affects processes
→ incident
```

### Case C

```text
Lock count normal
but 23 processes blocked
and oldest wait 108s
→ incident
```

## Technical references

Task scheduling:

- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSA_manage_taskmgr
- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ITECHREF_task
- https://docs.intersystems.com/irisforhealthlatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.Python&LIBRARY=%25SYS

Lock/process evidence:

- https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.LockQuery&LIBRARY=%25SYS
- https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.ProcessQuery&LIBRARY=%25SYS
- https://community.intersystems.com/post/how-do-i-trace-low-level-deadlocks-between-globals-sql-tables-and-object-transactions-across

## Required unit tests

- median/p90/p95;
- confidence classification;
- timezone bucket mapping;
- normal-noon scenario;
- abnormal-03:00 scenario;
- impact-driven incident;
- fingerprint stability;
- deduplication;
- resolution grace period;
- learning mode.

## Exit criteria

- [ ] snapshots persist in IRIS SQL;
- [ ] baseline aggregates build from historical samples;
- [ ] cold-start/learning mode is explicit;
- [ ] normal noon scenario does not create incident;
- [ ] abnormal 03:00 scenario can create incident;
- [ ] normal-volume/high-impact scenario creates incident;
- [ ] one condition does not create one incident per sample;
- [ ] resolved incident retains evidence after live condition disappears.

## No-go conditions

Do not add LLM-based incident classification. Incident creation remains deterministic.

---

# 11. PHASE 6 — STORAGE INTELLIGENCE: TOPOLOGY, GROWTH, IRISTEMP

## Objective

Connect logical IRIS resources to physical storage and detect abnormal growth behavior.

## Tasks — Namespace topology

1. list namespaces;
2. resolve default database context;
3. load verified global mappings;
4. resolve namespace + global → physical database/directory;
5. render simple topology;
6. link to Global Explorer and Database detail.

### SysAdmin sources

- `/v2/namespaces`
- `/v2/namespace`
- `/v2/databases`
- `/v2/database`
- `/v2/database-dir`

### Native enrichment

- `Config.MapGlobals`
- `%SYS.Namespace.GetGlobalDest()` or current verified equivalent.

### References

- https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=Config.MapGlobals&LIBRARY=%25SYS
- https://community.intersystems.com/post/how-get-db-and-global-location-information
- https://community.intersystems.com/post/how-find-globals-original-namespace-potentially-mapped-different-namespace
- https://community.intersystems.com/post/namespaces-and-databases-basics-inner-workings-intersystems-iris

## Tasks — Database growth

1. persist database size snapshots;
2. derive 24h/7d/30d growth;
3. compute temporal baseline/deviation;
4. link database growth to incident engine.

### Sources

- `/v2/databases`
- `/v2/database`
- `/v2/database-dir`

## Tasks — Global growth

1. verify `%Library.GlobalEdit.GetGlobalSize(...)` on target version;
2. prefer efficient estimation mode for recurring collection;
3. persist allocated/used/measurement type;
4. derive growth per period;
5. correlate top contributors to database growth;
6. never full-scan huge globals on normal page load.

### References

- `%Library.GlobalEdit`: https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25Library.GlobalEdit&LIBRARY=%25SYS
- Community sizing guidance: https://community.intersystems.com/post/determining-global-and-table-sizes-intersystems-iris

## Tasks — IRISTEMP

1. verify available IRISTEMP usage metric;
2. rank process-private global consumers when supported;
3. link PPG-heavy PID to Process Investigator;
4. do not estimate bytes from blocks unless block size/conversion is verified.

### References

- Process Private Globals: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GCOS_ppg
- `%SYS.ProcessQuery`: https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.ProcessQuery&LIBRARY=%25SYS
- Community IRISTEMP investigation: https://community.intersystems.com/post/how-identify-which-temporary-globals-are-consuming-size-iristemp-database

## Exit criteria

- [ ] namespace/global can resolve to physical database in tested cases;
- [ ] database growth history works;
- [ ] global growth collection uses verified efficient mechanism;
- [ ] growth can create anomaly/incident according to Phase 5 rules;
- [ ] expected temporary growth can remain normal;
- [ ] failed recovery can become anomaly;
- [ ] IRISTEMP path works or is clearly marked unsupported if target data is unavailable.

## No-go conditions

Do not perform uncontrolled exact sizing scans against large globals.

---

# 12. PHASE 7 — REPORTS AND OPERATIONAL UX

## Objective

Make preserved evidence understandable after the live problem is gone.

## Tasks

Implement:

### Incident Report

- classification;
- severity/confidence;
- reasons;
- timeline;
- related entities;
- resolution.

### Lock Report

- contention incidents;
- top resources;
- impact;
- normal/unusual time windows.

### Growth Report

- database growth;
- global contributors;
- expected vs observed.

### Behavior Report

- temporal baseline;
- confidence;
- normal peak windows.

Exports:

- HTML;
- JSON;
- CSV for tabular sections.

## UX tasks

1. implement LIVE vs HISTORICAL labels;
2. implement clear empty/error/permission states;
3. implement links among Incident ↔ Lock ↔ Process ↔ Global ↔ Database;
4. optimize list/detail loading;
5. verify responsive/basic usability.

## References

- Product screen contract: `PRODUCT_UX.md`
- Technical behavior contract: `SPEC.md`

## Exit criteria

- [ ] resolved incident is understandable without live data;
- [ ] reports contain deterministic evidence;
- [ ] investigation chain is navigable;
- [ ] historical data is never represented as live;
- [ ] no report requires an LLM.

---

# 13. PHASE 8 — BONUS INTELLIGENCE

## Objective

Add contest-aligned intelligence without destabilizing the core.

This phase is authorized only after Phases 0–7 are stable.

## 13.1 Vector Search

Use IRIS Vector Search for:

```text
current incident → similar incidents
error summary → similar historical error
incident → related runbook/resolution
```

Reference:

- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSQL_vecsearch

Tasks:

1. define compact text representation of incidents/resolutions;
2. separate embedding generation from retrieval;
3. store vectors in IRIS;
4. implement similarity query;
5. do not replace deterministic incident matching/filtering.

## 13.2 Community Opportunity DPI-I-574

Reference:

- https://ideas.intersystems.com/ideas/DPI-I-574

Tasks:

1. normalize error evidence;
2. correlate it to Argus process/lock/incident context;
3. retrieve similar historical incidents when available;
4. implement optional provider abstraction;
5. keep provider secret in IRIS Wallet;
6. generate explanation/suggested investigation steps;
7. show supporting evidence beside AI output.

## Security order

AI receives evidence only.

AI receives no capability to:

- execute SysAdmin actions;
- terminate process;
- delete lock;
- modify security;
- execute generated SQL/OS commands;
- rebuild index.

## Bonus references

- https://community.intersystems.com/post/technology-bonuses-intersystems-programming-contest-build-your-own-management-portal

Planning values:

```text
Embedded Python       3
Vector Search         2 conservative
Docker                2
ZPM/IPM               2
Online Demo           2
Community Opportunity 4
```

Note: the official bonus post currently lists Vector Search as 2 in the summary but says 5 in its detailed paragraph. Plan against 2 until clarified.

## Exit criteria

- [ ] core incidents still work with AI disabled;
- [ ] Vector Search has a real incident/runbook use case;
- [ ] LLM credential is not exposed to browser;
- [ ] AI explanation references structured evidence;
- [ ] no action privileges are delegated to AI.

---

# 14. PHASE 9 — PACKAGING, HARDENING, FINAL VALIDATION

## Objective

Produce a clean, reproducible, contest-ready repository.

## Tasks — Packaging

1. finalize `module.xml`;
2. install WSGI application reproducibly;
3. install Embedded Python requirements in correct runtime;
4. provide ZPM/IPM deployment if technically valid;
5. verify fresh-clone deployment.

## Tasks — Docker

1. deterministic Docker build;
2. no post-start manual configuration required;
3. explicit ports/environment variables;
4. health validation;
5. no real credentials committed.

## Tasks — README

English README must include:

- product purpose;
- architecture;
- prerequisite/version;
- build/start;
- URLs/ports;
- namespace;
- test commands;
- WSGI/Embedded Python explanation;
- SysAdmin usage;
- safety limitations;
- demo scenario description.

## Tasks — Demo readiness

Provide deterministic development/demo scenarios for:

- lock contention;
- unusual temporal workload;
- storage/global growth;
- error correlation if implemented.

These are application/test scenarios, not external videos or articles.

## Tasks — Security review

Verify:

- no secrets in repository;
- no `%All` production default solely for convenience;
- destructive actions gated;
- permission errors handled;
- Wallet secret values not rendered.

## Mandatory final build procedure

Execute the real repository build.

For Docker Compose:

```bash
docker compose down --remove-orphans
docker compose build
docker compose up -d
docker compose ps
docker compose logs --no-color
```

Use `--no-cache` when stale layers are suspected.

Then execute real HTTP smoke tests.

## Mandatory final smoke matrix

- [ ] `/argus` HTTP route;
- [ ] Embedded Python import inside IRIS;
- [ ] SysAdmin request;
- [ ] IRIS SQL persistence;
- [ ] Applications screen;
- [ ] Permissions screen;
- [ ] Security/Wallet screen;
- [ ] Tasks screen;
- [ ] System screen;
- [ ] Logs screen;
- [ ] Process Investigator;
- [ ] Lock Investigator;
- [ ] Incident persistence;
- [ ] baseline acceptance scenarios;
- [ ] growth/topology if P1 included;
- [ ] report generation.

## Exit criteria

- [ ] clean build passes;
- [ ] runtime remains healthy;
- [ ] tests pass;
- [ ] logs checked;
- [ ] primary user journey exercised;
- [ ] README reflects actual behavior;
- [ ] no irrelevant template code remains;
- [ ] no known broken P0 feature remains.

---

# 15. SUSTAINMENT

## 15.1 Dependency discipline

Only include dependencies with a defined responsibility.

Required/expected:

- Flask;
- template/UI helper dependencies actually used;
- testing libraries actually used.

Optional only when phase authorized:

- embedding/LLM client library.

Do not add a package merely because it is familiar.

## 15.2 Data retention

Default planning values:

```text
Process snapshots      7 days
Lock snapshots         30 days
Incident evidence      90 days
Behavior aggregates    365 days
Database/global growth 365 days
Incidents              365 days
```

Keep configurable.

## 15.3 Performance discipline

- no full global scans on ordinary page load;
- no deep process detail polling for every PID;
- no unlimited log/history queries;
- paginate large lists;
- compute/store aggregates where needed;
- retain raw evidence only as long as useful.

## 15.4 Failure discipline

If build/runtime/test fails:

1. inspect actual error;
2. inspect container logs;
3. inspect IRIS `messages.log` for WSGI/import issues;
4. fix root cause;
5. rerun failed validation;
6. do not remove validation to hide failure.

This follows `AGENT.md` build failure policy.

---

# 16. COMMAND AND SIGNAL

## 16.1 Authority

The engineering agent must report conflicts in this order:

```text
AGENT.md
SPEC.md
mainspec_v2.json
IMPLEMENTATION_PLAN.md
PRODUCT_UX.md
```

Current `mainspec_v2.json` overrides stale endpoint assumptions.

## 16.2 Change control

A change is **scope-changing** if it introduces:

- a new runtime service/container;
- new database;
- new language/runtime;
- new flagship module;
- autonomous action behavior;
- Enterprise-only dependency;
- significant new destructive operation.

Do not make scope-changing decisions silently.

Record them as an ADR or explicit specification change.

## 16.3 Phase report format

At the end of each phase, report:

```text
PHASE:
STATUS: COMPLETE / BLOCKED / PARTIAL

OBJECTIVE ACHIEVED:
- ...

FILES CHANGED:
- ...

REAL IRIS VALIDATION EXECUTED:
- command / endpoint / result

TESTS EXECUTED:
- ...

DOCUMENTATION / MAINSPEC REFERENCES USED:
- ...

BLOCKERS / UNVERIFIED ITEMS:
- ...

NEXT AUTHORIZED PHASE:
- ...
```

Do not write long narrative progress reports.

## 16.4 Stop conditions

Stop advancing and resolve the blocker when:

- WSGI does not run inside IRIS;
- current SysAdmin spec contradicts an assumed endpoint;
- core runtime requires an unapproved external service;
- a destructive action lacks privilege/safety guarantees;
- target Community Edition lacks a required P0 capability;
- tests reveal incident logic creates obvious false positives in required scenarios.

## 16.5 Definition of victory

The operation succeeds when an evaluator can follow this chain on a reproducible installation:

```text
Overview detects/contains a meaningful condition
   ↓
Incident explains why it matters
   ↓
Lock/Process Investigator identifies runtime context
   ↓
Global/Namespace/Database context is navigable when relevant
   ↓
Historical evidence remains after live condition disappears
   ↓
Report preserves the operational story
```

and all six official contest Management Portal task families have genuine IRIS-backed functional coverage.

---

# 17. REFERENCE QUICK INDEX

## Contest

- https://community.intersystems.com/post/intersystems-programming-contest-build-your-own-management-portal
- https://community.intersystems.com/post/technology-bonuses-intersystems-programming-contest-build-your-own-management-portal

## SysAdmin API

- https://github.com/intersystems-community/sysadmin-api-specification
- https://github.com/intersystems-community/sysadmin-api-specification/blob/master/mainspec_v2.json
- https://raw.githubusercontent.com/intersystems-community/sysadmin-api-specification/master/mainspec_v2.json

## Template / deployment

- https://github.com/intersystems-community/intersystems-iris-dev-template
- https://community.intersystems.com/post/running-wsgi-applications-ipm

## Embedded Python / WSGI

- https://community.intersystems.com/post/wsgi-support-introduction
- https://community.intersystems.com/post/introduction-python-first-approach-iris
- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GEPYTHON_reference_core
- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GEPYTHON_runpython
- https://docs.intersystems.com/irisforhealthlatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.Python&LIBRARY=%25SYS

## Processes / Locks

- https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.ProcessQuery&LIBRARY=%25SYS
- https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.LockQuery&LIBRARY=%25SYS
- https://community.intersystems.com/post/whats-taking-so-long-process-sampling-performance-analysis
- https://community.intersystems.com/post/how-do-i-trace-low-level-deadlocks-between-globals-sql-tables-and-object-transactions-across

## Storage / Globals / Namespace

- https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=Config.MapGlobals&LIBRARY=%25SYS
- https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25Library.GlobalEdit&LIBRARY=%25SYS
- https://community.intersystems.com/post/how-get-db-and-global-location-information
- https://community.intersystems.com/post/how-find-globals-original-namespace-potentially-mapped-different-namespace
- https://community.intersystems.com/post/namespaces-and-databases-basics-inner-workings-intersystems-iris
- https://community.intersystems.com/post/determining-global-and-table-sizes-intersystems-iris

## Tasks / IRISTEMP / Audit

- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSA_manage_taskmgr
- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ITECHREF_task
- https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.Task.History&LIBRARY=%25SYS
- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GCOS_ppg
- https://community.intersystems.com/post/how-identify-which-temporary-globals-are-consuming-size-iristemp-database
- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=AAUDIT
- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ITECHREF_auditing

## Optional intelligence

- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSQL_vecsearch
- https://ideas.intersystems.com/ideas/DPI-I-574
