# ✅ Checklist de Implementação - V5.0

Use este checklist para garantir que tudo está funcionando corretamente.

## 📋 Fase 1: Preparação (15 min)

### 1.1 Backup
- [ ] Fazer backup do código atual
- [ ] Fazer backup do `.env`
- [ ] Documentar endpoints em uso
- [ ] Listar integrações existentes

### 1.2 Ambiente
- [ ] Python 3.8+ instalado
- [ ] Pip atualizado: `pip install --upgrade pip`
- [ ] Git configurado
- [ ] Editor de código preparado (VSCode, PyCharm, etc)

### 1.3 Credenciais
- [ ] OpenAI API Key disponível
- [ ] Supabase Project criado
- [ ] Supabase URL anotada
- [ ] Supabase Anon Key anotada

## 📋 Fase 2: Estrutura de Arquivos (10 min)

### 2.1 Criar Diretórios
```bash
mkdir -p agents services database
```

- [ ] Diretório `agents/` criado
- [ ] Diretório `services/` criado
- [ ] Diretório `database/` criado

### 2.2 Criar Arquivos Base
```bash
touch agents/__init__.py
touch services/__init__.py
touch .env
touch .gitignore
```

- [ ] `agents/__init__.py` criado
- [ ] `services/__init__.py` criado
- [ ] `.env` criado
- [ ] `.gitignore` criado (incluir `.env`, `__pycache__`, `.venv`)

### 2.3 Copiar Arquivos Refatorados

- [ ] `config.py` - Configurações
- [ ] `models.py` - Modelos de dados
- [ ] `agents/orchestrator_agent.py` - Orquestrador
- [ ] `agents/sql_agent.py` - SQL Agent
- [ ] `services/memory_service.py` - Serviço de memória
- [ ] `main.py` - API principal (SUBSTITUIR)
- [ ] `requirements.txt` - Dependências (ATUALIZAR)
- [ ] `database/supabase_schema.sql` - Schema do banco
- [ ] `.env.example` - Template de configuração
- [ ] `README.md` - Documentação
- [ ] `Procfile` - Deploy (verificar se existe)

## 📋 Fase 3: Configuração do Supabase (15 min)

### 3.1 Criar Tabelas

- [ ] Acessar https://app.supabase.com
- [ ] Abrir seu projeto
- [ ] Ir em **SQL Editor**
- [ ] Criar nova query
- [ ] Copiar todo conteúdo de `database/supabase_schema.sql`
- [ ] Executar (Run)
- [ ] Verificar mensagem de sucesso

### 3.2 Verificar Tabelas Criadas

Execute no SQL Editor:
```sql
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename LIKE 'agent_%';
```

- [ ] Tabela `agent_conversations` existe
- [ ] Tabela `agent_messages` existe

### 3.3 Verificar Índices

Execute no SQL Editor:
```sql
SELECT indexname FROM pg_indexes 
WHERE tablename LIKE 'agent_%';
```

- [ ] Índice `idx_messages_session_id` existe
- [ ] Índice `idx_messages_timestamp` existe
- [ ] Índice `idx_messages_session_timestamp` existe

### 3.4 Testar Inserção Manual (Opcional)

```sql
INSERT INTO agent_conversations (session_id) 
VALUES ('test_setup');

INSERT INTO agent_messages (session_id, role, content) 
VALUES ('test_setup', 'user', 'Teste de configuração');

SELECT * FROM agent_messages WHERE session_id = 'test_setup';
```

- [ ] Insert funcionou
- [ ] Select retornou dados
- [ ] Timestamp foi preenchido automaticamente

## 📋 Fase 4: Configuração do Ambiente (10 min)

### 4.1 Copiar Template

```bash
cp .env.example .env
```

- [ ] Arquivo `.env` criado

### 4.2 Preencher Credenciais

Editar `.env`:

```env
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=eyJ...
```

- [ ] `OPENAI_API_KEY` preenchida
- [ ] `SUPABASE_URL` preenchida
- [ ] `SUPABASE_ANON_KEY` preenchida

### 4.3 Verificar .gitignore

Adicionar ao `.gitignore`:
```
.env
__pycache__/
*.pyc
.venv/
venv/
```

