# IRIS DBA Agents: desenvolvimento de agentes com Embedded Python, SysAdmin API e evidências SQL

## Introdução

O **IRIS DBA Agents** é um portal para configurar e executar agentes de administração do InterSystems IRIS. O DBA define instruções, tarefa, modelo, operações SysAdmin autorizadas e intervalo de execução. A aplicação armazena essa configuração, executa o agente e apresenta um relatório com os argumentos, resultados e IDs de evidência registrados para cada chamada.

A implementação combina Flask hospedado pelo WSGI do IRIS, Embedded Python, IRIS SQL, autenticação nativa e SysAdmin API. Adaptadores LangChain conectam o processo de execução ao Ollama ou à OpenAI. O modelo solicita operações; o código valida atribuição, disponibilidade, argumentos e limites de execução.

Este artigo acompanha o desenvolvimento desse fluxo, da requisição do navegador à persistência do relatório. Os exemplos práticos cobrem inspeção de journals e memória, investigação de locks e integração com uma tarefa ObjectScript.

![Agentes cadastrados e execuções recentes](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/screenshots/dashboard.png)

## 1. Arquitetura da aplicação no IRIS

A aplicação web, o banco e o worker rodam no contêiner do InterSystems IRIS Community Edition **2026.2**. O [Dockerfile](Dockerfile) fixa a imagem por digest. Com o perfil `local-llm`, o Docker Compose executa o Ollama em outro contêiner.

O diagrama representa a implantação padrão, em que o destino da SysAdmin API é a própria instância IRIS:

![Arquitetura do IRIS DBA Agents e comunicação entre componentes](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/diagrams/pt-br/01-architecture.png)

A persistência usa `iris.sql.exec()` pelo Embedded Python. As operações administrativas usam HTTP com destino e credenciais definidos no servidor. O modelo recebe instruções, schemas de ferramentas e resultados. A aplicação controla o acesso SQL e as credenciais do gateway.

O [merge.cpf](merge.cpf) cria o banco e o namespace, associa o armazenamento de globals e rotinas e registra a aplicação WSGI:

```ini
CreateDatabase:Name=AGENTIC,Directory=/usr/irissys/mgr/agentic,Resource=%DB_AGENTIC
CreateNamespace:Name=AGENTIC,Globals=AGENTIC,Routines=AGENTIC
CreateApplication:Name=/agentic,NameSpace=AGENTIC,WSGIAppLocation=/opt/agentic,WSGIAppName=app.wsgi,WSGICallable=application,Type=2,DispatchClass=%SYS.Python.WSGI,WSGIDebug=0,WSGIType=1,AutheEnabled=32,ServeFiles=0
```

O IRIS carrega o callable `application` de [app/wsgi.py](app/wsgi.py):

```python
from app import create_app

application = create_app()
```

A função `create_app()` configura templates, limite de 1 MiB por requisição, repositórios e dois blueprints. As rotas de agentes usam `/api/mvp`. Sessão, saúde e rotas de suporte ficam em `app/api/routes.py`. O endereço externo inclui o prefixo `/agentic`.

O Flask renderiza `frontend/templates/index.html` com a identidade autenticada. O HTML define editor, catálogo e janela de relatório; o CSS define a apresentação; o JavaScript envia requisições e atualiza os dados exibidos. As rotas autenticadas `/assets/style` e `/assets/script` servem uma lista fixa de arquivos. O IRIS reserva `/static` para o StreamServer nessa integração.

## 2. Estrutura do código e dependências

O projeto separa tratamento de requisições, validação, persistência e execução:

| Área | Arquivos principais | Responsabilidade |
| --- | --- | --- |
| Instalação | `merge.cpf`, `iris.script`, `scripts/startup.sh`, `app/install.py` | Namespace, WSGI, migrações, identidades e catálogo |
| API e segurança | `app/auth.py`, `app/mvp/routes.py` | Identidade nativa, permissões, CSRF e endpoints |
| Domínio | `app/mvp/domain.py` | Validação do agente e das atribuições de ferramentas |
| Catálogo | `app/tools/importer.py`, `app/mvp/catalog.py` | Importação OpenAPI e schemas de entrada |
| Persistência | `app/repositories/iris_repository.py`, `app/mvp/repository.py` | SQL, transações, configuração, fila e evidências |
| Execução | `app/mvp/runtime.py`, `app/mvp/gateway.py`, `app/mvp/providers.py` | Ciclo do modelo, requisições SysAdmin e adaptadores |
| Processos | `worker/main.py`, `worker/run_agent.py`, `worker/supervisor.py` | Agendamento, subprocesso executor e recuperação |
| Interface | `frontend/templates/index.html`, `frontend/static/` | Editor, catálogo, histórico e relatórios |

