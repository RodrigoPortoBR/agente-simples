"""Minimal SQL agent stub for validation"""
from typing import Any


class SQLAgent:
    def __init__(self, dsn: str = ""):
        self.dsn = dsn

    def query(self, q: str):
        return []


def get_agent():
    return SQLAgent()
