# Implementation plan

## Current scope — user decision 2026-09-26

The broad P0–P7 roadmap below is historical and deferred. The active delivery is the smaller [DBA-created agents MVP](docs/MVP_PLANO.md): persisted instructions/tasks, selected read-only SysAdmin tools, LangChain/Ollama, manual/periodic runs and reports. No agents are seeded. Implementation and acceptance evidence are recorded in `docs/MVP_VALIDACAO.md`.

The existing repository is continued in place. `SPEC_AGENTIC_IRIS_ADMIN.md` is the product contract; this file records implementation evidence.

| Unit | Objective / SPEC | Components and IRIS mechanism | Dependencies / action | Validation / exit |
| --- | --- | --- | --- | --- |
| P0 | Pin contract and runtime (§5, §17) | specification, importer, Docker | Pin provenance; verify local references and operation identities | Partial: 276 operations imported; importer semantics still need completion |
| P1a — current | Correct authentication and worker readiness (§4, §16) | auth, installer, worker; native IRIS identity, SQL and CallIn | Remove name-based authority; isolate worker identity; fail readiness when worker fails | Unit tests + authenticated/anonymous HTTP + worker SQL + restart |
| P1b | Durable schema and migration integrity (§10) | migrations, repositories | Add foreign keys, long text, migration recovery and explicit grants | Fresh install, interrupted migration and persistence tests |
| P2 | Reviewed read gateway (§5–6) | importer, registry, executor | Resolve OpenAPI parameters; stable keys; pinned target/credential; deny unknown tools | Contract regression + authorized live read and denial evidence |
| P3 | Exact approvals and dispatch (§7–9, §18) | policy, repositories, API | Transactional decisions/claims, scoped authority, expiry/drift guards and audit | Security/concurrency/fault-injection gates; mutations remain disabled until then |
| P4–P6 | Agents, VECTOR memory, watches (§11–14) | runtime, providers, memory, alerts | Depend on P1–P3; implement one complete read/finding/alert flow | Persistent GUI configuration and scoped retrieval; watch failure/dedup tests |
| P7 | Release (§17–20) | frontend, packaging, docs | Complete operational screens and reproducible release | Browser E2E, restore and all acceptance orders |

## Current evidence

- Pinned IRIS 2026.2 Build 221U builds and serves Flask through `/agentic`.
- Native WSGI probe: `REMOTE_USER` is absent; `$USERNAME` identifies `_SYSTEM`, while `Process.UserName()` yields the OS user `irisowner`. Use native IRIS security context.
- Worker now runs through an absolute `irispython` path with a dedicated `AgenticWorker` identity. Readiness requires a fresh heartbeat after a successful parameterized SQL probe.
- 2026-09-26: runtime image rebuilt successfully; 14 tests passed in the Docker test stage. Live HTTP smoke passed native identity, anonymous/unauthorized denial, SQL pagination, authenticated assets, CSRF denial and worker readiness.
- Live worker access probe passed native identity, parameterized migration-ledger reads and denial of unrelated application tables. This worker only checks connectivity; durable job execution remains pending.
- Restart verification passed the same HTTP smoke; container reported healthy and the imported catalog remained available.
- Environment limitation: Docker context `desktop-linux` currently contains only the IRIS container and `agentic-iris_agentic-data` volume. Neither the previous Ollama container nor `argus-iris_ollama-models` exists in this context. No volumes were removed during this continuation; recovering previous models needs their original context or backup.
- Initial schema and approval handlers are incomplete. No administrative mutation executor exists; release is not complete.
