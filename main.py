from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
import uvicorn
import json
import asyncpg
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from enum import Enum

app = FastAPI(title="Sistema de Agentes Orquestradores")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums
class IntentType(str, Enum):
    GENERAL_CHAT = "general_chat"
    DATA_ANALYSIS = "data_analysis"
    HELP = "help"

# Modelos de dados
class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str

class WebhookPayload(BaseModel):
    session_id: str
    user_message: str
    conversation_history: Optional[List[ConversationMessage]] = []

class SQLRequest(BaseModel):
    user_question: str
    session_id: str
    context: Optional[Dict[str, Any]] = {}

class SQLResponse(BaseModel):
    success: bool
    sql_query: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = 0
    error: Optional[str] = None
    execution_time: Optional[float] = None

class OrchestratorResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    success: bool
    agent_used: str
    sql_executed: Optional[bool] = False

# Armazenamento
conversations = {}

# ================================
# AGENTE SQL ESPECIALISTA
# ================================
# ================================
# AGENTE SQL ESPECIALISTA
# ================================
class SQLAgent:
    """Agente especialista em consultas SQL - retorna apenas JSON"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.db_url = os.getenv("SUPABASE_DATABASE_URL")
    
    async def get_database_schema(self) -> str:
        """Obtém esquema do banco para contexto"""
        try:
            conn = await asyncpg.connect(self.db_url)
            
            schema_query = """
            SELECT 
                table_name,
                column_name,
                data_type
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            ORDER BY table_name, ordinal_position;
            """
            
            rows = await conn.fetch(schema_query)
            await conn.close()
            
            schema_info = {}
            for row in rows:
                table = row['table_name']
                if table not in schema_info:
                    schema_info[table] = []
                schema_info[table].append(f"{row['column_name']} ({row['data_type']})")
            
            schema_text = "TABELAS DISPONÍVEIS:\n"
            for table, columns in schema_info.items():
                schema_text += f"\n{table}: {', '.join(columns)}"
            
            return schema_text
            
        except Exception as e:
            return f"Erro ao obter schema: {str(e)}"
    
    def validate_sql_security(self, sql_query: str):
        """Valida segurança da consulta"""
        sql_upper = sql_query.upper().strip()
        
        if not sql_upper.startswith('SELECT'):
            return False, "Apenas consultas SELECT são permitidas"
        
        forbidden = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE']
        for word in forbidden:
            if word in sql_upper:
                return False, f"Operação {word} não permitida"
        
        return True, "Consulta aprovada"
    
    async def generate_sql(self, user_question: str) -> str:
        """Gera consulta SQL baseada na pergunta"""
        try:
            schema = await self.get_database_schema()
            
            prompt = f"""
Você é um especialista em SQL PostgreSQL. Gere uma consulta SQL segura baseada na pergunta.

{schema}

REGRAS:
- Use apenas SELECT
- Use nomes exatos das tabelas/colunas do schema
- Adicione LIMIT 100 para performance
- Não use ponto e vírgula
- Sintaxe PostgreSQL

Pergunta: "{user_question}"

Responda APENAS com a consulta SQL:
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
            
            sql_query = response.choices[0].message.content.strip()
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            if sql_query.endswith(';'):
                sql_query = sql_query[:-1]
            
            return sql_query
            
        except Exception as e:
            return f"SELECT 'Erro na geração: {str(e)}' as erro"
    
    async def execute_sql(self, sql_query: str):
        """Executa SQL e retorna dados estruturados"""
        try:
            start_time = datetime.now()
            
            conn = await asyncpg.connect(self.db_url)
            rows = await conn.fetch(sql_query)
            await conn.close()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Converter para JSON serializável
            results = []
            for row in rows:
                row_dict = {}
                for key, value in row.items():
                    if hasattr(value, 'isoformat'):
                        row_dict[key] = value.isoformat()
                    elif isinstance(value, (int, float, str, bool)) or value is None:
                        row_dict[key] = value
                    else:
                        row_dict[key] = str(value)
                results.append(row_dict)
            
            return {
                "success": True,
                "data": results,
                "row_count": len(results),
                "execution_time": execution_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "row_count": 0
            }
    
    async def process_data_request(self, request: SQLRequest) -> SQLResponse:
        """Método principal do agente SQL - retorna JSON estruturado"""
        try:
            # 1. Gerar SQL
            sql_query = await self.generate_sql(request.user_question)
            
            # 2. Validar segurança
            is_safe, reason = self.validate_sql_security(sql_query)
            if not is_safe:
                return SQLResponse(
                    success=False,
                    error=f"Consulta rejeitada: {reason}",
                    sql_query=sql_query
                )
            
            # 3. Executar
            execution_result = await self.execute_sql(sql_query)
            
            # 4. Retornar resposta estruturada
            return SQLResponse(
                success=execution_result["success"],
                sql_query=sql_query,
                data=execution_result["data"],
                row_count=execution_result["row_count"],
                error=execution_result.get("error"),
                execution_time=execution_result.get("execution_time")
            )
            
        except Exception as e:
            return SQLResponse(
                success=False,
                error=str(e)
            )

# ================================
# AGENTE ORQUESTRADOR
# ================================
class OrchestratorAgent:
    """Agente orquestrador - interface com usuário em linguagem natural"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.sql_agent = SQLAgent()
    
    def analyze_user_intent(self, user_message: str) -> IntentType:
        """Analisa se usuário quer dados ou chat geral"""
        try:
            prompt = f"""
Analise a mensagem e determine a intenção:

INTENÇÕES:
- general_chat: Conversa geral, cumprimentos, perguntas não relacionadas a dados
- data_analysis: Perguntas sobre dados, relatórios, consultas, estatísticas
- help: Pedidos de ajuda

Mensagem: "{user_message}"

Palavras-chave para data_analysis: quantos, quanto, mostre, liste, dados, relatório, total, média, últimos, contar, somar, análise

Responda apenas: general_chat, data_analysis ou help
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0.1
            )
            
            intent_text = response.choices[0].message.content.strip().lower()
            
            if "data_analysis" in intent_text:
                return IntentType.DATA_ANALYSIS
            elif "help" in intent_text:
                return IntentType.HELP
            else:
                return IntentType.GENERAL_CHAT
                
        except Exception:
            return IntentType.GENERAL_CHAT
    
    async def handle_data_request(self, user_message: str, session_id: str) -> str:
        """Delega para agente SQL e converte resposta para linguagem natural"""
        try:
            # 1. Criar requisição para agente SQL
            sql_request = SQLRequest(
                user_question=user_message,
                session_id=session_id
            )
            
            # 2. Chamar agente SQL especialista
            sql_response = await self.sql_agent.process_data_request(sql_request)
            
            # 3. Converter resposta JSON para linguagem natural
            return self.convert_sql_response_to_natural_language(
                user_message, sql_response
            )
            
        except Exception as e:
            return f"Desculpe, ocorreu um erro ao processar sua solicitação de dados: {str(e)}"
    
    def convert_sql_response_to_natural_language(self, user_question: str, sql_response: SQLResponse) -> str:
        """Converte resposta JSON do agente SQL para linguagem natural"""
        try:
            if sql_response.success:
                prompt = f"""
Você é um assistente que converte dados estruturados em respostas naturais.

Pergunta do usuário: "{user_question}"
Dados retornados: {json.dumps(sql_response.data[:5], ensure_ascii=False, indent=2)}
Total de registros: {sql_response.row_count}
Tempo de execução: {sql_response.execution_time}s

Crie uma resposta em português brasileiro que:
- Seja natural e conversacional
- Explique os dados de forma clara
- Use números específicos dos resultados
- Seja concisa (máximo 200 palavras)
- Use emojis ocasionalmente
- Se houver muitos registros, destaque os principais

Exemplo: "Encontrei {sql_response.row_count} registros. Os principais dados mostram que..."
"""
            else:
                prompt = f"""
Houve um problema ao consultar os dados.

Pergunta: "{user_question}"
Erro: {sql_response.error}

Explique de forma amigável que não foi possível obter os dados e sugira reformular a pergunta.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=250,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Desculpe, ocorreu um erro ao interpretar os dados: {str(e)}"
    
    def handle_general_chat(self, user_message: str, history: List) -> str:
        """Responde conversas gerais"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """Você é um assistente amigável e inteligente.

