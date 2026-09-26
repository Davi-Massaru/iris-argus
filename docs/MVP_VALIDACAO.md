# Validação do MVP

## Escopo

Plataforma para o DBA criar agentes. Instruções, tarefa e ferramentas são configuradas pelo usuário e persistidas em `Agentic.MVP_AGENT`. Cada execução preserva uma cópia da configuração em `Agentic.MVP_RUN`. Evidências ficam em `Agentic.MVP_CALL`.

## Controles implementados

- Catálogo de 276 operações do contrato fixado: GET, POST, PUT, DELETE e HEAD. No primeiro setup, 18 GETs revisados são habilitados uma vez; as demais operações começam bloqueadas em `AI_TOOL_VERSION.Enabled`.
- Presets DBA: `Enable reviewed reads` habilita as 18 operações revisadas; `Block all` bloqueia o catálogo. O marcador de bootstrap impede que restarts sobrescrevam decisões posteriores do DBA.
- `AgenticDBAApprover` pode habilitar ou bloquear operações na interface. Cada alteração persiste ator e decisão em `AI_TOOL_POLICY_OVERRIDE`.
- Habilitar uma operação é autorização contínua para agentes atribuídos chamá-la automaticamente, inclusive em execuções agendadas; não há aprovação por chamada.
- Atribuição exige disponibilidade ativa. O gateway revalida a disponibilidade antes da execução e novamente imediatamente antes do despacho.
- Gateway valida parâmetros fixos e o schema OpenAPI, envia o método e body JSON definidos pelo contrato, recusa redirects e limita o tamanho da resposta.
- Operações que podem alterar estado exibem confirmação no toggle. Schemas com campos sensíveis também exigem reconhecimento; chaves de senha, token e credencial reconhecidas são redigidas na evidência persistida.
- A disponibilidade não amplia privilégios da identidade SysAdmin configurada. O alvo ainda precisa autorizar a operação.
- Fila transacional, uma execução pendente por agente, revisão otimista na edição e cópia das instruções por execução.
- Um worker por implantação, um executor por vez. Limites: 240 segundos, 8 iterações, 12 chamadas e 500 linhas por consulta quando o parâmetro existe.
- Pausa impede novos agendamentos e cancela itens ainda não iniciados quando são retirados da fila. Execuções em andamento podem terminar.
- Reinício encerra execuções interrompidas como falha, sem repetição automática dessas execuções.
- Relatórios sem uma ferramenta consultada com sucesso são recusados. Falhas parciais são identificadas.
- Evidência completa fica no banco; listas grandes são resumidas para o modelo, com contagem de linhas retornadas e indicação de amostra.

## Evidência de baseline

- Build com LangChain no runtime IRIS passou.
- Cadastro pela interface foi salvo e exibido no banco real.
- Consulta SysAdmin de locks executada pelo agente com credencial local gerada.
- Primeiro modelo (`qwen3:4b`) excedeu o orçamento de execução em CPU. O erro foi registrado e o slot liberado. Padrão alterado para `qwen2.5:3b`; verificação final pendente.

## Verificação do fluxo de disponibilidade

- `docker run --rm --entrypoint python3 agentic-iris-tests -m pytest -q`: 42 testes passaram.
- `docker compose build`: passou com validação de `specification/reviewed_read_operations.json` contra o SHA-256 do contrato pinado.
- API live após bootstrap: 276 operações no catálogo, 18 marcadas como defaults revisados e 18 habilitadas; nenhum não-GET liberado.
- `docker build --target runtime -t agentic-iris-runtime .`: build concluído usando a imagem pinada do IRIS 2026.2.
- A seleção do provider OpenAI é testada com um cliente mockado. O adapter real também foi instanciado offline com uma chave descartável; nenhuma chamada externa foi feita.
- Os testes de gateway usam transporte falso. Nenhuma operação SysAdmin mutável foi enviada a um destino real nesta validação.

Os scripts de aceitação criam apenas fixtures temporárias identificadas. `scripts/mvp_cleanup.py` remove essas fixtures e restaura os estados de disponibilidade registrados antes do teste, sem agentes pré-cadastrados na entrega.
