# 🤖 Sistema de Agentes Orquestradores - V5.0 Refatorado

Sistema modular de AI Agents com arquitetura em camadas, memória persistente e separação clara de responsabilidades.

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│  CAMADA 1: ORCHESTRATOR AGENT (User-Facing)            │
│  ─────────────────────────────────────────────────      │
│  • Único ponto de contato com usuário                   │
│  • Memória persistente (Supabase)                       │
│  • Análise de intenção (LLM)                           │
│  • Gerenciamento de contexto                           │
│  • Conversão para linguagem natural                    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  CAMADA 2: SPECIALIZED AGENTS                          │
│  ───────────────────────────────────────────────        │
│  • SQL Agent: executa queries estruturadas             │
│  • [Futuros]: Analytics, Export, Visualization         │
│  • Recebem instruções do Orchestrator                  │
│  • Retornam dados estruturados (JSON)                  │
└─────────────────────────────────────────────────────────┘
```

## 📁 Nova Estrutura de Arquivos

```
agente-simples/
├── config.py                    # Configurações centralizadas
├── models.py                    # Modelos de dados (Pydantic)
├── main.py                      # API principal (FastAPI)
├── requirements.txt             # Dependências
├── Procfile                     # Deploy (Heroku/Render)
│
├── agents/
│   ├── __init__.py
│   ├── orchestrator_agent.py   # Orquestrador (Camada 1)
│   └── sql_agent.py            # SQL Agent (Camada 2)
│
├── services/
│   ├── __init__.py
│   └── memory_service.py       # Gerenciamento de memória
│
└── database/
    └── supabase_schema.sql     # Schema do banco
```

## 🚀 Instalação

### 1. Clonar e Instalar Dependências

```bash
git clone https://github.com/RodrigoPortoBR/agente-simples.git
cd agente-simples
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente

Crie arquivo `.env`:

```env
# OpenAI
OPENAI_API_KEY=sk-your-key-here

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here

# Opcional
PORT=8000
```

### 3. Criar Tabelas no Supabase

1. Acesse seu projeto no Supabase
2. Vá em **SQL Editor**
3. Execute o script `database/supabase_schema.sql`
4. Verifique se as tabelas foram criadas:
   - `agent_conversations`
   - `agent_messages`

### 4. Rodar Localmente

```bash
python main.py
```

ou

```bash
uvicorn main:app --reload --port 8000
```

Acesse: `http://localhost:8000`

## 🔌 Endpoints

### Principal

**POST** `/webhook/lovable`
- Endpoint compatível com versão anterior
- Recebe mensagens do usuário
- Retorna resposta natural

```json
// Request
{
  "message": "Qual a receita do cluster 1?",
  "sessionId": "user123"
}

// Response
{
  "response": "📊 O Cluster 1 (Premium) teve receita total de R$ 2.5M...",
  "session_id": "user123",
  "timestamp": "2025-10-05T10:30:00",
  "success": true,
  "agents_used": ["orchestrator", "sql_agent"],
  "processing_steps": [...]
}
```

### Sistema

- **GET** `/` - Info do sistema
- **GET** `/health` - Health check
- **GET** `/debug/memory/{session_id}` - Ver histórico
- **DELETE** `/debug/memory/{session_id}` - Limpar histórico
- **POST** `/debug/test-sql` - Testar SQL Agent
- **GET** `/debug/config` - Ver configuração

## 🧪 Testes

### Testar Conversa Geral

```bash
curl -X POST http://localhost:8000/webhook/lovable \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá!", "sessionId": "test001"}'
```

### Testar Análise de Dados

```bash
curl -X POST http://localhost:8000/webhook/lovable \
  -H "Content-Type: application/json" \
  -d '{"message": "Quantos clientes premium temos?", "sessionId": "test001"}'
```

### Ver Histórico

```bash
curl http://localhost:8000/debug/memory/test001
```

## 🎯 Melhorias Implementadas

