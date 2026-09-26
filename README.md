# Plataforma de agentes DBA — MVP

O DBA cria agentes, escreve instruções e tarefas, escolhe ferramentas SysAdmin e acompanha relatórios. Não há agentes pré-cadastrados. Skills neste MVP são tarefas descritas em texto; não executam código enviado pelo usuário.

## Executar

Requisitos: Docker Compose e memória suficiente para IRIS e um modelo local (o modelo padrão usa CPU se não houver GPU configurada).

Copie .env.example para .env e execute:

~~~sh
docker compose --profile local-llm up -d --build
docker compose exec ollama ollama pull qwen2.5:3b
~~~

Abra http://localhost:52774/agentic/ e autentique com uma conta IRIS. A imagem Community usa a conta local de desenvolvimento _SYSTEM / SYS; ela possui %All. Para acesso de equipe, atribua papéis nativos AgenticViewer, AgenticAgentDesigner ou AgenticOperator às contas IRIS. O MVP é um espaço compartilhado pela equipe DBA: usuários autorizados a visualizar veem todos os agentes e relatórios.

O Ollama usa o volume argus-iris_ollama-models. O volume anterior não estava disponível neste contexto Docker; foi criado um novo durante a implementação. Nenhum volume anterior foi removido.

## Usar

1. Clique em **Criar agente**.
2. Defina nome, instruções, tarefa e modelo Ollama já baixado.
3. Escolha as consultas permitidas. Parâmetros fixos opcionais são JSON e não podem ser alterados pelo agente.
4. Use intervalo 0 para execução manual ou 60–86400 segundos para repetição.
5. Salve e clique em **Executar agora**. Abra **Ver relatório** para ver instruções utilizadas, resposta e evidências.
6. Use **Pausar** para impedir novos ciclos. Uma execução já iniciada pode terminar.

O exemplo “quando houver pelo menos 50 locks, inspecione os processos e registre relatório” é escrito pelo DBA no campo de tarefa e usa as consultas de locks e de processo selecionadas. Não é uma regra embutida. Condições em texto são interpretadas pelo modelo e devem ser conferidas nas evidências.

## Arquitetura

Navegador → Flask/WSGI no IRIS → SQL no namespace AGENTIC.

Worker Embedded Python → LangChain → adaptador Ollama → gateway de ferramentas → API SysAdmin. Configuração e relatórios persistem no IRIS. O arquivo OpenAPI descreve endpoints; as chamadas são feitas à instância IRIS configurada.

app/mvp/providers.py é a fronteira de provedores: retorna um modelo de chat LangChain com bind_tools e invoke. Ollama está implementado; outro provedor pode ser adicionado nesse módulo e na validação do cadastro, sem alterar fila ou gateway. OpenAI não está integrado neste MVP.

## Configuração

| Variável | Uso |
| --- | --- |
| AGENTIC_IRIS_PORT | Porta local, padrão 52774 |
| AGENTIC_OLLAMA_URL | Servidor Ollama, padrão http://ollama:11434 |
| AGENTIC_MODEL | Modelo sugerido em novos cadastros, padrão qwen2.5:3b |
| AGENTIC_SYSADMIN_URL | Alvo único definido no servidor, padrão http://127.0.0.1:52773/api/admin |
| AGENTIC_SYSADMIN_USER / PASSWORD | Credenciais do alvo externo; nunca enviadas ao modelo ou navegador |

Para o alvo local padrão, a instalação gera uma credencial própria, mantida no volume com permissão de arquivo 0600. Ela possui o recurso nativo %Admin_Operate; o gateway restringe seu uso às consultas revisadas. A credencial não é uma garantia nativa de leitura exclusiva.

O catálogo contém todas as 276 operações, mas somente 18 consultas revisadas podem ser atribuídas. A lista é explícita em app/mvp/catalog.py, vinculada ao checksum do contrato. Alterações administrativas, URLs livres, SQL livre e shell são bloqueados.

## Limites do MVP

- Até 12 ferramentas por agente; listagem limitada a 200 agentes e 100 execuções recentes.
- Um executor por implantação; execução limitada a 240 segundos, 8 iterações e 12 chamadas.
- Modelos locais variam em precisão e desempenho. Falhas de modelo, API e orçamento aparecem no histórico.
- Contagens de consultas filtradas/limitadas não representam necessariamente o total da instância.
- Sem memória vetorial, notificações externas, execução de alterações ou múltiplas instâncias pela interface.
- Entrega via Docker Compose. Instalação IPM não está validada.

## Testes

~~~sh
docker build --target test -t agentic-iris-tests .
~~~

scripts/mvp_smoke.py valida cadastro, edição, conflito de revisão, fila, Ollama, SysAdmin, relatório e pausa. Requer AGENTIC_SMOKE_USER e AGENTIC_SMOKE_PASSWORD no ambiente do container. scripts/mvp_locks_acceptance.py executa um cenário controlado de 50 locks pela sessão Embedded Python de instalação. Esses scripts geram fixtures temporárias, removidas por scripts/mvp_cleanup.py.

Plano: [docs/MVP_PLANO.md](docs/MVP_PLANO.md). Evidências: [docs/MVP_VALIDACAO.md](docs/MVP_VALIDACAO.md). A especificação ampla anterior permanece como referência futura; o plano MVP define o escopo atual.
