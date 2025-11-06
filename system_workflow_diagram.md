# Multi-Agent System Workflow Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER / CLIENT                                │
│                  (Lovable Frontend / Webhook)                        │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          │ HTTP POST /webhook/lovable
                          │ { session_id, user_message }
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FASTAPI APPLICATION                             │
│                         (main.py)                                    │
│  • CORS Middleware                                                   │
│  • Session Manager                                                   │
│  • Error Handling                                                    │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          │ process_user_message()
                          ▼
╔═════════════════════════════════════════════════════════════════════╗
║                   ORCHESTRATOR AGENT                                 ║
║                 (orchestrator_agent.py)                              ║
║                                                                       ║
║  🎯 MAIN COORDINATOR - Single Entry Point                           ║
╚═════════════════════════════════════════════════════════════════════╝
                          │
                          │ Step 1: Save user message
                          ▼
                 ┌────────────────────┐
                 │  Memory Service    │
                 │  (in-memory store) │
                 └────────────────────┘
                          │
                          │ Step 2: Get recent context (6 messages)
                          │
                          ▼
╔═════════════════════════════════════════════════════════════════════╗
║               INTENT ANALYSIS (LLM - OpenAI GPT-4)                   ║
║             _analyze_business_intent()                               ║
║                                                                       ║
║  Input: user_message + conversation_context                          ║
║  Output: IntentAnalysis {                                            ║
║    intent_type: "data_analysis" | "general_chat"                     ║
║    confidence: 0.0-1.0                                               ║
║    needs_data_analysis: boolean                                      ║
║    requires_agent: AgentType | null                                  ║
║    extracted_parameters: {                                           ║
║      query_type: "aggregate" | "count" | "select" | "filter"        ║
║      table: "clientes" | "clusters" | "pedidos" | "monthly_series"  ║
║      filters: {...}                                                  ║
║      fields: [...]                                                   ║
║      aggregation: {...}                                              ║
║      order_by: "field.desc"                                          ║
║      limit: N                                                        ║
║    }                                                                 ║
║  }                                                                   ║
╚═════════════════════════════════════════════════════════════════════╝
                          │
                          │ Step 3: Route based on intent
                          │
                ┌─────────┴──────────┐
                │                    │
    intent = "data_analysis"    intent = "general_chat"
                │                    │
                ▼                    ▼
    ┌───────────────────┐   ┌──────────────────┐
    │ DELEGATE TO       │   │ DIRECT RESPONSE  │
    │ SPECIALIST AGENT  │   │ WITH LLM         │
    └───────────────────┘   └──────────────────┘
                │                    │
                │                    │
                ▼                    │
╔═══════════════════════════════════╗│
║  SPECIALIST AGENTS LAYER          ││
║  (5 Specialized Agents)           ││
╚═══════════════════════════════════╝│
                │                    │
    ┌───────────┼───────────┬────────┼─────┬────────┐
    │           │           │        │     │        │
    ▼           ▼           ▼        ▼     ▼        │
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
│Client  │ │Cluster │ │Period  │ │Sale    │ │Product   │
│View    │ │View    │ │Compare │ │View    │ │View      │
│Agent   │ │Agent   │ │Agent   │ │Agent   │ │Agent     │
└────────┘ └────────┘ └────────┘ └────────┘ └──────────┘
    │           │           │        │          │
    │ All agents query Supabase via REST API    │
    │           │           │        │          │
    └───────────┴───────────┴────────┴──────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │      SUPABASE DATABASE         │
         │      (PostgreSQL REST API)     │
         │                                │
         │  Tables:                       │
         │  • clientes                    │
         │  • clusters                    │
         │  • pedidos                     │
         │  • monthly_series              │
         └────────────────────────────────┘
                          │
                          │ Return JSON data
                          ▼
