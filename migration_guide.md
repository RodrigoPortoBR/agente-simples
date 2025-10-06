# 🔄 Guia de Migração - V4 para V5

Este guia ajuda você a migrar da versão monolítica para a versão refatorada modular.

## 📋 Checklist de Migração

### Passo 1: Backup
- [ ] Fazer backup do código atual
- [ ] Exportar dados importantes (se houver)
- [ ] Anotar variáveis de ambiente atuais

### Passo 2: Preparar Supabase
- [ ] Acessar projeto Supabase
- [ ] Executar `database/supabase_schema.sql`
- [ ] Verificar tabelas criadas: `agent_conversations`, `agent_messages`
- [ ] Testar RLS policies

### Passo 3: Estrutura de Arquivos

**ANTIGA (V4):**
```
agente-simples/
├── main.py          # Tudo junto (2000+ linhas)
├── requirements.txt
└── Procfile
```

**NOVA (V5):**
```
agente-simples/
├── config.py
├── models.py
├── main.py
├── requirements.txt
├── Procfile
├── agents/
│   ├── __init__.py
│   ├── orchestrator_agent.py
│   └── sql_agent.py
├── services/
│   ├── __init__.py
│   └── memory_service.py
└── database/
    └── supabase_schema.sql
```

### Passo 4: Criar Nova Estrutura

```bash
# Criar diretórios
mkdir -p agents services database

# Criar arquivos __init__.py
touch agents/__init__.py
touch services/__init__.py
```

### Passo 5: Copiar Arquivos Refatorados

1. **config.py** - Copiar do artifact "config.py"
2. **models.py** - Copiar do artifact "models.py"
3. **services/memory_service.py** - Copiar do artifact
4. **agents/sql_agent.py** - Copiar do artifact
5. **agents/orchestrator_agent.py** - Copiar do artifact
6. **main.py** - SUBSTITUIR pelo novo
7. **requirements.txt** - ATUALIZAR
8. **database/supabase_schema.sql** - Adicionar

### Passo 6: Atualizar Dependências

```bash
pip install -r requirements.txt --upgrade
```

### Passo 7: Configurar Variáveis de Ambiente

Adicione ao `.env` (se não tiver):

```env
# Já existentes
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...

# Novas (opcionais - têm defaults)
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7
MAX_HISTORY_MESSAGES=50
CONTEXT_WINDOW_MESSAGES=10
```

### Passo 8: Testar Localmente

```bash
# Rodar servidor
python main.py

# Em outro terminal, testar
curl http://localhost:8000/health

# Testar conversa
curl -X POST http://localhost:8000/webhook/lovable \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá!", "sessionId": "test001"}'
```

### Passo 9: Verificar Funcionalidades

- [ ] Conversa geral funciona
- [ ] Análise de dados funciona
- [ ] Memória persiste no Supabase
- [ ] Debug endpoints funcionam
- [ ] Logs aparecem corretamente

### Passo 10: Deploy

```bash
# Git
git add .
git commit -m "refactor: migração para arquitetura modular v5"
git push origin main

# Se usa Heroku/Render, fazer redeploy
```

## 🔍 Comparação de Mudanças

### Memória

**ANTES:**
```python
# Memória em RAM (perde ao reiniciar)
self.conversations = {}
```

**DEPOIS:**
```python
# Memória persistente no Supabase
memory = MemoryService()
await memory.add_message(session_id, role, content)
history = await memory.get_conversation_history(session_id)
```

### SQL Agent

**ANTES:**
```python
# SQL Agent tinha lógica de negócio
cluster_patterns = {
    "1": ["cluster 1", "premium", "top"],
    ...
}
# Interpretava linguagem natural
```

**DEPOIS:**
```python
# SQL Agent é "burro" - só executa
instruction = AgentInstruction(
    agent_type=AgentType.SQL,
    parameters={
        "query_type": "aggregate",
        "table": "clientes",
        "filters": {"cluster_id": "1"},
        "aggregation": {"receita_12m": "sum"}
    }
)
```

### Orchestrator

