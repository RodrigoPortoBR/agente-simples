"""
Sistema de Agentes Orquestradores - VERSÃO FINAL COM CORS CORRIGIDO
Arquitetura modular com Orchestrator + Agents especializados
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
import os
import uvicorn
import json

from models import WebhookPayload, OrchestratorResponse
from config import settings
from agents.orchestrator_agent import OrchestratorAgent
from agents.sql_agent import SQLAgent

# ===================================
# INICIALIZAÇÃO
# ===================================

app = FastAPI(
    title="Sistema de Agentes Orquestradores",
    version="5.0.0 - CORS Fixed",
    description="Arquitetura modular com Orchestrator + Agents especializados"
)

# ===================================
# CORS - CONFIGURAÇÃO CRÍTICA
# ===================================

# Lista explícita de origens permitidas
origins = [
    "https://lovable.dev",
    "https://app.lovable.dev",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Instâncias globais dos agentes
orchestrator = OrchestratorAgent()
sql_agent = SQLAgent()

# ===================================
# ENDPOINTS DE SISTEMA
# ===================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the testing interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api")
def api_info():
    """API information endpoint"""
    return {
        "message": "🤖 Sistema de Agentes Orquestradores",
        "version": "5.0.0 - CORS Fixed",
        "status": "online",
        "architecture": {
            "layer_1": "Orchestrator Agent (user-facing)",
            "layer_2": "Specialized Agents (SQL, etc)",
            "memory": "Supabase (persistent)",
            "llm": settings.OPENAI_MODEL,
        },
        "improvements": [
            "✅ Arquitetura modular",
            "✅ Memória persistente no Supabase",
            "✅ Separação clara de responsabilidades",
            "✅ Orchestrator único ponto de contato",
            "✅ SQL Agent sem lógica de negócio",
            "✅ Context window management",
            "✅ Error handling robusto",
            "✅ CORS configurado corretamente",
            "✅ Interface local para testes"
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

# ===================================
# ENDPOINTS DE CHAT
# ===================================

@app.post("/chat")
async def chat_endpoint(request: Request):
    """Endpoint unificado de chat"""
    try:
        data = await request.json()
        message = data.get("message", "").strip()
        session_id = data.get("sessionId", f"chat_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        if not message:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Mensagem não fornecida",
                    "response": "Por favor, digite uma mensagem para começar."
                }
            )

        # Processa via orquestrador
        result = await orchestrator.process_user_message(message, session_id)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "response": result.response,
                "session_id": result.session_id
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "response": "Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente."
            }
        )

# ===================================
# ENDPOINT PRINCIPAL (WEBHOOK)
# ===================================

@app.post("/webhook/lovable")
async def lovable_webhook(request: Request):
    """
    Endpoint principal para integração com Lovable
    
    Recebe mensagens do chat e processa via Orchestrator Agent
    """
    try:
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            data = await request.json()
        else:
            form_data = await request.form()
            data = dict(form_data)
        
        message = data.get("message", "").strip()
        session_id = data.get("sessionId") or f"lovable_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if not message:
            return {
                "response": "❌ Mensagem não fornecida. Por favor, envie uma mensagem para que eu possa ajudar!",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "Campo 'message' é obrigatório",
            }
        
        # Processa via Orquestrador
        result = await orchestrator.process_user_message(message, session_id)
        
        return {
            "response": result.response,
            "session_id": result.session_id,
            "timestamp": datetime.now().isoformat(),
            "success": result.success,
        }
        
    except Exception as e:
        print(f"❌ Erro no webhook/lovable: {str(e)}")
        return {
            "response": f"❌ Erro ao processar: {str(e)}",
            "session_id": session_id if 'session_id' in locals() else f"error_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "error": str(e),
        }

# ===================================
# ENDPOINT ALTERNATIVO (COMPATIBILIDADE)
# ===================================

@app.post("/webhook")
async def webhook_generic(payload: WebhookPayload):
    """
    Endpoint genérico para compatibilidade
    Redireciona para o endpoint principal
    """
    try:
        result = await orchestrator.process_user_message(
            payload.message, 
            payload.session_id or f"generic_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        return {
            "response": result.response,
            "session_id": result.session_id,
            "success": result.success,
            "source": "webhook_generic"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar: {str(e)}")

# ===================================
# INICIALIZAÇÃO DO SERVIDOR
# ===================================

if __name__ == "__main__":
    # Install required packages if not present
    try:
        import jinja2
    except ImportError:
        print("Installing required packages...")
        import subprocess
        subprocess.check_call(["pip", "install", "jinja2"])
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )
