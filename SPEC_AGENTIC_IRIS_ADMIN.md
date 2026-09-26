# SPEC-001 — AGENTIC ADMINISTRATION PLATFORM FOR INTERSYSTEMS IRIS

**Status:** Implementation specification; not a claim of completed implementation.  
**Baseline date:** 2026-09-23.  
**Project:** Greenfield. Retire ARGUS as the application architecture.  
**Audience:** DBAs, system administrators, implementers, and reviewers.  
**Backend:** 100% Python, served through IRIS WSGI. No Java. No Quarkus.  
**System of record:** InterSystems IRIS SQL tables.  
**Authoritative SysAdmin contract:** `specification/mainspec_v2.json`.

## 1. MISSION AND COMMAND LANGUAGE

BUILD an open, AI-first administration platform for InterSystems IRIS. PROVIDE a GUI in which the DBA defines agents, prompts, tools, routines, memory scopes, schedules, and AI Watches. IMPLEMENT generic execution infrastructure in Python. STORE operational behavior and its versions in IRIS.

SHALL and MUST identify mandatory requirements. SHOULD identifies a recommendation. MAY identifies an optional capability. DO NOT interpret a model recommendation as authorization.

DO NOT hardcode SecurityAgent, PerformanceAgent, or other operational personalities. Seed examples MAY exist as editable database records. DO NOT implement a conventional portal with a summarization chatbot as the primary experience.

This document consolidates the referenced design and supplies implementation details where needed. The current requirement for explicit DBA approval overrides any earlier suggestion that child-agent creation could be autonomous. Administrative endpoint availability SHALL be established from the pinned specification and the deployed IRIS release, not from this document's examples.

## 2. NON-NEGOTIABLE ORDERS

| ID | Order |
|---|---|
| INV-01 | IMPLEMENT all application backend behavior in Python; expose the web backend through IRIS WSGI. |
| INV-02 | PERSIST agents, prompts, tools, routines, watches, policies, memory, and execution history in IRIS tables. |
| INV-03 | IMPORT SysAdmin tools from `specification/mainspec_v2.json`; do not hand-invent administrative endpoints. |
| INV-04 | IMPORT all SysAdmin operations disabled; on first setup, enable only the explicitly reviewed read-only preset. Thereafter execute only operations enabled by an authorized DBA and permitted by target credentials. |
| INV-05 | REQUIRE an Action Proposal and explicit DBA approval for managed SQL and application behavior changes. For a pinned SysAdmin API operation, an explicit DBA availability toggle is standing authorization for assigned agents to invoke it automatically, including scheduled runs; no per-call approval is required. |
| INV-06 | EXECUTE the exact approved action. Do not regenerate arguments with an LLM after approval. |
| INV-07 | REVALIDATE permissions, target identity, contract, expiry, and current resource state immediately before mutation. |
| INV-08 | DENY privilege escalation through child agents, delegation, SQL, custom tools, memory, or configuration changes. |
| INV-09 | MAKE AI Watches and Alerts a central product feature. Never equate an alert with approval to remediate. |
| INV-10 | RECORD evidence and outcomes. Treat uncertainty as uncertainty; never report an unverified mutation as successful. |

### 2.1 Scope of approval

Apply INV-05 to managed SQL and changes to application behavior: agent definitions, tool bindings, prompts, policies, routines, watches, model settings, and connection targets. A DBA editing a form SHALL review its exact proposed change and explicitly approve it. Merely saving a draft is not approval to activate it. SysAdmin API execution is the exception: a `DBAApprover` can enable a pinned operation as a standing grant; disabling it blocks future dispatches, while an in-flight request may finish. This grant does not add privileges to the target credential or authorize arbitrary URLs, SQL, or shell commands.

The runtime MUST persist proposals, runs, messages, findings, audit entries, alert lifecycle events, queue state, and extracted memory without recursively requesting approval. These are narrowly defined bookkeeping operations implemented by trusted repositories. They MUST NOT expose arbitrary SQL or accept caller-selected tables, privileges, targets, or executable configuration. An agent MAY create a draft child-agent proposal; only the approved activation creates the effective agent definition.

Initial installation and migrations require an explicit operator-initiated deployment. That authorization SHALL NOT become standing permission for subsequent agent mutations. Maintain a separate deployment identity and migration ledger.

## 3. ARCHITECTURE

```text
DBA Browser
    |
Web Server / IRIS Web Gateway
    |
Python WSGI Control Plane
    +-- Authentication / Authorization / GUI APIs
    +-- Agent and Routine Runtime
    +-- Prompt Compiler / Model Provider Adapter
    +-- Tool Registry / Policy Gateway
    +-- Action Proposal / Approval Service
    +-- Memory Service / Watch and Alert Service
    |
    +-- IRIS SQL: configuration, queue, evidence, audit, VECTOR memory
    |
    +-- Restricted READ executor -----------------> managed IRIS
    +-- Approved-action mutation executor --------> managed IRIS

Python Background Worker
    +-- durable jobs, schedules, watches, memory extraction
    +-- same policy gateway; no privileged shortcut
```

