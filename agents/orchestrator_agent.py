"""
Orchestrator Agent - REFATORADO PARA DADOS DE NEGÓCIO
CAMADA 1: Interface única com o usuário - FOCO EM ANÁLISE DE DADOS
"""
import openai
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from models import (
    OrchestratorResponse, 
    AgentInstruction, 
    AgentType, 
    MessageRole,
    IntentAnalysis,
    IntentType,
    SQLQueryRequest
)
from config import settings
from services.memory_service import MemoryService
from agents.sql_agent import SQLAgent

class OrchestratorAgent:
    """
    Agente Orquestrador - Especialista em Análise de Dados de E-commerce
    
    RESPONSABILIDADES:
    - Conversar com usuário sobre dados de negócio
    - Identificar quando precisa consultar banco de dados
    - Delegar análises ao SQL Agent
    - Converter resultados JSON em linguagem natural
    - NÃO analisar conversas - FOCAR EM DADOS DE CLIENTES
    """
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.memory = MemoryService()
        self.sql_agent = SQLAgent()
        
        # System prompt FOCADO EM DADOS DE NEGÓCIO
        self.system_prompt = """Você é um Analista de Dados de E-commerce especializado.

SUA FUNÇÃO:
- Analisar dados de CLIENTES, RECEITA, MARGEM e CLUSTERS
- Responder perguntas sobre NEGÓCIO e PERFORMANCE
- Fornecer INSIGHTS acionáveis baseados em dados

DADOS DISPONÍVEIS (Lovable Cloud - Supabase):

📊 CLIENTES (tabela: clientes)
- CPF, cluster, pedidos_12m, recencia_dias
- receita_bruta_12m, receita_liquida_12m
- qtde_produtos, cmv_12m, desconto
- gm_12m (margem bruta), gm_pct_12m
- mcc (margem contribuição), mcc_pct
- despesas

🎯 CLUSTERS (tabela: clusters)
- id, label (nome do cluster)
- gm_total, gm_pct_medio
- clientes (quantidade), freq_media, recencia_media
- gm_cv (volatilidade), tendencia

📈 SÉRIES TEMPORAIS (tabela: monthly_series)
- month (YYYY-MM)
- receita_bruta, receita_liquida, cmv, margem_bruta
- clusters (dados JSON por mês)

🛒 PEDIDOS (tabela: pedidos)
- pedido_id, cliente_id, data
- receita_bruta, margem_bruta, categoria

CLUSTERS EXISTENTES:
1. Premium - Clientes top de receita
2. Alto Valor - Bom faturamento
3. Médio - Performance regular
4. Baixo - Menor faturamento
5. Novos - Clientes recentes

REGRAS:
- Sempre que usuário perguntar sobre NÚMEROS, DADOS, MÉTRICAS → buscar no banco
- Conversa geral → responder diretamente
- Usar dados reais para dar insights
- Focar em ações práticas

ESTILO:
- Objetivo e direto
- Máximo 200 palavras
- Use emojis estrategicamente (📊 💰 📈 🎯 💡)
- Destaque números importantes
- Português brasileiro"""
    
    async def process_user_message(
        self, 
        user_message: str, 
        session_id: str
    ) -> OrchestratorResponse:
        """
        Processa mensagem do usuário (método principal)
        
        Args:
            user_message: Mensagem do usuário
            session_id: ID da sessão
        
        Returns:
            OrchestratorResponse com resposta final
        """
        try:
            processing_steps = []
            agents_used = [AgentType.ORCHESTRATOR]
            
            # 1. Salvar mensagem do usuário na memória
            await self.memory.add_message(
                session_id=session_id,
                role=MessageRole.USER,
                content=user_message
            )
            processing_steps.append("💾 Mensagem salva")
            
            # 2. Recuperar contexto recente (últimas mensagens)
            context_messages = await self.memory.get_recent_context(
                session_id=session_id,
                num_messages=6  # Reduzido para economizar tokens
            )
            processing_steps.append(f"📚 Contexto: {len(context_messages)} msgs")
            
            # 3. Analisar intenção - FOCO EM DADOS DE NEGÓCIO
            intent = await self._analyze_business_intent(user_message, context_messages)
            processing_steps.append(f"🔍 Intenção: {intent.intent_type.value}")
            
            # 4. Processar baseado na intenção
            if intent.needs_data_analysis and intent.requires_agent == AgentType.SQL:
                # Consultar dados de negócio no banco
                response_text = await self._handle_business_data_request(
                    user_message=user_message,
                    intent=intent,
                    session_id=session_id,
                    processing_steps=processing_steps
                )
                agents_used.append(AgentType.SQL)
            else:
                # Conversa geral sobre negócio
                response_text = await self._handle_business_chat(
                    user_message=user_message,
                    context_messages=context_messages
                )
                processing_steps.append("💬 Chat de negócio")
            
            # 5. Salvar resposta
            await self.memory.add_message(
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=response_text,
                metadata={
                    "agents_used": [a.value for a in agents_used],
                    "intent_type": intent.intent_type.value
                }
            )
            processing_steps.append("💾 Resposta salva")
            
            return OrchestratorResponse(
                response=response_text,
                session_id=session_id,
                timestamp=datetime.now(),
                success=True,
                agents_used=agents_used,
                processing_steps=processing_steps,
                metadata={
                    "intent_confidence": intent.confidence,
                    "intent_type": intent.intent_type.value
                }
            )
            
        except Exception as e:
            print(f"❌ Erro no Orchestrator: {e}")
            
            error_message = (
                "Desculpe, encontrei um problema ao processar sua solicitação. "
                "Pode reformular sua pergunta sobre os dados? 🤔"
            )
            
            await self.memory.add_message(
                session_id=session_id,
                role=MessageRole.ASSISTANT,
                content=error_message,
                metadata={"error": str(e)}
            )
            
            return OrchestratorResponse(
                response=error_message,
                session_id=session_id,
                timestamp=datetime.now(),
                success=False,
                agents_used=[AgentType.ERROR],
                processing_steps=[f"❌ Erro: {str(e)}"]
            )
    
    async def _analyze_business_intent(
        self,
        user_message: str,
        context_messages: List[Dict[str, str]]
    ) -> IntentAnalysis:
        """
        Analisa intenção do usuário - FOCO EM DADOS DE NEGÓCIO
        
        Args:
            user_message: Mensagem atual do usuário
            context_messages: Mensagens recentes
        
        Returns:
            IntentAnalysis com decisão estruturada
        """
        try:
            # Construir contexto recente
            conversation_context = ""
            if context_messages:
                recent = context_messages[-3:]  # Últimas 3 mensagens
                for msg in recent:
                    conversation_context += f"{msg['role']}: {msg['content']}\n"
            
            prompt = f"""Analise a pergunta do usuário e determine se precisa CONSULTAR DADOS DO BANCO.

CONTEXTO RECENTE:
{conversation_context}

PERGUNTA DO USUÁRIO: "{user_message}"

DADOS DISPONÍVEIS NO BANCO (Lovable Cloud):
• clientes: receita_bruta_12m, gm_12m, mcc, cluster, pedidos_12m, recencia_dias, etc
• clusters: label, gm_total, gm_pct_medio, clientes, freq_media, tendencia
• monthly_series: receita_bruta, margem_bruta por mês
• pedidos: pedido_id, cliente_id, receita_bruta, margem_bruta, categoria

CLUSTERS:
1=Premium, 2=Alto, 3=Médio, 4=Baixo, 5=Novos

EXEMPLOS DE ANÁLISE:

✅ PRECISA CONSULTAR BANCO (data_analysis):
- "Qual a receita do cluster premium?" → SELECT SUM(receita_bruta_12m) FROM clientes WHERE cluster=1
- "Quantos clientes temos?" → SELECT COUNT(*) FROM clientes
- "Top 10 clientes por margem" → SELECT * FROM clientes ORDER BY gm_12m DESC LIMIT 10
- "Receita do último mês" → SELECT receita_bruta FROM monthly_series ORDER BY month DESC LIMIT 1
- "Clientes do cluster 2" → SELECT * FROM clientes WHERE cluster=2

❌ NÃO PRECISA BANCO (general_chat):
- "Olá" / "Oi" / "Tudo bem?"
- "O que você pode fazer?"
- "Explica o que é cluster"
- "Como funciona a margem?"
- "O que significa MCC?"

RESPONDA EM JSON:
{{
  "intent_type": "data_analysis" | "general_chat",
  "confidence": 0.0-1.0,
  "needs_data_analysis": true/false,
  "requires_agent": "sql_agent" | null,
  "extracted_parameters": {{
    "query_type": "aggregate" | "count" | "select" | "filter",
    "table": "clientes" | "clusters" | "pedidos" | "monthly_series",
    "filters": {{"cluster": 1}},
    "fields": ["receita_bruta_12m", "gm_12m"],
    "aggregation": {{"receita_bruta_12m": "sum"}},
    "order_by": "receita_bruta_12m.desc",
    "limit": 10
  }},
  "reasoning": "Breve explicação"
}}

REGRAS:
- Se pergunta sobre NÚMEROS, DADOS, MÉTRICAS → data_analysis
- Se saudação, explicação conceitual → general_chat
- Extraia filtros: cluster, período, categoria
- Identifique campos necessários
- Defina tipo de agregação (sum, avg, count, max, min)"""

            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.2
            )
            
            llm_response = response.choices[0].message.content
            
            # Extrair JSON
            json_start = llm_response.find('{')
            json_end = llm_response.rfind('}') + 1
            json_str = llm_response[json_start:json_end]
            intent_data = json.loads(json_str)
            
            return IntentAnalysis(
                intent_type=IntentType(intent_data.get("intent_type", "general_chat")),
                confidence=intent_data.get("confidence", 0.7),
                needs_data_analysis=intent_data.get("needs_data_analysis", False),
                requires_agent=(
                    AgentType.SQL if intent_data.get("requires_agent") == "sql_agent" 
                    else None
                ),
                extracted_parameters=intent_data.get("extracted_parameters", {}),
                reasoning=intent_data.get("reasoning", "")
            )
            
        except Exception as e:
            print(f"⚠️ Erro na análise, usando fallback: {e}")
            
            # Fallback: análise por keywords de NEGÓCIO
            message_lower = user_message.lower()
            business_keywords = [
                'receita', 'margem', 'cliente', 'cluster', 'vendas',
                'faturamento', 'lucro', 'mcc', 'pedido', 'quanto',
                'quantos', 'total', 'média', 'top', 'melhor', 'pior',
                'crescimento', 'tendência', 'performance', 'dados'
            ]
            
            needs_data = any(keyword in message_lower for keyword in business_keywords)
            
            return IntentAnalysis(
                intent_type=IntentType.DATA_ANALYSIS if needs_data else IntentType.GENERAL_CHAT,
                confidence=0.6,
                needs_data_analysis=needs_data,
                requires_agent=AgentType.SQL if needs_data else None,
                extracted_parameters={},
                reasoning="Fallback: análise por keywords de negócio"
            )
    
    async def _handle_business_data_request(
        self,
        user_message: str,
        intent: IntentAnalysis,
        session_id: str,
        processing_steps: List[str]
    ) -> str:
        """
        Processa requisição de DADOS DE NEGÓCIO
        
        Args:
            user_message: Pergunta do usuário
            intent: Análise de intenção
            session_id: ID da sessão
            processing_steps: Lista de passos
        
        Returns:
            Resposta em linguagem natural
        """
        try:
            # Criar instrução estruturada para SQL Agent
            sql_instruction = AgentInstruction(
                agent_type=AgentType.SQL,
                task_description=f"Consultar dados de negócio: {user_message}",
                parameters=intent.extracted_parameters,
                context={
                    "user_question": user_message,
                    "intent_reasoning": intent.reasoning
                },
                session_id=session_id
            )
            
            processing_steps.append("📤 Consultando banco de dados")
            
            # Delegar para SQL Agent
            sql_response = await self.sql_agent.process_instruction(sql_instruction)
            
            if sql_response.success:
                processing_steps.append(
                    f"✅ Dados obtidos ({sql_response.metadata.get('row_count', 0)} registros)"
                )
                
                # Converter JSON em linguagem natural COM FOCO EM NEGÓCIO
                natural_response = await self._convert_business_data_to_natural(
                    user_question=user_message,
                    data=sql_response.data,
                    metadata=sql_response.metadata
                )
                
                processing_steps.append("🗣️ Resposta formatada")
                
                return natural_response
            else:
                processing_steps.append(f"❌ Erro: {sql_response.error}")
                
                return (
                    f"Não consegui obter os dados solicitados. "
                    f"Pode reformular sua pergunta sobre clientes, receita ou clusters? 😕"
                )
                
        except Exception as e:
            processing_steps.append(f"❌ Erro: {str(e)}")
            
            return (
                "Desculpe, encontrei um problema ao buscar os dados. "
                "Pode tentar perguntar de outra forma? 🤔"
            )
    
    async def _convert_business_data_to_natural(
        self,
        user_question: str,
        data: Optional[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Converte dados de NEGÓCIO em linguagem natural com INSIGHTS
        
        Args:
            user_question: Pergunta original
            data: Dados retornados
            metadata: Metadados da query
        
        Returns:
            Resposta formatada em linguagem natural
        """
        try:
            data_context = json.dumps(data, indent=2, ensure_ascii=False) if data else "{}"
            
            prompt = f"""Converta os dados de negócio em resposta natural com INSIGHTS ACIONÁVEIS.

PERGUNTA: "{user_question}"

DADOS OBTIDOS:
{data_context}

METADADOS:
- Registros: {metadata.get('row_count', 0)}
- Tempo: {metadata.get('execution_time', 0):.2f}s
- Tabela: {metadata.get('query_info', {}).get('table', 'N/A')}

CONTEXTO DE NEGÓCIO:
• Clusters: 1=Premium, 2=Alto, 3=Médio, 4=Baixo, 5=Novos
• Margem saudável: 20-30% (gm_pct_12m)
• MCC positivo = cliente rentável
• Recencia baixa = cliente ativo
• Frequência alta = cliente fiel

SUA RESPOSTA DEVE TER:
1. 📊 **NÚMEROS PRINCIPAIS** - Destaque os valores mais importantes
2. 💡 **INSIGHT** - O que esses números significam para o negócio?
3. 🎯 **AÇÃO SUGERIDA** - O que fazer com essa informação?

FORMATO:
- Máximo 200 palavras
- Use emojis estrategicamente
- Destaque números com negrito ou formatação
- Seja objetivo e direto
- Foque em AÇÕES PRÁTICAS

EXEMPLO:
"📊 O Cluster Premium tem **R$ 2,5 milhões** em receita (45% do total).

💡 São apenas 150 clientes, mas representam quase metade do faturamento! A margem média é de 28%, bem saudável.

🎯 **Ação recomendada**: Criar programa VIP para manter esses clientes engajados e aumentar frequência de compra."

IMPORTANTE: Não mencione termos técnicos como "query", "JSON", "banco de dados", etc."""

            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"⚠️ Erro na conversão, usando fallback: {e}")
            
            # Fallback simples
            if data and isinstance(data, dict):
                results = data.get("results", [])
                if results and len(results) > 0:
                    return (
                        f"📊 Encontrei os dados solicitados:\n\n"
                        f"```\n{json.dumps(results[0], indent=2, ensure_ascii=False)}\n```\n\n"
                        f"Total de {metadata.get('row_count', 0)} registros."
                    )
            
            return "📊 Dados encontrados, mas tive dificuldade em formatá-los. Pode reformular?"
    
    async def _handle_business_chat(
        self,
        user_message: str,
        context_messages: List[Dict[str, str]]
    ) -> str:
        """
        Responde conversa geral sobre NEGÓCIO (sem consultar banco)
        
        Args:
            user_message: Mensagem do usuário
            context_messages: Contexto
        
        Returns:
            Resposta conversacional
        """
        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Contexto recente
            messages.extend(context_messages[-4:])
            
            # Mensagem atual
            messages.append({"role": "user", "content": user_message})
            
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"⚠️ Erro na conversa: {e}")
            
            return (
                "Olá! 😊 Sou seu analista de dados de e-commerce. "
                "Posso ajudar com análises de clientes, receita, margem e clusters. "
                "Pergunte sobre seus dados de negócio!"
            )
