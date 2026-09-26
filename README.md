# IRIS DBA Agents

IRIS DBA Agents is a self-hosted MVP for configuring AI-assisted database administration tasks and reviewing their results. A DBA controls which operations from the pinned IRIS SysAdmin OpenAPI contract are available, then configures agents with instructions, tasks, an Ollama model, and selected available tools. Agents can call enabled operations and return reports with tool-call evidence.

On first startup, 18 explicitly reviewed read-only GET operations are enabled for quick use; all other operations start blocked. Enabling any additional operation is a standing authorization for assigned agents to invoke it automatically, including scheduled runs; there is no approval prompt for each call. A DBA is responsible for reviewing the operation and its consequences before enabling it. Task conditions are interpreted by a language model, so verify reports and evidence.

## What You Can Do

- Create, edit, enable, and pause shared DBA agents.
- Write agent instructions and describe a task in natural language.
- Select up to 12 DBA-enabled SysAdmin operations and optionally set fixed parameters.
- Search all operations in the pinned SysAdmin contract and block or enable each supported operation from the catalog.
- Run an agent on demand or schedule it at an interval.
- Review run status, the generated report, instructions used, tool calls, arguments, and returned evidence.
- Use the reviewed SysAdmin catalog to see which operations are available to agents.

The pinned contract contains 276 operations: GET, POST, PUT, DELETE, and HEAD. The first startup enables only the 18 reviewed read-only queries; all other operations remain blocked. A DBA can enable any supported operation, including operations that change state; only enabled operations can be assigned to agents. Ollama is the default model provider; OpenAI can be selected through deployment settings. Agent task text is not executable code, and model interpretations should be checked against returned evidence.

The default read set is maintained in [reviewed_read_operations.json](specification/reviewed_read_operations.json), separate from the upstream API contract. `docker compose build` checks its SHA-256 against the pinned contract and rejects unknown, unsupported, sensitive, duplicate, or non-GET entries before producing the runtime image.

## How It Works

```text
Browser -> IRIS web application (Flask/WSGI) -> IRIS database
                                             ^
                                             |
Ollama <- Embedded Python worker <- run queue
                       |
                       +-> availability-gated SysAdmin API gateway
```

IRIS stores agent configurations, tool availability, run history, and tool-call evidence. A worker inside the IRIS container claims queued runs, calls the configured Ollama model, checks tool availability before dispatch, and routes requests through a server-side SysAdmin gateway. The browser does not receive gateway credentials. Recognized password, token, and credential fields are redacted from stored tool evidence.

## Requirements

- Docker Engine with the Docker Compose plugin, or Docker Desktop with Compose enabled.
- A source checkout of this project.
- Enough memory for the IRIS Community container and the local Ollama model. The default model runs on CPU, but performance depends on available resources.
- Network access to download the container images, Python dependencies during the image build, and the Ollama model.

## Install and Start

Run the commands from the project root, where `docker-compose.yml` is located.

1. Create a local environment file. On Windows PowerShell:

   ```powershell
   Copy-Item .env.example .env
   ```

   On macOS, Linux, or a Unix shell:

   ```sh
   cp .env.example .env
   ```

2. Review `.env`. The defaults enable the local Ollama service, expose IRIS only on `127.0.0.1`, use port `52774`, and select `qwen2.5:3b`. Keep this deployment local unless you have separately configured secure network access and IRIS authentication.

3. Build the application image and start IRIS and Ollama:

   ```sh
   docker compose --profile local-llm up -d --build
   ```

   The first build and startup can take several minutes. The startup script applies database migrations, creates the application roles and service identities, imports the SysAdmin contract, and starts the worker.

4. If `AGENTIC_PROVIDER=ollama`, download the configured model into the Ollama container:

   ```sh
   docker compose exec ollama ollama pull qwen2.5:3b
   ```

   If you changed `AGENTIC_MODEL` in `.env`, pull that model identifier instead. OpenAI deployments do not need this step.

5. Check that the services are running:

   ```sh
   docker compose ps
   ```

   Wait for the `iris` service to report `healthy`. If startup fails, inspect its logs:

   ```sh
   docker compose logs --tail=100 iris
   ```