- [ ] `.env` está no .gitignore
- [ ] `.gitignore` commitado

## 📋 Fase 5: Instalação de Dependências (5 min)

### 5.1 Criar Ambiente Virtual (Recomendado)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

- [ ] Virtual environment criado
- [ ] Virtual environment ativado

### 5.2 Instalar Dependências

```bash
pip install -r requirements.txt
```

- [ ] Todas dependências instaladas sem erros
- [ ] FastAPI instalado
- [ ] OpenAI instalado
- [ ] Httpx instalado
- [ ] Pydantic instalado

### 5.3 Verificar Instalação

```bash
python -c "import fastapi; import openai; import httpx; print('OK')"
```

- [ ] Comando retornou "OK"

## 📋 Fase 6: Testes Locais (20 min)

### 6.1 Iniciar Servidor

```bash
python main.py
```

- [ ] Servidor iniciou sem erros
- [ ] Porta 8000 está ouvindo
- [ ] Logs mostram "OpenAI: ✅"
- [ ] Logs mostram "Supabase: ✅"

### 6.2 Testar Endpoints de Sistema

**Terminal 2:**

```bash
# Health check
curl http://localhost:8000/health
```

- [ ] Retornou JSON com status "healthy"
- [ ] `openai: true`
- [ ] `supabase: true`

```bash
# Info do sistema
curl http://localhost:8000/
```

- [ ] Retornou info da aplicação
- [ ] Versão "5.0.0"
- [ ] Lista de melhorias presente

```bash
# Debug config
curl http://localhost:8000/debug/config
```

- [ ] `openai_configured: true`
- [ ] `supabase_configured: true`
- [ ] Configurações corretas

### 6.3 Testar Conversa Geral

```bash
curl -X POST http://localhost:8000/webhook/lovable \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá!", "sessionId": "test_local"}'
```

- [ ] Retornou resposta amigável
- [ ] `success: true`
- [ ] `agents_used` inclui "orchestrator"
- [ ] `processing_steps` tem 4+ passos

### 6.4 Testar Análise de Dados

```bash
curl -X POST http://localhost:8000/webhook/lovable \
  -H "Content-Type: application/json" \
  -d '{"message": "Quantos clientes temos?", "sessionId": "test_local"}'
```

- [ ] Retornou resposta com dados
- [ ] `success: true`
- [ ] `agents_used` inclui "sql_agent"
- [ ] Resposta em linguagem natural

### 6.5 Verificar Memória

```bash
# Ver histórico
curl http://localhost:8000/debug/memory/test_local
```

- [ ] Retornou histórico com 2+ mensagens
- [ ] Mensagens do usuário presentes
- [ ] Respostas do assistente presentes
- [ ] Timestamps corretos

**Verificar no Supabase:**
- [ ] Acessar Supabase → Table Editor
- [ ] Tabela `agent_messages` tem registros
- [ ] Session_id "test_local" presente
- [ ] Roles "user" e "assistant" corretos

### 6.6 Testar SQL Agent Direto

```bash
curl -X POST http://localhost:8000/debug/test-sql
```

- [ ] `success: true`
- [ ] Dados retornados
- [ ] Metadata presente
- [ ] execution_time registrado

### 6.7 Testar Limpeza de Memória

```bash
# Limpar sessão de teste
curl -X DELETE http://localhost:8000/debug/memory/test_local
```

- [ ] `success: true`
- [ ] Mensagem de confirmação

**Verificar no Supabase:**
- [ ] Registros da sessão "test_local" foram deletados

## 📋 Fase 7: Testes de Integração (15 min)

### 7.1 Cenário Completo

```bash
# Sessão nova
SESSION_ID="integration_test_$(date +%s)"

# 1. Saudação
curl -X POST http://localhost:8000/webhook/lovable \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Olá\", \"sessionId\": \"$SESSION_ID\"}"

# 2. Pergunta sobre dados
curl -X POST http://localhost:8000/webhook/lovable \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Quantos clientes premium temos?\", \"sessionId\": \"$SESSION_ID\"}"

# 3. Follow-up
curl -X POST http://localhost:8000/webhook/lovable \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"E qual a receita deles?\", \"sessionId\": \"$SESSION_ID\"}"

# 4. Ver histórico
curl "http://localhost:8000/debug/memory/$SESSION_ID"
```