**ANTES:**
```python
# Tudo junto no mesmo arquivo
class OrchestratorAgent:
    def __init__(self):
        self.sql_agent = SQLAgent()
        self.conversations = {}  # memória local
```

**DEPOIS:**
```python
# Separado e com serviços
class OrchestratorAgent:
    def __init__(self):
        self.memory = MemoryService()  # serviço dedicado
        self.sql_agent = SQLAgent()    # agente especialista
```

## ⚠️ Breaking Changes

### 1. Estrutura de Resposta SQL Agent

**ANTES:**
```json
{
  "success": true,
  "data": [...],
  "query_info": {
    "method": "aggregate_manual"
  }
}
```

**DEPOIS:**
```json
{
  "success": true,
  "agent_type": "sql_agent",
  "data": {
    "results": [...]
  },
  "metadata": {
    "query_type": "aggregate",
    "execution_time": 0.15
  }
}
```

### 2. Instrução para SQL Agent

**ANTES:**
```python
sql_instruction = AgentInstruction(
    agent_type="sql_agent",
    task_description="Descrição em linguagem natural",
    user_question="Pergunta do usuário",
    context={}
)
```

**DEPOIS:**
```python
sql_instruction = AgentInstruction(
    agent_type=AgentType.SQL,
    task_description="Descrição técnica",
    parameters={  # NOVO: parâmetros estruturados
        "query_type": "aggregate",
        "table": "clientes",
        "filters": {...},
        "aggregation": {...}
    },
    context={}
)
```

## 🐛 Problemas Comuns

### Erro: "ModuleNotFoundError: No module named 'agents'"

**Solução:**
```bash
# Criar __init__.py nos diretórios
touch agents/__init__.py
touch services/__init__.py
```

### Erro: "Table 'agent_messages' doesn't exist"

**Solução:**
```sql
-- Executar no SQL Editor do Supabase
-- Copiar e colar todo conteúdo de database/supabase_schema.sql
```

### Memória não persiste

**Causa:** Tabelas não existem ou RLS policies bloqueando

**Solução:**
```sql
-- Verificar se tabelas existem
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename LIKE 'agent_%';

-- Desabilitar RLS temporariamente para testar
ALTER TABLE agent_messages DISABLE ROW LEVEL SECURITY;
```

### Erro: "KeyError: 'query_type'"

**Causa:** Orchestrator não está extraindo parâmetros corretamente

**Solução:** Verificar análise de intenção no Orchestrator. Deve extrair `query_type` no `extracted_parameters`.

## ✅ Validação Pós-Migração

Execute estes testes:

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Conversa simples
curl -X POST http://localhost:8000/webhook/lovable \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá", "sessionId": "test001"}'

# 3. Análise de dados
curl -X POST http://localhost:8000/webhook/lovable \
  -H "Content-Type: application/json" \
  -d '{"message": "Quantos clientes temos?", "sessionId": "test001"}'

# 4. Ver memória
curl http://localhost:8000/debug/memory/test001

# 5. Testar SQL Agent
curl -X POST http://localhost:8000/debug/test-sql
```

## 📊 Benefícios da Migração

| Aspecto | V4 (Antiga) | V5 (Nova) | Melhoria |
|---------|-------------|-----------|----------|
| **Arquitetura** | Monolito | Modular | ✅ Manutenibilidade |
| **Memória** | RAM | Supabase | ✅ Persistência |
| **SQL Agent** | Lógica negócio | Executor puro | ✅ Separação |
| **Testabilidade** | Difícil | Fácil | ✅ Módulos isolados |
| **Escalabilidade** | Limitada | Preparada | ✅ Novas features |
| **Código** | 2000 linhas | ~300/módulo | ✅ Legibilidade |

## 🎯 Próximos Passos Após Migração

1. **Monitorar** logs por 24-48h
2. **Coletar** feedback de usuários
3. **Ajustar** prompts se necessário
4. **Adicionar** novos agentes conforme demanda
5. **Implementar** testes automatizados

## 📞 Suporte

Se encontrar problemas:
1. Verificar logs do servidor
2. Testar endpoints de debug
3. Consultar este guia
4. Verificar issues no GitHub