"""Minimal orchestrator agent stub for validation"""
from typing import Any


class OrchestratorAgent:
    def __init__(self, config: Any = None):
        self.config = config

    def start(self):
        return "started"


def get_agent():
    return OrchestratorAgent()