╔═════════════════════════════════════════════════════════════════════╗
║         DATA TO NATURAL LANGUAGE CONVERSION                          ║
║         _convert_business_data_to_natural()                          ║
║                                                                       ║
║  Input: JSON data + metadata                                         ║
║  Process: LLM (OpenAI GPT-4) with deep analysis prompt              ║
║  Output: Natural language response with:                             ║
║    📊 Main Numbers                                                   ║
║    🔍 Deep Analysis                                                  ║
║    💡 Strategic Insights (2-3 specific)                              ║
║    🎯 Action Plan (detailed, implementable)                          ║
║    ⚠️  Alerts & Risks                                                ║
╚═════════════════════════════════════════════════════════════════════╝
                          │
                          │ Step 4: Save response
                          ▼
                 ┌────────────────────┐
                 │  Memory Service    │
                 │  (conversation     │
                 │   history)         │
                 └────────────────────┘
                          │
                          │ Step 5: Return to user
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR RESPONSE                             │
│  {                                                                   │
│    response: "Natural language answer...",                           │
│    session_id: "...",                                                │
│    success: true,                                                    │
│    agents_used: [ORCHESTRATOR, CLIENT_VIEW],                         │
│    processing_steps: ["💾 Saved", "📚 Context", ...],               │
│    metadata: {...}                                                   │
│  }                                                                   │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          │ JSON Response
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         USER / CLIENT                                │
│              Receives natural language answer                        │
└─────────────────────────────────────────────────────────────────────┘
```

## Detailed Flow Examples

### Example 1: Data Analysis Query

```
USER: "Quais são os top 10 clientes por receita?"

    ↓

ORCHESTRATOR: Analyze Intent
    • Intent: data_analysis ✓
    • Needs: CLIENT_VIEW_AGENT
    • Parameters: {
        query_type: "select",
        table: "clientes",
        fields: ["id", "receita_bruta_12m", "cluster"],
        order_by: "receita_bruta_12m.desc",
        limit: 10
      }

    ↓

CLIENT_VIEW_AGENT: Execute Query
    • Build Supabase URL with filters
    • GET /rest/v1/clientes?select=...&order=...&limit=10
    • Return: AgentResponse with JSON data

    ↓

ORCHESTRATOR: Convert to Natural Language
    • Prompt: "Analyze these 10 clients..."
    • LLM generates insights:
      📊 "Os top 10 clientes geram R$ 580.450..."
      🔍 "Concentração de 43% da receita..."
      💡 "3 clientes em risco de churn..."
      🎯 "Implementar programa VIP com..."

    ↓

USER: Receives natural language response
```

### Example 2: General Chat

```
USER: "Olá, como você está?"

    ↓

ORCHESTRATOR: Analyze Intent
    • Intent: general_chat ✓
    • Needs: Direct response (no agent)

    ↓

ORCHESTRATOR: _handle_business_chat()
    • Use OpenAI with conversation context
    • Generate friendly response
    • No database query needed

    ↓

USER: Receives conversational response
```

## Agent Specializations

```
┌──────────────────────────────────────────────────────────────┐
│ CLIENT VIEW AGENT                                             │
│ • Focus: Individual customer analysis                         │
│ • Table: clientes                                             │
│ • Keywords: "cliente", "top clientes", "perfil"              │
│ • Examples:                                                   │
│   - "Top 10 clientes por receita"                            │
│   - "Clientes do cluster premium"                            │
│   - "Clientes inativos há 90+ dias"                          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ CLUSTER VIEW AGENT                                            │
│ • Focus: Customer segment analysis                            │
│ • Table: clusters                                             │
│ • Keywords: "cluster", "segmento", "comportamento"           │
│ • Examples:                                                   │
│   - "Compare performance entre clusters"                      │
│   - "Qual cluster tem mais clientes?"                        │
│   - "Clusters com tendência de crescimento"                  │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ PERIOD COMPARISON AGENT                                       │
│ • Focus: Time-series and temporal analysis                    │
│ • Table: monthly_series                                       │
│ • Keywords: "comparar", "variação", "crescimento", "mês"     │
│ • Examples:                                                   │
│   - "Compare receita deste mês com anterior"                 │
│   - "Variação da margem entre Q1 e Q2"                       │
│   - "Crescimento nos últimos 6 meses"                        │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ SALE VIEW AGENT                                               │
│ • Focus: Transaction-level analysis                           │
│ • Table: pedidos                                              │
│ • Keywords: "venda", "pedido", "transação"                   │
│ • Examples:                                                   │
│   - "Top 20 vendas por receita"                              │
│   - "Vendas de janeiro com margem >50%"                      │
│   - "Volume de vendas por categoria"                         │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ PRODUCT VIEW AGENT                                            │
│ • Focus: Product/category analysis                            │
│ • Table: pedidos (aggregated)                                 │
│ • Keywords: "produto", "categoria", "item"                    │
│ • Examples:                                                   │
│   - "Produtos mais vendidos"                                 │
│   - "Produtos com maior margem"                              │
│   - "Receita por categoria"                                  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow Detail