Separate application persistence from managed targets. Identify each target by immutable instance ID, connection profile version, environment, and namespace. Even when both reside in one IRIS installation, separate credentials and SQL grants.

Use Flask as the initial WSGI framework. Use a Python provider adapter for model calls; LangChain-compatible integration is optional. Provider libraries SHALL NOT execute tools outside the gateway. The browser SHALL NOT receive SysAdmin credentials or call administrative APIs directly.

## 4. IRIS HOSTING AND PYTHON EXECUTION

INSTALL the WSGI framework and pinned dependencies in the IRIS-compatible Python environment. EXPORT `application` from `app/wsgi.py`. CONFIGURE an IRIS Web Application with the application namespace, WSGI enabled, module/callable name, and application directory. Select authenticated access and configure Web Gateway routing. Follow [R2]; use the deployed release's documentation.

Keep scheduled work outside WSGI request lifetimes. RUN a supervised Python worker using the supported IRIS Python execution environment. Prove `import iris` and parameterized SQL work under both WSGI and the worker before implementing the runtime. Do not assume an ordinary external Python interpreter automatically has Embedded Python connectivity. Follow [R3] and [R4].

Return a durable run ID for long operations. Poll run status initially; add streaming only after validating WSGI behavior. Disable debug mode in production. Bound requests, tool response sizes, SQL duration, and provider timeouts. Do not share request-specific identity or mutable IRIS session state across workers.

No custom ObjectScript business layer is required. IRIS-generated persistence classes, platform services, declarative deployment files, and package metadata do not change the Python-only backend requirement.

## 5. SOURCE CONTRACT AND TOOL REGISTRY

### 5.1 Import procedure

1. VENDOR the approved upstream file as `specification/mainspec_v2.json` from [R1]. RECORD upstream commit, retrieval time, SHA-256, and target IRIS version.
2. VALIDATE the OpenAPI document. Resolve local references and any explicitly allowlisted, pinned dependencies. Reject unresolved or unexpected remote references.
3. ENUMERATE operations and merge path-level and operation-level parameters according to OpenAPI semantics.
4. CAPTURE method, path template, operation ID, descriptions, parameter locations, serialization rules, request media types, response schemas, and declared security requirements.
5. CREATE immutable tool versions. Use a stable key from source identity, method, and path when operation IDs are absent or duplicated.
6. CLASSIFY semantics. Set new or uncertain operations to UNKNOWN and disabled pending review. HTTP verb and summary text are classification hints, not proof.
7. KEEP every imported operation disabled except the versioned first-setup preset of explicitly reviewed READ_ONLY operations. For this deployment's SysAdmin catalog, a `DBAApprover` may also use the availability control or presets; persist the actor and decision. Preserve previous versions for historical runs.
8. ON REIMPORT, generate a change report. Invalidate affected pending approvals. Never silently preserve READ_ONLY classification after semantic changes.

The registry SHALL remain traceable to `specification/mainspec_v2.json`. Do not manually maintain a competing endpoint catalog. Required privileges not declared by the source SHALL be recorded as reviewed policy metadata, with evidence from the deployed system.

### 5.2 Operation policy

| Classification | Behavior |
|---|---|
| READ_ONLY | Starts blocked except for the explicit first-setup reviewed-read preset; execute automatically only when enabled and the target authorizes it. |
| MUTATION | Starts blocked; a DBA may explicitly enable it as standing authorization for automatic calls. There is no per-run approval prompt. |
| UNKNOWN | Starts blocked. Never auto-enable on import; execution requires an explicit DBA availability toggle and a supported request shape. |

Treat create/update/delete, start/stop, pause/resume, terminate, enable/disable, grant/revoke, and administrative command execution as mutations whenever they change state. A GET can be unsafe. A POST can be observational. Classify actual behavior.

Bind tools to immutable agent versions. Assignment is not enough: the operation must also be globally enabled by a DBA. For enabled SysAdmin operations, that toggle authorizes automatic execution by any agent assigned the tool, including scheduled runs. Custom OpenAPI integrations are an extension; disable them initially and apply the same importer, target restrictions, and availability controls when introduced.

### 5.3 Request construction

Use only stored path templates and allowlisted target hosts. Validate all arguments against the pinned tool schema; enforce parameter encoding and media types. Reject arbitrary URLs, redirects to other hosts, unrecognized parameters, and agent-selected credentials. Preserve response status and bounded redacted evidence. Source or target incompatibility SHALL disable the operation rather than trigger a guessed fallback.

