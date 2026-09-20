# Argus IRIS — Product and UX Specification

**Project:** Argus IRIS  
**Audience:** UI implementation, product decisions, coding agents  
**Companion technical specification:** `SPEC.md`

---

# 1. Product position

Argus IRIS is a troubleshooting-first Management Portal for InterSystems IRIS.

It must cover the six Management Portal areas requested by the contest, but it must not become a generic clone of the native portal.

Its flagship value is investigation:

> **Why is IRIS behaving this way, is this behavior normal for the current context, what is involved, what is impacted, and what evidence should be preserved?**

The name references **Argus Panoptes**, the many-eyed guardian from Greek mythology.

```text
Processes  👁
Locks      👁
Globals    👁
Databases  👁
Tasks      👁
Logs       👁
History    👁
     \      |      /
      operational context
```

Tagline:

> **Argus IRIS — See beyond the symptoms.**

---

# 2. User problem

IRIS already exposes deep administrative information. The operational pain is correlation and timing.

A support ticket rarely begins with a precise diagnosis. It begins with:

> “The system is slow.”

or:

> “The application is stuck.”

or:

> “The IRIS disk is growing too fast.”

The operator then has to reconstruct a story:

```text
Process
  ↓
State
  ↓
Routine / generated .SQL.cls
  ↓
Transaction
  ↓
Lock
  ↓
Global
  ↓
Namespace / mapping
  ↓
Physical database
  ↓
Affected processes
```

Storage investigations have the same problem:

```text
Database grew
  ↓
Which global grew?
  ↓
Is that normal for this day/time?
  ↓
Which namespace exposes it?
  ↓
Is the growth temporary or persistent?
```

Argus makes these relationships navigable.

---

# 3. Product principles

## 3.1 Context is more important than magnitude

A large number is not automatically unhealthy.

```text
12:05
^OrderD = 520 locks
```

may be normal if the environment normally peaks around lunch.

The same resource at:

```text
03:05
^OrderD = 480 locks
```

may be exceptional if the historical p95 for that period is 31.

Argus should always try to show:

```text
current value
+ expected value now
+ deviation
+ impact
```

## 3.2 Preserve important evidence

Locks, processes and operational context can disappear before an administrator investigates them.

Argus should preserve selected evidence for meaningful conditions instead of storing every metric indefinitely.

Community motivation:

- https://community.intersystems.com/post/how-do-i-trace-low-level-deadlocks-between-globals-sql-tables-and-object-transactions-across

## 3.3 Evidence before AI

The product must be useful with no LLM configured.

The incident engine is deterministic. AI is an optional explanation layer.

## 3.4 Investigation before action

Dangerous administrative actions exist only as secondary controls.

The product experience is primarily:

```text
inspect → understand → correlate → preserve → report
```

not:

```text
click buttons to mutate the system
```

---

# 4. Contest fit

Official contest areas:

- Web Apps / REST;
- Permissions;
- Security & Secrets;
- Tasks;
- Operating System / runtime;
- Logs.

Official announcement:

- https://community.intersystems.com/post/intersystems-programming-contest-build-your-own-management-portal

SysAdmin API:

- https://github.com/intersystems-community/sysadmin-api-specification/blob/master/mainspec_v2.json

An official contest-team comment states that an alternative application is valid **“as long as it implements these calls”**, followed by those six families.

Product strategy:

> **Cover all six; specialize deeply in runtime investigation.**

Depth allocation:

```text
Applications      ███
Permissions       ███
Security          ███
Tasks             █████
Logs              ███████
System            ████████
Processes         ██████████
Locks             ██████████
Incidents         ██████████
Growth            ████████
```

---

# 5. Primary users

## Support / sustaining developer

Needs to answer:

- Which process is stuck?
- Which routine or generated `.SQL.cls` is executing?
- Is the process waiting on or holding a lock?
- What global is involved?
- Did the problem disappear before investigation?