6. Open the application at [http://localhost:52774/agentic/](http://localhost:52774/agentic/) and sign in with an IRIS account.

   For a fresh local InterSystems IRIS Community image, the development login is `_SYSTEM` with password `SYS`. This account has full administrative access: use it only for local development, do not expose the service publicly, and change the default password for any persistent environment.

## Configure Access

The first startup creates these IRIS roles and enables the reviewed read-only query preset once. Assign the DBA role to users through IRIS security administration:

| Role | Access |
| --- | --- |
| `AgenticViewer` | View agents, runs, and reports. |
| `AgenticOperator` | View and run enabled agents. |
| `AgenticAgentDesigner` | View, create, and edit agents; can also run them. |
| `AgenticDBAApprover` | Enable or block operations in the shared tool catalog. Enabling a mutating operation authorizes automatic calls without per-run approval. |

The default `_SYSTEM` development account has `%All` and therefore full access. The application is a shared workspace: authorized users see the same agents and reports. Use individual IRIS accounts and grant only the roles each person needs.

## Create and Run Your First Agent

1. Select **Create agent**.
2. Enter a name, keep the default Ollama model or choose a model already downloaded in Ollama, and write the agent instructions.
3. Describe one task in the task field. For example: “Check whether there are at least 50 locks, inspect the related processes, and summarize what you find.” Conditions in task text are interpreted by the model; they are not deterministic application rules.
4. Select one or more available operations that provide the information or action the task needs. An agent must have between 1 and 12 tools. Optional fixed parameters must match the schema and cannot be changed by the model. Leave `{}` to set no fixed values.
5. Leave the interval at `0` for manual runs, or choose `60` to `86400` seconds for recurring runs. Save the agent.
6. Select **Run now**. When the run completes, select **View report** to inspect the summary, status, instructions used, tool calls, and evidence.
7. Use **Pause** to prevent future scheduled runs. A run already in progress may finish.

For a new deployment, the reviewed read-only queries are ready to assign. A DBA can expand **Tool availability and SysAdmin catalog** and use **Enable reviewed reads** to restore that set or **Block all** to close every operation. Search the catalog to inspect methods, descriptions, and parameters before enabling anything else. Enabling an operation allows assigned agents to invoke it automatically; POST/PUT/DELETE may change IRIS state. Blocking a tool prevents future dispatches, though a request already in flight may finish.

Prefer focused tasks and assign only the operations each agent needs. Treat model conclusions as assistance and verify evidence before taking further operational action.

## Configuration

Settings are read by Docker Compose from `.env`. Defaults are also defined in `docker-compose.yml`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENTIC_IRIS_PORT` | `52774` | Host port for the local IRIS web application. It is bound to localhost. |
| `COMPOSE_PROFILES` | `local-llm` | Enables the local Ollama service. The install command also selects this profile explicitly. |
| `AGENTIC_PROVIDER` | `ollama` | Active deployment provider: `ollama` or `openai`. |
| `AGENTIC_OLLAMA_URL` | `http://ollama:11434` | Ollama endpoint as seen from the IRIS container. |
| `AGENTIC_MODEL` | `qwen2.5:3b` | Default model for the configured provider; it must be available from that provider. |
| `AGENTIC_OPENAI_API_KEY` | Empty | OpenAI API key. Keep it only in local environment configuration. |
| `AGENTIC_OPENAI_BASE_URL` | Empty | Optional base URL for an OpenAI-compatible endpoint. |
| `AGENTIC_SYSADMIN_URL` | `http://127.0.0.1:52773/api/admin` | Server-side SysAdmin API target. |
| `AGENTIC_SYSADMIN_USER` | Empty | Optional username for an externally configured SysAdmin target. |
| `AGENTIC_SYSADMIN_PASSWORD` | Empty | Optional password for an externally configured SysAdmin target. |

When the SysAdmin credentials are left empty, startup provisions a dedicated local gateway identity. That identity may not have privileges for every mutating operation. For a separate SysAdmin target, configure its URL and least-privilege credentials in `.env`; keep credentials out of source control. Enabling an operation does not grant additional privileges to the target identity.

### Switch to OpenAI

In `.env`, set `AGENTIC_PROVIDER=openai`, choose an OpenAI model such as `gpt-4o-mini` with `AGENTIC_MODEL`, and set `AGENTIC_OPENAI_API_KEY`. Optionally set `AGENTIC_OPENAI_BASE_URL` for an OpenAI-compatible endpoint. The API key is passed only to the IRIS server container and is never returned to the browser. Comment out `COMPOSE_PROFILES=local-llm` if Ollama is not needed, then rebuild/restart IRIS:

```sh
docker compose up -d --build iris
```

All three settings (`AGENTIC_PROVIDER`, `AGENTIC_MODEL`, and `AGENTIC_OPENAI_API_KEY`) must match the selected provider. Existing agents use the deployment's configured provider; when their saved provider differs, the configured `AGENTIC_MODEL` is used.

## Stop and Restart

Stop and remove the containers while preserving application data and downloaded models:

```sh
docker compose down
```

Start the existing deployment again:

```sh
docker compose --profile local-llm up -d
```

Docker volumes persist IRIS application data and Ollama models. **Do not use `docker compose down -v` unless you intend to permanently delete those volumes and their data.**

## Limits and Safety

- One worker executes runs per deployment; a run is limited to 240 seconds, 8 model iterations, and 12 tool calls.
- Each agent can use up to 12 tools. On initial setup, only 18 reviewed read-only operations are enabled; the remaining catalog stays blocked. A DBA-enabled operation is a shared standing authorization for automatic use by assigned agents, including schedules.
- The current tool-level toggle does not ask for per-action approval. Be especially careful when enabling POST, PUT, or DELETE operations. The target's credentials still determine whether the operation succeeds.
- Model output can be incomplete or incorrect. Verify report claims using the evidence shown in the run details.
- The MVP does not provide vector memory, external notifications, write operations, or multi-instance coordination.
- Task conditions are model-interpreted, not guaranteed rules or alerts.
- The local Community login and localhost-bound port are development defaults, not a production security setup.

## Run Tests

Build the test image to run the Python test suite during the Docker build:

```sh
docker build --target test -t agentic-iris-tests .
```

The project also includes runtime smoke and acceptance scripts under `scripts/`. The smoke test requires the corresponding IRIS and Ollama services and its documented environment credentials.

## Project References

- [Development plan](DEVELOPMENT_PLAN.md)
- [MVP implementation plan](docs/MVP_PLANO.md)
- [MVP validation notes](docs/MVP_VALIDACAO.md)
- [SysAdmin contract](specification/mainspec_v2.json)
- [Reviewed read-only endpoints](specification/reviewed_read_operations.json)
