# services/memory_service.py

from datetime import datetime
from typing import Dict, List

class MemoryService:
    """
    Serviço simples de memória em memória (pode ser substituído por Supabase).
    """

    def __init__(self):
        # Dicionário de sessões → lista de mensagens
        self.sessions: Dict[str, List[Dict[str, str]]] = {}

    async def add_message(self, session_id: str, role: str, content: str, metadata: dict = None):
        """Adiciona uma mensagem na memória da sessão"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []

        self.sessions[session_id].append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        })

    async def get_recent_context(self, session_id: str, num_messages: int = 6) -> List[Dict[str, str]]:
        """Retorna as últimas mensagens da sessão"""
        if session_id not in self.sessions:
            return []
        return self.sessions[session_id][-num_messages:]
