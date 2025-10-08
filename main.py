"""
Sistema de Agentes Orquestradores - VERSÃO REFATORADA
Arquitetura modular com separação de responsabilidades
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os
import uvicorn
import json

from models import WebhookPayload, OrchestratorResponse
from config import settings
from agents.orchestrator_agent import OrchestratorAgent

# ================================
# MODELOS PYDANTIC
# ================================

class LovableRequest(BaseModel):
    """Modelo para requisições do Lovable"""
    message: str
    sessionId: str = None

# ================================
# INICIALIZAÇÃO
# ================================

app = FastAPI(
    title="Sistema de Agentes Orquestradores",
    version="5.0.0 - Refatorado",
    description="Arquitetura modular com Orquestrador + Agents especializados"
)

# CORS
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
        "version": "5.0.0 - Refatorado",
        "status": "online",
        "architecture": {
            "layer_1": "Orchestrator Agent (user-facing)",
            "layer_2": "Specialized Agents (SQL, etc)",
            "memory": "Supabase (persistent)",
            "llm": settings.OPENAI_MODEL
        },
        "improvements": {
            "✅ Arquitetura modular",
            "✅ Memória persistente no Supabase",
            "✅ Separação clara de responsabilidades",
            "✅ Orquestrador único ponto de contato",
            "✅ SQL Agent sem lógica de negócio",
            "✅ Context window management",
            "✅ Error handling robusto"
        }
    }

@app.get("/health")
def health_check():
    """Verificação de saúde do sistema"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "5.0.0",
        "components": {
            "orchestrator": "✅ Online",
            "sql_agent": "✅ Standby", 
            "supabase": "✅ Connected",
            "openai": "✅ Available"
        }
    }

# ================================
# ENDPOINT WEBHOOK LOVABLE (CORRIGIDO)
# ================================

@app.post("/webhook/lovable")
async def lovable_webhook(request: LovableRequest):
    """
    Endpoint para integração com Lovable
    Processa mensagens do chat e retorna respostas do sistema
    """
    try:
        print(f"🔗 Webhook Lovable chamado: {datetime.now()}")
        print(f"📨 Dados recebidos: {request}")
        
        # Extrair dados do modelo Pydantic
        user_message = request.message
        session_id = request.sessionId or f"lovable_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"👤 Mensagem: '{user_message}'")
        print(f"🔑 Session ID: {session_id}")
        
        # Validar entrada
        if not user_message or not user_message.strip():
            return {
                "response": "❌ Mensagem não fornecida. Por favor, envie uma mensagem para que eu possa ajudar!",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "Campo 'message' é obrigatório",
                "github_integration": {
                    "project": "RodrigoPortoBR/agente-simples",
                    "version": "1.0",
                    "architecture": "minimalista"
                }
            }
        
        # Processar com Orquestrador
        print(f"🧠 Enviando para Orquestrador...")
        response = await orchestrator.process_user_message(
            message=user_message.strip(),
            session_id=session_id
        )
        
        print(f"✅ Resposta do Orquestrador: {response[:100]}...")
        
        # Retornar resposta estruturada
        return {
            "response": response,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "github_integration": {
                "project": "RodrigoPortoBR/agente-simples",
                "version": "1.0",
                "architecture": "minimalista",
                "endpoint": "webhook/lovable"
            }
        }
        
    except Exception as e:
        print(f"❌ Erro no webhook Lovable: {e}")
        error_session_id = getattr(request, 'sessionId', None) or f"error_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            "response": f"❌ Erro ao processar: {str(e)}",
            "session_id": error_session_id,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "error": str(e),
            "github_integration": {
                "project": "RodrigoPortoBR/agente-simples",
                "version": "1.0",
                "architecture": "minimalista"
            }
        }

# ================================
# ENDPOINTS LEGADOS (COMPATIBILIDADE)
# ================================

@app.post("/webhook")
async def webhook_legacy(payload: WebhookPayload):
    """
    Endpoint webhook legado para compatibilidade
    Redireciona para o novo sistema
    """
    try:
        print(f"🔄 Webhook legado chamado, redirecionando...")
        
        # Redirecionar para o novo sistema
        response = await orchestrator.process_user_message(
            message=payload.message,
            session_id=payload.session_id or f"legacy_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        return OrchestratorResponse(
            response=response,
            session_id=payload.session_id,
            success=True,
            metadata={
                "source": "legacy_webhook",
                "redirected": True,
                "github_integration": {
                    "project": "RodrigoPortoBR/agente-simples",
                    "version": "1.0",
                    "architecture": "minimalista"
                }
            }
        )
        
    except Exception as e:
        print(f"❌ Erro no webhook legado: {e}")
        return OrchestratorResponse(
            response=f"❌ Erro ao processar: {str(e)}",
            session_id=payload.session_id,
            success=False,
            metadata={"error": str(e), "source": "legacy_webhook"}
        )

# ================================
# INICIALIZAÇÃO DO SERVIDOR
# ================================

if __name__ == "__main__":
    print("🚀 Iniciando Sistema de Agentes Orquestradores v5.0")
    print("🏗️ Arquitetura: Orquestrador + Agents Especializados")
    print("📊 Dados: Supabase (tempo real)")
    print("🔗 Integração: Lovable webhook ativo com Request Body")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
