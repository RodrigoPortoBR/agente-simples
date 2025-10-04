from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
import uvicorn
import json
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

app = FastAPI(title="Agente Orquestrador com SQL")

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
    SQL_QUERY = "sql_query"
    HELP = "help"
    UNKNOWN = "unknown"

# Modelos de dados
class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str

class WebhookPayload(BaseModel):
    session_id: str
    user_message: str
    conversation_history: Optional[List[ConversationMessage]] = []

class IntentAnalysis(BaseModel):
    intent: IntentType
    confidence: float
    sql_context: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    success: bool
    intent: Optional[str] = None
    sql_executed: Optional[bool] = False

# Armazenamento em memória
conversations = {}

# Classe do Agente SQL
class SQLAgent:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def is_sql_safe(self, sql_query: str) -> tuple[bool, str]:
        """Valida se a consulta SQL é segura"""
        sql_upper = sql_query.upper().strip()
        
        # Apenas SELECT é permitido
        if not sql_upper.startswith('SELECT'):
            return False, "Apenas consultas SELECT são permitidas"
        
        # Palavras proibidas
        forbidden_words = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE', '--', ';']
        for word in forbidden_words:
            if word in sql_upper:
                return False, f"Palavra proibida encontrada: {word}"
        
        return True, "Consulta aprovada"
    
    def generate_sql_query(self, user_question: str, context: Dict[str, Any]) -> str:
        """Gera consulta SQL baseada na pergunta do usuário"""
        try:
            prompt = f"""
Você é um especialista em SQL. Converta a pergunta do usuário em uma consulta SQL segura.

REGRAS IMPORTANTES:
- Use apenas SELECT (nunca DROP, DELETE, UPDATE, INSERT)
- Assuma tabelas comuns: usuarios, vendas, produtos, pedidos
- Use nomes de colunas em português: nome, email, data_criacao, valor, quantidade
- Adicione LIMIT 100 para evitar resultados muito grandes
- Se não souber a estrutura exata, use nomes lógicos

Pergunta do usuário: "{user_question}"

Responda apenas com a consulta SQL, sem explicações:
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1
            )
            
            sql_query = response.choices[0].message.content.strip()
            
            # Limpar a resposta
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            
            return sql_query
            
        except Exception as e:
            return f"-- Erro na geração: {str(e)}"
    
    def execute_sql_simulation(self, sql_query: str) -> Dict[str, Any]:
        """Simula execução de SQL (sem banco real)"""
        # Como não temos banco real, vamos simular resultados
        simulated_results = {
            "usuarios": [
                {"id": 1, "nome": "João Silva", "email": "joao@email.com", "data_criacao": "2024-01-15"},
                {"id": 2, "nome": "Maria Santos", "email": "maria@email.com", "data_criacao": "2024-02-20"},
                {"id": 3, "nome": "Pedro Costa", "email": "pedro@email.com", "data_criacao": "2024-03-10"}
            ],
            "vendas": [
                {"id": 1, "produto": "Notebook", "valor": 2500.00, "data_venda": "2024-10-01"},
                {"id": 2, "produto": "Mouse", "valor": 50.00, "data_venda": "2024-10-02"},
                {"id": 3, "produto": "Teclado", "valor": 150.00, "data_venda": "2024-10-03"}
            ]
        }
        
        # Análise simples da query para retornar dados relevantes
        sql_lower = sql_query.lower()
        
        if 'count' in sql_lower and 'usuarios' in sql_lower:
            return {"resultado": [{"total_usuarios": 1247}]}
        elif 'usuarios' in sql_lower:
            return {"resultado": simulated_results["usuarios"][:3]}
        elif 'vendas' in sql_lower or 'venda' in sql_lower:
            return {"resultado": simulated_results["vendas"]}
        elif 'count' in sql_lower:
            return {"resultado": [{"total": 89}]}
        else:
            return {"resultado": [{"mensagem": "Consulta executada com sucesso"}]}

# Classe do Orquestrador
class OrchestratorAgent:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.sql_agent = SQLAgent()
    
    def analyze_intent(self, user_message: str) -> IntentAnalysis:
        """Analisa a intenção do usuário"""
        try:
            prompt = f"""
Analise a mensagem do usuário e determine a intenção:

INTENÇÕES POSSÍVEIS:
- general_chat: Conversa geral, cumprimentos, perguntas gerais
- sql_query: Perguntas sobre dados, relatórios, consultas, estatísticas
- help: Pedidos de ajuda sobre o sistema
- unknown: Não conseguiu identificar

Mensagem: "{user_message}"

Palavras-chave para SQL: quantos, quanto, mostre, liste, dados, relatório, vendas, usuários, total, média