- [ ] Todas requisições retornaram sucesso
- [ ] Contexto foi mantido entre mensagens
- [ ] Follow-up entendeu "deles" = cluster premium
- [ ] Histórico tem 6 mensagens (3 user + 3 assistant)

### 7.2 Teste de Erro

```bash
# Sem OpenAI key (temporário)
# Comentar OPENAI_API_KEY no .env e reiniciar

curl -X POST http://localhost:8000/webhook/lovable \
  -H "Content-Type: application/json" \
  -d '{"message": "teste", "sessionId": "error_test"}'
```

- [ ] Retornou erro gracioso
- [ ] `success: false`
- [ ] Mensagem de erro clara
- [ ] Não crashou o servidor

**Restaurar:**
- [ ] Descomentar OPENAI_API_KEY
- [ ] Reiniciar servidor

## 📋 Fase 8: Deploy (30 min)

### 8.1 Preparar para Deploy

- [ ] Código commitado no Git
- [ ] `.env` NÃO está no repositório
- [ ] `Procfile` existe e está correto
- [ ] `requirements.txt` atualizado

### 8.2 Deploy no Render/Heroku

**Render:**
1. [ ] Acessar https://render.com
2. [ ] Criar novo Web Service
3. [ ] Conectar repositório GitHub
4. [ ] Configurar:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. [ ] Adicionar variáveis de ambiente:
   - `OPENAI_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
6. [ ] Deploy

**Heroku:**
1. [ ] Instalar Heroku CLI
2. [ ] `heroku login`
3. [ ] `heroku create nome-do-app`
4. [ ] `heroku config:set OPENAI_API_KEY=...`
5. [ ] `heroku config:set SUPABASE_URL=...`
6. [ ] `heroku config:set SUPABASE_ANON_KEY=...`
7. [ ] `git push heroku main`

### 8.3 Testar Produção

```bash
PROD_URL="https://seu-app.onrender.com"  # ou .herokuapp.com

# Health check
curl $PROD_URL/health

# Teste básico
curl -X POST $PROD_URL/webhook/lovable \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá", "sessionId": "prod_test"}'
```

- [ ] Health check retornou OK
- [ ] Teste básico funcionou
- [ ] Logs de produção acessíveis
- [ ] Sem erros 500

### 8.4 Monitoramento

- [ ] Configurar alertas de erro
- [ ] Verificar logs periodicamente
- [ ] Monitorar uso de recursos
- [ ] Configurar backup do Supabase

## 📋 Fase 9: Validação Final (10 min)

### 9.1 Funcionalidades Core

- [ ] ✅ Conversa geral funciona
- [ ] ✅ Análise de dados funciona
- [ ] ✅ Memória persiste no Supabase
- [ ] ✅ Context window respeitado
- [ ] ✅ Follow-up entende contexto
- [ ] ✅ Erros tratados graciosamente
- [ ] ✅ Logs úteis e claros

### 9.2 Performance

- [ ] Resposta < 3s em 90% dos casos
- [ ] Memória não vaza (servidor estável)
- [ ] Queries SQL eficientes
- [ ] Cache funciona (se implementado)

### 9.3 Arquitetura

- [ ] Orchestrator é único ponto de entrada
- [ ] SQL Agent não interpreta linguagem natural
- [ ] Memória persiste entre reinícios
- [ ] Código modular e organizado
- [ ] Type hints em todos modelos

### 9.4 Documentação

- [ ] README.md atualizado
- [ ] ARCHITECTURE.md criado
- [ ] MIGRATION_GUIDE.md presente
- [ ] Comentários no código
- [ ] Endpoints documentados

## 📋 Fase 10: Próximos Passos (Opcional)

### 10.1 Melhorias Imediatas

- [ ] Adicionar logging estruturado (JSON)
- [ ] Implementar rate limiting
- [ ] Adicionar métricas (Prometheus/DataDog)
- [ ] Cache de queries frequentes
- [ ] Retry logic com exponential backoff

### 10.2 Features Novas

- [ ] Agente de visualização (gráficos)
- [ ] Export de relatórios (PDF/Excel)
- [ ] Análises preditivas
- [ ] Sugestões proativas
- [ ] Integração com Slack/Teams

### 10.3 Testes

- [ ] Testes unitários (pytest)
- [ ] Testes de integração
- [ ] Testes de carga (locust)
- [ ] CI/CD pipeline (GitHub Actions)

### 10.4 Observabilidade

- [ ] Sentry para error tracking
- [ ] DataDog/New Relic para APM
- [ ] Grafana para métricas
- [ ] Alerts customizados

## 🚨 Troubleshooting Comum

### Erro: "ModuleNotFoundError: No module named 'agents'"

**Solução:**
```bash
# Certifique-se de que __init__.py existe
touch agents/__init__.py
touch services/__init__.py