## IRIS administrator / infrastructure engineer

Needs to answer:

- Which database is growing?
- Which globals contributed?
- Is IRISTEMP pressure process-related?
- Are Tasks taking abnormally long?
- What happened before an incident?

## DBA / performance engineer

Needs to answer:

- Is this workload normal for the current time?
- Did storage behavior change?
- Is SQL/index health worth deeper inspection?
- Can a runtime symptom be tied to a physical resource?

---

# 6. Information architecture

```text
ARGUS IRIS

Overview

MANAGE
├── Applications & REST
├── Permissions
├── Security & Secrets
├── Tasks
├── System
└── Logs

INVESTIGATE
├── Processes
├── Locks
├── Incidents
└── Error Investigation

STORAGE
├── Databases
├── Namespace Topology
├── Global Explorer
├── IRISTEMP
└── Growth

REPORTS
├── Incidents
├── Lock Contention
├── Growth
└── Behavior
```

SQL/Index Health may be introduced after the core runtime/storage experience is stable.

---

# 7. UX rules

## 7.1 Start from the operational question

Every relevant object should link to its context.

Preferred flow:

```text
Incident
  ↓
Lock
  ↓
Process
  ↓
Routine
  ↓
Global
  ↓
Database
```

## 7.2 Put context beside numbers

Bad:

```text
Locks: 481
```

Argus:

```text
^OrderD lock activity
Current       481
Median now     11
p95 now        31
Deviation     ~15× p95
Affected       17 processes
```

## 7.3 Explain every incident

Every incident has a visible section:

```text
WHY THIS IS AN INCIDENT

• lock activity is 15× historical p95 for this time bucket
• condition persisted for 94 seconds
• 17 processes were affected
• primary PID has an 11-minute transaction
```

This explanation is deterministic.

## 7.4 Distinguish live and historical

Use explicit labels:

```text
LIVE
```

and:

```text
HISTORICAL SNAPSHOT
```

A resolved incident must never visually imply that its old process or lock is still active.

## 7.5 Progressive disclosure

Lists stay cheap and fast.

Deep details load only when selected:

- current routine/source;
- last global;
- expensive process details;
- graph relationships;
- historical evidence.

## 7.6 Missing data is a valid state

Use:

```text
Unavailable
Unsupported by current IRIS version
Insufficient history
Permission denied
```

Never invent values.

---

# 8. Screen — Overview

Purpose:

> What needs attention now?

Suggested composition:

```text
ARGUS IRIS

CPU 31%   Memory 63%   Processes 48   Open Incidents 3

ATTENTION

HIGH
Lock contention — ^OrderD
17 processes affected

MEDIUM
PROD_DATA growth
+5.8 GB today vs ~0.7 GB expected

MEDIUM
CleanupTask
runtime 6.7× above normal

CURRENT BEHAVIOR
Lock activity     Normal
Storage growth    Elevated
Tasks             1 anomaly
```

Do not make Overview a wall of graphs.

Contest relevance:

- OS/runtime;
- Tasks;
- Logs/incidents;
- navigation to Databases and Processes.

Technical basis:

- `mainspec_v2.json` monitor, processes, tasks and database APIs.

---

# 9. Screen — Applications & REST

Purpose:

- minimum contest coverage;
- clear view of Web Applications and related REST information.

Suggested UI:

```text
APPLICATIONS

/csp/sys            Enabled      %SYS
/api/atelier        Enabled      %SYS
/argus              Enabled      ARGUS
/myapp              Enabled      APP

[ Search ] [ New Application ]
```

Details:

```text
/myapp

Namespace       APP
Enabled         Yes
Authentication  Password / Delegated
Resource        %DB_APP

REST / OpenAPI
GET  /orders
POST /orders
GET  /orders/{id}
```

Do not spend flagship-level effort here.

Technical basis:

- `mainspec_v2.json`: `/v2/web-app`, `/v2/web-apps`.

