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
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instância global do Orquestrador
orchestrator = OrchestratorAgent()

# ===================================
# ENDPOINTS DE SISTEMA
# ===================================

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
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
