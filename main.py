"""
Sistema de Agentes Orquestradores - COMPATÍVEL COM LOVABLE
Versão corrigida com CORS melhorado e múltiplos formatos de payload
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import openai
import os
import uvicorn
import json
import httpx
import re
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

app = FastAPI(title="Sistema de Agentes Orquestradores - Compatível com Lovable")

# CORS MELHORADO - Mais permissivo para Lovable
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos os domínios
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Todos os métodos
    allow_headers=["*"],  # Todos os headers
    expose_headers=["*"]
)

# ================================
# MODELOS DE DADOS FLEXÍVEIS
# ================================

class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str

class WebhookPayload(BaseModel):
    """Modelo flexível para aceitar diferentes formatos do Lovable"""
    session_id: Optional[str] = Field(None, alias="sessionId")
    user_message: Optional[str] = Field(None, alias="message")
    conversation_history: Optional[List[ConversationMessage]] = []
    
    # Campos alternativos que o Lovable pode enviar
    message: Optional[str] = None
    sessionId: Optional[str] = None
    userId: Optional[str] = None
    text: Optional[str] = None
    content: Optional[str] = None
    
    class Config:
        allow_population_by_field_name = True

class AgentInstruction(BaseModel):
    agent_type: str
    task_description: str
    user_question: str
    context: Dict[str, Any]
    session_id: str

class AgentResponse(BaseModel):
    success: bool
    agent_type: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class OrchestratorResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    success: bool
    agents_used: List[str]
    processing_steps: List[str]

# ================================
# AGENTE SQL INDEPENDENTE (2ª CAMADA)
# ================================

class SQLAgent:
    """Agente especialista em análise SQL - 2ª camada"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        }
        
        # Base de conhecimento RAG
        self.business_context = {
            "tables": {
                "clientes": {
                    "description": "Dados principais dos clientes do e-commerce",
                    "key_fields": ["id", "nome", "email", "receita_12m", "gm_12m", "cluster_id"],
                    "metrics": {
                        "receita_12m": "Receita dos últimos 12 meses em reais",
                        "gm_12m": "Margem bruta dos últimos 12 meses em percentual",
                        "cluster_id": "Segmentação: 1=Premium, 2=Alto valor, 3=Médio, 4=Baixo, 5=Novo"
                    }
                },
                "clusters": {
                    "description": "Segmentação estratégica de clientes",
                    "key_fields": ["id", "nome", "descricao", "avg_receita", "avg_margem", "total_clientes"],
                    "business_logic": {
                        "1": "Premium - Alta receita (>R$100k) e margem (>30%)",
                        "2": "Alto Valor - Boa receita (R$50k-100k)",
                        "3": "Médios - Receita moderada (R$20k-50k)",
                        "4": "Baixo Valor - Receita baixa (<R$20k)",
                        "5": "Novos - Recém adquiridos"
                    }
                },
                "pedidos": {
                    "description": "Histórico completo de pedidos e transações",
                    "key_fields": ["id", "cliente_id", "valor", "data_pedido", "status"]
                },
                "monthly_series": {
                    "description": "Séries temporais mensais para análise de tendências",
                    "key_fields": ["mes", "receita", "margem", "pedidos_count"]
                }
            }
        }
    
    def analyze_data_request(self, instruction: AgentInstruction) -> Dict[str, Any]:
        """Analisa a instrução do Orquestrador e determina que dados buscar"""
        task_description = instruction.task_description.lower()
        user_question = instruction.user_question.lower()
        
        # Detectar tabela
        table = "clientes"  # Default
        if any(word in task_description for word in ["pedido", "order", "compra"]):
            table = "pedidos"
        elif any(word in task_description for word in ["cluster", "segmento"]):
            table = "clusters"
        elif any(word in task_description for word in ["mes", "mensal", "temporal", "crescimento"]):
            table = "monthly_series"
        
        # Detectar operação
        operation = "select"
        select_field = "*"
        
        if any(word in task_description for word in ["quantos", "count", "numero"]):
            operation = "count"
            select_field = "count()"
        elif any(word in task_description for word in ["soma", "total", "sum"]):
            operation = "sum"
            if "receita" in task_description:
                select_field = "sum(receita_12m)"
        elif any(word in task_description for word in ["media", "average", "avg"]):
            operation = "avg"
            if "margem" in task_description:
                select_field = "avg(gm_12m)"
            else:
                select_field = "avg(receita_12m)"
        else:
            # Selecionar campos relevantes por tabela
            if table == "clientes":
                select_field = "nome,receita_12m,gm_12m,cluster_id"
            elif table == "pedidos":
                select_field = "cliente_id,valor,data_pedido,status"
            elif table == "clusters":
                select_field = "nome,total_clientes,avg_receita,avg_margem"
            elif table == "monthly_series":
                select_field = "mes,receita,margem,pedidos_count"
        
        # Detectar filtros
        filters = {}
        if any(word in task_description for word in ["premium", "top", "melhor"]):
            if table == "clientes":
                filters["cluster_id"] = "eq.1"
        elif any(word in task_description for word in ["baixa margem", "risco"]):
            if table == "clientes":
                filters["gm_12m"] = "lt.20"
        elif any(word in task_description for word in ["alto valor"]):
            if table == "clientes":
                filters["cluster_id"] = "eq.2"
        
        # Detectar ordenação
        order = None
        if any(word in task_description for word in ["top", "maior", "melhor"]):
            if table == "clientes":
                order = "receita_12m.desc"
            elif table == "pedidos":
                order = "valor.desc"
            elif table == "clusters":
                order = "avg_receita.desc"
        elif any(word in task_description for word in ["recente", "ultimo"]):
            if table == "pedidos":
                order = "data_pedido.desc"
            elif table == "monthly_series":
                order = "mes.desc"
        
        # Detectar limite
        limit = None
        numbers = re.findall(r'\d+', task_description)
        if numbers and any(word in task_description for word in ["top", "primeiro", "ultimos"]):
            limit = int(numbers[0])
        elif operation == "select":
            limit = 10  # Default para listagens
        
        return {
            "table": table,
            "operation": operation,
            "params": {
                "select": select_field,
                "limit": limit,
                "order": order,
                "filters": filters
            }
        }
    
    async def execute_query(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Executa a consulta no Supabase e retorna dados estruturados"""
        try:
            start_time = datetime.now()
            
            table = analysis["table"]
            params = analysis["params"]
            
            # Construir URL
            url = f"{self.supabase_url}/rest/v1/{table}"
            query_params = []
            
            # Adicionar parâmetros
            if params.get("select"):
                query_params.append(f"select={params['select']}")
            
            if params.get("limit"):
                query_params.append(f"limit={params['limit']}")
            
            if params.get("order"):
                query_params.append(f"order={params['order']}")
            
            # Adicionar filtros
            for field, filter_value in params.get("filters", {}).items():
                query_params.append(f"{field}={filter_value}")
            
            if query_params:
                url += "?" + "&".join(query_params)
            
            # Executar requisição
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "success": True,
                        "data": data,
                        "row_count": len(data) if isinstance(data, list) else 1,
                        "execution_time": execution_time,
                        "query_info": {
                            "table": table,
                            "operation": analysis["operation"],
                            "url": url
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API Error {response.status_code}: {response.text}",
                        "data": None
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    async def process_instruction(self, instruction: AgentInstruction) -> AgentResponse:
        """Método principal do Agente SQL"""
        try:
            # 1. Analisar instrução
            analysis = self.analyze_data_request(instruction)
            
            # 2. Executar consulta
            query_result = await self.execute_query(analysis)
            
            # 3. Retornar resposta estruturada para o Orquestrador
            return AgentResponse(
                success=query_result["success"],
                agent_type="sql_agent",
                data=query_result.get("data"),
                error=query_result.get("error"),
                metadata={
                    "row_count": query_result.get("row_count", 0),
                    "execution_time": query_result.get("execution_time", 0),
                    "query_info": query_result.get("query_info", {}),
                    "analysis": analysis
                }
            )
            
        except Exception as e:
            return AgentResponse(
                success=False,
                agent_type="sql_agent",
                error=str(e)
            )

# ================================
# AGENTE ORQUESTRADOR PRINCIPAL (1ª CAMADA)
# ================================

class OrchestratorAgent:
    """Agente Orquestrador Principal - ÚNICO ponto de contato com usuário"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.sql_agent = SQLAgent()
        self.conversations = {}  # Memória conversacional
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """Recupera histórico da conversa"""
        return self.conversations.get(session_id, [])
    
    def add_to_conversation(self, session_id: str, role: str, content: str):
        """Adiciona mensagem ao histórico"""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        
        self.conversations[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Limitar histórico
        if len(self.conversations[session_id]) > 20:
            self.conversations[session_id] = self.conversations[session_id][-20:]
    
    async def analyze_user_intent_with_llm(self, user_message: str, history: List) -> Dict[str, Any]:
        """Usa LLM para analisar intenção do usuário e decidir ações"""
        try:
            # Preparar contexto da conversa
            conversation_context = ""
            if history:
                recent_messages = history[-4:]  # Últimas 4 mensagens
                for msg in recent_messages:
                    conversation_context += f"{msg['role']}: {msg['content']}\n"
            
            prompt = f"""Você é um Agente Orquestrador inteligente especializado em análise de dados de e-commerce.

CONTEXTO DA CONVERSA:
{conversation_context}

NOVA MENSAGEM DO USUÁRIO: "{user_message}"

SUAS CAPACIDADES:
1. Conversa geral (cumprimentos, explicações, ajuda)
2. Análise de dados via Agente SQL especializado

DADOS DISPONÍVEIS:
- Tabela "clientes": receita, margem bruta, clusters (1=Premium, 2=Alto valor, etc.)
- Tabela "pedidos": histórico de compras, valores, datas
- Tabela "clusters": análise por segmentos de clientes
- Tabela "monthly_series": tendências temporais, crescimento

ANÁLISE NECESSÁRIA:
1. A mensagem é sobre DADOS DE NEGÓCIO (receita, clientes, vendas, análises)?
2. Se SIM, que tipo de análise o usuário quer?
3. Como você instruiria um agente SQL para obter esses dados?

RESPONDA EM JSON:
{{
  "needs_data_analysis": true/false,
  "intent_type": "general_chat" | "data_analysis" | "help",
  "confidence": 0.0-1.0,
  "sql_instruction": {{
    "task_description": "Descrição clara da análise necessária",
    "expected_data": "Que dados espera receber",
    "business_context": "Contexto de negócio relevante"
  }},
  "reasoning": "Por que tomou essa decisão"
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.3
            )
            
            # Parse da resposta JSON
            response_text = response.choices[0].message.content.strip()
            
            # Tentar extrair JSON da resposta
            try:
                # Procurar por JSON na resposta
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    return json.loads(json_str)
                else:
                    raise ValueError("JSON não encontrado na resposta")
            except:
                # Fallback: análise baseada em regras
                return self.fallback_intent_analysis(user_message)
                
        except Exception as e:
            # Fallback em caso de erro
            return self.fallback_intent_analysis(user_message)
    
    def fallback_intent_analysis(self, user_message: str) -> Dict[str, Any]:
        """Análise de intenção de fallback baseada em regras"""
        message_lower = user_message.lower()
        
        # Palavras-chave para análise de dados
        data_keywords = [
            "quantos", "quanto", "total", "soma", "média", "margem", "receita", "vendas",
            "mostre", "liste", "dados", "relatório", "análise", "performance", "crescimento",
            "clientes", "pedidos", "clusters", "top", "ranking", "último", "recente"
        ]
        
        needs_data = any(keyword in message_lower for keyword in data_keywords)
        
        if needs_data:
            return {
                "needs_data_analysis": True,
                "intent_type": "data_analysis",
                "confidence": 0.7,
                "sql_instruction": {
                    "task_description": f"Analisar dados baseado na pergunta: {user_message}",
                    "expected_data": "Dados relevantes da consulta",
                    "business_context": "Análise de negócio solicitada pelo usuário"
                },
                "reasoning": "Detectadas palavras-chave relacionadas a dados de negócio"
            }
        else:
            return {
                "needs_data_analysis": False,
                "intent_type": "general_chat",
                "confidence": 0.8,
                "reasoning": "Conversa geral ou cumprimentos"
            }
    
    async def handle_data_analysis(self, user_message: str, intent_analysis: Dict, session_id: str) -> tuple:
        """Coordena análise de dados"""
        try:
            # 1. Preparar instrução para Agente SQL
            sql_instruction = AgentInstruction(
                agent_type="sql_agent",
                task_description=intent_analysis["sql_instruction"]["task_description"],
                user_question=user_message,
                context={
                    "expected_data": intent_analysis["sql_instruction"]["expected_data"],
                    "business_context": intent_analysis["sql_instruction"]["business_context"]
                },
                session_id=session_id
            )
            
            # 2. Enviar para Agente SQL e receber JSON
            sql_response = await self.sql_agent.process_instruction(sql_instruction)
            
            # 3. Converter JSON para linguagem natural usando LLM
            if sql_response.success:
                natural_response = await self.convert_json_to_natural_language(
                    user_message, sql_response.data, sql_response.metadata
                )
                return natural_response, ["sql_agent"], ["Análise de intenção com LLM", "Consulta SQL executada", "Conversão para linguagem natural"]
            else:
                return f"❌ Não foi possível obter os dados: {sql_response.error}", ["sql_agent"], ["Análise de intenção com LLM", "Erro na consulta SQL"]
                
        except Exception as e:
            return f"❌ Erro na análise de dados: {str(e)}", ["error"], ["Erro no processamento"]
    
    async def convert_json_to_natural_language(self, user_question: str, data: Any, metadata: Dict) -> str:
        """Converte dados JSON do Agente SQL em resposta natural"""
        try:
            prompt = f"""Você é um analista sênior de e-commerce. Converta os dados JSON em uma resposta natural e insights acionáveis.

PERGUNTA ORIGINAL: "{user_question}"

DADOS RETORNADOS:
{json.dumps(data, indent=2, ensure_ascii=False)}

METADADOS:
- Registros encontrados: {metadata.get('row_count', 0)}
- Tempo de execução: {metadata.get('execution_time', 0):.2f}s
- Tabela consultada: {metadata.get('query_info', {}).get('table', 'N/A')}

CONTEXTO DE NEGÓCIO:
• Margem bruta saudável: 20-30% (boa), 30%+ (excelente)
• Cliente premium: receita > R$ 100.000 (cluster 1)
• Clusters: 1=Premium, 2=Alto valor, 3=Médio, 4=Baixo, 5=Novo
• Benchmark do setor: crescimento 15%+ anual

FORNEÇA UMA RESPOSTA COMPLETA COM:
1. 📊 Interpretação clara dos números
2. 💡 Insights de negócio (o que isso significa?)
3. 🎯 Oportunidades identificadas
4. ⚠️ Alertas ou riscos (se houver)
5. 📈 Recomendações acionáveis

Use linguagem natural, seja específico com os números, máximo 300 palavras, inclua emojis estrategicamente."""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            # Fallback: resposta simples baseada nos dados
            if isinstance(data, list) and len(data) > 0:
                return f"📊 Encontrei {len(data)} registros. Dados: {str(data[:3])}..." if len(data) > 3 else f"📊 Dados encontrados: {str(data)}"
            elif isinstance(data, dict):
                return f"📊 Resultado da análise: {str(data)}"
            else:
                return f"📊 Análise concluída. Dados processados com sucesso."
    
    async def handle_general_chat(self, user_message: str, history: List) -> str:
        """Responde conversas gerais mantendo contexto"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """Você é um assistente inteligente especializado em análise de dados de e-commerce.

PERSONALIDADE:
- Profissional mas amigável
- Especialista em dados de negócio
- Prestativo e educativo
- Conciso e objetivo

CAPACIDADES:
- Análise de clientes, receita e margem bruta
- Segmentação por clusters
- Análise temporal e tendências
- Histórico de pedidos e transações
- Insights de negócio acionáveis

ESTILO:
- Use português brasileiro
- Seja educado e prestativo
- Use emojis ocasionalmente (máximo 2-3)
- Máximo 150 palavras
- Mencione suas capacidades quando relevante
- Incentive perguntas sobre dados"""
                }
            ]
            
            # Adicionar histórico recente
            for msg in history[-4:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return "Olá! 😊 Sou seu assistente de análise de dados de e-commerce. Posso ajudar com análises de clientes, receita, margem bruta e muito mais. Como posso ajudar você hoje?"
    
    async def process_user_message(self, user_message: str, session_id: str) -> OrchestratorResponse:
        """MÉTODO PRINCIPAL DO ORQUESTRADOR"""
        try:
            # 1. Recuperar histórico da conversa
            history = self.get_conversation_history(session_id)
            
            # 2. Adicionar mensagem do usuário ao histórico
            self.add_to_conversation(session_id, "user", user_message)
            
            # 3. Analisar intenção usando LLM
            intent_analysis = await self.analyze_user_intent_with_llm(user_message, history)
            
            # 4. Decidir ação baseada na análise
            if intent_analysis.get("needs_data_analysis", False):
                # Coordenar análise de dados
                response_text, agents_used, processing_steps = await self.handle_data_analysis(
                    user_message, intent_analysis, session_id
                )
            else:
                # Conversa geral
                response_text = await self.handle_general_chat(user_message, history)
                agents_used = ["orchestrator"]
                processing_steps = ["Análise de intenção com LLM", "Resposta conversacional"]
            
            # 5. Adicionar resposta ao histórico
            self.add_to_conversation(session_id, "assistant", response_text)
            
            # 6. Retornar resposta estruturada
            return OrchestratorResponse(
                response=response_text,
                session_id=session_id,
                timestamp=datetime.now().isoformat(),
                success=True,
                agents_used=agents_used,
                processing_steps=processing_steps
            )
            
        except Exception as e:
            error_response = f"❌ Erro no sistema: {str(e)}"
            self.add_to_conversation(session_id, "assistant", error_response)
            
            return OrchestratorResponse(
                response=error_response,
                session_id=session_id,
                timestamp=datetime.now().isoformat(),
                success=False,
                agents_used=["error"],
                processing_steps=["Erro no processamento"]
            )

# ================================
# INSTÂNCIA GLOBAL DO ORQUESTRADOR
# ================================

orchestrator = OrchestratorAgent()

# ================================
# ENDPOINTS DA API
# ================================

@app.get("/")
def home():
    return {
        "message": "🤖 Sistema de Agentes Orquestradores - COMPATÍVEL COM LOVABLE",
        "version": "3.1 - Lovable Compatible",
        "status": "online",
        "cors": "enabled",
        "payload_formats": ["json", "form-data", "multiple_field_names"],
        "architecture": {
            "layer_1": "Orquestrador Principal (único ponto de contato)",
            "layer_2": "Agente SQL Especialista (independente)",
            "communication": "JSON estruturado entre agentes"
        }
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "architecture": "correct",
        "orchestrator": "active_with_llm",
        "sql_agent": "independent",
        "cors": "enabled",
        "lovable_compatible": True,
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "supabase_configured": bool(os.getenv("SUPABASE_URL")) and bool(os.getenv("SUPABASE_ANON_KEY")),
        "timestamp": datetime.now().isoformat()
    }

# ENDPOINT PRINCIPAL COM COMPATIBILIDADE MELHORADA
@app.post("/webhook/lovable")
async def lovable_webhook(request: Request):
    """
    ENDPOINT PRINCIPAL - COMPATÍVEL COM MÚLTIPLOS FORMATOS
    - Aceita JSON, form-data, diferentes nomes de campos
    - CORS melhorado
    - Logs detalhados para debug
    """
    try:
        # Log da requisição para debug
        print(f"🔍 Headers recebidos: {dict(request.headers)}")
        
        # Tentar diferentes formatos de payload
        payload_data = {}
        
        try:
            # Tentar JSON primeiro
            if request.headers.get("content-type", "").startswith("application/json"):
                raw_body = await request.body()
                print(f"🔍 Raw JSON body: {raw_body.decode()}")
                payload_data = json.loads(raw_body.decode())
            else:
                # Tentar form data
                form_data = await request.form()
                payload_data = dict(form_data)
                print(f"🔍 Form data recebido: {payload_data}")
        except Exception as e:
            print(f"❌ Erro ao parsear payload: {e}")
            return {
                "response": "❌ Erro ao processar formato da mensagem",
                "session_id": "error",
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            }
        
        # Extrair dados com múltiplos formatos possíveis
        user_message = (
            payload_data.get("user_message") or 
            payload_data.get("message") or 
            payload_data.get("text") or 
            payload_data.get("content") or
            "Olá!"
        )
        
        session_id = (
            payload_data.get("session_id") or 
            payload_data.get("sessionId") or 
            payload_data.get("userId") or
            f"session_{datetime.now().timestamp()}"
        )
        
        print(f"🔍 Dados extraídos - Mensagem: '{user_message}', Sessão: '{session_id}'")
        
        # Validar configuração
        if not os.getenv("OPENAI_API_KEY"):
            return {
                "response": "⚠️ Sistema não configurado - OpenAI API key não encontrada",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "OpenAI not configured"
            }
        
        # PROCESSAR ATRAVÉS DO ORQUESTRADOR
        print(f"🚀 Processando através do orquestrador...")
        result = await orchestrator.process_user_message(user_message, session_id)
        
        print(f"✅ Resposta gerada: {result.response[:100]}...")
        
        # Retornar resposta compatível
        return {
            "response": result.response,
            "session_id": result.session_id,
            "timestamp": result.timestamp,
            "success": result.success,
            "agents_used": result.agents_used,
            "processing_steps": result.processing_steps
        }
        
    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        return {
            "response": f"❌ Erro crítico no sistema: {str(e)}",
            "session_id": "error",
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "error": str(e)
        }

# ENDPOINT ADICIONAL PARA TESTE DIRETO
@app.post("/test")
async def test_endpoint(data: dict):
    """Endpoint simples para teste direto"""
    try:
        user_message = data.get("message", "Teste de conexão")
        session_id = data.get("session_id", "test_session")
        
        result = await orchestrator.process_user_message(user_message, session_id)
        
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# ENDPOINT OPTIONS PARA CORS
@app.options("/webhook/lovable")
async def options_webhook():
    """Endpoint OPTIONS para CORS preflight"""
    return {"status": "ok"}

# ================================
# ENDPOINTS DE DEBUG
# ================================

@app.get("/debug/cors")
async def debug_cors():
    """Debug: verificar configuração CORS"""
    return {
        "cors_status": "enabled",
        "allowed_origins": ["*"],
        "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allowed_headers": ["*"],
        "credentials": True
    }

@app.post("/debug/payload")
async def debug_payload(request: Request):
    """Debug: verificar formato do payload recebido"""
    try:
        headers = dict(request.headers)
        
        # Tentar diferentes formatos
        try:
            raw_body = await request.body()
            body_text = raw_body.decode()
        except:
            body_text = "Não foi possível ler o body"
        
        try:
            if request.headers.get("content-type", "").startswith("application/json"):
                json_data = json.loads(body_text)
            else:
                json_data = "Não é JSON"
        except:
            json_data = "Erro ao parsear JSON"
        
        try:
            form_data = await request.form()
            form_dict = dict(form_data)
        except:
            form_dict = "Não é form data"
        
        return {
            "headers": headers,
            "raw_body": body_text,
            "json_parsed": json_data,
            "form_parsed": form_dict,
            "content_type": request.headers.get("content-type", "não especificado")
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
