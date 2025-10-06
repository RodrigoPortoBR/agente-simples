# 🚀 Quick Start - Sistema de Agentes V5.0

Guia rápido para começar em **menos de 15 minutos**.

## 📦 O Que Você Vai Ter

Um sistema de AI Agents modular com:
- 🤖 Orchestrator Agent conversacional
- 📊 SQL Agent para análise de dados
- 💾 Memória persistente no Supabase
- 🔄 Arquitetura escalável e extensível

## ⚡ Setup Rápido

### 1. Clone e Prepare (2 min)

```bash
# Clone o repositório
git clone https://github.com/RodrigoPortoBR/agente-simples.git
cd agente-simples

# Crie a estrutura de diretórios
mkdir -p agents services database

# Crie os __init__.py
touch agents/__init__.py services/__init__.py
```

### 2. Copie os Arquivos (3 min)

Copie estes arquivos dos artifacts:

```
✅ config.py                    → raiz
✅ models.py                    → raiz
✅ main.py                      → raiz (SUBSTITUIR)
✅ requirements.txt             → raiz (ATUALIZAR)
✅ agents/orchestrator_agent.py → agents/
✅ agents/sql_agent.py          → agents/
✅ services/memory_service.py   → services/
✅ database/supabase_schema.sql → database/
```

### 3. Configure Supabase (3 min)

```bash
# 1. Acesse https://app.supabase.com
# 2. Abra seu projeto
# 3. Vá em SQL Editor
# 4. Copie todo conteúdo de database/supabase_schema.sql
# 5. Execute (Run)
# 6. Verifique: tabelas agent_conversations e agent_messages criadas
```

### 4. Configure Variáveis (2 min)

```bash
# Crie o .env
cat > .env << EOF
OPENAI_API_KEY=sk-sua-key-aqui
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=sua-anon-key-aqui
EOF
```

### 5. Instale e Rode (3 min)

```bash
# Instale dependências
pip install -r requirements.txt

# Rode o servidor
python main.py

# Deve mostrar:
# 🚀 Iniciando servidor na porta 8000
# 📊 OpenAI: ✅
# 💾 Supabase: ✅
```

### 6. Teste (2 min)

```bash
# Terminal 2 - Health check
curl http://localhost:8000/health

# Teste conversa
curl -X POST http://localhost:8000/webhook/lovable \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá!", "sessionId": "quickstart"}'

# Teste análise de dados
curl -X POST http://localhost:8000/webhook/lovable \
  -H "Content-Type: application/json" \
  -d '{"message": "Quantos clientes temos?", "sessionId": "quickstart"}'

# Veja a memória
curl http://localhost:8000/debug/memory/quickstart
```

## ✅ Pronto!

Se todos os testes funcionaram, você está pronto! 🎉

## 📚 Próximos Passos

1. **Leia a documentação completa:** `README.md`
2. **Entenda a arquitetura:** `ARCHITECTURE.md`
3. **Faça deploy:** `IMPLEMENTATION_CHECKLIST.md` (Fase 8)
4. **Adicione features:** Veja seção "Extensibilidade" no README

## 🐛 Problemas?

### Erro: "OpenAI not configured"
→ Verifique `OPENAI_API_KEY` no `.env`

### Erro: "Table doesn't exist"
→ Execute `database/supabase_schema.sql` no Supabase

### Erro: "Module not found"
→ Certifique-se de ter criado os `__init__.py`:
```bash
touch agents/__init__.py services/__init__.py
```

### Memória não persiste
→ Verifique se as tabelas foram criadas no Supabase

## 📞 Suporte

- **Documentação:** Veja arquivos `*.md` na raiz
- **Checklist:** `IMPLEMENTATION_CHECKLIST.md` para guia detalhado
- **Migração:** `MIGRATION_GUIDE.md` se está migrando da v4

## 🎯 Estrutura do Projeto

```
agente-simples/
├── config.py              # Configurações
├── models.py              # Modelos de dados
├── main.py                # API FastAPI
├── requirements.txt       # Dependências
├── .env                   # Credenciais (não commitar!)
│
├── agents/                # Agentes especializados
│   ├── orchestrator_agent.py
│   └── sql_agent.py
│
├── services/              # Serviços (memória, etc)
│   └── memory_service.py
│
└── database/              # Scripts SQL
    └── supabase_schema.sql
```

## 🔗 Links Úteis

- OpenAI API Keys: https://platform.openai.com/api-keys
- Supabase Dashboard: https://app.supabase.com
- FastAPI Docs: http://localhost:8000/docs (após iniciar)

---

**Tempo estimado:** 15 minutos  
**Dificuldade:** Fácil  
**Pré-requisitos:** Python 3.8+, Conta OpenAI, Conta Supabase