Os repositórios executam SQL parametrizado diretamente. O código Python implementa o ciclo do agente e seus controles de acesso. O LangChain fornece adaptadores de modelos, mensagens e associação de ferramentas.

| Biblioteca | Versão fixada | Uso |
| --- | --- | --- |
| Flask | 3.1.2 | Aplicação WSGI, rotas JSON e templates |
| jsonschema | 4.25.1 | Validação de argumentos com `Draft7Validator` |
| requests | 2.32.5 | Cliente HTTP da SysAdmin API |
| langchain | 1.4.2 | Dependências de integração com modelos |
| langchain-ollama | 1.1.0 | Adaptador `ChatOllama` |
| langchain-openai | 1.6.6 | Adaptador `ChatOpenAI` |
| pytest | 8.4.2 | Testes automatizados |
| Ruff | 0.16.9 | Análise estática e formatação |

As dependências de execução estão fixadas em [requirements.txt](requirements.txt); pytest e Ruff estão em [requirements-dev.txt](requirements-dev.txt). O runtime InterSystems fornece o módulo `iris`.

## 3. Catálogo de ferramentas a partir do OpenAPI

O arquivo [specification/mainspec_v2.json](specification/mainspec_v2.json) contém o contrato OpenAPI 3.0.0 fixado, com **276 operações**. [specification/provenance.json](specification/provenance.json) registra origem, commit, SHA-256 e versão-alvo do IRIS.

O importador valida o documento e as referências locais e rejeita referências remotas. O catálogo resolve referências, combina parâmetros por localização e nome e gera um schema de entrada por operação. O adaptador suporta `GET`, `POST`, `PUT`, `DELETE` e `HEAD` com parâmetros de query e corpos JSON. Formatos incompatíveis, incluindo placeholders no caminho e parâmetros fora da query, ficam indisponíveis.

| Campo | Composição ou exemplo | Uso |
| --- | --- | --- |
| `key` | `get_v2_locks` | Nome da função apresentada ao modelo |
| `contract_hash` | SHA-256 do arquivo OpenAPI | Identifica os bytes do contrato |
| `stable_key` | SHA-256 do hash do contrato, método e caminho | Identifica a operação naquela versão |

O catálogo gera a identidade da operação assim:

```python
stable_key = hashlib.sha256(
    f"{digest}:{method}:{path}".encode("utf-8")
).hexdigest()
```

O hash do contrato integra essa identidade. Atualizar o contrato exige revisar seu checksum, as atribuições geradas e o manifesto de operações revisadas.

As operações entram no banco bloqueadas. O primeiro setup habilita **18 operações GET revisadas** de [reviewed_read_operations.json](specification/reviewed_read_operations.json). Um marcador em `AI_SCHEMA_MIGRATION` preserva decisões posteriores do DBA entre reinícios.

![Catálogo SysAdmin e controles de disponibilidade](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/screenshots/sysadmin-catalog.png)

O DBA pode habilitar ou bloquear operações suportadas, aplicar o preset de leituras revisadas ou bloquear o catálogo inteiro. O preset preserva outras operações habilitadas. `AI_TOOL_POLICY_OVERRIDE` registra ator, motivo e horário das alterações de política.

A execução exige disponibilidade global e atribuição ao agente. Habilitar operações mutáveis ou sensíveis exige reconhecimento explícito na interface e na API. Esse reconhecimento autoriza chamadas automáticas dos agentes atribuídos, inclusive em execuções periódicas. A instância IRIS de destino verifica os privilégios da identidade SysAdmin a cada requisição.

## 4. Modelagem no IRIS SQL

O fluxo operacional usa três tabelas de [migrations/002_mvp.sql](migrations/002_mvp.sql):

| Tabela | Dados persistidos |
| --- | --- |
| `Agentic.MVP_AGENT` | Configuração, revisão, habilitação, intervalo, próxima execução e execução ativa |
| `Agentic.MVP_RUN` | Snapshot do agente, estado, origem, ator, horários, relatório e erro |
| `Agentic.MVP_CALL` | Ferramenta, argumentos, resultado, desfecho e horário de cada chamada registrada |

