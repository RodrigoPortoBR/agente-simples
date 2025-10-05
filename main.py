"""
Sistema de Agentes Orquestradores - SQL CORRIGIDO
Versão com lógica de consulta SQL melhorada
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

app = FastAPI(title="Sistema de Agentes Orquestradores - SQL Corrigido")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# ================================
# MODELOS DE DADOS
# ================================

class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str

class WebhookPayload(BaseModel):
    session_id: Optional[str] = Field(None, alias="sessionId")
    user_message: Optional[str] = Field(None, alias="message")
    conversation_history: Optional[List[ConversationMessage]] = []
    
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
# AGENTE SQL CORRIGIDO
# ================================

class SQLAgent:
    """Agente SQL com lógica de consulta corrigida"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        }
        
        # Mapeamento correto de consultas
        self.query_patterns = {
            # Receita por cluster
            "receita_cluster": {
                "keywords": ["receita", "faturamento", "vendas", "cluster"],
                "table": "clientes",
                "operation": "sum",
                "field": "receita_12m",
                "filter_field": "cluster_id"
            },
            # Contagem por cluster
            "count_cluster": {
                "keywords": ["quantos", "numero", "count", "cluster"],
                "table": "clientes", 
                "operation": "count",
                "field": "*",
                "filter_field": "cluster_id"
            },
            # Margem por cluster
            "margem_cluster": {
                "keywords": ["margem", "cluster"],
                "table": "clientes",
                "operation": "avg",
                "field": "gm_12m",
                "filter_field": "cluster_id"
            },
            # Top clientes
            "top_clientes": {
                "keywords": ["top", "melhor", "maior", "cliente"],
                "table": "clientes",
                "operation": "select",
                "field": "nome,receita_12m,gm_12m,cluster_id",
                "order": "receita_12m.desc"
            },
            # Dados de cluster (tabela clusters)
            "info_clusters": {
                "keywords": ["cluster", "segmento", "grupo"],
                "table": "clusters",
                "operation": "select",
                "field": "*"
            },
            # Pedidos
            "pedidos": {
                "keywords": ["pedido", "compra", "order"],
                "table": "pedidos",
                "operation": "select",
                "field": "*"
            },
            # Séries temporais
            "temporal": {
                "keywords": ["mes", "mensal", "crescimento", "tempo"],
                "table": "monthly_series",
                "operation": "select",
                "field": "*",
                "order": "mes.desc"
            }
        }
    
    def analyze_data_request_improved(self, instruction: AgentInstruction) -> Dict[str, Any]:
        """Análise melhorada de consultas com lógica corrigida"""
        task_description = instruction.task_description.lower()
        user_question = instruction.user_question.lower()
        combined_text = f"{task_description} {user_question}"
        
        print(f"🔍 Analisando: '{combined_text}'")
        
        # Detectar cluster específico
        cluster_id = None
        cluster_patterns = {
            "1": ["cluster 1", "premium", "top", "melhor"],
            "2": ["cluster 2", "alto valor", "high value"],
            "3": ["cluster 3", "medio", "médio"],
            "4": ["cluster 4", "baixo", "low"],
            "5": ["cluster 5", "novo", "new"]
        }
        
        for cluster, patterns in cluster_patterns.items():
            if any(pattern in combined_text for pattern in patterns):
                cluster_id = cluster
                break
        
        # Detectar tipo de consulta
        query_type = None
        for pattern_name, pattern_config in self.query_patterns.items():
            keywords = pattern_config["keywords"]
            if all(keyword in combined_text for keyword in keywords[:2]):  # Pelo menos 2 keywords
                query_type = pattern_name
                break
            elif any(keyword in combined_text for keyword in keywords):
                if not query_type:  # Primeira correspondência parcial
                    query_type = pattern_name
        
        # Fallback para consultas de receita/cluster
        if not query_type and cluster_id and any(word in combined_text for word in ["receita", "faturamento", "vendas"]):
            query_type = "receita_cluster"
        elif not query_type and cluster_id and any(word in combined_text for word in ["quantos", "count"]):
            query_type = "count_cluster"
        elif not query_type and cluster_id:
            query_type = "top_clientes"
        
        # Configuração padrão se não detectar
        if not query_type:
            query_type = "top_clientes"
        
        config = self.query_patterns[query_type]
        
        # Detectar limite
        limit = None
        numbers = re.findall(r'\d+', combined_text)
        if numbers and any(word in combined_text for word in ["top", "primeiro", "ultimos"]):
            limit = int(numbers[0])
        elif config["operation"] == "select":
            limit = 10  # Default
        
        # Construir parâmetros
        params = {
            "select": config["field"],
            "limit": limit,
            "order": config.get("order"),
            "filters": {}
        }
        
        # Adicionar filtro de cluster se detectado
        if cluster_id and config.get("filter_field"):
            params["filters"][config["filter_field"]] = f"eq.{cluster_id}"
        
        # Ajustar para operações de agregação
        if config["operation"] in ["sum", "count", "avg"]:
            if config["operation"] == "sum":
                params["select"] = f"{config['field']}.sum()"
            elif config["operation"] == "count":
                params["select"] = "*"  # Para count, usamos select=* e contamos no código
            elif config["operation"] == "avg":
                params["select"] = f"{config['field']}.avg()"
        
        result = {
            "table": config["table"],
            "operation": config["operation"],
            "query_type": query_type,
            "cluster_id": cluster_id,
            "params": params
        }
        
        print(f"✅ Análise resultado: {result}")
        return result
    
    async def execute_query_improved(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Execução melhorada de consultas"""
        try:
            start_time = datetime.now()
            
            table = analysis["table"]
            params = analysis["params"]
            operation = analysis["operation"]
            
            # Construir URL base
            url = f"{self.supabase_url}/rest/v1/{table}"
            query_params = []
            
            # Para operações de agregação, usar sintaxe correta do PostgREST
            if operation == "sum":
                # Para soma, precisamos usar select com função de agregação
                field_to_sum = params["select"].replace(".sum()", "")
                query_params.append(f"select={field_to_sum}.sum()")
            elif operation == "count":
                # Para contagem, usar select=count
                query_params.append("select=count")
            elif operation == "avg":
                # Para média, usar função de agregação
                field_to_avg = params["select"].replace(".avg()", "")
                query_params.append(f"select={field_to_avg}.avg()")
            else:
                # Select normal
                if params.get("select"):
                    query_params.append(f"select={params['select']}")
            
            # Adicionar filtros
            for field, filter_value in params.get("filters", {}).items():
                query_params.append(f"{field}={filter_value}")
            
            # Adicionar ordenação (apenas para select normal)
            if operation == "select" and params.get("order"):
                query_params.append(f"order={params['order']}")
            
            # Adicionar limite (apenas para select normal)
            if operation == "select" and params.get("limit"):
                query_params.append(f"limit={params['limit']}")
            
            # Construir URL final
            if query_params:
                url += "?" + "&".join(query_params)
            
            print(f"🔗 URL construída: {url}")
            
            # Executar requisição
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                print(f"📊 Status: {response.status_code}")
                print(f"📊 Resposta: {response.text[:200]}...")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Processar resultado baseado na operação
                    if operation == "count":
                        # Para count, o resultado vem como lista, precisamos contar
                        if isinstance(data, list):
                            processed_data = [{"count": len(data)}]
                        else:
                            processed_data = data
                    else:
                        processed_data = data
                    
                    return {
                        "success": True,
                        "data": processed_data,
                        "row_count": len(processed_data) if isinstance(processed_data, list) else 1,
                        "execution_time": execution_time,
                        "query_info": {
                            "table": table,
                            "operation": operation,
                            "url": url,
                            "cluster_id": analysis.get("cluster_id")
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API Error {response.status_code}: {response.text}",
                        "data": None,
                        "query_info": {
                            "url": url,
                            "table": table,
                            "operation": operation
                        }
                    }
                    
        except Exception as e:
            print(f"❌ Erro na execução: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    async def process_instruction(self, instruction: AgentInstruction) -> AgentResponse:
        """Método principal do Agente SQL corrigido"""
        try:
            print(f"🚀 SQL Agent processando: {instruction.user_question}")
            
            # 1. Analisar instrução com lógica melhorada
            analysis = self.analyze_data_request_improved(instruction)
            
            # 2. Executar consulta com sintaxe corrigida
            query_result = await self.execute_query_improved(analysis)
            
            # 3. Retornar resposta estruturada
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
            print(f"❌ Erro no SQL Agent: {e}")
            return AgentResponse(
                success=False,
                agent_type="sql_agent",
                error=str(e)
            )

# ================================
# AGENTE ORQUESTRADOR (MANTIDO IGUAL)
# ================================

class OrchestratorAgent:
    """Agente Orquestrador Principal"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.sql_agent = SQLAgent()
        self.conversations = {}
    
    def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        return self.conversations.get(session_id, [])
    
    def add_to_conversation(self, session_id: str, role: str, content: str):
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        
        self.conversations[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        if len(self.conversations[session_id]) > 20:
            self.conversations[session_id] = self.conversations[session_id][-20:]
    
    async def analyze_user_intent_with_llm(self, user_message: str, history: List) -> Dict[str, Any]:
        """Análise de intenção com LLM"""
        try:
            conversation_context = ""
            if history:
                recent_messages = history[-4:]
                for msg in recent_messages:
                    conversation_context += f"{msg['role']}: {msg['content']}\n"
            
            prompt = f"""Você é um Agente Orquestrador especializado em análise de dados de e-commerce.

CONTEXTO DA CONVERSA:
{conversation_context}

NOVA MENSAGEM: "{user_message}"

DADOS DISPONÍVEIS:
- Tabela "clientes": receita_12m, gm_12m (margem), cluster_id (1=Premium, 2=Alto, 3=Médio, 4=Baixo, 5=Novo)
- Tabela "clusters": informações dos segmentos
- Tabela "pedidos": histórico de compras
- Tabela "monthly_series": dados mensais

EXEMPLOS DE ANÁLISE:
- "receita do cluster 1" → DADOS (somar receita_12m dos clientes cluster_id=1)
- "quantos clientes premium" → DADOS (contar clientes cluster_id=1)
- "olá" → CHAT GERAL
- "como funciona" → CHAT GERAL

RESPONDA EM JSON:
{{
  "needs_data_analysis": true/false,
  "intent_type": "general_chat" | "data_analysis",
  "confidence": 0.0-1.0,
  "sql_instruction": {{
    "task_description": "Descrição específica da análise",
    "expected_data": "Que dados espera",
    "business_context": "Contexto relevante"
  }},
  "reasoning": "Por que tomou essa decisão"
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.3
            )
            
            response_text = response.choices[0].message.content.strip()
            
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    return json.loads(json_str)
                else:
                    raise ValueError("JSON não encontrado")
            except:
                return self.fallback_intent_analysis(user_message)
                
        except Exception as e:
            return self.fallback_intent_analysis(user_message)
    
    def fallback_intent_analysis(self, user_message: str) -> Dict[str, Any]:
        """Fallback para análise de intenção"""
        message_lower = user_message.lower()
        
        data_keywords = [
            "quantos", "quanto", "total", "soma", "média", "margem", "receita", "vendas",
            "mostre", "liste", "dados", "relatório", "análise", "performance", "crescimento",
            "clientes", "pedidos", "clusters", "top", "ranking", "último", "recente", "cluster"
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
                    "business_context": "Análise de negócio solicitada"
                },
                "reasoning": "Detectadas palavras-chave de dados"
            }
        else:
            return {
                "needs_data_analysis": False,
                "intent_type": "general_chat",
                "confidence": 0.8,
                "reasoning": "Conversa geral"
            }
    
    async def handle_data_analysis(self, user_message: str, intent_analysis: Dict, session_id: str) -> tuple:
        """Coordena análise de dados"""
        try:
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
            
            sql_response = await self.sql_agent.process_instruction(sql_instruction)
            
            if sql_response.success:
                natural_response = await self.convert_json_to_natural_language(
                    user_message, sql_response.data, sql_response.metadata
                )
                return natural_response, ["sql_agent"], ["Análise LLM", "Consulta SQL", "Conversão natural"]
            else:
                return f"❌ Erro na consulta: {sql_response.error}", ["sql_agent"], ["Análise LLM", "Erro SQL"]
                
        except Exception as e:
            return f"❌ Erro na análise: {str(e)}", ["error"], ["Erro no processamento"]
    
    async def convert_json_to_natural_language(self, user_question: str, data: Any, metadata: Dict) -> str:
        """Converte JSON em resposta natural"""
        try:
            prompt = f"""Converta os dados em resposta natural e insights de negócio.

PERGUNTA: "{user_question}"

DADOS:
{json.dumps(data, indent=2, ensure_ascii=False)}

METADADOS:
- Registros: {metadata.get('row_count', 0)}
- Tempo: {metadata.get('execution_time', 0):.2f}s
- Tabela: {metadata.get('query_info', {}).get('table', 'N/A')}
- Cluster: {metadata.get('query_info', {}).get('cluster_id', 'N/A')}

CONTEXTO:
• Cluster 1 = Premium (receita >R$100k)
• Cluster 2 = Alto valor (R$50k-100k)  
• Cluster 3 = Médio (R$20k-50k)
• Cluster 4 = Baixo (<R$20k)
• Cluster 5 = Novos clientes
• Margem saudável: 20-30%

FORNEÇA:
1. 📊 Interpretação dos números
2. 💡 Insights de negócio
3. 🎯 Oportunidades
4. 📈 Recomendações

Máximo 250 palavras, use emojis estrategicamente."""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            if isinstance(data, list) and len(data) > 0:
                return f"📊 Encontrei {len(data)} registros. Dados: {str(data[:2])}..."
            else:
                return f"📊 Análise concluída: {str(data)}"
    
    async def handle_general_chat(self, user_message: str, history: List) -> str:
        """Conversa geral"""
        try:
            messages = [
                {
                    "role": "system",
                    "content": """Você é um assistente de análise de dados de e-commerce.

PERSONALIDADE: Profissional, amigável, especialista em dados
CAPACIDADES: Análise de clientes, receita, margem, clusters, pedidos
ESTILO: Português brasileiro, educado, máximo 150 palavras, emojis ocasionais"""
                }
            ]
            
            for msg in history[-4:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            messages.append({"role": "user", "content": user_message})
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return "Olá! 😊 Sou seu assistente de análise de dados. Posso ajudar com análises de clientes, receita, margem e clusters. Como posso ajudar?"
    
    async def process_user_message(self, user_message: str, session_id: str) -> OrchestratorResponse:
        """Método principal do Orquestrador"""
        try:
            history = self.get_conversation_history(session_id)
            self.add_to_conversation(session_id, "user", user_message)
            
            intent_analysis = await self.analyze_user_intent_with_llm(user_message, history)
            
            if intent_analysis.get("needs_data_analysis", False):
                response_text, agents_used, processing_steps = await self.handle_data_analysis(
                    user_message, intent_analysis, session_id
                )
            else:
                response_text = await self.handle_general_chat(user_message, history)
                agents_used = ["orchestrator"]
                processing_steps = ["Análise LLM", "Resposta conversacional"]
            
            self.add_to_conversation(session_id, "assistant", response_text)
            
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
# INSTÂNCIA GLOBAL
# ================================

orchestrator = OrchestratorAgent()

# ================================
# ENDPOINTS
# ================================

@app.get("/")
def home():
    return {
        "message": "🤖 Sistema de Agentes Orquestradores - SQL CORRIGIDO",
        "version": "3.2 - SQL Fixed",
        "status": "online",
        "fixes": ["Lógica SQL corrigida", "Sintaxe PostgREST adequada", "Mapeamento cluster melhorado"]
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "sql_logic": "fixed",
        "postgrest_syntax": "correct",
        "cluster_mapping": "improved",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "supabase_configured": bool(os.getenv("SUPABASE_URL")) and bool(os.getenv("SUPABASE_ANON_KEY")),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/webhook/lovable")
async def lovable_webhook(request: Request):
    """Endpoint principal com SQL corrigido"""
    try:
        print(f"🔍 Headers: {dict(request.headers)}")
        
        payload_data = {}
        
        try:
            if request.headers.get("content-type", "").startswith("application/json"):
                raw_body = await request.body()
                print(f"🔍 JSON body: {raw_body.decode()}")
                payload_data = json.loads(raw_body.decode())
            else:
                form_data = await request.form()
                payload_data = dict(form_data)
                print(f"🔍 Form data: {payload_data}")
        except Exception as e:
            print(f"❌ Erro payload: {e}")
            return {
                "response": "❌ Erro ao processar mensagem",
                "session_id": "error",
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            }
        
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
        
        print(f"🔍 Processando - Mensagem: '{user_message}', Sessão: '{session_id}'")
        
        if not os.getenv("OPENAI_API_KEY"):
            return {
                "response": "⚠️ OpenAI não configurada",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "OpenAI not configured"
            }
        
        print(f"🚀 Enviando para orquestrador...")
        result = await orchestrator.process_user_message(user_message, session_id)
        
        print(f"✅ Resposta: {result.response[:100]}...")
        
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
            "response": f"❌ Erro crítico: {str(e)}",
            "session_id": "error",
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "error": str(e)
        }

@app.options("/webhook/lovable")
async def options_webhook():
    return {"status": "ok"}

@app.get("/debug/sql-test")
async def debug_sql_test():
    """Debug: testar lógica SQL corrigida"""
    try:
        sql_agent = SQLAgent()
        
        # Teste 1: Receita cluster 1
        instruction1 = AgentInstruction(
            agent_type="sql_agent",
            task_description="Calcular receita total do cluster 1 (premium)",
            user_question="Quanto de receita o cluster 1 fez?",
            context={},
            session_id="debug"
        )
        
        result1 = await sql_agent.process_instruction(instruction1)
        
        # Teste 2: Contagem cluster 1
        instruction2 = AgentInstruction(
            agent_type="sql_agent", 
            task_description="Contar clientes do cluster premium",
            user_question="Quantos clientes premium temos?",
            context={},
            session_id="debug"
        )
        
        result2 = await sql_agent.process_instruction(instruction2)
        
        return {
            "test_1_receita_cluster_1": {
                "success": result1.success,
                "data": result1.data,
                "error": result1.error,
                "metadata": result1.metadata
            },
            "test_2_count_cluster_1": {
                "success": result2.success,
                "data": result2.data,
                "error": result2.error,
                "metadata": result2.metadata
            }
        }
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