# E que você está rodando do diretório raiz
pwd  # deve mostrar /path/to/agente-simples
```

### Erro: "Table 'agent_messages' doesn't exist"

**Solução:**
1. Verifique se executou `supabase_schema.sql`
2. No Supabase SQL Editor:
```sql
SELECT tablename FROM pg_tables 
WHERE tablename LIKE 'agent_%';
```
3. Se vazio, execute o schema novamente

### Erro: "OpenAI API key not configured"

**Solução:**
```bash
# Verifique .env
cat .env | grep OPENAI_API_KEY

# Deve retornar: OPENAI_API_KEY=sk-...
# Se não, adicione a key

# Reinicie o servidor
```

### Memória não persiste

**Causas possíveis:**
1. Tabelas não existem → Execute schema SQL
2. RLS bloqueando → Verifique policies no Supabase
3. Credenciais erradas → Verifique SUPABASE_URL e KEY

**Debug:**
```bash
# Ver logs do servidor (deve mostrar avisos)
# Se vir "⚠️ Erro ao salvar mensagem", é problema de Supabase

# Testar conexão manualmente:
curl -X POST "$SUPABASE_URL/rest/v1/agent_messages" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "role": "user",
    "content": "teste",
    "timestamp": "2025-10-05T10:00:00"
  }'
```

### Respostas lentas

**Soluções:**
1. Verificar timeout do OpenAI (aumentar se necessário)
2. Otimizar queries SQL (adicionar índices)
3. Implementar cache de respostas
4. Reduzir context window se muito grande

### SQL Agent retorna dados vazios

**Debug:**
```bash
# Usar endpoint de debug
curl -X POST http://localhost:8000/debug/test-sql

# Verificar URL da query nos logs
# Testar URL diretamente no browser ou Postman
```

## 📊 Métricas de Sucesso

Após implementação, você deve ter:

| Métrica | Target | Status |
|---------|--------|--------|
| Uptime | > 99% | [ ] |
| Tempo de resposta | < 3s (p90) | [ ] |
| Taxa de erro | < 1% | [ ] |
| Memória persistente | 100% | [ ] |
| Cobertura de testes | > 80% | [ ] |
| Satisfação do usuário | > 4.5/5 | [ ] |

## ✅ Checklist Final

Antes de considerar completo:

- [ ] ✅ Todas as fases acima completas
- [ ] ✅ Testes passando em local
- [ ] ✅ Deploy em produção funcionando
- [ ] ✅ Memória persistindo corretamente
- [ ] ✅ Documentação atualizada
- [ ] ✅ Equipe treinada (se aplicável)
- [ ] ✅ Monitoramento configurado
- [ ] ✅ Backup strategy definida
- [ ] ✅ Rollback plan documentado
- [ ] ✅ Stakeholders informados

## 🎉 Parabéns!

Se chegou até aqui, seu sistema está refatorado e em produção! 

**Próximos passos recomendados:**
1. Monitorar por 7 dias
2. Coletar feedback dos usuários
3. Ajustar prompts conforme necessário
4. Planejar próximas features
5. Implementar testes automatizados

---

**Data de conclusão:** ___/___/_____  
**Responsável:** _________________  
**Versão implantada:** 5.0.0  
**Ambiente:** [ ] Local [ ] Staging [ ] Production