![Modelo de dados de agentes, execuções e chamadas de ferramentas](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/diagrams/pt-br/02-data-model.png)

`AgentID` e `RunID` são chaves estrangeiras. As atribuições de ferramentas ficam no JSON de configuração com parâmetros fixos, `stable_key` e `contract_hash`. O catálogo usa `AI_TOOL`, `AI_TOOL_VERSION` e `AI_TOOL_POLICY_OVERRIDE`.

As colunas relacionais atendem às consultas e à coordenação da fila. O JSON armazena configuração variável e resultados. `ConfigJSON`, `SnapshotJSON`, `ResultJSON` e `Report` usam `VARCHAR(32000)`; `ArgumentsJSON` usa `VARCHAR(4000)`. A validação de domínio limita a configuração serializada a 28.000 caracteres, e o repositório armazena até 30.000 caracteres do relatório.

Cada execução enfileirada recebe um snapshot da configuração. O repositório preserva esse snapshot em edições posteriores. Administradores do banco mantêm seus privilégios sobre as tabelas.

![Cadastro dos agentes consultado por SQL](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/screenshots/sql-registered-agents.png)

### Revisão e transações

A edição envia a revisão originalmente lida pelo usuário. `AgentRepository.save_agent()` bloqueia a linha e verifica essa revisão dentro de uma transação:

```python
_sql("UPDATE Agentic.MVP_AGENT SET Revision=Revision WHERE ID=?", (identifier,))
old = self.get_agent(identifier)
if type(revision) is not int or old["revision"] != revision:
    raise Conflict("Agent changed. Reload before saving.")
```

O `UPDATE` adquire o bloqueio de escrita que serializa edição e enfileiramento. `ActiveRun` restringe cada agente a uma execução pendente ou ativa. O enfileiramento insere o snapshot e atualiza `ActiveRun` na mesma transação.

A função SQL de [iris_repository.py](app/repositories/iris_repository.py) passa os valores separadamente do texto da consulta:

```python
def _sql(statement: str, params: tuple[Any, ...] = ()):
    import iris

    try:
        return iris.sql.exec(statement, *params)
    except Exception as error:
        if getattr(error, "sqlcode", None) == 100:
            return []
        raise
```

`START TRANSACTION`, `COMMIT` e `ROLLBACK` delimitam operações compostas.

## 5. Cadastro e ciclo de execução

O editor recebe nome, instruções, tarefa, modelo, intervalo, habilitação e ferramentas. A validação de domínio aceita de uma a 12 ferramentas distintas e verifica os parâmetros fixos contra seus schemas. O intervalo é `0` para execução manual ou de 60 a 86.400 segundos para execução periódica.

![Editor de configuração do agente](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/screenshots/agent-configuration.png)

As operações disponíveis podem ser selecionadas e receber parâmetros JSON fixos. Na edição, operações atribuídas anteriormente e bloqueadas depois permanecem visíveis, com a seleção desabilitada.

![Seleção de ferramentas e parâmetros fixos](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/screenshots/create-agent.png)

### Navegador e API Flask

[frontend/static/app.js](frontend/static/app.js) obtém os papéis do usuário e o token CSRF em `/api/v1/session`. Sua função de requisição usa `fetch` com `credentials: "same-origin"`, corpos JSON e o cabeçalho `X-Agentic-CSRF`.

As chamadas abaixo usam essa função. `config` representa os dados do editor; `agentId` é o ID do agente salvo:

```javascript
const agent = await api("/api/mvp/agents", "POST", config);
const agentId = agent.id;
const run = await api("/api/mvp/agents/" + agentId + "/runs", "POST", {});
const detail = await api("/api/mvp/runs/" + run.id);
```

A rota de criação verifica permissão e CSRF antes de validar e persistir os dados:

```python
# app/mvp/routes.py
@bp.post("/agents")
@require_permission("design")
@require_csrf
def create():
    available_keys = {item["key"] for item in tool_catalog() if item["allowed"]}
    config = validate_agent(request.get_json(silent=True), enabled_keys=available_keys)
    return jsonify(repository().save_agent(config, current_principal().name)), 201
```

