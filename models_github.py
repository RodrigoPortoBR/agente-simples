"""
Modelos de Dados do Sistema
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# ================================
# ENUMS
# ================================

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    SQL = "sql_agent"
    ERROR = "error"

class IntentType(str, Enum):
    GENERAL_CHAT = "general_chat"
    DATA_ANALYSIS = "data_analysis"
    UNKNOWN = "unknown"

# ================================
# CONVERSAÇÃO
# ================================

class ConversationMessage(BaseModel):
    """Mensagem na conversa"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

class ConversationHistory(BaseModel):
    """Histórico de conversa"""
    session_id: str
    messages: List[ConversationMessage] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

# ================================
# AGENTE - INSTRUÇÕES E RESPOSTAS
# ================================

class AgentInstruction(BaseModel):
    """Instrução para um agente especialista"""
    agent_type: AgentType
    task_description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)

class AgentResponse(BaseModel):
    """Resposta de um agente especialista"""
    success: bool
    agent_type: AgentType
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# ================================
# ANÁLISE DE INTENÇÃO
# ================================

class IntentAnalysis(BaseModel):
    """Análise de intenção do usuário"""
    intent_type: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    needs_data_analysis: bool = False
    requires_agent: Optional[AgentType] = None
    extracted_parameters: Dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""

# ================================
# ORQUESTRADOR - RESPOSTA FINAL
# ================================

class OrchestratorResponse(BaseModel):
    """Resposta final do orquestrador ao usuário"""
    response: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool = True
    agents_used: List[AgentType] = []
    processing_steps: List[str] = []
    metadata: Optional[Dict[str, Any]] = None

# ================================
# WEBHOOK PAYLOAD
# ================================

class WebhookPayload(BaseModel):
    """Payload recebido do webhook"""
    session_id: Optional[str] = Field(None, alias="sessionId")
    user_message: Optional[str] = Field(None, alias="message")
    
    # Aliases alternativos
    message: Optional[str] = None
    sessionId: Optional[str] = None
    userId: Optional[str] = None
    text: Optional[str] = None
    content: Optional[str] = None
    
    class Config:
        populate_by_name = True

# ================================
# SQL AGENT - ESPECÍFICO
# ================================

class SQLQueryRequest(BaseModel):
    """Requisição estruturada para SQL Agent"""
    query_type: str  # "aggregate", "count", "select", "filter"
    table: str
    fields: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    aggregation: Optional[Dict[str, str]] = None  # {"field": "sum|avg|count"}
    order_by: Optional[str] = None
    limit: Optional[int] = None
    
class SQLQueryResult(BaseModel):
    """Resultado da query SQL"""
    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    row_count: int = 0
    execution_time: float = 0.0
    query_info: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None