### ✅ Arquitetura
- **Modular**: Cada componente em arquivo separado
- **Camadas bem definidas**: Orchestrator (L1) + Specialists (L2)
- **Responsabilidades claras**: Cada agente tem papel específico

### ✅ Memória
- **Persistente**: Supabase guarda histórico completo
- **Context window**: Controle de mensagens enviadas ao LLM
- **Limpeza automática**: Remove mensagens antigas
- **Fallback**: Cache em memória se Supabase falhar

### ✅ SQL Agent
- **Sem lógica de negócio**: Só executa instruções estruturadas
- **4 tipos de query**: aggregate, count, select, filter
- **Agregação manual**: Resolve problemas do Supabase
- **Retorno estruturado**: JSON consistente

### ✅ Orchestrator
- **Análise de intenção**: LLM decide se precisa dados
- **Extração de parâmetros**: Identifica filtros, campos, etc
- **Conversão natural**: Transforma JSON em texto amigável
- **Error handling**: Tratamento robusto de erros

### ✅ Código
- **Type hints**: Pydantic models em tudo
- **Async/await**: Performance otimizada
- **Configuração**: Centralizada em `config.py`
- **Debug endpoints**: Facilita troubleshooting

## 📊 Fluxo de Processamento

```
1. USER → Webhook → main.py
2. main.py → orchestrator.process_user_message()
3. Orchestrator → memory.add_message() [salva no Supabase]
4. Orchestrator → memory.get_recent_context() [recupera histórico]
5. Orchestrator → _analyze_intent() [LLM analisa]
6. SE needs_data:
   6a. Orchestrator → _handle_data_request()
   6b. Orchestrator → sql_agent.process_instruction()
   6c. SQL Agent → executa query no Supabase
   6d. SQL Agent → retorna JSON
   6e. Orchestrator → _convert_to_natural_language()
7. SENÃO:
   7a. Orchestrator → _handle_general_conversation()
8. Orchestrator → memory.add_message() [salva resposta]
9. Orchestrator → OrchestratorResponse
10. main.py → retorna JSON ao webhook
```

## 🔧 Próximos Passos Sugeridos

### Curto Prazo (Quick Wins)
- [ ] Logging estruturado (JSON logs)
- [ ] Métricas de performance
- [ ] Cache de queries frequentes
- [ ] Rate limiting

### Médio Prazo (Features)
- [ ] Agente de visualização (gráficos)
- [ ] Export de relatórios (PDF/Excel)
- [ ] Análises preditivas
- [ ] Sugestões proativas

### Longo Prazo (Escalabilidade)
- [ ] Testes automatizados
- [ ] CI/CD pipeline
- [ ] Monitoramento (Sentry/DataDog)
- [ ] Múltiplos LLMs (fallback)

## 🐛 Troubleshooting

### Erro: "OpenAI not configured"
- Verifique `.env` tem `OPENAI_API_KEY`
- Teste: `GET /debug/config`

### Erro: "Supabase connection failed"
- Verifique `SUPABASE_URL` e `SUPABASE_ANON_KEY`
- Rode script SQL para criar tabelas
- Sistema funciona com cache em memória (fallback)

### Memória não persiste
- Verifique se tabelas existem no Supabase
- Check RLS policies (devem permitir acesso)
- Veja logs: sistema avisa se está usando fallback

## 📝 Exemplos de Uso

### Conversa Geral
```
USER: Olá!
BOT: Olá! 😊 Sou seu assistente de análise...

USER: O que são clusters?
BOT: Clusters são segmentações de clientes...
```

### Análise de Dados
```
USER: Qual a receita do cluster premium?
BOT: 📊 O Cluster 1 (Premium) teve receita total de R$ 2.5M nos últimos 12 meses...

USER: E quantos clientes são?
BOT: 💡 São 150 clientes no cluster Premium...
```

## 📄 Licença

MIT

## 👤 Autor

Rodrigo Porto
GitHub: [@RodrigoPortoBR](https://github.com/RodrigoPortoBR)