O endpoint de execução retorna HTTP `202` com o ID da execução enfileirada. O worker a processa de forma assíncrona. Consultas posteriores de detalhes retornam estado atual, snapshot salvo, relatório e chamadas.

![Sequência de execução do navegador à persistência de evidências](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/diagrams/pt-br/03-execution-sequence.png)

### LangChain e provedores de modelos

`AGENTIC_PROVIDER` seleciona Ollama ou OpenAI para a implantação. `ChatOllama` usa `AGENTIC_OLLAMA_URL`; `ChatOpenAI` lê `AGENTIC_OPENAI_API_KEY` no servidor e aceita `AGENTIC_OPENAI_BASE_URL` como configuração opcional. Os dois adaptadores configuram temperatura `0` e limite de 1.000 tokens por geração. O adaptador Ollama também define contexto de 8.192 tokens e timeout de 90 segundos no cliente.

O agente armazena modelo e provedor. Quando o provedor salvo difere do ativo na implantação, o runtime seleciona o modelo padrão da implantação.

[app/mvp/runtime.py](app/mvp/runtime.py) monta as definições de funções a partir das operações atribuídas. Os parâmetros fixos são removidos dos campos de schema fornecidos pelo modelo e incluídos na descrição de cada função. O gateway aplica esses valores no despacho.

O runtime associa as definições ao modelo e inicia a conversa:

```python
model = model_factory(provider, model_name).bind_tools(definitions)
messages = [
    SystemMessage(content=SYSTEM),
    HumanMessage(content=config["prompt"] + "\nTAREFA:\n" + config["task"]),
]
```

`model.invoke(messages)` retorna chamadas de ferramentas ou um relatório. Cada chamada tratada produz uma `ToolMessage` com ID de evidência e resultado. O prompt de sistema solicita relatórios concisos em inglês, observações fundamentadas nos retornos e limitações explícitas dos dados.

Cada execução permite oito interações com o modelo e 12 chamadas de ferramentas. Um relatório preenchido e com pelo menos uma chamada bem-sucedida termina como `SUCCEEDED` quando todas as chamadas registradas tiveram sucesso, ou `PARTIAL` quando coexistem chamadas bem-sucedidas e falhas. Esses estados descrevem o processamento; a conferência das evidências determina se uma conclusão tem fundamento.

![Histórico com execuções bem-sucedidas, parciais e falhas](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/screenshots/runs-overview.png)

## 6. Validação e despacho no gateway

O gateway compara as identidades das ferramentas salvas com o contrato fixado durante a inicialização. Para cada chamada, verifica atribuição e disponibilidade atual, combina parâmetros fixos, valida argumentos e consulta novamente a disponibilidade antes do despacho HTTP.

As verificações de argumentos em [app/mvp/gateway.py](app/mvp/gateway.py) incluem:

```python
if any(key in arguments and arguments[key] != value for key, value in fixed.items()):
    raise ToolError("FIXED_PARAMETER_OVERRIDE")
params = {**arguments, **fixed}
```

Após aplicar os valores padrão específicos de tarefas, a validação JSON Schema rejeita parâmetros inválidos:

```python
if list(Draft7Validator(item["schema"]).iter_errors(params)):
    raise ToolError("INVALID_ARGUMENTS")
```

Uma atribuição com `{"maxRows": 100}` faz uma requisição com `maxRows: 500` falhar antes do acesso à rede. Para operações GET que declaram `maxRows`, o gateway fornece `200` quando omitido e aceita valores de 1 a 500.

`AGENTIC_SYSADMIN_URL` define o destino, com padrão `http://127.0.0.1:52773/api/admin`. O catálogo fornece método e caminho. Uma `requests.Session` envia os parâmetros de query e o corpo JSON opcional:

```python
# Trecho de _dispatch_request()
with transport.request(
    item["method"],
    base + item["path"],
    params=query_params,
    json=params.get("body"),
    auth=credentials,
    timeout=(5, 20),
    allow_redirects=False,
    stream=True,
) as response:
    if not 200 <= response.status_code < 300:
        raise ToolError(f"SYSADMIN_HTTP_{response.status_code}")
```

A sessão configura `trust_env=False` para evitar proxies herdados do ambiente. O gateway lê a resposta em blocos limitados e verifica os erros informados pela API.