---

# 10. Screen — Permissions

Purpose:

- minimum usable permission-management view.

Tabs:

```text
Users | Roles | Resources | SQL Privileges
```

Example:

```text
operator

Roles
%Operator
ArgusOperator

Resources
%DB_APP        Read
%Service_SQL   Use
```

Technical basis:

- `mainspec_v2.json` security endpoints.

---

# 11. Screen — Security & Secrets

Tabs may include only capabilities verified in the current API:

```text
Wallet | Audit | Certificates | OAuth
```

Wallet should never reveal secret values unnecessarily.

Argus may use a Wallet collection for optional AI provider credentials:

```text
ARGUS
LLM_PROVIDER
LLM_API_KEY      ********
```

Technical basis:

- `mainspec_v2.json`: `/v2/wallet/*`, `/v2/security/*`.

---

# 12. Screen — Tasks & Task Health

Base list:

```text
TASKS

CleanupTask        Next 02:00   Last: Success
StatsCollection    Next 03:00   Last: Success
ImportOrders       Next 12:00   Last: Success
```

Argus context:

```text
CleanupTask

Last runtime       28m 43s
Typical runtime     3m 12s
Historical p95      4m 10s

6.6× above expected
Status: ANOMALOUS
```

A task anomaly is not automatically an incident.

Technical basis:

- `/v2/tasks`
- `/v2/task`
- `/v2/task/history`
- Task Manager / `%SYS.Task.History`.

---

# 13. Screen — System

Purpose:

- satisfy OS/runtime coverage;
- provide direct navigation into Argus investigations.

Show concise current state:

```text
CPU
Memory / shared memory
Processes
Databases / storage
License usage
Journal status
Other verified runtime resources
```

System values should link into detailed areas rather than duplicating them.

Technical basis:

- `mainspec_v2.json`: `/v2/monitor/*`, `/v2/databases`, `/v2/processes`, `/v2/journal/*`.

---

# 14. Screen — Processes

Administrative list:

```text
PID     User       Namespace    State     CPU     Runtime
8142    appuser    PRODUCTION   LOCKW     1.2%    18m
8211    appuser    PRODUCTION   LOCKW     0.2%     4m
8377    system     %SYS         RUN       4.1%    52m
```

Clicking a PID opens Process Investigator.

Community pain:

- https://community.intersystems.com/post/whats-taking-so-long-process-sampling-performance-analysis

Technical basis:

- `/v2/processes`
- `/v2/process`
- `%SYS.ProcessQuery`.

---

# 15. Screen — Process Investigator

Flagship screen.

Question:

> What is this process doing, and is it unusual?

Suggested layout:

```text
PROCESS 8142                                      HIGH IMPACT

User              appuser
Namespace         PRODUCTION
State             LOCKW
Runtime           18m 41s
Transaction       11m 32s

CURRENT EXECUTION
App.Order.SQL1 +193

LAST GLOBAL
^App.OrderD(89122)

Global references 8.2M
Global updates    183K
Private globals   41K blocks
```

Behavior context:

```text
This workload normally runs:
11:45–13:20 weekdays

Current time:
03:12

Execution-time anomaly: HIGH
```

Relationships:

```text
3 locks owned
17 processes affected
^App.OrderD → PROD_DATA
INC-0042 active
```

Actions such as suspend/resume/terminate remain secondary.

---

# 16. Screen — Locks

List:

```text
Reference             PID      Mode       Routine
^OrderD(89122)        8142     Exclusive  Order.SQL1
^PatientD(921)        8311     Shared     Patient.SQL1
```

Clicking opens Lock Investigator.

Community pain:

- https://community.intersystems.com/post/how-do-i-trace-low-level-deadlocks-between-globals-sql-tables-and-object-transactions-across

Technical basis:

- `/v2/locks`
- `/v2/lock`
- `%SYS.LockQuery`.

---

# 17. Screen — Lock Investigator

