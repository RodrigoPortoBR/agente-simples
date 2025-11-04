"""Configurações Centralizadas do Sistema"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações do sistema"""

    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

    # OpenAI
    OPENAI_MODEL: str = "gpt-4"  # or gpt-3.5-turbo if gpt-4 is not available
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 500

    # Conversação
    MAX_HISTORY_MESSAGES: int = 50
    CONTEXT_WINDOW_MESSAGES: int = 10
    SESSION_EXPIRY_HOURS: int = 24

    # Performance
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    CACHE_TTL_SECONDS: int = 300

    # Database
    CONVERSATION_TABLE: str = "agent_conversations"
    CONVERSATION_MESSAGES_TABLE: str = "agent_messages"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()