## 6. SINGLE TOOL EXECUTION GATEWAY

IMPLEMENT `ToolExecutionGateway` as the sole agent-facing entry point.

```text
request -> resolve pinned tool -> validate input -> authorize agent and scope
        -> check enabled state and budgets -> classify
          disabled/unsupported -> blocked
          enabled SysAdmin tool -> method-specific executor -> redacted evidence -> result
          managed SQL or non-catalog mutation -> immutable proposal -> WAITING_APPROVAL
```

Apply the gateway to agents, routines, watches, delegation, and retries. Reject direct network, shell, unrestricted Python evaluation, raw IRIS handles, and unregistered database access from model-generated content. Instructions embedded in API output or memory SHALL remain untrusted data.

## 7. ACTION PROPOSALS AND DBA APPROVAL

This proposal protocol applies to managed SQL and other mutations outside the DBA-enabled SysAdmin catalog. An enabled SysAdmin operation follows the standing-authorization policy in Section 5.2 and does not create or wait for a per-call Action Proposal.

### 7.1 Immutable action envelope

Persist the following before presenting approval:

```text
proposal_id, revision, origin_run_id, origin_agent_version_id
tool_version_id, specification_hash, policy_version
target_instance_id, connection_profile_version, environment, namespace
method, resolved_path, ordered_query_parameters, semantic_headers
content_type, body_bytes, body_sha256
sql_text, typed_bind_values                 [SQL actions only]
credential_identity_ref, credential_version [never a plaintext secret]
resource_identity, before_state, before_state_hash
preconditions, precondition_strategy, expected_effect, risk
created_at, expires_at, idempotency_key
canonicalization_version, action_hash
```

Canonicalize metadata deterministically, reject duplicate JSON keys and invalid numeric values, and store the exact request body bytes. Include every field that can change action meaning in the action hash. Do not reapply defaults at execution time. Transport-only authentication headers may be generated at dispatch, but principal, target, and credential version must remain bound to the approval. Secret-valued business inputs SHALL use immutable encrypted values or immutable secret versions.

Show the DBA the target/environment, tool, exact parameters, proposed diff, current-state evidence, risk, expiry, expected effect, and recovery limitations. Redact secrets while displaying their immutable references and fingerprints. Provide APPROVE and REJECT. Changing anything creates a new revision and requires new approval.

### 7.2 Approval authority

Require an authenticated human with the DBA approval permission for the target. Bind the decision to proposal ID, revision, action hash, approver, timestamp, and expiry. Protect browser decisions against CSRF and replay. Never accept approval from an agent, model-generated text, memory, a notification click without authenticated review, or a generic conversational acknowledgment.

Approval is one-use and action-specific. Do not implement blanket approval for a session, tool category, routine, or future retry. Recheck approver authority and agent scope at dispatch. Revoked permissions SHALL prevent execution.

### 7.3 State machine

```text
DRAFT -> PENDING_APPROVAL -> APPROVED -> VALIDATING -> EXECUTING
                  |             |           |             |
               REJECTED      EXPIRED    INVALIDATED    SUCCEEDED
               CANCELLED     CANCELLED                 FAILED
                                                       OUTCOME_UNKNOWN
```

Use a transactional compare-and-set to claim the approved revision once. Keep the approval decision append-only. Expiry applies before dispatch. A lease expiry after possible dispatch SHALL trigger reconciliation, not an automatic second mutation.

### 7.4 Exact execution

1. CLAIM the stored approved revision.
2. VERIFY the action hash and all current authorization conditions.
3. VERIFY the pinned contract and target identity.
4. REVALIDATE resource state as specified below.
5. DISPATCH the stored request without another LLM call.
6. RECORD response and postcondition evidence.
7. REPORT success only when the result is established.

Do not automatically retry a mutation after a timeout. If the target supports a verified idempotency mechanism, reuse the same key and exact payload only under the approved retry policy. Otherwise mark OUTCOME_UNKNOWN and reconcile through read operations. Exactly-once remote execution is not guaranteed by a local queue.

## 8. PRE-MUTATION STATE VALIDATION

Capture a relevant resource snapshot when proposing. Define stable fields and exclude irrelevant volatile fields through a reviewed per-tool projection. Store both the snapshot and projection version. For creation, verify expected absence and relevant parent configuration. For deletion or update, verify identity and version. For SQL, bind affected row keys, versions, expected row count, and applicable constraints.

Immediately before mutation, read authoritative current state and compare it with approved preconditions. Any relevant drift, missing evidence, identity mismatch, or expired proposal SHALL invalidate the action and require a new proposal and approval.

