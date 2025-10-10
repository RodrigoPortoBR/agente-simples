"""
Sistema de Agentes Orquestradores - COMPATÍVEL COM REFATORAÇÃO
CORS + Chamada correta do Orchestrator
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import os
import uvicorn
import json

from models import OrchestratorResponse
from config import settings
from agents.orchestrator_agent import OrchestratorAgent

# ================================
# INICIALIZAÇÃO
# ================================

app = FastAPI(
    title="Sistema de Agentes Orquestradores",
    version="5.0.0 - Fixed Connection",
    description="Arquitetura modular focada em dados de negócio"
)

# ================================
# CORS - CRÍTICO
# ================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
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
        "version": "5.0.0 - Fixed Connection",
        "status": "online",
        "focus": "Dados de negócio (clientes, receita, margem, clusters)",
        "tables": ["clientes", "clusters", "pedidos", "monthly_series"]
    }

@app.get("/health")
def health_check():
    """Verificação de saúde"""
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
# CORS PREFLIGHT
# ================================

@app.options("/webhook/lovable")
async def options_webhook():
    """Handler para CORS preflight"""
    return JSONResponse(
        content={"status": "ok"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    )

# ================================
# ENDPOINT PRINCIPAL (WEBHOOK)
# ================================

@app.post("/webhook/lovable")
async def lovable_webhook(request: Request):
    """
    Endpoint principal - COMPATÍVEL COM LOVABLE
    
    Aceita:
    - {"message": "...", "sessionId": "..."}
    - {"user_message": "...", "session_id": "..."}
    - {"message": "...", "sessionId": "...", "context": {...}}
    """
    try:
        # Log para debug
        print(f"📥 Headers: {dict(request.headers)}")
        
        # Processar payload
        payload_data = {}
        
        try:
            content_type = request.headers.get("content-type", "")
            
            if "application/json" in content_type:
                raw_body = await request.body()
                print(f"📄 Body recebido: {raw_body.decode()}")
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
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                }
            )
        
        # Extrair mensagem (múltiplos formatos)
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
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                }
            )
        
        # Extrair session_id (múltiplos formatos)
        session_id = (
            payload_data.get("sessionId") or
            payload_data.get("session_id") or
            payload_data.get("userId") or
            payload_data.get("user_id") or
            f"session_{int(datetime.now().timestamp())}"
        )
        
        print(f"🎯 Processando:")
        print(f"   Mensagem: '{user_message}'")
        print(f"   Session: '{session_id}'")
        
        # Validar OpenAI
        if not settings.OPENAI_API_KEY:
            return JSONResponse(
                status_code=500,
                content={
                    "response": "⚠️ Sistema não configurado (OpenAI)",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "error": "OpenAI API key not configured"
                },
                headers={
                    "Access-Control-Allow-Origin": "*",
                }
            )
        
        # ================================
        # CHAMADA CORRETA DO ORCHESTRATOR
        # Argumentos POSICIONAIS (não keywords!)
        # ================================
        
        print(f"🚀 Chamando Orchestrator Agent...")
        
        # ✅ CORRETO: Chamada posicional
        result = await orchestrator.process_user_message(
            user_message,  # ← Primeiro argumento (posicional)
            session_id     # ← Segundo argumento (posicional)
        )
        
        print(f"✅ Resposta gerada:")
        print(f"   Success: {result.success}")
        print(f"   Response: {result.response[:100]}...")
        print(f"   Agents: {[a.value for a in result.agents_used]}")
        
        # Retornar resposta
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
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Detalhes: {str(e)}")
        
        # Tentar extrair session_id para erro
        try:
            error_session = session_id if 'session_id' in locals() else "error"
        except:
            error_session = "error"
        
        return JSONResponse(
            status_code=500,
            content={
                "response": f"❌ Erro ao processar: {str(e)}",
                "session_id": error_session,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            },
            headers={
                "Access-Control-Allow-Origin": "*",
            }
        )

# ================================
# ENDPOINTS DE DEBUG
# ================================

@app.get("/debug/test-orchestrator")
async def test_orchestrator():
    """Testar Orchestrator diretamente"""
    try:
        # Teste simples
        result = await orchestrator.process_user_message(
            "Olá, tudo bem?",
            "debug_test"
        )
        
        return {
            "test": "Orchestrator Agent",
            "success": result.success,
            "response": result.response,
            "agents_used": [a.value for a in result.agents_used],
            "metadata": result.metadata
        }
    except Exception as e:
        return {
            "test": "Orchestrator Agent",
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

@app.get("/debug/memory/{session_id}")
async def debug_memory(session_id: str):
    """Ver memória de uma sessão"""
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
            ]
        }
    except Exception as e:
        return {"error": str(e)}

@app.delete("/debug/memory/{session_id}")
async def clear_memory(session_id: str):
    """Limpar memória de uma sessão"""
    try:
        success = await orchestrator.memory.clear_session(session_id)
        return {
            "success": success,
            "session_id": session_id,
            "message": "Memória limpa" if success else "Erro ao limpar"
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/config")
def debug_config():
    """Ver configuração"""
    return {
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "openai_model": settings.OPENAI_MODEL,
        "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY),
        "max_history": settings.MAX_HISTORY_MESSAGES,
        "context_window": settings.CONTEXT_WINDOW_MESSAGES
    }

@app.post("/debug/test-simple")
async def test_simple(request: Request):
    """Teste simplificado"""
    try:
        body = await request.json()
        message = body.get("message", "teste")
        session_id = body.get("sessionId", "debug")
        
        # Chamada direta
        result = await orchestrator.process_user_message(message, session_id)
        
        return {
            "input": {"message": message, "sessionId": session_id},
            "output": {
                "response": result.response,
                "success": result.success,
                "agents_used": [a.value for a in result.agents_used]
            }
        }
    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }

# ================================
# STARTUP
# ================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Iniciando servidor na porta {port}")
    print(f"📊 OpenAI: {'✅' if settings.OPENAI_API_KEY else '❌'}")
    print(f"💾 Supabase: {'✅' if settings.SUPABASE_URL else '❌'}")
    print(f"🎯 Foco: Dados de negócio (clientes, receita, margem)")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
