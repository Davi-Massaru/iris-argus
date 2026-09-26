# Validação do MVP

## Escopo

Plataforma para o DBA criar agentes. Instruções, tarefa e ferramentas são configuradas pelo usuário e persistidas em `Agentic.MVP_AGENT`. Cada execução preserva uma cópia da configuração em `Agentic.MVP_RUN`. Evidências ficam em `Agentic.MVP_CALL`.

## Controles implementados

- Catálogo de 276 operações do contrato fixado; 18 consultas revisadas disponíveis para atribuição.
- Gateway verifica atribuição, parâmetros fixos, schema, alvo configurado e limite da resposta. Redirecionamentos e operações de alteração são recusados.
- Fila transacional, uma execução pendente por agente, revisão otimista na edição e cópia das instruções por execução.
- Um worker por implantação, um executor por vez. Limites: 240 segundos, 8 iterações, 12 chamadas e 500 linhas por consulta quando o parâmetro existe.
- Pausa impede novos agendamentos e cancela itens ainda não iniciados quando são retirados da fila. Execuções em andamento podem terminar.
- Reinício encerra execuções interrompidas como falha, sem repetição automática dessas execuções.
- Relatórios sem uma ferramenta consultada com sucesso são recusados. Falhas parciais são identificadas.
- Evidência completa fica no banco; listas grandes são resumidas para o modelo, com contagem de linhas retornadas e indicação de amostra.

## Evidência em andamento

- Build com LangChain no runtime IRIS passou.
- Cadastro pela interface foi salvo e exibido no banco real.
- Consulta SysAdmin de locks executada pelo agente com credencial local gerada.
- Primeiro modelo (`qwen3:4b`) excedeu o orçamento de execução em CPU. O erro foi registrado e o slot liberado. Padrão alterado para `qwen2.5:3b`; verificação final pendente.

Os scripts de aceitação criam apenas fixtures temporárias identificadas. `scripts/mvp_cleanup.py` remove essas fixtures, sem agentes pré-cadastrados na entrega.
