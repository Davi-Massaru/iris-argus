# Argus IRIS — Engineering Specification

**Status:** Frozen implementation baseline  
**Project:** Argus IRIS  
**Audience:** Claude Code, Codex, maintainers, reviewers  
**Target runtime:** InterSystems IRIS Community Edition 2026.2  
**Custom server-side logic:** 100% Embedded Python  
**Web runtime:** `%SYS.Python.WSGI`  
**Primary administrative contract:** InterSystems SysAdmin API v2 (`mainspec_v2.json`)  
**Source template:** `https://github.com/intersystems-community/intersystems-iris-dev-template`

---

## 0. Document authority

The engineering authority order is:

1. `AGENT.md`
2. `SPEC.md`
3. current official `mainspec_v2.json`
4. `IMPLEMENTATION_PLAN.md`
5. `PRODUCT_UX.md`
6. README and secondary notes

When a conflict exists:

- obey `AGENT.md` for engineering process and runtime validation;
- obey this specification for product scope and architecture;
- obey the current `mainspec_v2.json` for SysAdmin endpoint names, schemas and privileges;
- do not invent unsupported endpoints or IRIS classes;
- mark an uncertain capability **UNVERIFIED** until validated against official documentation or a running IRIS instance.

The coding agent must read all four project documents before making large changes.

---

# 1. Product mission

Argus IRIS is a troubleshooting-first Management Portal for InterSystems IRIS.

Its purpose is to reduce the effort required to move from a vague operational symptom to concrete IRIS evidence.

Typical starting point:

> “IRIS is slow.”

Argus should help answer:

```text
What is abnormal?
    ↓
Which process / task / lock / resource is involved?
    ↓
What routine is executing?
    ↓
Which global is involved?
    ↓
Which namespace exposes it?
    ↓
Which physical database stores it?
    ↓
Is this normal for this day/time?
    ↓
Is there actual impact?
    ↓
Should this be preserved as an incident?
    ↓
What evidence remains after the live problem disappears?
```

Product statement:

> **Argus IRIS transforms scattered IRIS administrative data into contextual operational evidence.**

Working tagline:

> **Argus IRIS — See beyond the symptoms.**

The name references **Argus Panoptes**, the many-eyed guardian of Greek mythology. The product metaphor is multiple operational views converging into one investigation context.

---

# 2. Contest mission and mandatory coverage

The official contest asks for a GUI powered by InterSystems IRIS management APIs for:

- Web Applications and REST APIs;
- Permission Management;
- Security and Secrets;
- Task Management;
- Operating System / runtime management;
- Logs from IRIS subsystems.

The announcement explicitly allows additional useful screens and actions.

An official contest-team response in the announcement comments states that an alternative application is valid **“as long as it implements these calls”**, followed by the six areas above.

Therefore Argus uses this strategy:

> **minimum functional coverage across all six contest areas + deep vertical specialization in runtime investigation.**

Official references:

- Contest announcement: https://community.intersystems.com/post/intersystems-programming-contest-build-your-own-management-portal
- SysAdmin API repository: https://github.com/intersystems-community/sysadmin-api-specification
- Main OpenAPI contract: https://github.com/intersystems-community/sysadmin-api-specification/blob/master/mainspec_v2.json
- Raw OpenAPI contract: https://raw.githubusercontent.com/intersystems-community/sysadmin-api-specification/master/mainspec_v2.json

General contest constraints that affect engineering:

- application must be functional;
- application must work on IRIS Community Edition or IRIS for Health Community Edition;
- application must be open source;
- README must be in English and include installation instructions and product explanation/demo;
- complexity and usefulness affect approval/judging.

---

# 3. Scope strategy

## 3.1 Minimum contest coverage

These modules must exist and use real IRIS management functionality:

```text
Applications & REST
Permissions
Security & Secrets
Tasks
System / Runtime
Logs
```

They do not require equal depth.

## 3.2 Flagship product capabilities

The majority of engineering depth belongs to:

```text
Process Investigator
Lock Investigator
Behavior Baselines
Incidents
Namespace / Global Topology
Database / Global Growth
IRISTEMP Investigation
Operational Reports
```

## 3.3 Optional intelligence

Only after the core product is stable:

```text
IRIS Vector Search
Similar Incident Search
DPI-I-574 AI Error Analysis
```

Do not start with AI or vector search.

---

# 4. Non-negotiable architecture

## 4.1 Runtime path

All custom backend logic must execute inside IRIS using Embedded Python.

```text
Browser
  ↓
IRIS Web Gateway
  ↓
/argus Web Application
  ↓
%SYS.Python.WSGI
  ↓
Flask / Jinja / HTMX
  ↓
Embedded Python
  ├── SysAdmin API v2
  ├── iris.cls(...)
  ├── iris.gref(...)
  ├── IRIS SQL
  ├── IRIS Vector Search (optional phase)
  └── Argus services / collectors
```

