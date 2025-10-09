"""
Sistema de Agentes Orquestradores - VERSÃO FINAL COM CORS CORRIGIDO
Arquitetura modular com Orchestrator + Agents especializados
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import os
import uvicorn
import json

from models import WebhookPayload, OrchestratorResponse
from config import settings
from agents.orchestrator_agent import OrchestratorAgent

# ================================
# INICIALIZAÇÃO
# ================================

app = FastAPI(
    title="Sistema de Agentes Orquestradores",
    version="5.0.0 - CORS Fixed",
    description="Arquitetura modular com Orchestrator + Agents especializados"
)

# ================================
# CORS - CONFIGURAÇÃO CRÍTICA
# ================================
# Lista explícita de origens permitidas
origins = [
    "https://lovable.dev",
    "https://app.lovable.dev",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # ❌ não use "*"
    allow_credentials=True,  # Permite cookies/autenticação
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Inclui OPTIONS
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "User-Agent",
        "X-Requested-With",
    ],
    expose_headers=["Content-Disposition"],  # opcional: p/ download de arquivos
)

# Instância global do Orquestrador
orchestrator = OrchestratorAgent()

# ================================
# ENDPOINTS DE SISTEMA
# ================================

@app.get("/")
def home():
    """Endpoint raiz"""
    return {
        "message": "🤖 Sistema de Agentes Orquestradores",
        "version": "5.0.0 - CORS Fixed",
        "status": "online",
        "architecture": {
            "layer_1": "Orchestrator Agent (user-facing)",
            "layer_2": "Specialized Agents (SQL, etc)",
            "memory": "Supabase (persistent)",
            "llm": settings.OPENAI_MODEL
        },
        "improvements": [
            "✅ Arquitetura modular",
            "✅ Memória persistente no Supabase",
            "✅ Separação clara de responsabilidades",
            "✅ Orchestrator único ponto de contato",
            "✅ SQL Agent sem lógica de negócio",
            "✅ Context window management",
            "✅ Error handling robusto",
            "✅ CORS configurado corretamente"
        ]
    }

@app.get("/health")
def health_check():
    """Verificação de saúde do sistema"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "openai": bool(settings.OPENAI_API_KEY),
            "supabase": bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY),
            "orchestrator": orchestrator is not None
        },
        "config": {
            "model": settings.OPENAI_MODEL,
            "max_history": settings.MAX_HISTORY_MESSAGES,
            "context_window": settings.CONTEXT_WINDOW_MESSAGES
        }
    }

# ================================
# ENDPOINT PRINCIPAL (WEBHOOK)
# ================================

