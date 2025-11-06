# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-agent e-commerce data analysis system built with Python and FastAPI. The system uses an orchestrator pattern to route user queries about business data (customers, revenue, margin, clusters) to specialized agents that query a Supabase database and return natural language insights.

**Key Technologies:**
- Python 3.x with FastAPI for the REST API
- OpenAI GPT-4 for intent analysis and natural language generation
- Supabase (PostgreSQL) via REST API for data storage
- Async/await throughout for performance

## Project Structure

```
/
├── agente_orquestrador/          # Main production system (current version)
│   ├── agents/                   # Specialized agents for different data views
│   │   ├── orchestrator_agent.py # Main orchestrator (entry point)
│   │   ├── client_view_agent.py  # Customer-focused queries
│   │   ├── cluster_view_agent.py # Customer segment analysis
│   │   ├── period_comparison_agent.py # Time-based comparisons
│   │   ├── sale_view_agent.py    # Transaction-level analysis
│   │   └── product_view_agent.py # Product/category analysis
│   ├── services/
│   │   ├── memory_service.py     # In-memory conversation history
│   │   └── session_manager.py    # Session lifecycle management
│   ├── models.py                 # Pydantic models for data validation
│   ├── config.py                 # Settings and environment variables
│   ├── main.py                   # FastAPI application entry point
│   └── test_system.py            # System integration tests
├── agente_simples/               # Legacy simple agent (reference only)
├── *_github.py                   # Root-level validation/reference files
└── .env                          # Environment variables (in agente_orquestrador/)
```

## Development Commands

### Environment Setup
```bash
# Navigate to main project directory
cd "agente_orquestrador"

# Install dependencies
pip install -r requirements.txt

# Configure environment variables (copy from .env.example if exists)
# Required: OPENAI_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY
```

### Running the Application
```bash
# Start the FastAPI server
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run system tests
python test_system.py

# The test suite validates:
# - Session management
# - Orchestrator agent routing
# - Specialized agents
# - End-to-end integration
```

### API Endpoints
- `GET /` - API info and stats
- `GET /health` - Health check
- `POST /webhook/lovable` - Main webhook endpoint (production)
- `POST /webhook/test` - Test endpoint
- `GET /session/{session_id}` - Session info
- `GET /stats` - Usage statistics

## Architecture

### Agent Orchestration Pattern

The system uses a two-tier architecture:

1. **Orchestrator Agent** (`orchestrator_agent.py`):
   - Single entry point for all user messages
   - Uses OpenAI LLM to analyze user intent
   - Routes to specialized agents OR responds directly
   - Converts data responses to natural language with business insights
   - Manages conversation memory

2. **Specialized Agents** (5 types):
   - `ClientViewAgent` - Customer data (table: `Visão_cliente`)
   - `ClusterViewAgent` - Customer segments (table: `Visão_cluster`)
   - `PeriodComparisonAgent` - Time-series analysis ⚠️ **TEMPORARILY DISABLED** (awaiting time-series table)
   - `SaleViewAgent` - Transaction data (table: `Visão_pedidos`)
   - `ProductViewAgent` - Product/category data (table: `Visão_pedidos` aggregated)

### Intent Analysis Flow

```
User Message
    ↓
Orchestrator: Analyze Intent (LLM)
    ├─→ DATA_ANALYSIS: Extract parameters → Route to Specialist Agent → Convert to Natural Language
    └─→ GENERAL_CHAT: Respond directly with conversational LLM
```

The orchestrator uses `_analyze_business_intent()` to:
- Classify intent as `data_analysis` or `general_chat`
- Extract structured parameters (table, filters, aggregations, ordering)
- Identify which specialist agent should handle the query
- This is done via OpenAI prompt with JSON response parsing

### Data Model

**Supabase Tables (New Database - Portuguese naming convention):**
- `Visão_cliente` - Customer metrics (revenue, margin, cluster, recency, frequency)
- `Visão_cluster` - Segment aggregates (5 clusters: Premium=1, Alto=2, Médio=3, Baixo=4, Novos=5)
- ⚠️ Time-series table - **NOT YET CREATED** (Period comparison temporarily disabled)
- `Visão_pedidos` - Individual transactions/orders

**Key Metrics:**
- `receita_bruta_12m` / `receita_liquida_12m` - Revenue
- `gm_12m` / `gm_pct_12m` - Gross margin
- `mcc` / `mcc_pct` - Customer contribution margin
- `cluster` - Customer segment (1-5)
- `pedidos_12m` - Order frequency
- `recencia_dias` - Days since last order