Reference:

- WSGI Support Introduction: https://community.intersystems.com/post/wsgi-support-introduction
- Running WSGI Applications with IPM: https://community.intersystems.com/post/running-wsgi-applications-ipm
- Embedded Python Core API: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GEPYTHON_reference_core
- Run Embedded Python: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GEPYTHON_runpython
- `%SYS.Python`: https://docs.intersystems.com/irisforhealthlatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.Python&LIBRARY=%25SYS

## 4.2 Forbidden runtime dependencies

Do not add the following as required runtime components:

- Quarkus;
- Spring Boot;
- standalone Node backend;
- FastAPI/Uvicorn service;
- Gunicorn;
- PostgreSQL;
- MySQL;
- Redis;
- Kafka;
- RabbitMQ;
- Qdrant;
- Pinecone;
- Chroma;
- external scheduler service;
- Grafana/Prometheus as required product dependencies.

Frontend JavaScript libraries are allowed because the restriction applies to custom server-side application logic.

## 4.3 ObjectScript rule

Custom product business logic must not be implemented in ObjectScript.

Built-in IRIS classes, declarative configuration and minimal installation/scheduling glue are allowed when required by IRIS, but collection, correlation, incident logic, reports and HTTP application behavior remain Python.

## 4.4 IRIS-first rule

Use native IRIS capabilities before adding infrastructure:

```text
Administration      → SysAdmin API v2
Persistence         → IRIS SQL
Native enrichment   → Embedded Python + iris module
Globals             → IRIS global APIs
Scheduling          → IRIS Task Manager invoking Python
Secrets             → IRIS Wallet
Authentication      → IRIS security
Vectors              → IRIS Vector Search
Web runtime          → %SYS.Python.WSGI
```

## 4.5 Community Edition rule

Core V1 must run on IRIS Community Edition.

Do not make V1 depend on:

- ECP;
- mirroring;
- sharding;
- Enterprise-only topology.

---

# 5. Repository and package target

The agent starts from a clean clone of:

- https://github.com/intersystems-community/intersystems-iris-dev-template

Expected final shape:

```text
argus-iris/
├── AGENT.md
├── SPEC.md
├── PRODUCT_UX.md
├── IMPLEMENTATION_PLAN.md
├── README.md
├── LICENSE
├── Dockerfile
├── docker-compose.yml
├── iris.script / merge.cpf as required
├── module.xml
├── requirements.txt
│
├── python/
│   └── argus/
│       ├── app.py
│       ├── config.py
│       ├── api/
│       ├── iris/
│       ├── domain/
│       ├── services/
│       ├── collectors/
│       ├── intelligence/
│       └── reports/
│
├── web/
│   ├── templates/
│   └── static/
│
└── tests/
```

The exact internal folders may be simplified if the implementation remains coherent.

The template must be cleaned. No sample `dc.sample` identifiers, classes, tests or README instructions may remain unless intentionally reused and documented.

---

# 6. Canonical SysAdmin API contract

The current OpenAPI document declares `/api/admin` as the base server URL and exposes API version 2 resources.

Before implementing a SysAdmin feature, verify the endpoint, method, payload and required privilege in the current raw file:

- https://raw.githubusercontent.com/intersystems-community/sysadmin-api-specification/master/mainspec_v2.json

## 6.1 API families used by Argus

| Domain | Primary paths | Purpose |
|---|---|---|
| General/auth | `/info`, `/login`, `/logout`, `/refresh`, `/revoke` | session/API context |
| Databases | `/v2/database`, `/v2/database-dir`, `/v2/databases` | configuration and physical DB state |
| Monitor | `/v2/monitor/dashboard/main`, `/v2/monitor/dashboard/system-resources`, `/v2/monitor/dashboard/globals-and-routines`, `/v2/monitor/system-usage`, `/v2/monitor/system-usage/shared-memory`, `/v2/monitor/license-usage` | overview/runtime state |
| Processes | `/v2/process`, `/v2/processes`, `/v2/process/suspend`, `/v2/process/resume`, `/v2/process/terminate` | runtime process inspection and controlled actions |
| Locks | `/v2/locks`, `/v2/lock` | live locks and controlled deletion where supported |
| Namespaces | `/v2/namespace`, `/v2/namespaces` | namespace configuration |
| Tasks | `/v2/task`, `/v2/tasks`, `/v2/task/history`, `/v2/task/run`, `/v2/task/suspend`, `/v2/task/resume` | task administration/history |
| Web Apps | `/v2/web-app`, `/v2/web-apps` | web application management |
| Security | `/v2/security/users`, `/v2/security/roles`, `/v2/security/resources`, `/v2/security/sql-privileges`, `/v2/security/audit/records` | permission and audit views |
| Wallet | `/v2/wallet/collections`, `/v2/wallet/secret`, `/v2/wallet/secrets` | secrets management |
| Journal | `/v2/journal/*` | IRIS-specific journal management |
| Web sessions | `/v2/web-sessions`, `/v2/web-session` | web session administration when used |

