from fastapi import FastAPI
import uvicorn
import os

app = FastAPI(title="Agente Simples")

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
    
    # Resposta simples sem IA (para testar)
    response = f"Olá! Recebi sua mensagem: '{user_message}'. Em breve terei IA integrada!"
    
    return {
        "response": response,
        "session_id": session_id,
        "success": True,
        "timestamp": "2025-10-04T16:00:00Z"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)