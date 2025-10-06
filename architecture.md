# 🏗️ Arquitetura do Sistema - Visão Completa

## 📐 Diagrama de Arquitetura

```
┌──────────────────────────────────────────────────────────────────┐
│                           USUÁRIO                                 │
│                    (Frontend/Webhook)                             │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                │ HTTP POST /webhook/lovable
                                │ {"message": "...", "sessionId": "..."}
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│                      MAIN.PY (FastAPI)                            │
│  ────────────────────────────────────────────────────────────    │
│  • Recebe requisições HTTP                                        │
│  • Valida payload                                                 │
│  • Extrai message + sessionId                                     │
│  • Delega ao Orchestrator                                         │
│  • Retorna resposta formatada                                     │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                │ orchestrator.process_user_message()
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│            CAMADA 1: ORCHESTRATOR AGENT                           │
│  ──────────────────────────────────────────────────────────────  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 1. SALVAR MENSAGEM DO USUÁRIO                              │  │
│  │    memory.add_message(session_id, "user", message)         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                          ↓                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 2. RECUPERAR CONTEXTO                                      │  │
│  │    context = memory.get_recent_context(session_id)         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                          ↓                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 3. ANALISAR INTENÇÃO (LLM)                                 │  │
│  │    intent = _analyze_intent(message, context)              │  │
│  │    • Determina: DATA_ANALYSIS ou GENERAL_CHAT              │  │
│  │    • Extrai parâmetros estruturados                        │  │
│  │    • Confidence score                                      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                          ↓                                        │
│              ┌───────────┴───────────┐                            │
│              ↓                       ↓                            │
│  ┌──────────────────────┐  ┌──────────────────────┐              │
│  │ 4a. DADOS NECESSÁRIOS│  │ 4b. CONVERSA GERAL   │              │
│  │ _handle_data_request │  │ _handle_general_chat │              │
│  └──────────┬───────────┘  └──────────────────────┘              │
│             │                         │                           │
│             │                         │ LLM direto                │
│             │                         ↓                           │
│             │              ┌──────────────────────┐               │
│             │              │ Resposta natural     │               │
│             │              └──────────────────────┘               │
│             │                                                     │
│             │ Criar AgentInstruction                              │
│             ↓                                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ DELEGAR A AGENTE ESPECIALISTA                              │  │
│  │ sql_agent.process_instruction(instruction)                 │  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                │ AgentInstruction {
                                │   agent_type: SQL,
                                │   parameters: {
                                │     query_type: "aggregate",
                                │     table: "clientes",
                                │     filters: {...}
                                │   }
                                │ }
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│            CAMADA 2: SQL AGENT (Specialist)                       │
│  ──────────────────────────────────────────────────────────────  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 1. RECEBER INSTRUÇÃO ESTRUTURADA                           │  │
│  │    • NÃO interpreta linguagem natural                      │  │
│  │    • Apenas executa o que foi pedido                       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                          ↓                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 2. ESCOLHER MÉTODO DE EXECUÇÃO                             │  │
│  │    • aggregate → _execute_aggregate()                      │  │
│  │    • count → _execute_count()                              │  │
│  │    • select → _execute_select()                            │  │
│  │    • filter → _execute_filter()                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                          ↓                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 3. EXECUTAR QUERY NO SUPABASE                              │  │
│  │    • Construir URL com parâmetros                          │  │
│  │    • Fazer requisição HTTP                                 │  │
│  │    • Agregar dados manualmente (se necessário)             │  │
│  └────────────────────────────────────────────────────────────┘  │
│                          ↓                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 4. RETORNAR JSON ESTRUTURADO                               │  │
│  │    AgentResponse {                                         │  │
│  │      success: true,                                        │  │
│  │      data: {...},                                          │  │
│  │      metadata: {execution_time, row_count, ...}            │  │
│  │    }                                                       │  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                │ AgentResponse (JSON)
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│            VOLTA PARA ORCHESTRATOR                                │
│  ──────────────────────────────────────────────────────────────  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 5. CONVERTER JSON → LINGUAGEM NATURAL                      │  │
│  │    natural = _convert_to_natural_language(data)            │  │
│  │    • LLM transforma dados em texto                         │  │
│  │    • Adiciona insights de negócio                          │  │
│  │    • Usa emojis e formatação                               │  │
│  └────────────────────────────────────────────────────────────┘  │
│                          ↓                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 6. SALVAR RESPOSTA NA MEMÓRIA                              │  │
│  │    memory.add_message(session_id, "assistant", response)   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                          ↓                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 7. RETORNAR OrchestratorResponse                           │  │
│  │    {                                                       │  │
│  │      response: "texto natural",                            │  │
│  │      agents_used: [...],                                   │  │
│  │      processing_steps: [...]                               │  │
│  │    }                                                       │  │
│  └────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│                    RETORNA PARA MAIN.PY                           │
│  ────────────────────────────────────────────────────────────    │
│  • Formata resposta JSON final                                    │
│  • Retorna HTTP 200 com payload                                   │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│                           USUÁRIO                                 │
│  Recebe: {                                                        │
│    "response": "📊 Texto natural com insights...",                │
│    "session_id": "...",                                           │
│    "success": true                                                │
│  }                                                                │
└──────────────────────────────────────────────────────────────────┘
```