This table is a navigation aid, not a substitute for the live OpenAPI contract.

## 6.2 SysAdmin adapter

All SysAdmin access must pass through one adapter boundary, for example:

```text
argus.iris.sysadmin.SysAdminClient
```

Responsibilities:

- base URL/session handling;
- authentication/token handling where used;
- request construction;
- timeout/error normalization;
- privilege/403 handling;
- response schema isolation;
- testability.

Do not scatter raw SysAdmin HTTP requests across UI handlers.

---

# 7. Contest core modules

## 7.1 Applications & REST

Required minimum:

- list Web Applications;
- inspect application details;
- edit a safe/basic configuration subset supported by SysAdmin;
- expose REST/OpenAPI information when discoverable;
- show permission errors safely.

Primary source:

- `mainspec_v2.json`: `/v2/web-app`, `/v2/web-apps`

This is compliance coverage, not a flagship area.

## 7.2 Permissions

Required minimum:

- Users view;
- Roles view;
- Resources view;
- SQL Privileges view;
- one safe relationship operation only if clearly supported and testable.

Primary source:

- `mainspec_v2.json`: `/v2/security/users`, `/v2/security/roles`, `/v2/security/resources`, `/v2/security/sql-privileges`

## 7.3 Security & Secrets

Required minimum:

- Wallet collections/secrets metadata;
- audit view;
- supported security/certificate/OAuth configuration may be surfaced only where current `mainspec_v2` exposes it clearly.

Primary sources:

- `mainspec_v2.json`: `/v2/wallet/*`, `/v2/security/*`
- Auditing: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=AAUDIT
- Auditing APIs: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ITECHREF_auditing

Argus may use Wallet to store optional LLM provider credentials. Secret values must never be sent to browser JavaScript.

## 7.4 Tasks

Required minimum:

- list tasks;
- inspect task details;
- task history;
- run/suspend/resume when supported and authorized;
- Task Health context derived from historical runtime.

Primary sources:

- `mainspec_v2.json`: `/v2/task`, `/v2/tasks`, `/v2/task/history`, `/v2/task/run`, `/v2/task/suspend`, `/v2/task/resume`
- Task Manager: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSA_manage_taskmgr
- Task APIs: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ITECHREF_task
- `%SYS.Task.History`: https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.Task.History&LIBRARY=%25SYS

## 7.5 System / Runtime

Required minimum:

- CPU/system resource summary;
- memory/shared-memory summary;
- process count/navigation;
- database/disk-oriented status available through SysAdmin;
- license/system state where useful;
- devices only if exposed and useful in the current spec.

Primary source:

- `mainspec_v2.json`: `/v2/monitor/*`, `/v2/databases`, `/v2/database-dir`, `/v2/processes`

## 7.6 Logs

Required minimum:

- unified UI for available operational log sources;
- audit records;
- WSGI/Argus errors where safely accessible;
- task-history failures;
- links from relevant error evidence into investigation.

Primary references:

- `mainspec_v2.json`: `/v2/security/audit/records`
- WSGI Support Introduction: https://community.intersystems.com/post/wsgi-support-introduction
- Auditing: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=AAUDIT

Do not claim universal access to every IRIS log until the exact source is verified on the target image.

---

# 8. Overview

The landing page must prioritize attention, not graph density.

It should combine current management data with Argus context:

```text
CPU                  31%
Memory               63%
Processes             48
Open incidents         3

ATTENTION
HIGH    Lock contention — ^OrderD
MEDIUM  PROD_DATA growth outside baseline
MEDIUM  CleanupTask runtime anomaly
```

Sources:

- `/v2/monitor/dashboard/main`
- `/v2/monitor/dashboard/system-resources`
- `/v2/monitor/dashboard/globals-and-routines`
- `/v2/monitor/system-usage`
- `/v2/monitor/system-usage/shared-memory`
- `/v2/monitor/license-usage`

Current values and historical interpretations must be visually distinct.

---

# 9. Process Investigator

The process list is administrative coverage. The Process Investigator is a flagship feature.

Primary SysAdmin sources:

- `/v2/processes`
- `/v2/process`
- `/v2/process/suspend`
- `/v2/process/resume`
- `/v2/process/terminate`

Native enrichment:

- `%SYS.ProcessQuery`

References:

