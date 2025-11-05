# Documentação dos Agentes Especializados

## 📋 Visão Geral

O sistema foi refatorado para usar agentes especializados, cada um focado em um tipo específico de análise de dados. O **Orquestrador** agora funciona como um verdadeiro orquestrador, entendendo o papel de cada agente e roteando as solicitações para o agente mais apropriado.

---

## 🎯 Agente Orquestrador

### Responsabilidades

O **Orquestrador** é o ponto de entrada único do sistema. Ele:

1. **Analisa a intenção** do usuário usando LLM (OpenAI)
2. **Identifica qual agente especializado** deve processar a solicitação
3. **Roteia para o agente apropriado** baseado nas palavras-chave e contexto
4. **Converte os resultados** em linguagem natural com insights profundos

### Processo de Roteamento

```
Mensagem do Usuário
    ↓
Análise de Intenção (LLM)
    ↓
Identificação do Agente Especializado
    ↓
Roteamento para o Agente
    ↓
Processamento pelo Agente
    ↓
Conversão em Linguagem Natural
    ↓
Resposta ao Usuário
```

---

## 🔍 Agentes Especializados

### 1. Period Comparison Agent

**Especialidade**: Comparação de Períodos

#### Responsabilidades
- Comparar métricas entre diferentes períodos (meses, trimestres, anos)
- Calcular variações percentuais e absolutas
- Identificar tendências e padrões temporais
- Analisar crescimento/declínio de receita, margem, clientes, etc

#### Quando Usar
- Perguntas sobre comparação entre períodos
- Análise de variações temporais
- Identificação de tendências

#### Palavras-chave
- "comparar", "variação", "crescimento", "trend", "entre períodos", "vs", "versus"

#### Exemplos de Perguntas
- "Compare a receita deste mês com o mês anterior"
- "Qual foi a variação da margem entre Q1 e Q2?"
- "Mostre o crescimento de clientes nos últimos 6 meses"
- "Compare receita do cluster premium entre este ano e ano passado"

#### Tabelas Principais
- `monthly_series`: Dados mensais consolidados
- `pedidos`: Dados de pedidos por data
- `clientes`: Dados de clientes por período

---

### 2. Client View Agent

**Especialidade**: Visão Cliente

#### Responsabilidades
- Analisar dados consolidados por `cliente_id`
- Identificar perfil de cada cliente (receita, margem, frequência, recência)
- Comparar clientes entre si
- Identificar top clientes, clientes em risco, oportunidades
- Analisar comportamento de clientes por cluster

#### Quando Usar
- Perguntas sobre clientes individuais ou grupos de clientes
- Análise de perfil de clientes
- Ranking e comparação de clientes

#### Palavras-chave
- "cliente(s)", "clientes", "perfil", "cluster", "recência", "top clientes"

#### Exemplos de Perguntas
- "Quais são os top 10 clientes por receita?"
- "Mostre clientes do cluster premium com margem acima de 50%"
- "Quais clientes não compram há mais de 90 dias?"
- "Compare a receita média entre clusters"
- "Quais clientes têm maior margem de contribuição?"

#### Tabela Principal
- `clientes`: Cada linha = um `cliente_id` com métricas consolidadas
  - `receita_bruta_12m`, `receita_liquida_12m`
  - `gm_12m` (margem bruta), `gm_pct_12m`
  - `mcc` (margem contribuição), `mcc_pct`
  - `pedidos_12m`, `recencia_dias`
  - `cluster`, `qtde_produtos`, `cmv_12m`

---

### 3. Sale View Agent

**Especialidade**: Visão Venda

#### Responsabilidades
- Analisar dados consolidados por `id_venda` (pedido_id)
- Identificar características de cada venda (valor, margem, categoria, cliente)
- Analisar vendas por período, categoria, cliente
- Identificar top vendas, vendas com melhor margem
- Analisar padrões de vendas

#### Quando Usar
- Perguntas sobre vendas/pedidos individuais ou grupos de vendas
- Análise de transações
- Performance de vendas

#### Palavras-chave
- "venda(s)", "pedido(s)", "transação", "id_venda", "pedido_id"

#### Exemplos de Perguntas
- "Quais foram as top 20 vendas por receita?"
- "Mostre vendas do mês de janeiro com margem acima de 50%"
- "Quais categorias têm maior volume de vendas?"
- "Compare receita de vendas entre meses"
- "Quais clientes têm mais vendas?"

#### Tabela Principal
- `pedidos`: Cada linha = uma venda (id_venda/pedido_id) com métricas
  - `pedido_id`, `cliente_id`, `data`
  - `receita_bruta`, `margem_bruta`
  - `categoria`

---

### 4. Product View Agent

**Especialidade**: Visão Produto

#### Responsabilidades
- Analisar dados consolidados por produto/categoria
- Identificar produtos mais vendidos, mais rentáveis
- Analisar performance de produtos por categoria
- Comparar produtos entre si
- Identificar oportunidades e produtos em declínio

#### Quando Usar
- Perguntas sobre produtos ou categorias
- Análise de performance de produtos
- Comparação entre categorias

#### Palavras-chave
- "produto(s)", "produtos", "categoria", "categorias", "item", "produtos mais vendidos"

#### Exemplos de Perguntas
- "Quais são os produtos mais vendidos por receita?"
- "Mostre produtos com maior margem bruta"
- "Compare vendas de produtos entre categorias"
- "Quais categorias têm melhor performance?"
- "Analise a receita por categoria no último trimestre"

#### Tabela Principal
- `pedidos`: Agregado por categoria/produto (campo `categoria`)

---

