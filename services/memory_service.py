"""Minimal memory service stub for validation"""
from typing import Any, List


class MemoryService:
    def __init__(self):
        self.store: List[Any] = []

    def add(self, item: Any):
        self.store.append(item)

    def list(self) -> List[Any]:
        return list(self.store)


def get_service():
    return MemoryService()