```
┌─────────────────────────────────────────────────────────────┐
│                  SUPABASE REST API CALLS                     │
│                                                              │
│  Base URL: {SUPABASE_URL}/rest/v1/{table}                   │
│                                                              │
│  Headers:                                                    │
│    apikey: {SUPABASE_ANON_KEY}                              │
│    Authorization: Bearer {SUPABASE_ANON_KEY}                │
│                                                              │
│  Query Parameters:                                           │
│    • select=field1,field2     - Select specific fields      │
│    • field=eq.value           - Filter equality             │
│    • order=field.desc         - Ordering                    │
│    • limit=N                  - Limit results               │
│                                                              │
│  Example:                                                    │
│  GET /rest/v1/clientes?                                      │
│      select=id,receita_bruta_12m,cluster&                   │
│      cluster=eq.1&                                           │
│      order=receita_bruta_12m.desc&                          │
│      limit=10                                                │
│                                                              │
│  Returns: JSON array of results                              │
└─────────────────────────────────────────────────────────────┘
```

## Memory & Session Management

```
┌───────────────────────────────────────────────────────────┐
│                  MEMORY SERVICE                            │
│                                                            │
│  session_id_to_messages = {                                │
│    "session_123": [                                        │
│      { role: "user", content: "...", timestamp: "..." },  │
│      { role: "assistant", content: "...", metadata: {...} }│
│    ]                                                       │
│  }                                                         │
│                                                            │
│  Methods:                                                  │
│    • add_message(session_id, role, content, metadata)      │
│    • get_recent_context(session_id, num_messages=6)        │
│                                                            │
│  Note: Currently in-memory (not persistent)                │
│  Production: Extend with Redis/Database                    │
└───────────────────────────────────────────────────────────┘
```

## Error Handling Flow

```
Try:
  ├─→ Process user message
  │   ├─→ Analyze intent
  │   ├─→ Route to agent OR respond directly
  │   └─→ Convert to natural language
  │
Catch Exception:
  ├─→ Log error
  ├─→ Return user-friendly error message
  ├─→ Save error in metadata
  └─→ Return OrchestratorResponse(success=False)
```

## Key Decision Points

```
┌────────────────────────────────────────────────────────┐
│  DECISION 1: Analyze Intent                            │
│                                                         │
│  IF message contains business data keywords            │
│     (receita, margem, cliente, cluster, etc.)          │
│  THEN: intent = "data_analysis"                        │
│  ELSE: intent = "general_chat"                         │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  DECISION 2: Which Specialist Agent?                   │
│                                                         │
│  Keywords → Agent mapping:                             │
│  • "cliente", "top clientes" → CLIENT_VIEW_AGENT       │
│  • "cluster", "segmento" → CLUSTER_VIEW_AGENT          │
│  • "comparar", "variação" → PERIOD_COMPARISON_AGENT    │
│  • "venda", "pedido" → SALE_VIEW_AGENT                 │
│  • "produto", "categoria" → PRODUCT_VIEW_AGENT         │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  DECISION 3: Query Type                                │
│                                                         │
│  • "quantos", "count" → query_type: "count"            │
│  • "total", "soma" → query_type: "aggregate"           │
│  • "top", "lista" → query_type: "select"               │
│  • filters present → query_type: "filter"              │
└────────────────────────────────────────────────────────┘
```