A read followed by a write has a race window. Use a target-supported conditional update/version token when available. For suitable SQL changes, validate and mutate within the same transaction using appropriate locking or version predicates. A local mutex does not block external administrators. If the target provides no enforceable concurrency guard, document that limitation in the proposal and disable high-risk execution until an adequate operational guard is established. Never invent ETag or conditional-header support absent from the target contract.

Rollback or compensation is a new mutation and requires approval unless the exact compensation was separately included and explicitly approved. Do not promise transactional rollback across administrative HTTP calls or arbitrary DDL.

## 9. CONTROLLED SQL

Expose `iris.sql.query` and `iris.sql.mutate` as separate tools. Use parameterized statements through Embedded Python [R4]. Define schema migrations through IRIS SQL DDL [R5].

`iris.sql.query` SHALL use a restricted identity with SELECT-only grants on approved objects, bounded rows and runtime, and a reviewed IRIS-compatible parser or an allowlisted query-template mechanism. A string starting with SELECT is insufficient: reject unreviewed functions, procedures, multi-statement input, write-capable extensions, and indirect side effects. If parsing is uncertain, reject the query or classify it as a mutation; never execute it optimistically.

`iris.sql.mutate` SHALL cover INSERT, UPDATE, DELETE, MERGE, DDL, privilege changes, stored procedure execution with side effects, and any other mutable operation. Persist SQL text and typed parameters in the Action Proposal. Include affected-resource preconditions. Execute only the approved statement under a dedicated executor identity. Do not expose the application's internal tables through unrestricted managed SQL.

## 10. IRIS DATA MODEL

Use a dedicated application schema such as `Agentic`. Use application-generated UUID identifiers, UTC timestamps, explicit foreign keys, unique version numbers, and optimistic revision fields. Store large JSON/text in appropriate IRIS long-text types. Validate JSON in Python. Keep credentials outside prompts and use credential references. Implement the schema with reviewed SQL migrations [R5].

The following is the required logical model; implementation migrations SHALL define concrete IRIS types, lengths, constraints, and indexes for the pinned release.

| Table | Required data |
|---|---|
| AI_TARGET | Instance ID, environment, namespace, connection profile version, allowed host, credential references, enabled flag. |
| AI_PROMPT | Name, purpose, current version, owner, lifecycle. |
| AI_PROMPT_VERSION | Prompt ID, version, content, input/output schemas, author, timestamp. Immutable. |
| AI_MODEL_PROFILE_VERSION | Provider, model identifier, parameters, credential reference, token/time/cost budgets. Immutable. |
| AI_AGENT | Name, description, status, current version, creator identity, parent provenance. |
| AI_AGENT_VERSION | Prompt/model versions, iteration limits, memory scope, delegation rules, child proposal policy, resource scope. |
| AI_TOOL / AI_TOOL_VERSION | Stable key, source, contract hash, operation details, input/output schemas, classification, risk, activation state. |
| AI_TOOL_POLICY_OVERRIDE | Tool version, reviewed classification, privileges, scope rules, reason, reviewer, approval reference. |
| AI_AGENT_TOOL | Agent version, tool version, allowed resource scope, limits; unique binding. |
| AI_AGENT_RELATION | Parent, child, relation type, origin run, effective scope, approval reference. |
| AI_ROUTINE / AI_ROUTINE_VERSION | Name, trigger, schedule/timezone, immutable workflow definition, concurrency and retry policy. |
| AI_ROUTINE_STEP | Routine version, step key, type, dependencies, pinned references, input mapping, output schema. |
| AI_RUN | Parent run, agent/routine/watch version, trigger, state, start/end, budgets, failure category. |
| AI_RUN_MESSAGE | Run, sequence, role, content, timestamps, redaction metadata. |
| AI_TOOL_EXECUTION | Run, tool version, arguments hash, proposal reference, timing, status, evidence reference. |
| AI_FINDING | Run, severity, confidence, resource, observation time, evidence references, explanation, recommendation. |
| AI_ACTION_PROPOSAL | Immutable action envelope, revision, hash, preconditions, expiry, execution state. |
| AI_APPROVAL | Proposal revision/hash, authenticated DBA, decision, timestamp, reason. Append-only. |
| AI_ACTION_EXECUTION | Proposal revision, unique dispatch identity, claim state, result, reconciliation, postconditions. |
| AI_MEMORY | Content, category, scope, resource, source run/finding, observed time, confidence, expiry, supersession. |
| AI_MEMORY_EMBEDDING | Memory ID, model/version, dimension, VECTOR value, indexing state. |
| AI_ALERT_RULE / AI_ALERT_RULE_VERSION | Watch mission, agent/prompt version, schedule, scope, severity rules, cooldown, escalation configuration. |
| AI_ALERT_EVENT | Rule, finding/run, fingerprint, severity, lifecycle, first/last seen, occurrence count, owner. |
| AI_ALERT_DELIVERY | Alert, destination reference, delivery key, attempt status, next retry. |
| AI_JOB | Type, payload reference, due time, lease owner, fencing token, attempts, status. |
| AI_AUDIT_EVENT | Actor, action, entity, correlation ID, timestamp, redacted before/after hashes. Append-only. |
| AI_SCHEMA_MIGRATION | Version, checksum, applied time, deployment identity, outcome. |