### 5. Cluster View Agent

**Especialidade**: Visão Cluster

#### Responsabilidades
- Analisar dados consolidados por cluster (comportamento de cada cluster)
- Identificar características de cada cluster (receita total, margem média, quantidade de clientes)
- Comparar clusters entre si
- Analisar tendências e volatilidade de clusters
- Identificar padrões de comportamento por cluster
- Analisar performance e saúde de cada cluster

#### Quando Usar
- Perguntas sobre clusters ou segmentos de clientes
- Análise de comportamento consolidado por cluster
- Comparação de performance entre clusters
- Análise de tendências e padrões de clusters

#### Palavras-chave
- "cluster", "clusters", "segmento", "segmentos", "grupo", "comportamento", "clusters"

#### Exemplos de Perguntas
- "Quais são os clusters com maior receita total?"
- "Compare a margem média entre os clusters"
- "Qual cluster tem mais clientes?"
- "Mostre o cluster com maior volatilidade"
- "Quais clusters têm tendência de crescimento?"
- "Analise a performance de cada cluster"
- "Compare o comportamento dos clusters"

#### Tabela Principal
- `clusters`: Cada linha = um cluster com métricas consolidadas
  - `id`, `label` (nome do cluster)
  - `gm_total` (margem bruta total)
  - `gm_pct_medio` (margem bruta média em %)
  - `clientes` (quantidade de clientes)
  - `freq_media` (frequência média de compras)
  - `recencia_media` (recência média em dias)
  - `gm_cv` (coeficiente de variação - volatilidade)
  - `tendencia` (tendência de crescimento)

#### Clusters Existentes
- **1. Premium**: Clientes top de receita - maior valor e melhor performance
- **2. Alto Valor**: Bom faturamento e performance acima da média
- **3. Médio**: Performance regular, clientes estáveis
- **4. Baixo**: Menor faturamento, necessitam atenção
- **5. Novos**: Clientes recentes, potencial de crescimento

---


## 🔄 Fluxo de Roteamento

### Exemplo 1: Comparação de Períodos

```
Usuário: "Compare a receita deste mês com o mês anterior"
    ↓
Orquestrador analisa: Palavras-chave "comparar", "mês" → PERIOD_COMPARISON_AGENT
    ↓
Roteamento para PeriodComparisonAgent
    ↓
Agent busca dados de monthly_series para os 2 meses
    ↓
Calcula variação percentual e absoluta
    ↓
Retorna dados estruturados
    ↓
Orquestrador converte em linguagem natural com insights
    ↓
Resposta: "A receita deste mês foi R$ X, variação de Y% em relação ao mês anterior..."
```

### Exemplo 2: Análise de Clientes

```
Usuário: "Quais são os top 10 clientes por receita?"
    ↓
Orquestrador analisa: Palavras-chave "clientes", "top" → CLIENT_VIEW_AGENT
    ↓
Roteamento para ClientViewAgent
    ↓
Agent busca dados de clientes ordenados por receita_bruta_12m DESC, limit 10
    ↓
Retorna lista de clientes
    ↓
Orquestrador converte em linguagem natural com insights
    ↓
Resposta: "Os top 10 clientes por receita são: 1. Cliente X (R$ Y)..."
```

### Exemplo 3: Análise de Clusters

```
Usuário: "Compare a performance entre os clusters"
    ↓
Orquestrador analisa: Palavras-chave "clusters", "compare" → CLUSTER_VIEW_AGENT
    ↓
Roteamento para ClusterViewAgent
    ↓
Agent busca dados de clusters com todas as métricas
    ↓
Retorna dados comparativos de todos os clusters
    ↓
Orquestrador converte em linguagem natural com insights
    ↓
Resposta: "Comparação de performance: Cluster Premium (R$ X, margem Y%)..."
```

---

## 📊 Estrutura de Dados

### Tabelas e suas Especialidades

| Tabela | Agente Principal | Uso |
|--------|------------------|-----|
| `clientes` | Client View Agent | Análise por cliente_id |
| `pedidos` | Sale View Agent | Análise por id_venda |
| `pedidos` (agregado) | Product View Agent | Análise por categoria/produto |
| `monthly_series` | Period Comparison Agent | Comparação entre períodos |
| `clusters` | Cluster View Agent | Análise por cluster (comportamento consolidado) |

---

## 🎯 Vantagens da Arquitetura Especializada

1. **Especialização**: Cada agente é expert em seu domínio
2. **Manutenibilidade**: Código mais fácil de manter e evoluir
3. **Escalabilidade**: Fácil adicionar novos agentes especializados
4. **Performance**: Agentes otimizados para suas tarefas específicas
5. **Clareza**: Código mais claro e fácil de entender

---

## 🔧 Como Adicionar um Novo Agente

1. Criar novo arquivo `new_agent.py` em `agents/`
2. Herdar padrão de `process_instruction(instruction: AgentInstruction) -> AgentResponse`
3. Adicionar `AgentType.NEW_AGENT` no enum `models.py`
4. Atualizar `__init__.py` em `agents/`
5. Atualizar Orquestrador:
   - Adicionar import
   - Inicializar no `__init__`
   - Adicionar roteamento em `_route_to_specialist_agent`
   - Atualizar prompt de análise de intenção

---

## 📝 Notas Importantes

- O **SQL Agent genérico** ainda existe como fallback para casos não cobertos
- O Orquestrador usa LLM para identificar qual agente usar, mas tem fallback baseado em keywords
- Todos os agentes retornam dados estruturados que são convertidos em linguagem natural pelo Orquestrador
- Cada agente é independente e pode ser testado isoladamente