## 🔄 Fluxo de Memória (Paralelo)

```
┌──────────────────────────────────────────────────────────────────┐
│                    MEMORY SERVICE                                 │
│  ──────────────────────────────────────────────────────────────  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    SUPABASE DATABASE                        │  │
│  │  ────────────────────────────────────────────────────────  │  │
│  │                                                            │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │ agent_conversations                                  │ │  │
│  │  │ ─────────────────────                                │ │  │
│  │  │ • id (UUID)                                          │ │  │
│  │  │ • session_id (TEXT, UNIQUE)                          │ │  │
│  │  │ • created_at (TIMESTAMP)                             │ │  │
│  │  │ • updated_at (TIMESTAMP)                             │ │  │
│  │  │ • metadata (JSONB)                                   │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  │                          │                                 │  │
│  │                          │ 1:N                             │  │
│  │                          ↓                                 │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │ agent_messages                                       │ │  │
│  │  │ ──────────────                                       │ │  │
│  │  │ • id (BIGSERIAL)                                     │ │  │
│  │  │ • session_id (FK → agent_conversations)              │ │  │
│  │  │ • role (TEXT: user|assistant|system)                 │ │  │
│  │  │ • content (TEXT)                                     │ │  │
│  │  │ • timestamp (TIMESTAMP)                              │ │  │
│  │  │ • metadata (JSONB)                                   │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ OPERAÇÕES                                                  │  │
│  │ ─────────                                                  │  │
│  │ • add_message() → INSERT INTO agent_messages              │  │
│  │ • get_conversation_history() → SELECT com filtros         │  │
│  │ • get_recent_context() → SELECT últimas N mensagens       │  │
│  │ • clear_session() → DELETE de uma sessão                  │  │
│  │ • _cleanup_old_messages() → DELETE antigas                │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ FALLBACK: Cache em Memória                                 │  │
│  │ ────────────────────────────                               │  │
│  │ _memory_cache: Dict[session_id, ConversationHistory]       │  │
│  │ • Usado se Supabase falhar                                 │  │
│  │ • Sincroniza quando possível                               │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## 📦 Estrutura de Dados

### AgentInstruction (Orchestrator → Specialist)
```python
{
  "agent_type": "sql_agent",
  "task_description": "Calcular receita total do cluster premium",
  "parameters": {
    "query_type": "aggregate",        # aggregate|count|select|filter
    "table": "clientes",
    "fields": ["receita_12m", "gm_12m"],
    "filters": {
      "cluster_id": "1"
    },
    "aggregation": {
      "receita_12m": "sum",
      "gm_12m": "avg"
    },
    "order_by": "receita_12m.desc",
    "limit": 10
  },
  "context": {
    "user_question": "Quanto o cluster premium faturou?",
    "intent_reasoning": "Usuário quer dados agregados"
  },
  "session_id": "user123"
}
```

### AgentResponse (Specialist → Orchestrator)
```python
{
  "success": true,
  "agent_type": "sql_agent",
  "data": {
    "results": [
      {
        "receita_12m_sum": 2500000.00,
        "gm_12m_avg": 0.25,
        "total_records": 150,
        "filters_applied": {"cluster_id": "1"}
      }
    ]
  },
  "error": null,
  "metadata": {
    "row_count": 1,
    "execution_time": 0.15,
    "query_info": {
      "method": "aggregate_manual",
      "table": "clientes",
      "url": "https://..."
    },
    "query_type": "aggregate"
  },
  "execution_time": 0.15
}
```

### OrchestratorResponse (Orchestrator → User)
```python
{
  "response": "📊 O Cluster 1 (Premium) teve uma receita total de R$ 2,5 milhões...",
  "session_id": "user123",
  "timestamp": "2025-10-05T10:30:00",
  "success": true,
  "agents_used": ["orchestrator", "sql_agent"],
  "processing_steps": [
    "💾 Mensagem salva na memória",
    "📚 Contexto recuperado (8 msgs)",
    "🔍 Intenção: data_analysis",
    "📤 Instrução enviada ao SQL Agent",
    "✅ Dados recebidos (1 registros)",
    "🗣️ Resposta convertida para linguagem natural",
    "💾 Resposta salva na memória"
  ],
  "metadata": {
    "intent_confidence": 0.95,
    "intent_type": "data_analysis"
  }
}
```

## 🎯 Responsabilidades por Camada

### CAMADA 1: Orchestrator Agent
✅ **FAZ:**
- Recebe mensagens do usuário
- Mantém contexto da conversa
- Analisa intenção com LLM
- Decide qual agente chamar
- Extrai parâmetros estruturados
- Converte JSON em linguagem natural
- Gerencia memória persistente

❌ **NÃO FAZ:**
- Executar queries SQL diretamente
- Acessar banco de dados de negócio
- Ter lógica de domínio específica

### CAMADA 2: SQL Agent
✅ **FAZ:**
- Recebe instruções estruturadas
- Executa queries no Supabase
- Agrega dados manualmente
- Retorna JSON estruturado
- Trata erros de query

❌ **NÃO FAZ:**
- Interpretar linguagem natural
- Decidir qual query executar
- Formatar resposta para usuário
- Manter estado ou memória

### Memory Service
✅ **FAZ:**
- Persiste conversas no Supabase
- Recupera histórico
- Gerencia context window
- Limpa mensagens antigas
- Fallback para cache em memória

❌ **NÃO FAZ:**
- Processar conteúdo das mensagens
- Tomar decisões de negócio
- Formatar dados

## 🔐 Separação de Preocupações

```
┌─────────────────────────────────────────────────┐
│  ORCHESTRATOR                                   │
│  ─────────────                                  │
│  • Lógica de negócio                            │
│  • Tomada de decisão                            │
│  • Gestão de contexto                           │
│  • Conversão para linguagem natural             │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  SPECIALISTS (SQL, etc)                         │
│  ───────────────────────                        │
│  • Execução técnica pura                        │
│  • Sem lógica de negócio                        │
│  • Entrada/Saída estruturada                    │
│  • Stateless (sem memória)                      │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  SERVICES (Memory, etc)                         │
│  ──────────────────────                         │
│  • Infraestrutura                               │
│  • Persistência                                 │
│  • Utilitários                                  │
│  • Sem lógica de negócio                        │
└─────────────────────────────────────────────────┘
```

## 🚀 Extensibilidade

Para adicionar novo agente especialista:

```python
# 1. Criar arquivo agents/novo_agent.py
class NovoAgent:
    async def process_instruction(
        self, 
        instruction: AgentInstruction
    ) -> AgentResponse:
        # Implementação
        pass

# 2. Registrar no Orchestrator
class OrchestratorAgent:
    def __init__(self):
        self.sql_agent = SQLAgent()
        self.novo_agent = NovoAgent()  # ← Adicionar

# 3. Atualizar análise de intenção
# Incluir nova lógica para detectar quando chamar NovoAgent

# 4. Adicionar ao enum
class AgentType(str, Enum):
    SQL = "sql_agent"
    NOVO = "novo_agent"  # ← Adicionar
```

**Nenhuma mudança necessária em:**
- Models
- Memory Service
- Main.py (endpoints)
- Estrutura de dados