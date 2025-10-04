from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
import uvicorn
from typing import List, Optional
from datetime import datetime

app = FastAPI(title="Agente Inteligente")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos de dados
class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str

class WebhookPayload(BaseModel):
    session_id: str
    user_message: str
    conversation_history: Optional[List[ConversationMessage]] = []

class AgentResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    success: bool

# Armazenamento simples em memória para histórico
conversations = {}

@app.get("/")
def home():
    return {
        "message": "🤖 Agente Inteligente funcionando!",
        "status": "online",
        "ai_enabled": bool(os.getenv("OPENAI_API_KEY"))
    }

@app.get("/health")
def health():
    openai_configured = bool(os.getenv("OPENAI_API_KEY"))
    return {
        "status": "healthy",
        "openai_configured": openai_configured,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/webhook/lovable", response_model=AgentResponse)
async def lovable_webhook(payload: WebhookPayload):
    try:
        # Verificar se OpenAI está configurada
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return AgentResponse(
                response="⚠️ OpenAI não configurada. Usando resposta básica: " + payload.user_message,
                session_id=payload.session_id,
                timestamp=datetime.now().isoformat(),
                success=False
            )
        
        # Configurar cliente OpenAI
        client = openai.OpenAI(api_key=api_key)
        
        # Recuperar histórico da sessão
        session_history = conversations.get(payload.session_id, [])
        
        # Preparar mensagens para OpenAI
        messages = [
            {
                "role": "system",
                "content": """Você é um assistente inteligente e prestativo integrado a um chat.

Características:
- Responda sempre em português brasileiro
- Seja amigável, educado e prestativo
- Mantenha conversas naturais e contextuais
- Se perguntarem sobre dados ou consultas SQL, explique que você pode ajudar com análises
- Seja conciso mas informativo (máximo 200 palavras por resposta)
- Use emojis ocasionalmente para ser mais amigável
- Se não souber algo, seja honesto

Contexto: Você está integrado a um sistema de chat e pode ajudar com diversas tarefas."""
            }
        ]
        
        # Adicionar histórico recente (últimas 6 mensagens)
        for msg in session_history[-6:]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Adicionar mensagem atual
        messages.append({
            "role": "user",
            "content": payload.user_message
        })
        
        # Chamar OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Modelo econômico
            messages=messages,
            max_tokens=300,
            temperature=0.7
        )
        
        # Extrair resposta
        ai_response = response.choices[0].message.content
        
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
                "content": ai_response,
                "timestamp": datetime.now().isoformat()
            }
        ])
        
        # Limitar histórico (manter apenas últimas 20 mensagens)
        if len(conversations[payload.session_id]) > 20:
            conversations[payload.session_id] = conversations[payload.session_id][-20:]
        
        return AgentResponse(
            response=ai_response,
            session_id=payload.session_id,
            timestamp=datetime.now().isoformat(),
            success=True
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
    """Recuperar histórico de uma sessão"""
    history = conversations.get(session_id, [])
    return {
        "session_id": session_id,
        "message_count": len(history),
        "history": history[-10:]  # Últimas 10 mensagens
    }

@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    """Limpar histórico de uma sessão"""
    if session_id in conversations:
        del conversations[session_id]
        return {"message": f"Histórico da sessão {session_id} limpo"}
    return {"message": "Sessão não encontrada"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
