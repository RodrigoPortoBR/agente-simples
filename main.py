"""
Sistema de Agentes Orquestradores - VERSÃO FINAL CORRIGIDA
Problemas de agregação SQL no Supabase resolvidos
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

app = FastAPI(title="Sistema de Agentes Orquestradores - FINAL CORRIGIDO")

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
# AGENTE SQL CORRIGIDO - VERSÃO FINAL
# ================================

class SQLAgent:
    """Agente SQL com problemas de agregação RESOLVIDOS"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # Estratégias de consulta corrigidas
        self.query_strategies = {
            # Receita por cluster - CORRIGIDO
            "receita_cluster": {
                "keywords": ["receita", "faturamento", "vendas", "cluster"],
                "method": "aggregate_manual",  # Fazer agregação manual
                "table": "clientes",
                "field": "receita_12m",
                "filter_field": "cluster_id"
            },
            # Contagem por cluster - CORRIGIDO
            "count_cluster": {
                "keywords": ["quantos", "numero", "count", "cluster"],
                "method": "count_manual",  # Contar manualmente
                "table": "clientes",
                "filter_field": "cluster_id"
            },
            # Margem média por cluster - CORRIGIDO
            "margem_cluster": {
                "keywords": ["margem", "cluster"],
                "method": "aggregate_manual",
                "table": "clientes",
                "field": "gm_12m",
                "filter_field": "cluster_id"
            },
            # Top clientes - FUNCIONA
            "top_clientes": {
                "keywords": ["top", "melhor", "maior", "cliente"],
                "method": "select_ordered",
                "table": "clientes",
                "fields": "nome,receita_12m,gm_12m,cluster_id",
                "order": "receita_12m.desc"
            },
            # Dados de cluster - FUNCIONA
            "info_clusters": {
                "keywords": ["cluster", "segmento", "grupo"],
                "method": "select_simple",
                "table": "clusters",
                "fields": "*"
            }
        }
    
    def analyze_data_request_final(self, instruction: AgentInstruction) -> Dict[str, Any]:
        """Análise final com estratégias corrigidas"""
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
        
        # Detectar estratégia de consulta
        strategy_name = None
        for name, strategy in self.query_strategies.items():
            keywords = strategy["keywords"]
            # Verificar se pelo menos 2 keywords estão presentes
            matches = sum(1 for keyword in keywords if keyword in combined_text)
            if matches >= 2:
                strategy_name = name
                break
            elif matches >= 1 and not strategy_name:
                strategy_name = name
        
        # Fallback baseado em cluster + tipo
        if not strategy_name and cluster_id:
            if any(word in combined_text for word in ["receita", "faturamento", "vendas"]):
                strategy_name = "receita_cluster"
            elif any(word in combined_text for word in ["quantos", "count", "numero"]):
                strategy_name = "count_cluster"
            elif any(word in combined_text for word in ["margem"]):
                strategy_name = "margem_cluster"
            else:
                strategy_name = "top_clientes"
        
        # Default
        if not strategy_name:
            strategy_name = "top_clientes"
        
        strategy = self.query_strategies[strategy_name]
        
        # Detectar limite para consultas ordenadas
        limit = None
        numbers = re.findall(r'\\d+', combined_text)
        if numbers and any(word in combined_text for word in ["top", "primeiro", "ultimos"]):
            limit = int(numbers[0])
        elif strategy["method"] in ["select_ordered", "select_simple"]:
            limit = 10
        
        result = {
            "strategy_name": strategy_name,
            "method": strategy["method"],
            "table": strategy["table"],
            "cluster_id": cluster_id,
            "limit": limit,
            "strategy_config": strategy
        }
        
        print(f"✅ Estratégia selecionada: {result}")
        return result
    
    async def execute_query_final(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Execução final com métodos corrigidos"""
        try:
            start_time = datetime.now()
            method = analysis["method"]
            table = analysis["table"]
            cluster_id = analysis.get("cluster_id")
            strategy_config = analysis["strategy_config"]
            
            print(f"🚀 Executando método: {method}")
            
            if method == "aggregate_manual":
                # CORREÇÃO: Buscar dados e agregar manualmente
                return await self._aggregate_manual(table, strategy_config, cluster_id, start_time)
            
            elif method == "count_manual":
                # CORREÇÃO: Buscar dados e contar manualmente
                return await self._count_manual(table, strategy_config, cluster_id, start_time)
            
            elif method == "select_ordered":
                # Consulta ordenada (funciona normalmente)
                return await self._select_ordered(table, strategy_config, cluster_id, analysis.get("limit"), start_time)
            
            elif method == "select_simple":
                # Consulta simples (funciona normalmente)
                return await self._select_simple(table, strategy_config, start_time)
            
            else:
                return {
                    "success": False,
                    "error": f"Método não implementado: {method}",
                    "data": None
                }
                
        except Exception as e:
            print(f"❌ Erro na execução: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    async def _aggregate_manual(self, table: str, config: Dict, cluster_id: str, start_time: datetime) -> Dict[str, Any]:
        """Agregação manual - SOLUÇÃO para problemas do Supabase"""
        try:
            # Construir URL para buscar dados brutos
            url = f"{self.supabase_url}/rest/v1/{table}"
            params = []
            
            # Selecionar campo necessário
            field = config["field"]
            params.append(f"select={field}")
            
            # Adicionar filtro de cluster se especificado
            if cluster_id and config.get("filter_field"):
                params.append(f"{config['filter_field']}=eq.{cluster_id}")
            
            # Construir URL final
            if params:
                url += "?" + "&".join(params)
            
            print(f"🔗 URL agregação manual: {url}")
            
            # Executar requisição
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if response.status_code == 200:
                    raw_data = response.json()
                    
                    if not raw_data:
                        return {
                            "success": True,
                            "data": [{"total": 0, "count": 0, "average": 0}],
                            "row_count": 1,
                            "execution_time": execution_time,
                            "query_info": {
                                "method": "aggregate_manual",
                                "table": table,
                                "field": field,
                                "cluster_id": cluster_id,
                                "raw_count": 0
                            }
                        }
                    
                    # Fazer agregação manual
                    values = [item[field] for item in raw_data if item.get(field) is not None]
                    
                    if values:
                        total = sum(values)
                        count = len(values)
                        average = total / count if count > 0 else 0
                    else:
                        total = count = average = 0
                    
                    # Resultado agregado
                    aggregated_data = [{
                        "total": total,
                        "count": count,
                        "average": round(average, 2),
                        "field": field,
                        "cluster_id": cluster_id
                    }]
                    
                    return {
                        "success": True,
                        "data": aggregated_data,
                        "row_count": 1,
                        "execution_time": execution_time,
                        "query_info": {
                            "method": "aggregate_manual",
                            "table": table,
                            "field": field,
                            "cluster_id": cluster_id,
                            "raw_count": len(raw_data),
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
                "error": f"Erro na agregação manual: {str(e)}",
                "data": None
            }
    
    async def _count_manual(self, table: str, config: Dict, cluster_id: str, start_time: datetime) -> Dict[str, Any]:
        """Contagem manual - SOLUÇÃO para problemas do Supabase"""
        try:
            # Construir URL para buscar dados
            url = f"{self.supabase_url}/rest/v1/{table}"
            params = ["select=id"]  # Só precisamos do ID para contar
            
            # Adicionar filtro de cluster se especificado
            if cluster_id and config.get("filter_field"):
                params.append(f"{config['filter_field']}=eq.{cluster_id}")
            
            # Construir URL final
            if params:
                url += "?" + "&".join(params)
            
            print(f"🔗 URL contagem manual: {url}")
            
            # Executar requisição
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if response.status_code == 200:
                    raw_data = response.json()
                    count = len(raw_data)
                    
                    # Resultado da contagem
                    count_data = [{
                        "count": count,
                        "cluster_id": cluster_id,
                        "table": table
                    }]
                    
                    return {
                        "success": True,
                        "data": count_data,
                        "row_count": 1,
                        "execution_time": execution_time,
                        "query_info": {
                            "method": "count_manual",
                            "table": table,
                            "cluster_id": cluster_id,
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
                "error": f"Erro na contagem manual: {str(e)}",
                "data": None
            }
    
    async def _select_ordered(self, table: str, config: Dict, cluster_id: str, limit: int, start_time: datetime) -> Dict[str, Any]:
        """Consulta ordenada (funciona normalmente)"""
        try:
            url = f"{self.supabase_url}/rest/v1/{table}"
            params = []
            
            # Campos a selecionar
            if config.get("fields"):
                params.append(f"select={config['fields']}")
            
            # Filtro de cluster
            if cluster_id and config.get("filter_field"):
                params.append(f"{config['filter_field']}=eq.{cluster_id}")
            
            # Ordenação
            if config.get("order"):
                params.append(f"order={config['order']}")
            
            # Limite
            if limit:
                params.append(f"limit={limit}")
            
            # Construir URL final
            if params:
                url += "?" + "&".join(params)
            
            print(f"🔗 URL select ordenado: {url}")
            
            # Executar requisição
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "success": True,
                        "data": data,
                        "row_count": len(data),
                        "execution_time": execution_time,
                        "query_info": {
                            "method": "select_ordered",
                            "table": table,
                            "cluster_id": cluster_id,
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
                "error": f"Erro no select ordenado: {str(e)}",
                "data": None
            }
    
    async def _select_simple(self, table: str, config: Dict, start_time: datetime) -> Dict[str, Any]:
        """Consulta simples (funciona normalmente)"""
        try:
            url = f"{self.supabase_url}/rest/v1/{table}"
            params = []
            
            # Campos a selecionar
            if config.get("fields"):
                params.append(f"select={config['fields']}")
            
            # Construir URL final
            if params:
                url += "?" + "&".join(params)
            
            print(f"🔗 URL select simples: {url}")
            
            # Executar requisição
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "success": True,
                        "data": data,
                        "row_count": len(data),
                        "execution_time": execution_time,
                        "query_info": {
                            "method": "select_simple",
                            "table": table,
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
                "error": f"Erro no select simples: {str(e)}",
                "data": None
            }
    
    async def process_instruction(self, instruction: AgentInstruction) -> AgentResponse:
        """Método principal do Agente SQL - VERSÃO FINAL"""
        try:
            print(f"🚀 SQL Agent FINAL processando: {instruction.user_question}")
            
            # 1. Analisar instrução
            analysis = self.analyze_data_request_final(instruction)
            
            # 2. Executar consulta com método corrigido
            query_result = await self.execute_query_final(analysis)
            
            # 3. Retornar resposta estruturada
            return AgentResponse(
                success=query_result["success"],
                agent_type="sql_agent_final",
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
            print(f"❌ Erro no SQL Agent FINAL: {e}")
            return AgentResponse(
                success=False,
                agent_type="sql_agent_final",
                error=str(e)
            )

# ================================
# AGENTE ORQUESTRADOR (MANTIDO)
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
                    conversation_context += f"{msg['role']}: {msg['content']}\\n"
            
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
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.3
            )
            
            llm_response = response.choices[0].message.content
            
            # Extrair JSON da resposta
            try:
                json_start = llm_response.find('{')
                json_end = llm_response.rfind('}') + 1
                json_str = llm_response[json_start:json_end]
                intent_analysis = json.loads(json_str)
            except:
                # Fallback: análise por palavras-chave
                message_lower = user_message.lower()
                data_keywords = ['quantos', 'quanto', 'total', 'receita', 'margem', 'clientes', 'cluster', 'vendas', 'dados']
                needs_data = any(keyword in message_lower for keyword in data_keywords)
                
                intent_analysis = {
                    "needs_data_analysis": needs_data,
                    "intent_type": "data_analysis" if needs_data else "general_chat",
                    "confidence": 0.7,
                    "sql_instruction": {
                        "task_description": f"Analisar dados baseado na pergunta: {user_message}",
                        "expected_data": "Dados relevantes da consulta",
                        "business_context": "Análise de negócio solicitada"
                    },
                    "reasoning": "Fallback: análise por palavras-chave"
                }
            
            return intent_analysis
            
        except Exception as e:
            print(f"❌ Erro na análise de intenção: {e}")
            return {
                "needs_data_analysis": False,
                "intent_type": "general_chat",
                "confidence": 0.5,
                "reasoning": f"Erro na análise: {str(e)}"
            }
    
    async def handle_data_analysis(self, user_message: str, intent_analysis: Dict, session_id: str) -> tuple:
        """Delegar para agente SQL e converter resposta"""
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
                return natural_response, ["sql_agent_final"], ["Análise LLM", "Consulta SQL corrigida", "Conversão natural"]
            else:
                return f"❌ Erro na consulta: {sql_response.error}", ["sql_agent_final"], ["Análise LLM", "Erro SQL"]
                
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
- Método: {metadata.get('query_info', {}).get('method', 'N/A')}
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
                model="gpt-4.1-mini",
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
                model="gpt-4.1-mini",
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
        "message": "🤖 Sistema de Agentes Orquestradores - VERSÃO FINAL CORRIGIDA",
        "version": "4.0 - FINAL FIXED",
        "status": "online",
        "fixes": [
            "✅ Agregação manual implementada",
            "✅ Contagem manual implementada", 
            "✅ Problemas Supabase resolvidos",
            "✅ Métodos de consulta corrigidos"
        ]
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "sql_aggregation": "fixed_manual",
        "supabase_issues": "resolved",
        "query_methods": "corrected",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "supabase_configured": bool(os.getenv("SUPABASE_URL")) and bool(os.getenv("SUPABASE_ANON_KEY")),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/webhook/lovable")
async def lovable_webhook(request: Request):
    """Endpoint principal - VERSÃO FINAL CORRIGIDA"""
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
        
        print(f"🚀 Enviando para orquestrador FINAL...")
        result = await orchestrator.process_user_message(user_message, session_id)
        
        print(f"✅ Resposta FINAL: {result.response[:100]}...")
        
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

@app.get("/debug/sql-test-final")
async def debug_sql_test_final():
    """Debug: testar correções finais"""
    try:
        sql_agent = SQLAgent()
        
        # Teste 1: Receita cluster 1 (agregação manual)
        instruction1 = AgentInstruction(
            agent_type="sql_agent",
            task_description="Calcular receita total do cluster 1 (premium) usando agregação manual",
            user_question="Quanto de receita o cluster 1 fez?",
            context={},
            session_id="debug"
        )
        
        result1 = await sql_agent.process_instruction(instruction1)
        
        # Teste 2: Contagem cluster 1 (contagem manual)
        instruction2 = AgentInstruction(
            agent_type="sql_agent", 
            task_description="Contar clientes do cluster premium usando contagem manual",
            user_question="Quantos clientes premium temos?",
            context={},
            session_id="debug"
        )
        
        result2 = await sql_agent.process_instruction(instruction2)
        
        # Teste 3: Top clientes (select ordenado - funciona normalmente)
        instruction3 = AgentInstruction(
            agent_type="sql_agent",
            task_description="Listar top 5 clientes por receita",
            user_question="Top 5 clientes por receita",
            context={},
            session_id="debug"
        )
        
        result3 = await sql_agent.process_instruction(instruction3)
        
        return {
            "test_1_receita_cluster_1_manual": {
                "success": result1.success,
                "data": result1.data,
                "error": result1.error,
                "metadata": result1.metadata
            },
            "test_2_count_cluster_1_manual": {
                "success": result2.success,
                "data": result2.data,
                "error": result2.error,
                "metadata": result2.metadata
            },
            "test_3_top_clientes_ordenado": {
                "success": result3.success,
                "data": result3.data,
                "error": result3.error,
                "metadata": result3.metadata
            },
            "summary": {
                "aggregation_fixed": result1.success,
                "counting_fixed": result2.success,
                "ordering_works": result3.success,
                "all_methods_working": result1.success and result2.success and result3.success
            }
        }
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