- `%SYS.ProcessQuery`: https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.ProcessQuery&LIBRARY=%25SYS
- Community process sampling: https://community.intersystems.com/post/whats-taking-so-long-process-sampling-performance-analysis

When available, show:

```text
PID
User
Namespace
State
Runtime / CPU context
Transaction context
Current line/routine
Last global reference
Global references / updates
PrivateGlobalBlockCount
Related locks
Related incident
Behavioral context
```

Deep process queries should be lazy/on-demand where fields are expensive or require process communication.

Process actions are always privilege-aware and human-confirmed.

---

# 10. Lock Investigator

Locks are a primary Argus domain.

Primary SysAdmin sources:

- `/v2/locks`
- `/v2/lock`

Native enrichment:

- `%SYS.LockQuery`

References:

- `%SYS.LockQuery`: https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.LockQuery&LIBRARY=%25SYS
- Community historical-lock pain: https://community.intersystems.com/post/how-do-i-trace-low-level-deadlocks-between-globals-sql-tables-and-object-transactions-across

The lock view should correlate, where verifiable:

```text
Lock reference
Owner PID
Mode/count
RoutineInfo
Physical directory
Namespace/process context
Transaction context
Affected/waiting processes
Behavioral deviation
Related incident
```

Desired investigation chain:

```text
PID 8142
App.Order.SQL1
     │
     │ owns
     ▼
^App.OrderD(89122)
     │
     │ contention
     ▼
affected processes
```

Do not fabricate blocking trees when the waiter/owner relationship is not actually derivable.

Lock deletion, if exposed, must preserve the safety semantics of the official API and require explicit confirmation.

---

# 11. Behavioral baseline

Argus must distinguish **high** from **abnormal for this environment at this time**.

Pipeline:

```text
COLLECT
  ↓
OBSERVATION
  ↓
COMPARE TO TEMPORAL BASELINE
  ↓
ANOMALY
  ↓
PERSISTENCE + IMPACT + CORRELATION
  ↓
INCIDENT
```

## 11.1 Default baseline key

```text
metric_type
+ entity_type/entity_key
+ namespace
+ day_of_week
+ local time bucket
```

Default time bucket:

- 15 minutes.

Default rolling history:

- 30 days.

Persist timestamps in UTC. Build behavior buckets using configured environment timezone.

## 11.2 Statistics

Initial baseline statistics:

```text
sample_count
minimum
maximum
average
median
p90
p95
standard_deviation
```

Prefer transparent statistics over opaque machine-learning models in V1.

## 11.3 Confidence

Suggested confidence:

```text
<5 samples      INSUFFICIENT
5–10            LOW
11–20           MEDIUM
>20             HIGH
```

A new installation operates in **LEARNING MODE**. Lack of history must never be treated as proof of normality.

---

# 12. Incident engine

An incident is not every anomaly.

Promote an observation/anomaly to an incident when one or more of these strategies applies.

## 12.1 Persistent contextual anomaly

Example:

```text
current lock activity >> historical p95
AND
condition persists beyond configured duration
```

## 12.2 Impact-driven condition

Example:

```text
lock count historically normal
BUT
23 affected processes + oldest wait 108s
```

This still creates an incident.

## 12.3 Correlated anomalies

Several moderate signals may jointly justify an incident:

```text
transaction age abnormal
+ LOCKW processes abnormal
+ global updates abnormal
+ task runtime abnormal
```

## 12.4 Deterministic critical condition

Some conditions do not require baseline comparison when directly verifiable and severe.

Examples may include:

- critical IRIS error;
- repeated task failure;
- database capacity danger;
- index validation failure;
- lock exhaustion condition.

Exact rules must be supported by available evidence.

## 12.5 Explainability

Every incident must store deterministic reasons.

Example:

```text
WHY THIS IS AN INCIDENT

+ lock activity 15× historical p95 for this time bucket
+ persisted > 60 seconds
+ 17 processes affected
+ primary PID has an 11-minute transaction
```

An LLM is never required to explain why the incident exists.

## 12.6 Lifecycle

Statuses:

```text
OPEN
ACKNOWLEDGED
RESOLVED
IGNORED
```

Auto-resolution requires the trigger condition to remain absent for a configurable grace period.

## 12.7 Deduplication

Do not create one incident per polling cycle.

Use a stable fingerprint such as:

```text
incident_type
+ namespace
+ primary resource/global
+ primary PID where stable/relevant
```

Update the active incident while the same condition remains active.

---

# 13. Persistence model

Minimum Argus-owned relational entities:

```text
ArgusConfiguration
ArgusProcessSnapshot
ArgusLockSnapshot
ArgusDatabaseSnapshot
ArgusGlobalSnapshot
ArgusTaskSnapshot
ArgusBehaviorBaseline
ArgusIncident
ArgusIncidentEvidence
ArgusReportExecution
```