## Implementation Guidelines

### Adding a New Specialized Agent

1. Create `agents/new_agent.py` implementing `process_instruction(instruction: AgentInstruction) -> AgentResponse`
2. Add `AgentType.NEW_AGENT` to `models.py` enum
3. Import in `agents/__init__.py`
4. Update `orchestrator_agent.py`:
   - Import and initialize the new agent in `__init__`
   - Add routing logic in `_analyze_business_intent()` prompt
   - Route in `_handle_business_data_request()` if needed

### Working with the Orchestrator

The orchestrator has two main response paths:

**Path 1: Data Analysis**
- `_analyze_business_intent()` → Extract parameters
- `_handle_business_data_request()` → Delegate to specialist agent
- `_convert_business_data_to_natural()` → Convert JSON to insights

**Path 2: General Chat**
- `_handle_business_chat()` → Direct LLM response with context

### Memory Management

- `MemoryService` stores conversation history in-memory (per session)
- Sessions tracked by `session_id`
- Recent context (last 6 messages) passed to LLM for continuity
- Production may need Redis/database persistence (see `session_manager.py`)

### Supabase Integration

Agents use `httpx.AsyncClient()` to call Supabase REST API:
- Base URL: `{SUPABASE_URL}/rest/v1/{table}`
- Auth: `apikey` and `Authorization: Bearer {SUPABASE_ANON_KEY}` headers
- Filters: `field=eq.value` query params
- Select: `select=field1,field2`
- Order: `order=field.desc`
- Limit: `limit=N`

### Error Handling

- All async methods use try/except with fallback responses
- Orchestrator has global exception handler returning user-friendly messages
- Failed queries return `AgentResponse(success=False, error=...)`
- Intent analysis has keyword-based fallback if LLM parsing fails

## Common Development Tasks

### Debugging Agent Routing
Check logs for:
- "🔍 Intenção: {intent_type}" - Intent classification
- "📤 Consultando banco de dados" - Database query triggered
- "✅ Dados obtidos ({N} registros)" - Successful data retrieval
- Print statements in agents show query URLs

### Modifying Intent Analysis
Edit `_analyze_business_intent()` prompt in `orchestrator_agent.py`:
- Add/modify keyword examples
- Adjust parameter extraction logic
- Update fallback keyword detection

### Changing Response Style
Edit `_convert_business_data_to_natural()` prompt in `orchestrator_agent.py`:
- Adjust analysis depth requirements
- Modify output format (currently: Numbers → Analysis → Insights → Action Plan → Alerts)
- Change temperature/max_tokens for creativity vs consistency

### Environment Variables
Located in `agente_orquestrador/.env`:
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4

# New Supabase Database (migrated from Lovable Cloud)
SUPABASE_URL=https://qtetgofuzwcsszozcgwv.supabase.co
SUPABASE_ANON_KEY=eyJ...
# Tables: Visão_cliente, Visão_cluster, Visão_pedidos
```

## Important Notes

- **Working Directory**: Always `cd agente_orquestrador` before running commands
- **Async/Await**: All agent methods are async; use `await` and `asyncio.run()`
- **Two Codebases**: `agente_orquestrador/` is current; root-level `*_github.py` files are reference/validation copies
- **LLM Costs**: System makes multiple OpenAI calls per user query (intent analysis + data conversion)
- **Session Isolation**: Each `session_id` maintains separate conversation history
- **Portuguese Output**: All user-facing responses are in Brazilian Portuguese
- **Business Focus**: System is specialized for e-commerce metrics, not a general-purpose SQL agent

## Database Migration Notes

**Migration Date**: 2025-11-05
**Previous**: Lovable Cloud backend
**Current**: New Supabase instance at `https://qtetgofuzwcsszozcgwv.supabase.co`

**Table Name Changes** (Portuguese naming convention):
- `clientes` → `Visão_cliente`
- `clusters` → `Visão_cluster`
- `pedidos` → `Visão_pedidos`
- `monthly_series` → ⚠️ **Not yet created** (PeriodComparisonAgent disabled)

**Future Work**:
- Create time-series table for period comparisons
- Create dedicated product table (currently using aggregated `Visão_pedidos`)
- Re-enable PeriodComparisonAgent when time-series table is available
