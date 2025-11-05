"""Minimal memory service stub for validation"""
from typing import Any, List, Dict, Optional
from datetime import datetime


class MemoryService:
    def __init__(self):
        self.store: List[Any] = []
        self.session_id_to_messages: Dict[str, List[Dict[str, Any]]] = {}

    def add(self, item: Any):
        self.store.append(item)

    def list(self) -> List[Any]:
        return list(self.store)

    # Assíncronos para compatibilidade com OrchestratorAgent
    async def add_message(
        self,
        session_id: str,
        role: Any,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        role_value = getattr(role, "value", role)
        message = {
            "role": role_value,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }
        messages = self.session_id_to_messages.setdefault(session_id, [])
        messages.append(message)

    async def get_recent_context(self, session_id: str, num_messages: int = 6) -> List[Dict[str, Any]]:
        messages = self.session_id_to_messages.get(session_id, [])
        return messages[-num_messages:]


def get_service():
    return MemoryService()