| Controle | Valor ou comportamento |
| --- | --- |
| Timeout HTTP | 5 segundos para conexão e 20 para leitura |
| Argumentos serializados | Até 3.500 caracteres |
| Resposta recebida | Até 24.000 bytes |
| Resultado JSON serializado | Até 30.000 caracteres |
| Status HTTP aceitos | 2xx |
| Erros da API | `status.errors` preenchido causa falha |
| Disponibilidade | Verificada na preparação e novamente antes do despacho |

Para `POST /v2/task`, `TASK_CREATE_DEFAULTS` fornece `StartDate`, `EndDate`, `SuspendOnError` e `SuspendTerminated`. Valores explícitos prevalecem. O catálogo converte a declaração textual de campos obrigatórios desse schema em restrições de validação.

## 7. Persistência e consulta das evidências

O runtime grava a chamada em `MVP_CALL` antes de devolver o resultado ao modelo. O UUID da linha identifica a evidência. Erros de ferramenta tratados também produzem registros com desfecho `FAILED`.

O runtime percorre argumentos e resultados e oculta valores de campos cujos nomes indiquem senha, segredo, token, credencial, autorização ou API key. Esse processamento depende dos nomes dos campos; segredos em texto livre podem permanecer. A configuração do agente e os parâmetros fixos seguem caminhos próprios de armazenamento e envio ao modelo.

A passagem da persistência para o contexto do modelo é explícita:

```python
evidence = repository.record_call(
    run_id, key[:100], redact_sensitive(safe_args), result, outcome
)
evidence_ids.append(evidence)
messages.append(
    ToolMessage(
        content=json.dumps({"evidence_id": evidence, "data": model_evidence(result)}),
        tool_call_id=call["id"],
    )
)
```

Quando a resposta contém uma lista em `result`, `model_evidence()` envia até oito linhas, a contagem retornada e um indicador de truncamento. Linhas com `Pid` também geram contagens por processo. O SQL preserva o resultado sanitizado aceito pelo gateway, dentro dos limites de tamanho. As contagens descrevem a resposta filtrada e limitada.

![Relatório e sequência de ferramentas registradas](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/screenshots/report-evidence.png)

O runtime acrescenta IDs de evidência omitidos no relatório antes de salvá-lo. `ArgumentsJSON` armazena os argumentos solicitados após ocultação de campos sensíveis e tratamento de tamanho; o snapshot armazena os parâmetros fixos; o gateway acrescenta os valores padrão. A reconstrução da requisição efetiva exige essas três fontes.

![Argumentos e resultado de uma chamada](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/screenshots/tool-evidence-detail.png)

A consulta abaixo relaciona agentes, execuções e chamadas no namespace `AGENTIC`:

```sql
SELECT TOP 100
    a.Name,
    r.ID AS RunID,
    r.State,
    c.ID AS EvidenceID,
    c.ToolKey,
    c.Outcome,
    c.ArgumentsJSON,
    c.ResultJSON,
    c.CreatedAt
FROM Agentic.MVP_AGENT a
JOIN Agentic.MVP_RUN r ON r.AgentID = a.ID
JOIN Agentic.MVP_CALL c ON c.RunID = r.ID
ORDER BY c.CreatedAt DESC, c.ID;
```

![Evidências persistidas consultadas por SQL](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/screenshots/sql-tool-evidence.png)

## 8. Autenticação e autorização

[app/auth.py](app/auth.py) lê o contexto IRIS autenticado pelo Embedded Python:

```python
name = str(iris.execute("return $username"))
native_roles = set(str(iris.execute("return $roles")).split(","))
```

A aplicação deriva permissões desses papéis nativos e rejeita acesso quando não consegue estabelecer uma identidade autenticada. Cabeçalhos do navegador fornecem dados da requisição, enquanto o IRIS fornece a identidade.

| Papel IRIS | Permissão na aplicação |
| --- | --- |
| `AgenticViewer` | Consultar agentes, execuções, relatórios e catálogo |
| `AgenticOperator` | Consultar e executar agentes habilitados |
| `AgenticAgentDesigner` | Criar, editar, pausar, habilitar e executar agentes |
| `AgenticDBAApprover` | Alterar disponibilidade das operações |
| `%All` | Administrar a aplicação |

A permissão interna `run_read` inicia agentes. Suas capacidades efetivas seguem o catálogo e as atribuições salvas, incluindo operações mutáveis autorizadas.