Index due jobs, active watches, run history, unresolved alerts, proposal expiry, and memory scopes. Add unique constraints for logical schedule occurrences, approval revisions, dispatch identities, and notification delivery keys. Do not cascade-delete audit history when an agent is retired. Use retention jobs with explicit operator policy.

## 11. AGENT RUNTIME AND DELEGATION

At run start, pin agent, prompt, model, tool, and policy versions. Compile only declared prompt variables. Retrieve authorized memory. Send the model only allowed tool schemas. Process each call through the gateway. Validate structured output. Persist the run transcript and evidence. Stop at iteration, elapsed-time, token, cost, or tool-call limits.

Run states SHALL include QUEUED, RUNNING, WAITING_APPROVAL, SUCCEEDED, FAILED, CANCELLED, and BUDGET_EXCEEDED. An agent may finish its analysis while a linked proposal remains pending; the GUI SHALL distinguish both states. Resuming a run must not duplicate dispatched actions.

Agents MAY propose other agents through `platform.agent.propose_create`. Require explicit approval before activating a child. Enforce:

```text
effective child authority
  = requested authority
    intersect parent authority
    intersect initiating principal authority
    intersect target policy
```

Apply the same intersection to delegation, including target scope, read/propose modes, memory access, credentials, budgets, and delegated tools. Recheck inherited grants at execution so revocation takes effect. Block cycles, bound depth and fan-out, and maintain a parent run trace. Neither a child nor a delegate may approve an action. Shared memory is knowledge exchange; explicit delegation is task assignment.

## 12. ROUTINES AND DURABLE SCHEDULING

A routine is a versioned workflow; an agent is a goal-driven executor. Provide steps RUN_AGENT, CALL_READ_TOOL, GENERATE_REPORT, EVALUATE_ALERT, DELEGATE, and PROPOSE_ACTION. Do not provide an unguarded mutation step.

Validate workflow dependencies and typed input/output mappings before activation. Pause dependent steps while approval is pending. Persist checkpoints. Pin action inputs before approval. Never recalculate them after approval without creating a new revision.

Store schedule timezone explicitly and calculate due times in UTC. Define daylight-saving behavior, missed-run policy, maximum parallel runs, backoff, and cancellation. Claim jobs transactionally with leases and fencing tokens. Read jobs may retry within limits. Mutation recovery follows Section 7, regardless of scheduler retry configuration.

## 13. SHARED MEMORY THROUGH IRIS VECTOR SEARCH

Persist complete responses in run history. Extract operational knowledge into separate memory records: incidents, findings, verified resolutions, patterns, runbook notes, and significant observations. Exclude conversational filler and secrets. Preserve provenance and distinguish observation, hypothesis, and verified resolution.

Store embeddings in IRIS VECTOR columns and retrieve using supported similarity functions. Choose one embedding model/version and dimension per compatible index. Follow [R6]. Add an HNSW index only after confirming support and measuring filtered retrieval on the deployed release. Embedding generation MAY use a Python provider; the SQL EMBEDDING function is optional and release-dependent [R7].

Apply access, target, environment, namespace, sensitivity, and retention filters before memories enter model context. Retrieve a bounded top-k, carry evidence links, and record retrieved memory IDs. Never retrieve broadly and rely on the model to enforce access control. Test that approximate indexing preserves the application's isolation requirements.

Memory is historical context. Before proposing a mutation, collect current evidence through live read tools. Memory cannot grant authority, prove approval, override policies, or establish current state. Handle embedding failures asynchronously; full run history must survive. Version embedding migrations and do not compare incompatible vectors.

## 14. AI WATCHES AND ALERTS — CORE FEATURE

### 14.1 Watch definition

An AI Watch combines a DBA-defined mission, pinned agent and prompt, target scope, schedule, reviewed read capabilities, structured finding schema, severity policy, deduplication policy, cooldown, and notification destinations. Watch creation or modification follows configuration approval.

Example mission: inspect permitted operational evidence, identify sustained resource pressure, compare with prior incidents, and produce evidence-backed findings. Enable a seed watch only when the required operations exist in `specification/mainspec_v2.json` and the target supports them.

### 14.2 Evaluation procedure