Características:
- Responda em português brasileiro
- Seja educado e prestativo
- Use emojis ocasionalmente
- Se perguntarem sobre dados, mencione que você pode consultar informações
- Seja conciso (máximo 150 palavras)
- Mantenha conversas naturais"""
                }
            ]
            
            # Adicionar histórico recente
            for msg in history[-4:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Desculpe, ocorreu um erro: {str(e)}"
    
    async def process_user_message(self, user_message: str, session_id: str, history: List) -> tuple[str, str, bool]:
        """Método principal do orquestrador"""
        try:
            # 1. Analisar intenção do usuário
            intent = self.analyze_user_intent(user_message)
            
            # 2. Rotear para agente apropriado
            if intent == IntentType.DATA_ANALYSIS:
                response = await self.handle_data_request(user_message, session_id)
                return response, "sql_agent", True
            
            elif intent == IntentType.HELP:
                response = """Olá! 😊 Sou seu assistente inteligente. Posso ajudar você com:

📊 **Análise de dados**: Faça perguntas sobre seus dados e eu consultarei o banco para você
💬 **Conversas gerais**: Posso conversar sobre diversos assuntos
🔍 **Consultas específicas**: "Quantos usuários temos?", "Mostre as vendas do mês", etc.

Como posso ajudar você hoje?"""
                return response, "orchestrator", False
            
            else:  # GENERAL_CHAT
                response = self.handle_general_chat(user_message, history)
                return response, "orchestrator", False
                
        except Exception as e:
            return f"Desculpe, ocorreu um erro: {str(e)}", "error", False

# Instância global
orchestrator = OrchestratorAgent()

# ================================
# ENDPOINTS DA API
# ================================

@app.get("/")
def home():
    return {
        "message": "🤖 Sistema de Agentes Orquestradores funcionando!",
        "architecture": "Orquestrador + Agente SQL",
        "agents": ["orchestrator", "sql_specialist"],
        "database": "Supabase",
        "status": "online"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "orchestrator": "online",
        "sql_agent": "online",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "supabase_configured": bool(os.getenv("SUPABASE_DATABASE_URL")),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/webhook/lovable", response_model=OrchestratorResponse)
async def lovable_webhook(payload: WebhookPayload):
    """Endpoint principal - sempre passa pelo orquestrador"""
    try:
        if not os.getenv("OPENAI_API_KEY"):
            return OrchestratorResponse(
                response="⚠️ Sistema não configurado corretamente",
                session_id=payload.session_id,
                timestamp=datetime.now().isoformat(),
                success=False,
                agent_used="error"
            )
        
        # Recuperar histórico da sessão
        session_history = conversations.get(payload.session_id, [])
        
        # Processar através do orquestrador
        response_text, agent_used, sql_executed = await orchestrator.process_user_message(
            payload.user_message, 
            payload.session_id, 
            session_history
        )
        
        # Salvar no histórico
        if payload.session_id not in conversations:
            conversations[payload.session_id] = []
        
        conversations[payload.session_id].extend([
            {
                "role": "user",
                "content": payload.user_message,
                "timestamp": datetime.now().isoformat()
            },
            {
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat()
            }
        ])
        
        # Limitar histórico
        if len(conversations[payload.session_id]) > 20:
            conversations[payload.session_id] = conversations[payload.session_id][-20:]
        
        return OrchestratorResponse(
            response=response_text,
            session_id=payload.session_id,
            timestamp=datetime.now().isoformat(),
            success=True,
            agent_used=agent_used,
            sql_executed=sql_executed
        )
        
    except Exception as e:
        return OrchestratorResponse(
            response=f"Desculpe, ocorreu um erro no sistema: {str(e)}",
            session_id=payload.session_id,
            timestamp=datetime.now().isoformat(),
            success=False,
            agent_used="error"
        )

# Endpoint para testar agente SQL diretamente (debug)
@app.post("/debug/sql-agent")
async def test_sql_agent(request: SQLRequest):
    """Endpoint para testar agente SQL diretamente"""
    sql_agent = SQLAgent()
    return await sql_agent.process_data_request(request)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