Escritas exigem `X-Agentic-CSRF`, calculado com HMAC-SHA256 a partir do usuário e de um segredo do servidor. As respostas incluem Content Security Policy, `nosniff`, política de referência e `Cache-Control: no-store`. A interface exibe relatórios e dados por nós de texto.

`AgenticWorker` recebe grants SQL específicos para persistência operacional e leitura das tabelas necessárias. O instalador atribui `AgenticSysAdminReader,AgenticTaskRunner,%All` à identidade local `AgenticSysAdmin`, concedendo privilégios amplos no destino. A política do catálogo e as verificações do gateway restringem as operações enviadas pela aplicação.

## 9. Agendamento, recuperação e implantação

O scheduler seleciona até 20 agentes habilitados com intervalo positivo, `NextDue` vencido e `ActiveRun` vazio. O enfileiramento calcula o próximo horário a partir do instante atual e do intervalo.

A implantação executa um worker e um subprocesso executor por vez. O worker assume o item `QUEUED` mais antigo, inicia `worker/run_agent.py` com `irispython`, verifica o subprocesso a cada dois segundos e o encerra após 240 segundos.

![Estados das execuções, agendamento e transições de falha](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/diagrams/pt-br/04-run-states.png)

A pausa bloqueia novos enfileiramentos. O worker cancela uma execução na fila ao encontrar o agente pausado; uma execução iniciada pode terminar. Após reinício, a recuperação marca as linhas ainda em `RUNNING` como `FAILED` com `WORKER_RESTARTED` e mantém as chamadas administrativas sem repetição automática.

![Snapshots e estados das execuções consultados por SQL](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/screenshots/sql-agent-runs.png)

O supervisor encerra grupos de processos remanescentes antes da recuperação e limita as tentativas de reinício. A prontidão exige um marcador de startup e um heartbeat com menos de 20 segundos, atualizado após uma consulta SQL bem-sucedida. A disponibilidade do modelo é verificada durante as chamadas ao provedor.

Na inicialização, `scripts/startup.sh` invoca o instalador Python de uma sessão ObjectScript:

```objectscript
set installer=##class(%SYS.Python).Import("app.install")
do installer.setup()
```

O instalador aplica migrações verificadas por checksum, compila a classe de demonstração por `%SYSTEM.OBJ.Load`, configura identidades, importa o contrato e aplica o preset inicial. O volume `agentic-data` preserva o banco e os arquivos gerados. O volume `ollama-models` armazena os modelos baixados.

Copie `.env.example` para `.env` a partir da raiz do repositório. No PowerShell:

```powershell
Copy-Item .env.example .env
```

No Linux ou macOS:

```sh
cp .env.example .env
```

Para inferência local, mantenha `AGENTIC_PROVIDER=ollama` e `AGENTIC_MODEL=qwen2.5:3b` e execute:

```sh
docker compose --profile local-llm up -d --build
docker compose exec ollama ollama pull qwen2.5:3b
docker compose ps
```