1. CLAIM a due watch occurrence.
2. COLLECT current evidence through READ_ONLY tools.
3. RETRIEVE authorized historical memory.
4. RUN bounded analysis and validate structured findings.
5. APPLY deterministic severity, confidence, and evidence requirements.
6. UPSERT an alert incident by stable fingerprint.
7. NOTIFY according to cooldown and escalation rules.
8. STORE evidence and queue memory extraction.
9. CREATE a separate Action Proposal if remediation is recommended.

Do not let a watch execute remediation automatically. Do not resolve an incident because the model failed, evidence was unavailable, or a scheduled run was skipped. Produce a separate watch-health event for stale or failed monitoring.

### 14.3 Finding and lifecycle contract

Require resource identity, observation interval, severity, confidence, evidence references, explanation, and recommended next step. Use INFO, LOW, MEDIUM, HIGH, and CRITICAL. Do not derive severity solely from model wording.

Alert states SHALL include OPEN, ACKNOWLEDGED, RESOLVED, and SUPPRESSED. Preserve acknowledgment actor/time, suppression reason/expiry, resolution evidence, recurrence count, and escalation history. Acknowledgment is not resolution or approval. Reopen on verified recurrence. Group equivalent findings by rule, target, resource, and condition family; do not fingerprint free-form model prose.

Write notifications through a durable outbox with unique delivery IDs. Cooldown reduces repeated notifications without discarding observations. Notify again for material escalation or recurrence. Keep the in-app alert center mandatory; email/webhooks are optional approved integrations with redacted payloads.

### 14.4 Relationship to native IRIS monitoring

Use IRIS monitoring documentation to interpret system metrics and native alerts [R8, R9]. Production managed alerts are a distinct interoperability feature [R10]. The Python AI alert center SHALL operate without requiring a custom interoperability production.

Do not label monitoring endpoints as SysAdmin endpoints. When a required monitoring source is absent from `specification/mainspec_v2.json`, either leave the watch unsupported or implement a separately documented, reviewed read-only monitoring adapter. Do not claim that Vector Search or native alerting alone provides the application-specific AI analysis described here.

## 15. GUI AREAS AND APPLICATION API

| Area | Required behavior |
|---|---|
| Operations Home | Show active agents, current runs, pending approvals, open alerts, and monitoring freshness first. |
| Agents | Create versioned definitions, inspect effective capabilities, test reads, propose child agents. |
| Prompts | Edit drafts, compare versions, validate variables and output schemas, approve activation. |
| Tools | Browse imported operations, source hashes, classifications, reviewed privileges, and compatibility. |
| Routines | Build workflows and schedules; inspect blocked steps and checkpoints. |
| AI Watches | Define missions and policies; show last success, next run, evidence, and monitor health. |
| Alerts | Filter, acknowledge, assign, suppress, inspect evidence, and request remediation proposals. |
| Approvals | Compare exact actions and preconditions; explicitly approve or reject one revision. |
| Runs and Findings | Inspect calls, evidence, budgets, outputs, and linked proposals. |
| Shared Memory | Search authorized knowledge and inspect provenance, age, scope, and supersession. |
| Models and Settings | Manage profiles, targets, budgets, roles, retention, and approved configuration changes. |

Define application APIs under a separate prefix such as `/agentic/api/v1`. These are new application routes, not claims about IRIS SysAdmin routes. Provide resources for agents, prompts, tools, routines, watches, runs, findings, memories, alerts, and proposals. Provide explicit approve/reject operations binding proposal revision and hash. Use pagination, schema validation, correlation IDs, and stable errors. Return a conflict on stale revision and accepted/queued status for asynchronous work.

## 16. SECURITY, AUDIT, AND OPERATIONS

Use distinct Viewer, Operator, AgentDesigner, DBAApprover, and PlatformAdministrator application permissions with target-specific scopes. Map identities to verified IRIS/application authorization. Avoid shared unrestricted credentials. A configured tool is not evidence that its caller has permission.

Restrict LLM network access to approved providers and executor access to registered targets. Redact secrets from prompts, evidence, logs, embeddings, and notifications. Encrypt sensitive proposal values and backups. Sanitize model text before rendering HTML. Apply authentication, authorization, CSRF protection, session expiry, and request limits to all relevant routes.

Audit configuration changes, proposals, decisions, state checks, dispatch attempts, results, delegations, and memory access where required. Do not store hidden model reasoning as an audit requirement; store inputs permitted by policy, outputs, tool calls, evidence, and concise decision explanations. Restrict audit update/delete privileges and export integrity checkpoints where stronger tamper detection is required.

Monitor queue lag, watch freshness, read failures, proposal age, invalidation rate, unknown mutation outcomes, provider usage, and embedding backlog. Implement graceful worker shutdown and health/readiness checks. Back up IRIS application data and referenced secret versions. After restore, freeze ambiguous in-flight mutations for reconciliation instead of replaying them.

## 17. REPOSITORY AND IMPLEMENTATION ORDERS

```text
app/
  wsgi.py
  api/                  # authenticated application routes
  runtime/              # agents, routines, prompts, delegation
  tools/                # importer, registry, read and SQL adapters
  policy/               # authorization, proposals, mutation guard
  memory/               # extraction, embeddings, retrieval
  alerts/               # evaluation, deduplication, lifecycle, outbox
  repositories/         # restricted IRIS persistence
  providers/            # model and embedding adapters
worker/main.py
migrations/
specification/mainspec_v2.json
frontend/
tests/
docs/
Dockerfile
docker-compose.yml
module.xml              # IPM package metadata, if delivered
```

| Phase | Execute | Exit evidence | References |
|---|---|---|---|
| P0 — Contract | Pin IRIS release, source commit/hash, supported API domains, Python dependencies, and deployment identity. | Compatibility inventory; no invented endpoints. | R1–R5 |
| P1 — Foundation | Create schema migrations; deploy authenticated Python WSGI; prove worker SQL connectivity. | Fresh installation and authenticated persistence smoke test. | R2–R5 |
| P2 — Registry | Import contracts; version operations; build the DBA availability catalog and method-specific gateway. | Every imported tool maps to the source; all operations start disabled; unsupported shapes stay blocked. | R1 |
| P3 — Safety | Implement proposals, exact payloads, DBA decisions, concurrency guards, dispatch ledger, and SQL restrictions for proposal-gated actions. | All proposal/recovery tests in Section 18 pass before enabling managed SQL mutations. | R1, R4, R5 |
| P4 — Agents | Implement persisted prompts/agents, provider adapters, budgets, history, and constrained delegation. | DBA creates an agent in the GUI without editing Python. | R3–R5 |
| P5 — Memory | Add extraction, VECTOR persistence, scoped retrieval, provenance, and embedding failure recovery. | A second authorized agent retrieves prior knowledge; unauthorized retrieval fails. | R6, R7 |
| P6 — Watches | Add durable schedules, findings, alert lifecycle, deduplication, outbox, and monitoring freshness. | A watch detects a seeded condition and produces an approval-gated remediation proposal. | R8–R10 |
| P7 — Release | Complete GUI, compatibility report, Docker/IPM artifacts, README, demo, and restore tests. | Reproducible installation and end-to-end demonstration. | R11, R12 |

Do not enable managed SQL or other proposal-gated mutation execution before P3 passes. SysAdmin operations use the standing DBA toggle in Section 5.2, with explicit automatic-execution warnings; only the reviewed-read preset is enabled at first setup. Prioritize a complete read–finding–alert flow over unsupported breadth. Maintain a coverage matrix for web applications, permissions, security/secrets, tasks, operating-system resources, and logs; mark unsupported operations explicitly.

## 18. ACCEPTANCE AND SECURITY TESTS

| Test | Mandatory result |
|---|---|
| Reviewed authorized read | Executes without DBA interruption and records evidence. |
| Unassigned or disabled tool | Denied before dispatch. |
| Disabled or unsupported operation | Denied before dispatch, even when an agent still has a historical binding. |
| Enabled mutating SysAdmin operation | Executes automatically only for an assigned agent; the DBA toggle is logged and no per-call approval is requested. |
| Changed source hash or unsupported request shape | Operation remains blocked until the new pinned version is reviewed and enabled. |
| Managed SQL mutation or non-catalog side-effect command | Proposal exists; zero mutation before approval. |
| Mutable SQL, procedure, or disguised multi-statement input | Cannot bypass approval or SQL restrictions. |
| Body, SQL bind, target, header, or tool-version tampering | Hash/authorization check fails; zero dispatch. |
| Drift between proposal and execution | INVALIDATED; new approval required. |
| Concurrent drift during execution | Conditional guard fails, or unsupported high-risk operation remains disabled. |
| Expired/rejected/cancelled approval | Zero dispatch. |
| Two workers claim one approval | At most one dispatch claim succeeds. |
| Timeout or crash after possible dispatch | OUTCOME_UNKNOWN; no blind mutation replay. |
| Approval granted by agent or unauthorized user | Rejected. |
| Child/delegate requests wider authority | Rejected; parent revocation also takes effect. |
| Prompt injection in logs or memory | Cannot change policy, credentials, approval, or tool scope. |
| Cross-target or unauthorized memory search | No unauthorized content enters the model context. |
| Repeated watch finding | One incident accumulates occurrences; notification policy is honored. |
| Watch or model failure | Monitoring-health event; incident is not falsely resolved. |
| Restore with in-flight actions | Mutations frozen for reconciliation. |