Flagship screen.

```text
LOCK INVESTIGATOR

^App.OrderD(89122)

OWNER
PID 8142
App.Order.SQL1 +193
Transaction: 11m 32s

RESOURCE
Namespace       PRODUCTION
Database        PROD_DATA
Global          ^App.OrderD

IMPACT
17 processes affected
Oldest wait: 94s
```

Behavior:

```text
CURRENT LOCK ACTIVITY ON ^OrderD
481

Expected for 03:00–03:15
Median 11
p95    31

~15× historical p95
```

Graph only when relationships are verified:

```text
             PID 8142
          App.Order.SQL1
                │
               owns
                ▼
         ^OrderD(89122)
                │
         ┌──────┼──────┐
         ▼      ▼      ▼
      PID8211 PID8237 PID8271
```

Do not fabricate waiters.

---

# 18. Screen — Incidents

Incidents are not alerts for every large number.

Pipeline:

```text
Observation
  ↓
Behavior comparison
  ↓
Anomaly
  ↓
Persistence + impact + correlation
  ↓
Incident
```

List:

```text
OPEN INCIDENTS

INC-0042 HIGH
Unusual lock contention — ^OrderD
Started 03:07
17 processes affected

INC-0043 MEDIUM
Unexpected PROD_DATA growth
+5.8 GB today
```

Resolved incidents remain searchable.

---

# 19. Screen — Incident Detail

This screen tells the operational story.

```text
INC-0042 — UNUSUAL LOCK CONTENTION

Started    03:07
Resolved   03:12
Duration   5m
Severity   HIGH
Confidence HIGH
```

Why:

```text
• ^OrderD lock activity = 481
• historical p95 at 03:00 = 31
• condition persisted > 60s
• 17 processes were affected
• PID 8142 held the relevant resource
• PID 8142 had an 11-minute transaction
```

Timeline:

```text
03:07:00 abnormal lock level detected
03:07:20 PID 8142 correlated
03:07:40 3 processes affected
03:08:00 8 processes affected
03:09:31 17 processes affected
03:11:20 contention disappeared
03:12:20 incident resolved
```

Related entities must be navigable.

---

# 20. Screen — Behavior / What Is Normal?

Purpose:

- make Argus behavior transparent;
- let administrators validate what Argus has learned.

Example:

```text
RESOURCE: ^OrderD

Weekdays

00:00   ▂
03:00   ▁   median 11 / p95 31
06:00   ▂
09:00   ▅
12:00   █   median 493 / p95 621
15:00   ▆
18:00   ▃
21:00   ▂

Samples: 26
Confidence: HIGH
```

Cold start:

```text
LEARNING MODE
9 samples collected
Confidence: LOW
```

---

# 21. Screen — Namespace Topology

IRIS-specific differentiator.

```text
                    PRODUCTION
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
      PROD_CODE      PROD_DATA      IRISTEMP
                        │
                        ├── ^OrderD
                        ├── ^OrderI
                        └── ^PatientD

Mappings
^Audit*  ─────────────────► AUDIT_DATA
^Config  ─────────────────► SHARED_DATA
```

Questions answered:

- What is the default globals database?
- What is the routines database?
- What mappings override the defaults?
- Where does this global physically live?
- Which namespaces expose the same data?

Community references:

- https://community.intersystems.com/post/how-get-db-and-global-location-information
- https://community.intersystems.com/post/how-find-globals-original-namespace-potentially-mapped-different-namespace
- https://community.intersystems.com/post/namespaces-and-databases-basics-inner-workings-intersystems-iris

---

# 22. Screen — Global Explorer

Input:

```text
Namespace: PRODUCTION
Global:    ^ServiceLogD
```

Output:

```text
^ServiceLogD

Physical database      PROD_DATA
Estimated size         164 GB
Allocated              188 GB
30-day growth          +21.8 GB
Typical daily growth   ~700 MB
Today's growth         +4.9 GB
Status                 ANOMALOUS

Visible from
PRODUCTION
REPORTING
```

