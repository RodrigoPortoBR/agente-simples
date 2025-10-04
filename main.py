from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

app = FastAPI(title="Agente Simples" )

# ADICIONAR CORS - MUITO IMPORTANTE!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos os domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "🤖 Agente funcionando!", "status": "online"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/webhook/lovable")
def webhook(data: dict):
    user_message = data.get("user_message", "")
    session_id = data.get("session_id", "test")
    
    response = f"Olá! Recebi sua mensagem: '{user_message}'. Sistema funcionando!"
    
    return {
        "response": response,
        "session_id": session_id,
        "success": True,
        "timestamp": "2025-10-04T16:00:00Z"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