Run unit tests for canonicalization, state transitions, classification rules, and scope intersections. Run integration tests against the pinned IRIS image for WSGI, SQL, VECTOR retrieval, transaction behavior, importer compatibility, and guarded mutations. Use a disposable target for destructive scenarios. Add an end-to-end browser test for the approval review and a fault-injection test for post-dispatch crashes.

## 19. CONTEST ALIGNMENT AND BONUS EVIDENCE

The published contest requests a GUI backed by IRIS management APIs, an open-source repository, Community Edition compatibility, and an English README with installation and demonstration material [R11]. Present this application as a DBA-configurable agentic administration portal with concrete administrative coverage.

The bonus announcement lists the following opportunities [R12]. Treat points as the published baseline, not a guaranteed award; recheck before submission.

| Bonus | Points | Evidence to deliver |
|---|---:|---|
| Embedded Python | 3 | Working IRIS-hosted Python code and reproduction steps. |
| IRIS Vector Search | 2 | Persisted vectors and demonstrated shared-memory retrieval. |
| Docker | 2 | Reproducible container installation. |
| ZPM package deployment | 2 | Published installable package and installation proof. |
| Online demo | 2 | Reachable isolated demonstration. |
| Implement a Community Idea | 4 | Eligible idea link and matching implemented behavior. |
| Find an Embedded Python bug | 2 | Qualifying report and required confirmation. |
| First / second Developer Community article | 2 / 1 | Published explanatory articles. |
| First-time contribution | 3 | Eligibility confirmation. |
| YouTube video | 3 | Demonstration video. |

Do not claim an unearned bonus. Run public demonstrations against disposable data with isolated credentials. Demonstrate DBA-created agents, shared memory, a scheduled alert, a blocked mutation, explicit approval, exact execution, and drift invalidation.

## 20. RELEASE DEFINITION OF DONE

RELEASE only when the DBA can create behavior through the GUI, restart the application without losing it, enable or block pinned SysAdmin operations, and inspect evidence from automatic runs. Enabling a mutating operation is an explicit standing authorization; proposal-gated managed SQL remains subject to Section 7.

DELIVER source, pinned dependencies, migrations, the pinned `specification/mainspec_v2.json`, provenance manifest, classification/coverage report, security test results, installation instructions, backup/restore procedure, and demonstration instructions. Confirm that Java/Quarkus are absent from the application backend and no model-facing path bypasses the approval gateway.

## 21. OFFICIAL REFERENCES AND SOURCE AUTHORITY

References were consulted for this specification. `irislatest` is a moving documentation alias; pin the deployed release and record the corresponding documentation version during P0. These sources document platform mechanisms. The approval protocol, schema, AI Watches, and implementation phases above are project requirements, not claims that IRIS supplies this application out of the box.

- **R1 — Authoritative SysAdmin source:** [InterSystems Community SysAdmin OpenAPI specification](https://github.com/intersystems-community/sysadmin-api-specification/blob/master/mainspec_v2.json). Vendor as `specification/mainspec_v2.json`. Preserve source provenance and verify target compatibility.
- **R2 — WSGI:** [Creating WSGI Applications](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=AWSGI). Use for callable and Web Application configuration.
- **R3 — Embedded Python execution:** [Run Embedded Python](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GEPYTHON_runpython). Use for the supported Python execution model.
- **R4 — Python access to IRIS:** [Call InterSystems IRIS from Embedded Python](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GEPYTHON_calliris). Use for `iris` integration and SQL access.
- **R5 — SQL persistence:** [Defining Tables](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSQL_tables) and [Querying the Database](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSQL_queries). Use for DDL and prepared query implementation.
- **R6 — Vector Search:** [Using Vector Search](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSQL_vecsearch). Use for vector types, similarity queries, and supported indexing.
- **R7 — Optional SQL embeddings:** [EMBEDDING (SQL)](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=RSQL_embedding). Verify release support and configuration before use.
- **R8 — Monitoring overview:** [Monitoring](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=PAGE_monitoring).
- **R9 — Native system monitoring:** [Using System Monitor](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GCM_healthmon_sysmon) and [Monitoring InterSystems IRIS via REST](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GCM_rest). Keep monitoring contracts separate from SysAdmin contracts.
- **R10 — Production alerts:** [Monitoring Alerts](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=EMONITOR_alerts). Use only when integrating with native interoperability alerting.
- **R11 — Contest requirements:** [InterSystems Programming Contest: Build Your Own Management Portal](https://community.intersystems.com/post/intersystems-programming-contest-build-your-own-management-portal).
- **R12 — Contest bonuses:** [Technology Bonuses for the InterSystems Programming Contest: Build Your Own Management Portal](https://community.intersystems.com/post/technology-bonuses-intersystems-programming-contest-build-your-own-management-portal).

**END OF SPECIFICATION.**