Optional later entities:

```text
ArgusRunbook
ArgusResolution
```

## 13.1 Incident

Minimum fields:

```text
id
type
severity
status
title
summary
started_at
last_seen_at
resolved_at
namespace
primary_pid
primary_global
primary_database
behavior_score
impact_score
confidence
fingerprint
created_by
resolution
```

## 13.2 Evidence

Evidence types:

```text
PROCESS
LOCK
LOG
GLOBAL
DATABASE
TASK
SQL
SYSTEM
BEHAVIOR
```

Evidence must preserve captured facts sufficient to understand an incident after the live resource disappears.

## 13.3 Retention defaults

Suggested defaults:

```text
Raw process snapshots      7 days
Raw lock snapshots         30 days
Incident evidence          90 days
Behavior aggregates        365 days
Database growth            365 days
Global growth              365 days
Incidents                  365 days
```

Retention must be configurable.

---

# 14. Background collection

Do not run permanent Flask background threads.

Use IRIS Task Manager as the scheduler and invoke Embedded Python collector entry points.

Concept:

```text
IRIS Task Manager
   ↓
%SYS.Python.Run(...)
   ↓
argus.jobs / argus.collectors
   ↓
Embedded Python collection
```

References:

- Task Manager: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSA_manage_taskmgr
- Task APIs: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=ITECHREF_task
- `%SYS.Python`: https://docs.intersystems.com/irisforhealthlatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.Python&LIBRARY=%25SYS

Recommended initial collection policy:

```text
Process deep detail        on demand / selective
Lock snapshots             configurable; short interval only when enabled
Database snapshot          hourly or daily logical interval
Global snapshot            daily or manual
Task behavior              after task history refresh
Incident evaluation        after relevant collection
```

Do not turn Argus into a full telemetry warehouse.

---

# 15. Namespace topology

Argus must make logical-to-physical IRIS storage relationships visible.

Primary SysAdmin sources:

- `/v2/namespaces`
- `/v2/namespace`
- `/v2/databases`
- `/v2/database`
- `/v2/database-dir`

Native enrichment:

- `Config.MapGlobals`
- `%SYS.Namespace.GetGlobalDest()` or verified equivalent
- supported routine/package mapping APIs where needed.

References:

- `Config.MapGlobals`: https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=Config.MapGlobals&LIBRARY=%25SYS
- DB/global location: https://community.intersystems.com/post/how-get-db-and-global-location-information
- Global original namespace/mapping: https://community.intersystems.com/post/how-find-globals-original-namespace-potentially-mapped-different-namespace
- Namespace/database basics: https://community.intersystems.com/post/namespaces-and-databases-basics-inner-workings-intersystems-iris

Required user question:

> Where does `^App.OrderD` physically live when accessed from `PRODUCTION`?

Desired resolution:

```text
Namespace
  ↓
Mapping resolution
  ↓
Physical database
  ↓
Directory
  ↓
Global
```

---

# 16. Database and global growth

## 16.1 Database growth

Persist lightweight database snapshots using data available through SysAdmin database endpoints.

Derive:

- current size;
- 24-hour change;
- 7-day change;
- 30-day change;
- rate/day;
- deviation from historical behavior.

Primary source:

- `mainspec_v2.json`: `/v2/database`, `/v2/database-dir`, `/v2/databases`

## 16.2 Global growth

Use native IRIS APIs through Embedded Python for global-level sizing.

Preferred documented source:

- `%Library.GlobalEdit.GetGlobalSize(...)`

References:

- `%Library.GlobalEdit`: https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25Library.GlobalEdit&LIBRARY=%25SYS
- Community sizing article: https://community.intersystems.com/post/determining-global-and-table-sizes-intersystems-iris

Recurring collection must prefer an efficient estimate mode where supported and verified.

Do not perform full expensive global scans on ordinary page requests.

Required flow:

```text
Database growth anomaly
   ↓
Which globals contributed?
   ↓
Which namespace exposes them?
   ↓
Is this behavior expected for this period?
```

---

# 17. IRISTEMP Investigator

Goal:

```text
IRISTEMP pressure
   ↓
process-private global usage
   ↓
PID
   ↓
routine / namespace
   ↓
Process Investigator
```

Useful process context includes `PrivateGlobalBlockCount` where available.

References:

- Process Private Globals: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GCOS_ppg
- `%SYS.ProcessQuery`: https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.ProcessQuery&LIBRARY=%25SYS
- Community investigation: https://community.intersystems.com/post/how-identify-which-temporary-globals-are-consuming-size-iristemp-database

This feature is P1 unless the target IRIS version exposes the necessary measurements early and safely.

---

# 18. Reports

Required reports:

## 18.1 Incident Report

Must show:

- incident classification;
- severity/confidence;
- start/end/duration;
- deterministic reasons;
- timeline;
- related process/routine/global/database/namespace;
- preserved evidence;
- resolution.

## 18.2 Lock Report

Must show:

- incidents in period;
- top resources/globals;
- top owner processes where meaningful;
- total/peak contention impact;
- normal vs unusual time windows.

## 18.3 Growth Report

Must show:

- database growth;
- top global contributors;
- expected vs observed growth;
- anomalies/incidents.

## 18.4 Behavior Report

Must explain what is normal for a resource/workload by time/day and expose baseline confidence.

V1 export targets:

- HTML;
- JSON;
- CSV where tabular.

PDF is not required.

---

# 19. Logs and Community Opportunity

Argus must support an Error Investigation flow, but AI remains optional.

Community Opportunity:

- DPI-I-574 — AI analysis of error logs: https://ideas.intersystems.com/ideas/DPI-I-574

Flow:

```text
Error/log evidence
   ↓
Normalize timestamp/source/PID/namespace/routine where available
   ↓
Correlate with process/lock/storage/incident context
   ↓
Preserve evidence
   ↓
Optional similar incident search
   ↓
Optional AI explanation
```

The AI may:

- summarize evidence;
- classify error text;
- explain relationships;
- suggest investigation steps;
- compare with previous incidents/runbooks.

The AI may not:

- terminate processes;
- delete locks;
- modify security;
- rebuild indexes;
- execute arbitrary generated code;
- perform autonomous administrative actions.

---

# 20. Vector Search

Vector Search is P2/bonus, not a prerequisite for incidents.

Use cases:

```text
current incident → similar incidents
error summary    → similar error/resolution
incident         → related runbook
```

Reference:

- IRIS Vector Search: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSQL_vecsearch

Do not use vector search where deterministic filtering is sufficient.

---

# 21. UX implementation rules

The coding agent must implement the following principles:

1. **Operational question first.** Link related entities instead of forcing manual subsystem hopping.
2. **Context beside values.** Current value + expected behavior + impact.
3. **Explain incidents deterministically.** Always show “Why this is an incident.”
4. **Distinguish live and historical.** Never render historical evidence as if it were still active.
5. **Progressive disclosure.** Lists stay fast; deep process/lock detail loads on demand.
6. **Do not hide missing data.** Show `Unavailable`, `Unsupported` or `Insufficient history` rather than fabricating values.
7. **Dangerous actions are secondary.** Investigation is the dominant interaction.

See `PRODUCT_UX.md` for screen-level details.

---

# 22. Safety and authorization

Classify actions:

## Read

```text
inspect
search
analyze
report
validate
```

## Controlled write

```text
run task
suspend/resume process
collect statistics if implemented
```

## Dangerous

```text
terminate process
delete lock
rebuild index
modify security
delete configuration
```

Dangerous operations require:

```text
preview
→ target/context display
→ privilege check
→ explicit confirmation
→ execute
→ read-back verification where possible
→ audit/event record
```

AI never performs dangerous operations.

---

# 23. Required acceptance scenarios

These scenarios are product acceptance tests, not marketing examples.

## Scenario 1 — Noon lock peak is normal

Historical:

```text
^OrderD, weekdays 12:00–12:15
median 493
p95 621
```

Observed:

```text
12:07
544 locks
0 affected waiters
transaction ages within normal range
```

Expected:

```text
Observation = NORMAL
No incident
```

Feasibility:

- `/v2/locks` in `mainspec_v2.json`
- `%SYS.LockQuery`
- historical lock snapshots stored by Argus.

## Scenario 2 — Same activity at 03:00 is anomalous

Historical:

```text
^OrderD, weekdays 03:00–03:15
median 11
p95 31
```

Observed:

```text
03:07
481 locks
```

Expected:

```text
Anomaly immediately
Incident after persistence/impact conditions are met
```

Feasibility:

- same lock sources as Scenario 1;
- Argus temporal baseline engine.

## Scenario 3 — Normal volume, abnormal impact

Observed at noon:

```text
510 locks = historically normal
23 affected processes
oldest wait 108s
primary transaction 18m
```

Expected:

```text
LOCK VOLUME = NORMAL
IMPACT = ABNORMAL
INCIDENT = HIGH
```

Feasibility:

- `/v2/locks`, `/v2/processes`, `/v2/process`
- `%SYS.LockQuery`, `%SYS.ProcessQuery`
- correlation engine.

## Scenario 4 — Process outside usual execution window

Historical signature:

```text
namespace + routine + user
normally observed 11:45–13:20 weekdays
```

Observed:

```text
03:12
same workload signature
```

Expected:

```text
Temporal anomaly
No incident unless persistence/impact/correlated signals justify it
```

Feasibility:

- `/v2/processes`, `/v2/process`
- `%SYS.ProcessQuery`
- Argus process snapshots/baselines.

## Scenario 5 — Unexpected database/global growth

Historical:

```text
PROD_DATA typical daily growth 720 MB
p95 1.1 GB/day
```

Observed:

```text
+5.8 GB today
^ServiceLogD contributes +4.9 GB
```

Expected:

```text
Storage anomaly
Growth incident if threshold/persistence/risk criteria are met
```

Feasibility:

- `/v2/databases`, `/v2/database-dir`
- `%Library.GlobalEdit.GetGlobalSize(...)`
- Argus snapshots.

## Scenario 6 — Expected temporary growth fails to recover

Historical:

```text
03:00 import grows ^ImportTemp temporarily
normally returns near baseline by 07:00
```

Observed:

```text
03:10 expected growth
07:00 growth remains
```

Expected:

```text
03:10 = expected behavior
07:00 = recovery anomaly
possible incident
```

Feasibility:

- global snapshots + temporal baseline.

## Scenario 7 — IRISTEMP pressure traced to process

Observed:

```text
IRISTEMP pressure
PID 8142 has unusually high private-global blocks
```

Expected:

```text
IRISTEMP Investigator identifies PID/routine/namespace
link opens Process Investigator
```

Feasibility:

- `%SYS.ProcessQuery`
- `PrivateGlobalBlockCount`
- Process Private Globals documentation.

## Scenario 8 — Task runtime anomaly

Historical:

```text
CleanupTask median 3m12s
p95 4m10s
```

Observed:

```text
28m43s
```

Expected:

```text
Task anomaly
Incident only if configured impact/repetition rules are met
```

Feasibility:

- `/v2/task/history`
- `%SYS.Task.History`
- Argus task baseline.

## Scenario 9 — Error becomes correlated incident evidence

Observed:

```text
error event with timestamp/PID/namespace context
```

Expected:

```text
normalize → correlate to active/recent process/lock incident → preserve evidence
optional AI explanation later
```

Feasibility:

- audit/log sources available in target runtime;
- `/v2/security/audit/records` where applicable;
- Argus incident engine;
- DPI-I-574 for optional AI layer.

## Scenario 10 — Resolve logical global to physical database

Input:

```text
Namespace = PRODUCTION
Global = ^ServiceLogD
```

Expected:

```text
mapping/default resolution
→ physical database
→ directory
→ global context
```

Feasibility:

- `/v2/namespaces`, `/v2/databases`, `/v2/database-dir`
- `Config.MapGlobals`
- `%SYS.Namespace.GetGlobalDest()` or verified current equivalent.

---

# 24. Priority classes

## P0 — submission-blocking

- clean repository/template;
- deterministic Docker build;
- Embedded Python import in real IRIS runtime;
- `/argus` WSGI route;
- SysAdmin adapter;
- functional coverage of all six contest areas;
- Overview;
- Process list + Process Investigator;
- Lock list + Lock Investigator;
- basic incident persistence and incident detail;
- English README;
- tests/smoke tests for P0 paths.

## P1 — high-value differentiation

- lock history;
- behavior baseline;
- incident promotion/dedup/resolution;
- namespace topology;
- database growth;
- global growth;
- reports;
- Task Health;
- IRISTEMP Investigator.

## P2 — only after P0/P1 are stable

- Vector Search;
- similar incident search;
- DPI-I-574 AI explanation;
- SQL/index doctor extensions;
- advanced topology visualizations;
- optional external observability integration.

---

# 25. Bonus strategy relevant to implementation

Official bonus announcement:

- https://community.intersystems.com/post/technology-bonuses-intersystems-programming-contest-build-your-own-management-portal

Product-aligned bonuses:

| Bonus | Target | Planning value |
|---|---|---:|
| Embedded Python | core architecture | 3 |
| IRIS Vector Search | similar incidents | 2 conservatively |
| Docker | Community Edition runtime | 2 |
| ZPM/IPM package | reproducible deployment | 2 |
| Online Demo | runnable demo instance | 2 |
| Community Opportunity | DPI-I-574 | 4 |

The published bonus post currently contains inconsistent wording for Vector Search: the summary lists **2**, while the detailed paragraph says **5**. Engineering planning must assume **2** unless the organizers clarify otherwise.

Articles, videos and promotional work are outside this engineering specification and must not distract coding agents.

---

# 26. Explicit non-goals

Do not turn Argus into:

- a complete replacement for every Management Portal page;
- a generic APM;
- a Grafana clone;
- an autonomous DBA;
- an LLM agent with system-control privileges;
- an external microservice architecture;
- a telemetry warehouse retaining every sample forever;
- an ECP/mirroring/sharding manager in V1.

Do not automatically:

- terminate processes;
- delete locks;
- rebuild indexes;
- run TUNE TABLE everywhere;
- change security configuration;
- execute arbitrary generated code.

---

# 27. Testing and build requirements

Follow `AGENT.md` strictly.

Minimum test layers:

## Unit

- baseline statistics;
- anomaly classification;
- incident promotion;
- incident deduplication;
- resolution grace period;
- fingerprint generation;
- growth calculations.

## Adapter

- SysAdmin response normalization;
- 401/403/404/error handling;
- missing/optional fields;
- timeout handling.

## Integration

- WSGI route through real IRIS Web Application;
- Embedded Python import in IRIS runtime;
- representative SysAdmin request;
- representative IRIS SQL persistence operation;
- Process/Lock path against target container;
- deterministic scenario data where safe.

## Build/smoke

At completion of each major phase, execute the repository's actual build/start commands. For Docker Compose the normal sequence is:

```bash
docker compose down --remove-orphans
docker compose build
docker compose up -d
docker compose ps
docker compose logs --no-color
```

Then execute real HTTP smoke tests against `/argus` and at least one real IRIS-backed operation.

Do not declare a milestone complete if runtime validation fails.

---

# 28. Definition of Done

Contest-ready V1 is complete only when all applicable items are true:

- [ ] repository starts from the approved IRIS template and sample code is removed;
- [ ] IRIS Community Edition container starts reproducibly;
- [ ] `/argus` runs through `%SYS.Python.WSGI`;
- [ ] Embedded Python dependencies are installed in the actual IRIS Python environment;
- [ ] all six contest task families have functional, real-IRIS-backed coverage;
- [ ] SysAdmin calls are centralized and verified against `mainspec_v2.json`;
- [ ] Process Investigator works with real process data;
- [ ] Lock Investigator works with real lock data;
- [ ] a live condition can be preserved as historical incident evidence;
- [ ] incident detail explains why the incident exists without requiring AI;
- [ ] baseline/anomaly behavior passes the required scenarios;
- [ ] database/global growth paths are safe and do not perform uncontrolled expensive scans;
- [ ] dangerous operations require explicit confirmation and authorization;
- [ ] tests pass;
- [ ] Docker build/start succeeds;
- [ ] logs are inspected for runtime failures;
- [ ] README is in English and reflects the finished product;
- [ ] no irrelevant template artifacts remain.

---

# 29. Reference map

## Contest and API

- https://community.intersystems.com/post/intersystems-programming-contest-build-your-own-management-portal
- https://community.intersystems.com/post/technology-bonuses-intersystems-programming-contest-build-your-own-management-portal
- https://github.com/intersystems-community/sysadmin-api-specification
- https://github.com/intersystems-community/sysadmin-api-specification/blob/master/mainspec_v2.json
- https://raw.githubusercontent.com/intersystems-community/sysadmin-api-specification/master/mainspec_v2.json

## Template / WSGI / Embedded Python

- https://github.com/intersystems-community/intersystems-iris-dev-template
- https://community.intersystems.com/post/wsgi-support-introduction
- https://community.intersystems.com/post/running-wsgi-applications-ipm
- https://community.intersystems.com/post/introduction-python-first-approach-iris
- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GEPYTHON_reference_core
- https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GEPYTHON_runpython
- https://docs.intersystems.com/irisforhealthlatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.Python&LIBRARY=%25SYS

## Processes / locks

- https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.ProcessQuery&LIBRARY=%25SYS
- https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25SYS.LockQuery&LIBRARY=%25SYS
- https://community.intersystems.com/post/whats-taking-so-long-process-sampling-performance-analysis
- https://community.intersystems.com/post/how-do-i-trace-low-level-deadlocks-between-globals-sql-tables-and-object-transactions-across

## Namespace / storage / growth

- https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=Config.MapGlobals&LIBRARY=%25SYS
- https://docs.intersystems.com/irislatest/csp/documatic/%25CSP.Documatic.cls?CLASSNAME=%25Library.GlobalEdit&LIBRARY=%25SYS
- https://community.intersystems.com/post/how-get-db-and-global-location-information
- https://community.intersystems.com/post/how-find-globals-original-namespace-potentially-mapped-different-namespace
- https://community.intersystems.com/post/namespaces-and-databases-basics-inner-workings-intersystems-iris
- https://community.intersystems.com/post/determining-global-and-table-sizes-intersystems-iris

## Tasks / IRISTEMP / audit

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

---

# 30. Final implementation test

If an implementation decision does not help Argus do at least one of the following, it probably does not belong in V1:

```text
administer a required contest area
investigate a real IRIS runtime problem
preserve evidence that would otherwise disappear
explain abnormal behavior in temporal context
resolve logical IRIS resources to physical context
report an operational incident clearly
```