Community sizing reference:

- https://community.intersystems.com/post/determining-global-and-table-sizes-intersystems-iris

---

# 23. Screen — Growth

Database view:

```text
Database       Current     24h      30d       Status
PROD_DATA      284 GB      +5.8GB   +43GB     HIGH
AUDIT_DATA      81 GB      +120MB   +3.2GB    NORMAL
```

Details:

```text
PROD_DATA

Current                  284 GB
Typical daily growth     720 MB
Today's growth           5.8 GB
Historical p95           1.1 GB/day
```

Contributors:

```text
^ServiceLogD     +4.9 GB
^ServiceLogI     +0.7 GB
^OrderD          +0.2 GB
```

Do not create a growth incident solely because a value is large. Use temporal behavior and risk.

---

# 24. Screen — IRISTEMP Investigator

```text
IRISTEMP

Current usage / trend

TOP PRIVATE GLOBAL CONSUMERS

PID 8142    Report.SQL1     high PPG usage
PID 8191    Import.SQL1     high PPG usage
```

Clicking a PID opens Process Investigator.

Community reference:

- https://community.intersystems.com/post/how-identify-which-temporary-globals-are-consuming-size-iristemp-database

---

# 25. Screen — Logs & Error Investigation

Base log view should expose source and context clearly:

```text
Timestamp | Severity | Source | PID | Namespace | Message
```

Potential source groups:

```text
IRIS audit/system evidence
Tasks
WSGI
Argus
Security
```

Relevant rows expose:

```text
[ Investigate ]
```

which attempts:

```text
Error
  ↓
PID / namespace / time correlation
  ↓
Process / Lock / Incident
```

---

# 26. Community Opportunity — DPI-I-574

Reference:

- https://ideas.intersystems.com/ideas/DPI-I-574

Argus implementation:

```text
Error evidence
  ↓
Normalization
  ↓
Correlation with Argus evidence
  ↓
Similar historical incidents (optional Vector Search)
  ↓
Optional AI explanation
```

The LLM is an explanatory assistant, never the incident detector or administrator.

---

# 27. Reports

## Incident Report

Operational narrative + reasons + timeline + evidence + resolution.

## Lock Report

Contention history + resources + impact + normal/unusual windows.

## Growth Report

Database/global growth + contributors + expected behavior.

## Behavior Report

What “normal” means for a selected resource/workload.

---

# 28. Core behavioral scenarios

## A — Noon peak is normal

```text
^OrderD current = 544
historical noon p95 = 621
no wait impact
→ normal
```

## B — Same activity at 03:00

```text
^OrderD current = 481
historical 03:00 p95 = 31
→ anomaly
→ incident if persistent/impactful
```

## C — Normal volume, abnormal impact

```text
lock volume normal
23 affected processes
oldest wait 108s
→ incident
```

## D — Unusual process execution time

```text
routine normally runs at noon
same signature observed 03:12
→ temporal anomaly
```

## E — Unexpected growth

```text
expected daily DB growth ~720 MB
observed +5.8 GB
→ anomaly / possible incident
```

## F — Expected nightly growth fails to recover

```text
03:00 temporary increase expected
07:00 still elevated
→ recovery anomaly
```

## G — IRISTEMP pressure

```text
IRISTEMP rises
PPG-heavy PID identified
→ process investigation
```

## H — Error correlation

```text
error event
→ timestamp/PID/namespace correlation
→ incident evidence
```

---

# 29. Community pains informing Argus

## Process/performance investigation

Community reference:

- https://community.intersystems.com/post/whats-taking-so-long-process-sampling-performance-analysis

Product implication:

- Process Investigator must make process state/routine/runtime context navigable.

## Historical lock evidence

Community reference:

- https://community.intersystems.com/post/how-do-i-trace-low-level-deadlocks-between-globals-sql-tables-and-object-transactions-across

