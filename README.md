# IRIS DBA Agents

IRIS DBA Agents is a self-hosted MVP for defining AI-assisted database administration tasks and reviewing their results. A DBA configures an agent with instructions, a task, a local Ollama model, and a restricted set of approved IRIS SysAdmin queries. The agent can inspect the configured environment and produce a report with tool-call results as evidence.

The application is designed for human-supervised, read-only diagnostics. It does not execute user-supplied code or make database changes. Task conditions are interpreted by a language model, so review the report and its evidence before acting on a recommendation.

## What You Can Do

- Create, edit, enable, and pause shared DBA agents.
- Write agent instructions and describe a task in natural language.
- Select up to 12 approved SysAdmin queries and optionally set fixed query parameters.
- Run an agent on demand or schedule it at an interval.
- Review run status, the generated report, instructions used, tool calls, arguments, and returned evidence.
- Use the reviewed SysAdmin catalog to see which operations are available to agents.

The source contract contains 276 SysAdmin operations. Only 18 explicitly reviewed read queries are available to agents; other operations are blocked. Ollama is the only implemented model provider in this MVP. Agent task text is not executable code, and model interpretations should be checked against the returned evidence.

## How It Works

```text
Browser -> IRIS web application (Flask/WSGI) -> IRIS database
                                             ^
                                             |
Ollama <- Embedded Python worker <- run queue
                       |
                       +-> restricted SysAdmin query gateway
```

IRIS stores agent configurations, runs, and tool-call records. A worker inside the IRIS container claims queued runs, calls the configured Ollama model, and routes permitted requests through a server-side SysAdmin gateway. The browser does not receive the gateway credentials.

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

4. Download the default model into the Ollama container:

   ```sh
   docker compose exec ollama ollama pull qwen2.5:3b
   ```

   If you changed `AGENTIC_MODEL` in `.env`, pull that model identifier instead.

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

The first startup creates these IRIS roles. Assign them to users through IRIS security administration:

| Role | Access |
| --- | --- |
| `AgenticViewer` | View agents, runs, and reports. |
| `AgenticOperator` | View and run enabled agents. |
| `AgenticAgentDesigner` | View, create, and edit agents; can also run them. |

The default `_SYSTEM` development account has `%All` and therefore full access. The application is a shared workspace: authorized users see the same agents and reports. Use individual IRIS accounts and grant only the roles each person needs.

## Create and Run Your First Agent

1. Select **Create agent**.
2. Enter a name, keep the default Ollama model or choose a model already downloaded in Ollama, and write the agent instructions.
3. Describe one task in the task field. For example: “Check whether there are at least 50 locks, inspect the related processes, and summarize what you find.” Conditions in task text are interpreted by the model; they are not deterministic application rules.
4. Select one or more reviewed queries that provide the information the task needs. An agent must have between 1 and 12 tools. Optional fixed parameters must match the query schema and cannot be overridden by the model.
5. Leave the interval at `0` for manual runs, or choose `60` to `86400` seconds for recurring runs. Save the agent.
6. Select **Run now**. When the run completes, select **View report** to inspect the summary, status, instructions used, tool calls, and evidence.
7. Use **Pause** to prevent future scheduled runs. A run already in progress may finish.

Prefer focused tasks and grant only the queries needed for them. Treat the model's conclusions as assistance, and verify the supporting tool results before taking operational action.

## Configuration

Settings are read by Docker Compose from `.env`. Defaults are also defined in `docker-compose.yml`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENTIC_IRIS_PORT` | `52774` | Host port for the local IRIS web application. It is bound to localhost. |
| `COMPOSE_PROFILES` | `local-llm` | Enables the local Ollama service. The install command also selects this profile explicitly. |
| `AGENTIC_OLLAMA_URL` | `http://ollama:11434` | Ollama endpoint as seen from the IRIS container. |
| `AGENTIC_MODEL` | `qwen2.5:3b` | Suggested model for new agents; the model must be available in Ollama. |
| `AGENTIC_SYSADMIN_URL` | `http://127.0.0.1:52773/api/admin` | Server-side SysAdmin API target. |
| `AGENTIC_SYSADMIN_USER` | Empty | Optional username for an externally configured SysAdmin target. |
| `AGENTIC_SYSADMIN_PASSWORD` | Empty | Optional password for an externally configured SysAdmin target. |

When the SysAdmin credentials are left empty, startup provisions a dedicated local gateway identity. For a separate SysAdmin target, configure its URL and credentials in `.env`; keep credentials out of source control. The gateway still restricts agent access to the reviewed read-query allowlist.

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
- Each agent can use up to 12 tools. Only the 18 reviewed read queries can be assigned; the rest of the 276-operation catalog is blocked.
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