Responda apenas com: general_chat, sql_query, help ou unknown
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=50,
                temperature=0.1
            )
            
            intent_text = response.choices[0].message.content.strip().lower()
            
            # Mapear resposta para enum
            intent_mapping = {
                "general_chat": IntentType.GENERAL_CHAT,
                "sql_query": IntentType.SQL_QUERY,
                "help": IntentType.HELP,
                "unknown": IntentType.UNKNOWN
            }
            
            intent = intent_mapping.get(intent_text, IntentType.UNKNOWN)
            confidence = 0.8 if intent != IntentType.UNKNOWN else 0.3
            
            return IntentAnalysis(intent=intent, confidence=confidence)
            
        except Exception as e:
            return IntentAnalysis(intent=IntentType.UNKNOWN, confidence=0.0)
    
    def process_sql_query(self, user_message: str, session_id: str) -> Dict[str, Any]:
        """Processa consulta SQL"""
        try:
            # Gerar SQL
            sql_query = self.sql_agent.generate_sql_query(user_message, {})
            
            # Validar segurança
            is_safe, safety_reason = self.sql_agent.is_sql_safe(sql_query)
            
            if not is_safe:
                return {
                    "success": False,
                    "error": f"Consulta rejeitada: {safety_reason}",
                    "sql_query": sql_query
                }
            
            # Executar (simulado)
            results = self.sql_agent.execute_sql_simulation(sql_query)
            
            return {
                "success": True,
                "sql_query": sql_query,
                "results": results,
                "row_count": len(results.get("resultado", []))
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_natural_response(self, user_message: str, sql_results: Dict[str, Any], history: List) -> str:
        """Gera resposta em linguagem natural"""
        try:
            if sql_results.get("success"):
                results_data = sql_results.get("results", {})
                sql_query = sql_results.get("sql_query", "")
                
                prompt = f"""
Você é um assistente que converte resultados de consultas SQL em respostas naturais.

Pergunta do usuário: "{user_message}"
SQL executado: {sql_query}
Resultados: {json.dumps(results_data, ensure_ascii=False, indent=2)}

Crie uma resposta em português brasileiro que:
- Seja natural e amigável
- Explique os resultados de forma clara
- Use números e dados específicos
- Seja concisa (máximo 150 palavras)
- Use emojis ocasionalmente

Exemplo: "Encontrei 1.247 usuários cadastrados no sistema 📊. A maioria se cadastrou nos últimos 3 meses."
"""
            else:
                prompt = f"""
Houve um erro na consulta SQL. Explique de forma amigável que não foi possível processar a consulta sobre dados.

Pergunta: "{user_message}"
Erro: {sql_results.get("error", "Erro desconhecido")}

Seja educado e sugira reformular a pergunta.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Desculpe, ocorreu um erro ao processar sua consulta: {str(e)}"
    
    def generate_chat_response(self, user_message: str, history: List) -> str:
        """Gera resposta para chat geral"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """Você é um assistente inteligente e amigável.

Características:
- Responda em português brasileiro
- Seja educado e prestativo
- Use emojis ocasionalmente
- Mantenha conversas naturais
- Se perguntarem sobre dados/consultas, mencione que você pode ajudar com análises
- Seja conciso (máximo 150 palavras)"""
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

# Instância global do orquestrador
orchestrator = OrchestratorAgent()

@app.get("/")
def home():
    return {
        "message": "🤖 Agente Orquestrador com SQL funcionando!",
        "status": "online",
        "features": ["chat_inteligente", "consultas_sql", "analise_intencao"],
        "ai_enabled": bool(os.getenv("OPENAI_API_KEY"))
    }

@app.get("/health")
def health():
    openai_configured = bool(os.getenv("OPENAI_API_KEY"))
    return {
        "status": "healthy",
        "openai_configured": openai_configured,
        "sql_agent": "enabled",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/webhook/lovable", response_model=AgentResponse)
async def lovable_webhook(payload: WebhookPayload):
    try:
        # Verificar OpenAI
        if not os.getenv("OPENAI_API_KEY"):
            return AgentResponse(
                response="⚠️ OpenAI não configurada",
                session_id=payload.session_id,
                timestamp=datetime.now().isoformat(),
                success=False
            )
        
        # Recuperar histórico
        session_history = conversations.get(payload.session_id, [])
        
        # Analisar intenção
        intent_analysis = orchestrator.analyze_intent(payload.user_message)
        
        # Processar baseado na intenção
        if intent_analysis.intent == IntentType.SQL_QUERY:
            # Processar consulta SQL
            sql_results = orchestrator.process_sql_query(payload.user_message, payload.session_id)
            response_text = orchestrator.generate_natural_response(
                payload.user_message, sql_results, session_history
            )
            sql_executed = sql_results.get("success", False)
        else:
            # Chat geral
            response_text = orchestrator.generate_chat_response(payload.user_message, session_history)
            sql_executed = False
        
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
        
        return AgentResponse(
            response=response_text,
            session_id=payload.session_id,
            timestamp=datetime.now().isoformat(),
            success=True,
            intent=intent_analysis.intent.value,
            sql_executed=sql_executed
        )
        
    except Exception as e:
        return AgentResponse(
            response=f"Desculpe, ocorreu um erro: {str(e)}",
            session_id=payload.session_id,
            timestamp=datetime.now().isoformat(),
            success=False
        )

@app.get("/session/{session_id}")
def get_session_history(session_id: str):
    history = conversations.get(session_id, [])
    return {
        "session_id": session_id,
        "message_count": len(history),
        "history": history[-10:]
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