Product implication:

- Argus stores selected lock/process snapshots for later incident analysis.

## Global/table sizing

Community reference:

- https://community.intersystems.com/post/determining-global-and-table-sizes-intersystems-iris

Product implication:

- growth investigation uses efficient size estimates and avoids expensive scanning by default.

## IRISTEMP / process-private globals

Community reference:

- https://community.intersystems.com/post/how-identify-which-temporary-globals-are-consuming-size-iristemp-database

Product implication:

- IRISTEMP Investigator correlates pressure to processes.

## Namespace/global mappings

Community references:

- https://community.intersystems.com/post/how-get-db-and-global-location-information
- https://community.intersystems.com/post/how-find-globals-original-namespace-potentially-mapped-different-namespace

Product implication:

- logical namespace/global relationships must be resolvable to physical storage.

## SQL statistics / index validation

Useful future references:

- https://community.intersystems.com/post/towards-smarter-table-statistics
- https://community.intersystems.com/post/how-get-corrupted-index-names-only-large-tables

Product implication:

- SQL/index features should diagnose before performing expensive maintenance and remain after the core runtime product.

---

# 30. Competitive posture

Argus should not compete on the number of administrative CRUD forms.

Its position is:

```text
Traditional portal
“How do I configure IRIS?”

Observability cockpit
“How is IRIS doing?”

Argus IRIS
“Why is IRIS behaving this way, what is involved, and has it happened before?”
```

The minimum contest modules prove coverage. The investigation flow creates differentiation.

---

# 31. Bonus-aware product decisions

Official bonus reference:

- https://community.intersystems.com/post/technology-bonuses-intersystems-programming-contest-build-your-own-management-portal

Bonuses that naturally fit the product:

- Embedded Python;
- Docker;
- ZPM/IPM;
- Online Demo;
- IRIS Vector Search after core;
- Community Opportunity DPI-I-574 after core.

The product must not be reshaped to chase articles, videos or promotional bonus work.

---

# 32. Product priorities

## P0

- six contest areas functional;
- Overview;
- Process Investigator;
- Lock Investigator;
- basic incidents;
- real IRIS integration;
- English README and reproducible startup.

## P1

- lock history;
- baseline/anomaly engine;
- incident lifecycle;
- namespace topology;
- database/global growth;
- reports;
- Task Health;
- IRISTEMP.

## P2

- Vector Search;
- AI error explanation;
- SQL/index extensions;
- advanced visual polish.

---

# 33. What Argus must not become

Argus must not become:

- a generic monitoring dashboard;
- a clone of the full Management Portal;
- an autonomous remediation agent;
- an LLM wrapper over `messages.log`;
- a collection of static red/yellow/green thresholds;
- a product that needs external observability infrastructure to function.

---

# 34. Reference user journey

```text
1. Operator opens Overview.
2. HIGH incident shows unusual ^OrderD contention at 03:07.
3. Incident Detail explains the baseline deviation and impact.
4. Operator opens the lock.
5. Lock Investigator shows owner PID and resource.
6. Operator opens PID 8142.
7. Process Investigator shows App.Order.SQL1 and transaction context.
8. Operator opens ^App.OrderD.
9. Namespace/Global view resolves it to PROD_DATA.
10. Historical timeline remains available after the contention disappears.
11. Incident Report preserves the evidence.
```

That journey is the product.

---

# 35. Product success criterion

Argus succeeds when it can turn:

> “The system was slow around 03:00.”

into something like:

> “At 03:07, `^OrderD` reached lock activity far above its historical p95 for that time window. The condition persisted, affected 17 processes, and was associated with PID 8142 executing `App.Order.SQL1` in `PRODUCTION`. The global resolves to `PROD_DATA`. The live condition cleared at 03:11, but the incident timeline and evidence were preserved.”

without requiring the operator to manually reconstruct the same story across unrelated tools.
