# Análise do Funcionamento do Agente Orquestrador (Versão GitHub)

## 📋 Resumo da Atualização

Os arquivos foram atualizados com o código do GitHub [RodrigoPortoBR/agente-simples](https://github.com/RodrigoPortoBR/agente-simples). A versão atual é **completamente diferente** da versão anterior, com foco em **dados de negócio/e-commerce**.

---

## 🔄 Principais Mudanças

### 1. **Arquitetura Simplificada**
- **Antes**: Usava LangChain com múltiplas camadas
- **Agora**: Usa OpenAI diretamente, arquitetura mais simples e focada

### 2. **Foco em Dados de Negócio**
- **Antes**: Sistema genérico para qualquer tipo de consulta
- **Agora**: Especializado em análise de dados de e-commerce (clientes, receita, margem, clusters)

### 3. **Banco de Dados**
- **Antes**: SQLAlchemy (qualquer banco SQL)
- **Agora**: Supabase REST API (httpx) - específico para dados de negócio

---

## 🎯 Como o Orquestrador Funciona Agora

### **Fluxo Principal**

```
Mensagem do Usuário
    ↓
1. Salvar mensagem na memória
    ↓
2. Recuperar contexto (últimas 6 mensagens)
    ↓
3. Analisar Intenção (LLM - OpenAI)
    ↓
4. Decisão de Roteamento
    ├─ DATA_ANALYSIS → Delegar para SQL Agent
    └─ GENERAL_CHAT → Responder diretamente
    ↓
5. Gerar Resposta Final
    ↓
6. Salvar resposta na memória
```

---

## 🔍 Análise de Intenção (LLM)

### **Método**: `_analyze_business_intent()`

O orquestrador usa uma LLM (OpenAI) para analisar a intenção do usuário. A análise retorna:

1. **Tipo de Intenção**:
   - `data_analysis`: Precisa consultar banco de dados
   - `general_chat`: Conversa geral (sem banco)

2. **Parâmetros Extraídos**:
   - `query_type`: "aggregate", "count", "select", "filter"
   - `table`: "clientes", "clusters", "pedidos", "monthly_series"
   - `filters`: Filtros específicos (ex: `{"cluster": 1}`)
   - `fields`: Campos a retornar
   - `aggregation`: Tipo de agregação (sum, avg, count, etc)
   - `order_by`: Ordenação
   - `limit`: Limite de resultados

3. **Decisão de Agente**:
   - `requires_agent`: `AgentType.SQL` ou `None`

### **Exemplos de Análise**

✅ **PRECISA CONSULTAR BANCO**:
- "Qual a receita do cluster premium?"
- "Quantos clientes temos?"
- "Top 10 clientes por margem"
- "Receita do último mês"

❌ **NÃO PRECISA BANCO**:
- "Olá" / "Oi"
- "O que você pode fazer?"
- "Explica o que é cluster"
- "Como funciona a margem?"

---

## 🎯 Roteamento de Mensagens

### **Cenário 1: DATA_ANALYSIS (Delegação para SQL Agent)**

```python
if intent.needs_data_analysis and intent.requires_agent == AgentType.SQL:
    # 1. Criar instrução estruturada
    sql_instruction = AgentInstruction(
        agent_type=AgentType.SQL,
        task_description=f"Consultar dados: {user_message}",
        parameters=intent.extracted_parameters,
        context={...},
        session_id=session_id
    )
    
    # 2. Delegar para SQL Agent
    sql_response = await self.sql_agent.process_instruction(sql_instruction)
    
    # 3. Converter dados JSON em linguagem natural
    response_text = await self._convert_business_data_to_natural(
        user_question=user_message,
        data=sql_response.data,
        metadata=sql_response.metadata
    )
```

**O SQL Agent**:
- Recebe instruções estruturadas (não linguagem natural)
- Executa queries na API REST do Supabase
- Retorna dados JSON estruturados
- **NÃO** interpreta linguagem natural (isso é feito pelo orquestrador)

**Geração de Resposta Natural**:
- Usa LLM para converter dados JSON em análise profunda
- Inclui insights estratégicos, planos de ação e alertas
- Foco em valor de negócio, não apenas números

### **Cenário 2: GENERAL_CHAT (Resposta Direta)**

```python
else:
    # Conversa geral - responder diretamente com LLM
    response_text = await self._handle_business_chat(
        user_message=user_message,
        context_messages=context_messages
    )
```

**Resposta Direta**:
- Usa LLM com contexto da conversa
- Não consulta banco de dados
- Foca em explicações conceituais e orientações

---

## 📊 Estrutura de Dados

### **Tabelas Disponíveis** (Supabase)

1. **clientes**: Dados de clientes (receita, margem, cluster, etc)
2. **clusters**: Informações dos clusters (gm_total, clientes, tendência)
3. **monthly_series**: Séries temporais mensais (receita, margem)
4. **pedidos**: Dados de pedidos individuais

### **Clusters**
- 1 = Premium (top receita)
- 2 = Alto Valor
- 3 = Médio
- 4 = Baixo
- 5 = Novos

---

## 🔑 Diferenças-Chave da Versão Anterior

### **1. Análise de Intenção**
- **Antes**: Usava LangChain com parser estruturado
- **Agora**: Prompt direto para OpenAI com extração de JSON manual

### **2. SQL Agent**
- **Antes**: Gera SQL via LLM e executa com SQLAlchemy
- **Agora**: Recebe instruções estruturadas e usa Supabase REST API

### **3. Conversão de Resposta**
- **Antes**: Conversão simples de dados em texto
- **Agora**: Análise profunda com insights estratégicos, planos de ação e alertas

### **4. Memória**
- **Antes**: Usava Redis ou sessão
- **Agora**: MemoryService simples (em memória, pode ser expandido)

---

## ✅ Resposta à Pergunta Original

### **O orquestrador está filtrando o tipo de mensagem?**

**SIM!** O orquestrador usa uma LLM (OpenAI) no método `_analyze_business_intent()` para:
1. Identificar se a mensagem precisa consultar dados (DATA_ANALYSIS)
2. Ou se é uma conversa geral (GENERAL_CHAT)
3. Extrair parâmetros estruturados para a consulta

### **O orquestrador está entendendo quando responder direto?**

**SIM!** Quando a intenção é `GENERAL_CHAT`, o orquestrador:
- Responde diretamente usando LLM
- Não consulta o SQL Agent
- Usa o método `_handle_business_chat()`

### **O orquestrador está passando para o SQL Agent quando necessário?**

**SIM!** Quando a intenção é `DATA_ANALYSIS`:
1. Cria uma `AgentInstruction` estruturada
2. Delega para `SQLAgent.process_instruction()`
3. SQL Agent executa query no Supabase
4. Orquestrador recebe dados JSON
5. Converte em linguagem natural com insights profundos

---

## 🎯 Conclusão

O sistema atualizado está **funcionando corretamente**:

1. ✅ **Filtra mensagens** usando LLM para análise de intenção
2. ✅ **Responde diretamente** para conversas gerais
3. ✅ **Delega para SQL Agent** quando precisa consultar dados
4. ✅ **Converte resultados** em respostas naturais com insights de negócio

A arquitetura está mais simples, focada e eficiente para o caso de uso específico (análise de dados de e-commerce).