@app.options("/webhook/lovable")
async def options_webhook():
    """Handler para CORS preflight (OPTIONS)"""
    return JSONResponse(
        content={"status": "ok"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )

@app.post("/webhook/lovable")
async def lovable_webhook(request: Request):
    """
    Endpoint principal do webhook - MANTÉM COMPATIBILIDADE
    
    Aceita múltiplos formatos:
    - {"message": "...", "sessionId": "..."}
    - {"user_message": "...", "session_id": "..."}
    - {"message": "...", "sessionId": "...", "context": {...}}
    
    Recebe mensagens e delega ao Orquestrador
    """
    try:
        # Log headers para debug
        print(f"📥 Headers: {dict(request.headers)}")
        
        # Processar payload (JSON ou Form)
        payload_data = {}
        
        try:
            content_type = request.headers.get("content-type", "")
            
            if "application/json" in content_type:
                raw_body = await request.body()
                print(f"📄 JSON body: {raw_body.decode()}")
                payload_data = json.loads(raw_body.decode())
            else:
                form_data = await request.form()
                payload_data = dict(form_data)
                print(f"📄 Form data: {payload_data}")
                
        except Exception as e:
            print(f"⚠️ Erro ao processar payload: {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "response": "❌ Erro ao processar mensagem",
                    "session_id": "error",
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "error": str(e)
                }
            )
        
        # Extrair mensagem do usuário (múltiplos formatos aceitos)
        user_message = (
            payload_data.get("message") or
            payload_data.get("user_message") or
            payload_data.get("text") or
            payload_data.get("content")
        )
        
        if not user_message:
            return JSONResponse(
                status_code=400,
                content={
                    "response": "❌ Mensagem não fornecida. Envie 'message' ou 'user_message'.",
                    "session_id": payload_data.get("sessionId") or payload_data.get("session_id") or "error",
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "error": "Missing message field"
                }
            )
        
        # Extrair session_id (múltiplos formatos aceitos)
        session_id = (
            payload_data.get("sessionId") or
            payload_data.get("session_id") or
            payload_data.get("userId") or
            payload_data.get("user_id") or
            f"session_{int(datetime.now().timestamp())}"
        )
        
        # Extrair context (opcional)
        context = payload_data.get("context") or payload_data.get("contextData")
        
        print(f"🎯 Processando - Mensagem: '{user_message}' | Sessão: '{session_id}'")
        if context:
            print(f"📊 Context recebido: {json.dumps(context, indent=2)}")
        
        # Validar configuração
        if not settings.OPENAI_API_KEY:
            return JSONResponse(
                status_code=500,
                content={
                    "response": "⚠️ Sistema não configurado corretamente (OpenAI)",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "error": "OpenAI API key not configured"
                }
            )
        
        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            print("⚠️ Supabase não configurado - usando memória temporária")
        
        # DELEGAR AO ORQUESTRADOR (único ponto de entrada)
        print(f"🚀 Delegando ao Orquestrador...")
        result = await orchestrator.process_user_message(user_message, session_id)
        
        print(f"✅ Resposta gerada: {result.response[:100]}...")
        
        # Retornar resposta (formato compatível)
        return JSONResponse(
            content={
                "response": result.response,
                "session_id": result.session_id,
                "timestamp": result.timestamp.isoformat(),
                "success": result.success,
                "agents_used": [agent.value for agent in result.agents_used],
                "processing_steps": result.processing_steps,
                "metadata": result.metadata
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
        )
        
    except Exception as e:
        print(f"❌ Erro crítico no webhook: {e}")
        
        session_id_fallback = "error"
        try:
            session_id_fallback = session_id if 'session_id' in locals() else "error"
        except:
            pass
        
        return JSONResponse(
            status_code=500,
            content={
                "response": f"❌ Erro ao processar: {str(e)}",
                "session_id": session_id_fallback,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            },
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
        )

# ================================
# ENDPOINTS DE DEBUG
# ================================

@app.get("/debug/memory/{session_id}")
async def debug_memory(session_id: str):
    """Debug: visualizar memória de uma sessão"""
    try:
        history = await orchestrator.memory.get_conversation_history(session_id)
        
        return {
            "session_id": session_id,
            "message_count": len(history.messages),
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in history.messages
            ],
            "created_at": history.created_at.isoformat(),
            "updated_at": history.updated_at.isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.delete("/debug/memory/{session_id}")
async def clear_memory(session_id: str):
    """Debug: limpar memória de uma sessão"""
    try:
        success = await orchestrator.memory.clear_session(session_id)
        
        return {
            "success": success,
            "session_id": session_id,
            "message": "Memória limpa com sucesso" if success else "Erro ao limpar memória"
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/debug/test-sql")
async def test_sql_agent():
    """Debug: testar SQL Agent diretamente"""
    from models import AgentInstruction, AgentType
    
    try:
        # Teste de agregação
        instruction = AgentInstruction(
            agent_type=AgentType.SQL,
            task_description="Teste de agregação",
            parameters={
                "query_type": "aggregate",
                "table": "clientes",
                "filters": {"cluster_id": "1"},
                "aggregation": {
                    "receita_12m": "sum",
                    "gm_12m": "avg"
                }
            },
            context={},
            session_id="debug"
        )
        
        result = await orchestrator.sql_agent.process_instruction(instruction)
        
        return {
            "test": "SQL Agent - Agregação",
            "success": result.success,
            "data": result.data,
            "metadata": result.metadata,
            "error": result.error
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/config")
def debug_config():
    """Debug: verificar configuração"""
    return {
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "openai_model": settings.OPENAI_MODEL,
        "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY),
        "max_history": settings.MAX_HISTORY_MESSAGES,
        "context_window": settings.CONTEXT_WINDOW_MESSAGES,
        "tables": {
            "conversations": settings.CONVERSATION_TABLE,
            "messages": settings.CONVERSATION_MESSAGES_TABLE
        }
    }

@app.get("/debug/structure")
def debug_structure():
    """Debug: verificar estrutura de arquivos"""
    import sys
    
    return {
        "python_path": sys.path,
        "current_dir": os.getcwd(),
        "files_in_root": os.listdir(".") if os.path.exists(".") else [],
        "agents_exists": os.path.exists("agents"),
        "agents_files": os.listdir("agents") if os.path.exists("agents") else [],
        "services_exists": os.path.exists("services"),
        "services_files": os.listdir("services") if os.path.exists("services") else [],
        "python_version": sys.version
    }

# ================================
# STARTUP
# ================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Iniciando servidor na porta {port}")
    print(f"📊 OpenAI: {'✅' if settings.OPENAI_API_KEY else '❌'}")
    print(f"💾 Supabase: {'✅' if settings.SUPABASE_URL else '❌'}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
