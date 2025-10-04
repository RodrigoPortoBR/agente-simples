from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
import uvicorn
import json
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

app = FastAPI(title="Sistema de Agentes Orquestradores" )

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
# AGENTE SQL ESPECIALISTA (API)
# ================================
class SQLAgent:
    """Agente especialista em consultas SQL via Supabase API"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        # Headers para Supabase API
        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        }
    
    async def get_database_schema(self) -> str:
        """Obtém informações das tabelas via API do Supabase"""
        try:
            async with httpx.AsyncClient( ) as client:
                # Fazer uma requisição para descobrir tabelas
                # Vamos tentar algumas tabelas comuns primeiro
                common_tables = ["users", "profiles", "posts", "products", "orders", "sales", "customers"]
                
                available_tables = []
                
                for table in common_tables:
                    try:
                        response = await client.get(
                            f"{self.supabase_url}/rest/v1/{table}?limit=1",
                            headers=self.headers
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if data:  # Se retornou dados, a tabela existe
                                # Pegar as colunas do primeiro registro
                                columns = list(data[0].keys()) if data else []
                                available_tables.append(f"{table}: {', '.join(columns)}")
                            else:
                                available_tables.append(f"{table}: (tabela vazia)")
                    except:
                        continue
                
                if available_tables:
                    return "TABELAS DISPONÍVEIS:\n" + "\n".join(available_tables)
                else:
                    return "Nenhuma tabela comum encontrada. Tabelas possíveis: users, profiles, posts, products, orders"
                    
        except Exception as e:
            return f"Erro ao obter schema: {str(e)}"
    
    def validate_sql_security(self, user_question: str):
        """Valida se a pergunta é segura (não usamos SQL direto na API)"""
        # Para API, validamos a intenção em vez de SQL
        dangerous_words = ['delete', 'drop', 'truncate', 'alter', 'create', 'update']
        question_lower = user_question.lower()
        
        for word in dangerous_words:
            if word in question_lower:
                return False, f"Operação {word} não permitida"
        
        return True, "Pergunta aprovada"
    
    async def analyze_question_and_build_api_call(self, user_question: str) -> Dict[str, Any]:
        """Analisa a pergunta e determina qual chamada de API fazer"""
        try:
            schema = await self.get_database_schema()
            
            prompt = f"""
Você é um especialista em API Supabase. Analise a pergunta do usuário e determine:
1. Qual tabela consultar
2. Que tipo de operação (count, select, filter)
3. Quais parâmetros usar

{schema}

OPERAÇÕES DISPONÍVEIS:
- Contar registros: GET /table?select=count()
- Listar registros: GET /table?limit=10
- Filtrar por data: GET /table?created_at=gte.2024-01-01
- Ordenar: GET /table?order=created_at.desc

Pergunta: "{user_question}"

Responda em JSON com:
{{
  "table": "nome_da_tabela",
  "operation": "count|select|filter",
  "params": {{"limit": 10, "select": "*", "order": "created_at.desc"}},
  "description": "descrição da operação"
}}

Responda APENAS com o JSON:
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
            
            api_plan = response.choices[0].message.content.strip()
            
            # Tentar fazer parse do JSON
            try:
                return json.loads(api_plan)
            except:
                # Fallback se não conseguir fazer parse
                return {
                    "table": "users",
                    "operation": "count",
                    "params": {"select": "count()"},
                    "description": "Contagem de registros"
                }
                
        except Exception as e:
            return {
                "table": "users",
                "operation": "select",
                "params": {"limit": 5},
                "description": f"Erro na análise: {str(e)}"
            }
    
    async def execute_supabase_api_call(self, api_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Executa a chamada para API do Supabase"""
        try:
            start_time = datetime.now()
            
            table = api_plan.get("table", "users")
            params = api_plan.get("params", {})
            
            # Construir URL da API
            url = f"{self.supabase_url}/rest/v1/{table}"
            
            # Construir query parameters
            query_params = []
            for key, value in params.items():
                query_params.append(f"{key}={value}")
            
            if query_params:
                url += "?" + "&".join(query_params)
            
            # Fazer requisição
            async with httpx.AsyncClient( ) as client:
                response = await client.get(url, headers=self.headers)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "success": True,
                        "data": data,
                        "row_count": len(data) if isinstance(data, list) else 1,
                        "execution_time": execution_time,
                        "api_url": url
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API Error {response.status_code}: {response.text}",
                        "data": [],
                        "row_count": 0
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "row_count": 0
            }
    
    async def process_data_request(self, request: SQLRequest) -> SQLResponse:
        """Método principal do agente SQL - usa API do Supabase"""
        try:
            # 1. Validar pergunta
            is_safe, reason = self.validate_sql_security(request.user_question)
            if not is_safe:
                return SQLResponse(
                    success=False,
                    error=f"Pergunta rejeitada: {reason}"
                )
            
            # 2. Analisar pergunta e planejar chamada API
            api_plan = await self.analyze_question_and_build_api_call(request.user_question)
            
            # 3. Executar chamada API
            execution_result = await self.execute_supabase_api_call(api_plan)
            
            # 4. Retornar resposta estruturada
            return SQLResponse(
                success=execution_result["success"],
                sql_query=f"API: {api_plan.get('description', 'Consulta via API')}",
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

Palavras-chave para data_analysis: quantos, quanto, mostre, liste, dados, relatório, total, média, últimos, contar, somar, análise, usuários, vendas, produtos

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
Você é um assistente que converte dados da API em respostas naturais.

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

Exemplo: "Encontrei {sql_response.row_count} registros. Os dados mostram que..."
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
    
    async def process_user_message(self, user_message: str, session_id: str, history: List):
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

📊 **Análise de dados**: Faça perguntas sobre seus dados e eu consultarei via API
💬 **Conversas gerais**: Posso conversar sobre diversos assuntos
🔍 **Consultas específicas**: "Quantos usuários temos?", "Mostre os últimos registros", etc.

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
        "architecture": "Orquestrador + Agente SQL via API",
        "agents": ["orchestrator", "sql_api_specialist"],
        "database": "Supabase API",
        "status": "online"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "orchestrator": "online",
        "sql_agent": "online",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "supabase_url_configured": bool(os.getenv("SUPABASE_URL")),
        "supabase_key_configured": bool(os.getenv("SUPABASE_ANON_KEY")),
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