Abra [http://localhost:52774/agentic/](http://localhost:52774/agentic/) e autentique-se com uma conta IRIS que tenha os papéis necessários. O Compose publica a porta web em `127.0.0.1:52774` por padrão. O [README.md](README.md) documenta as credenciais da implantação e a configuração OpenAI. `module.xml` contém os metadados do módulo; Docker, CPF e scripts de inicialização implementam esse fluxo de instalação.

## 10. Exemplos práticos e uso operacional

### Journals e memória

O **Storage Growth and Journal Risk Sentinel**, documentado no [README](README.md#practical-example--save-run-and-audit-the-sentinel), reúne dados de journals, recursos e memória compartilhada em um relatório. O DBA obtém uma inspeção repetível, com evidências de origem para cada observação.

Para reproduzir o fluxo:

1. Abra **Tool availability** e confirme a habilitação das três operações abaixo.
2. Selecione **Create agent**, informe o nome acima, mantenha o modelo da implantação, marque **Enabled** e defina **Interval** como `0`.
3. Atribua as operações e os parâmetros fixos da tabela.
4. Preencha instruções e tarefa para definir a inspeção, usando o exemplo abaixo.
5. Selecione **Save agent** e depois **Run now** na linha do agente salvo.
6. Atualize **Runs and reports**, abra **View report** e confira o desfecho e os campos retornados de cada chamada.

| Operação | Dados coletados | Parâmetros fixos |
| --- | --- | --- |
| `GET /v2/journal/files` | Arquivos de journal e tamanhos informados | `{"maxRows":100}` |
| `GET /v2/monitor/dashboard/system-resources` | Contadores atuais de recursos | `{}` |
| `GET /v2/monitor/system-usage/shared-memory` | Alocação e uso de memória compartilhada | `{}` |

Estes campos fornecem uma configuração reproduzível para a inspeção:

```text
Agent instructions:
Atue como DBA de IRIS inspecionando journals e memória. Use as três operações
de leitura atribuídas. Fundamente as observações nos campos retornados,
preserve as unidades, cite IDs de evidência e identifique dados ausentes.
Mantenha a execução restrita à leitura.

Task / skill:
Execute cada operação atribuída. Informe quantidade de arquivos de journal
e tamanhos retornados, contadores atuais de recursos e alocação e uso de
memória compartilhada. Descreva o escopo dos dados retornados. Liste lacunas
e verificações do DBA necessárias para avaliar capacidade e crescimento
do armazenamento. Escreva o relatório em inglês.
```

A configuração usa esta estrutura de atribuição antes de a validação de domínio acrescentar as identidades do contrato:

```json
{
  "interval_seconds": 0,
  "enabled": true,
  "tools": [
    {"key": "get_v2_journal_files", "fixed": {"maxRows": 100}},
    {"key": "get_v2_monitor_dashboard_system_resources", "fixed": {}},
    {"key": "get_v2_monitor_system_usage_shared_memory", "fixed": {}}
  ]
}
```

Esse JSON representa a parte de agendamento e ferramentas do payload do agente. O editor fornece os demais campos descritos na seção 5.

O README registra a revisão **1** concluída como **Succeeded** em **26 de setembro de 2026, às 15h17min36s**, no horário local do navegador. As três chamadas tiveram sucesso. A resposta de journals continha quatro arquivos com valores de `Size` de **1.048.576**, **229.376**, **372.736** e **69.632 bytes**.

![Relatório do sentinel salvo](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/screenshots/sentinel-report.png)

| Ferramenta | ID de evidência registrado |
| --- | --- |
| `get_v2_journal_files` | `1e2a21c1-6cc7-490d-ab6a-e63311f0f2dc` |
| `get_v2_monitor_dashboard_system_resources` | `7cd2cf3c-59a3-453c-ba1d-c3f079b33d3f` |
| `get_v2_monitor_system_usage_shared_memory` | `5cbfc298-5447-46ca-aee9-798bbe23d728` |

![Recomendações do sentinel e três chamadas bem-sucedidas](https://raw.githubusercontent.com/Davi-Massaru/iris-argus/refs/heads/master/docs/screenshots/sentinel-evidence.png)

Esses valores descrevem a instância de demonstração documentada. Ao interpretar outra execução, confira unidades, carga de trabalho e limites da consulta. Uma categoria de memória zerada exige contexto da carga. A avaliação de crescimento requer medições em momentos diferentes; a avaliação de capacidade requer dados suficientes de armazenamento.

Após revisar o relatório, defina o intervalo como `3600` para obter snapshots horários, se essa frequência atender ao ambiente e ao custo do provedor. Cada execução acrescenta relatório e evidências para consulta posterior. A análise histórica de tendências e a entrega de notificações permanecem fora do fluxo implementado neste exemplo.

### Locks e processos

[scripts/mvp_locks_acceptance.py](scripts/mvp_locks_acceptance.py) cria 50 locks em um global de teste no namespace `AGENTIC`:

```python
iris.execute("for i=1:1:50 lock +^AgenticMVPTest(i):1")
```

O agente recebe `get_v2_locks` com `filter: "AgenticMVPTest"` e `maxRows: 100` fixos, além de `get_v2_process`. A tarefa solicita uma consulta de processo para cada PID distinto observado quando pelo menos 50 linhas de locks forem retornadas.

O script verifica a quantidade de locks, as evidências bem-sucedidas e a presença do primeiro PID consultado nos resultados de locks:

```python
assert locks and len(locks[0]["result"]["result"]) == 50
assert processes, "Model did not inspect the observed process"
assert str(processes[0]["arguments"]["id"]) in {
    str(r["Pid"]) for r in locks[0]["result"]["result"]
}
```

Um bloco `finally` libera os locks e pausa o agente de teste. O script registra os identificadores dos dados de teste para limpeza explícita. Sua execução exige uma implantação ativa e as variáveis de ambiente `AGENTIC_SMOKE_USER` e `AGENTIC_SMOKE_PASSWORD`.

Esse cenário conecta uma operação de lock em ObjectScript, Embedded Python, consultas complementares escolhidas pelo modelo, SysAdmin API e evidências SQL. As asserções verificam como o modelo tratou a condição expressa na tarefa.

### Task Manager e ObjectScript

[Agentic.Demo.EmailTask](iris/Agentic/Demo/EmailTask.cls) estende `%SYS.Task.Definition`. A classe define propriedades para destinatário, assunto, resumo de CPU, resumo de locks e IDs de evidência. O Task Manager invoca `OnTask()`:

```objectscript
Method OnTask() As %Status
{
    Quit ..SendSimulatedEmail(
        ..Recipient,
        ..Subject,
        ..CpuSummary,
        ..LockSummary,
        ..EvidenceIds)
}
```

`SendSimulatedEmail()` incrementa uma sequência e armazena os campos em `^AgenticDemoEmail`. A persistência inclui:

```objectscript
Set messageId = $Increment(^AgenticDemoEmail("Sequence"))
Set ^AgenticDemoEmail(messageId, "Recipient") = recipient
Set ^AgenticDemoEmail(messageId, "EvidenceIds") = evidenceIds
Set ^AgenticDemoEmail(messageId, "Delivery") = "SIMULATED"
```

A entrega é simulada por armazenamento local em global. O envio por SMTP exigiria uma implementação adicional.

O README registra consultas de recursos e locks, busca de tarefa, requisição de criação, nova busca e requisição `RunNow` pela SysAdmin API. Esse caminho conecta operações HTTP autorizadas ao Task Manager nativo e à classe ObjectScript.

O relatório dessa demonstração descreveu o ID de tarefa `1` como assumido. Um fluxo que executa tarefas precisa obter e verificar o ID pretendido nas evidências retornadas. O sucesso HTTP registrado estabelece o desfecho da chamada; a conferência da identidade determina qual tarefa a operação afetou.

## 11. Validação técnica e referências no código

O estágio `test` do Dockerfile executa Ruff, verificação de formatação e pytest:

```sh
docker build --target test -t agentic-iris-tests .
```

Os testes cobrem identidade nativa, permissões, CSRF, importação do contrato, manifesto revisado, parâmetros fixos, ferramentas bloqueadas, limites de resposta e exigência de evidências. Os testes injetam modelos e transportes simulados para exercitar essas regras com resultados controlados.

Por exemplo, [tests/test_mvp.py](tests/test_mvp.py) verifica o vínculo entre o resultado de uma ferramenta e o relatório salvo:

```python
execute("run-1", repo, lambda *_: model, ReadGateway)
assert repo.calls[0][1] == "get_v2_locks"
assert repo.finished[1] == "SUCCEEDED"
assert repo.finished[2].endswith("Evidence IDs: evidence-1")
```

Nesse trecho, `repo` registra escritas em memória, `model` retorna respostas predefinidas e `ReadGateway` devolve uma lista vazia de locks. Os scripts de smoke e aceitação verificam separadamente o comportamento dos endpoints em uma implantação ativa.

Durante o build do runtime, `scripts/embedded_check.py` importa a aplicação WSGI, executa `SELECT 1` pelo Embedded Python e carrega o contrato. A prontidão no startup verifica o acesso SQL do worker. Esses testes cobrem integração da aplicação, acesso à persistência e atividade do worker em suas respectivas etapas.

Para acompanhar a implementação, leia [routes.py](app/mvp/routes.py), [domain.py](app/mvp/domain.py), [repository.py](app/mvp/repository.py), [worker/main.py](worker/main.py), [runtime.py](app/mvp/runtime.py) e [gateway.py](app/mvp/gateway.py). [app/install.py](app/install.py) prepara o ambiente IRIS.

O fluxo ativo é `MVP_AGENT → MVP_RUN → MVP_CALL`. As tabelas de base e rotas de propostas adicionais atendem a trabalho separado desse ciclo. As chamadas SysAdmin usam autorização prévia do catálogo, atribuição ao agente e privilégios no destino.
