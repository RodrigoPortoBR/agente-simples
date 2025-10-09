"""
Orchestrator Agent - Assistente de IA para Lovable Cloud
Especializado em análises de negócios e conversas naturais
"""
from typing import Any, Dict
import json
from datetime import datetime

class OrchestratorAgent:
    def __init__(self, config: Any = None):
        self.config = config
        self.sql_agent = None
    
    def start(self):
        return "started"
    
    async def process_user_message(self, message: str, session_id: str) -> str:
        """
        Método principal - Assistente de IA para Lovable Cloud
        Conversa naturalmente OU analisa dados de negócios
        """
        try:
            print(f"🧠 Orquestrador Lovable Cloud: '{message}' (sessão: {session_id})")
            
            # Análise de intenção - detecta consultas de negócios
            needs_business_analysis = self._analyze_business_intent(message)
            
            if needs_business_analysis:
                print(f"📊 Delegando análise de negócios para SQL Agent")
                return await self._delegate_to_sql_agent(message, session_id)
            else:
                print(f"💬 Respondendo conversa natural")
                return self._respond_naturally(message, session_id)
                
        except Exception as e:
            print(f"❌ Erro no Orquestrador: {e}")
            return f"Desculpe, ocorreu um erro interno. Tente novamente em alguns instantes."

    def _analyze_business_intent(self, message: str) -> bool:
        """
        Analisa se a mensagem é sobre dados de negócios do Lovable Cloud
        Retorna True APENAS para consultas sobre clientes, pedidos, receita, etc.
        """
        message_lower = message.lower()
        
        # Palavras-chave de NEGÓCIOS do Lovable Cloud
        business_keywords = [
            # Clientes
            'quantos clientes', 'número de clientes', 'total de clientes',
            'clientes ativos', 'clientes inativos', 'novos clientes',
            'lista de clientes', 'dados dos clientes', 'informações de clientes',
            
            # Pedidos e Vendas
            'quantos pedidos', 'número de pedidos', 'total de pedidos',
            'pedidos em aberto', 'pedidos fechados', 'pedidos cancelados',
            'vendas do mês', 'vendas totais', 'faturamento',
            
            # Receita e Financeiro
            'receita', 'faturamento', 'valor total', 'receita mensal',
            'quanto faturamos', 'valor arrecadado', 'receita do período',
            'análise financeira', 'performance financeira',
            
            # Clusters e Segmentação
            'clientes premium', 'clientes básicos', 'cluster premium',
            'segmentação', 'tipos de cliente', 'categorias de cliente',
            
            # Análises e Relatórios
            'relatório', 'análise', 'dashboard', 'métricas',
            'estatísticas', 'performance', 'indicadores',
            'top clientes', 'ranking', 'maiores clientes',
            
            # Séries Temporais
            'dados mensais', 'série temporal', 'evolução mensal',
            'crescimento', 'tendência', 'histórico',
            
            # Consultas Específicas
            'dados do lovable', 'base de dados', 'informações do sistema',
            'consultar dados', 'buscar informações'
        ]
        
        # Retorna True se encontrar palavras-chave de NEGÓCIOS
        return any(keyword in message_lower for keyword in business_keywords)

    async def _delegate_to_sql_agent(self, message: str, session_id: str) -> str:
        """
        Delega análise de negócios para SQL Agent especializado
        """
        try:
            # Importar SQL Agent dinamicamente
            from .sql_agent import get_sql_agent
            
            if not self.sql_agent:
                self.sql_agent = get_sql_agent()
            
            # Chamar SQL Agent para análise de negócios
            sql_result = await self.sql_agent.process_business_query(message, session_id)
            
            # Formatar resposta de negócios
            return self._format_business_response(sql_result, message)
            
        except Exception as e:
            print(f"❌ Erro ao chamar SQL Agent: {e}")
            return "Não consegui acessar os dados do Lovable Cloud no momento. Tente novamente em alguns instantes."

    def _respond_naturally(self, message: str, session_id: str) -> str:
        """
        Responde conversas naturais - NÃO relacionadas a negócios
        """
        message_lower = message.lower()
        
        # Nome e Identidade
        if any(word in message_lower for word in ['qual seu nome', 'como você se chama', 'quem é você', 'seu nome']):
            return "Sou seu assistente de IA para análises do Lovable Cloud. Posso conversar e também analisar dados de clientes, pedidos e receita!"
        
        # Saudações
        if any(greeting in message_lower for greeting in ['olá', 'oi', 'hello', 'hi', 'bom dia', 'boa tarde', 'boa noite']):
            return "Olá! Sou seu assistente para o Lovable Cloud. Posso conversar ou ajudar com análises de negócios. Como posso ajudar?"
        
        # Como está
        if any(word in message_lower for word in ['como você está', 'tudo bem', 'como vai']):
            return "Estou ótimo e pronto para ajudar! Como posso auxiliar você hoje?"
        
        # Função e Capacidades
        if any(word in message_lower for word in ['o que você faz', 'para que serve', 'suas funções', 'capacidades']):
            return """Sou especializado em duas áreas:

💬 **Conversas**: Posso conversar naturalmente sobre diversos assuntos
📊 **Análises de Negócios**: Posso analisar dados do Lovable Cloud como:
   • Informações de clientes
   • Dados de pedidos e vendas
   • Receita e faturamento
   • Segmentação por clusters
   • Relatórios e métricas

Que tipo de ajuda você precisa?"""
        
        # Ajuda
        if any(word in message_lower for word in ['ajuda', 'help', 'como usar', 'comandos']):
            return """🆘 **Como posso ajudar:**

💬 **Para conversas**: Faça qualquer pergunta casual
📊 **Para análises**: Pergunte sobre dados do Lovable Cloud

**Exemplos de análises:**
• "Quantos clientes temos?"
• "Qual a receita do mês passado?"
• "Mostre os clientes premium"
• "Pedidos em aberto"
• "Relatório de vendas"

O que você gostaria de saber?"""
        
        # Sobre Lovable Cloud
        if any(word in message_lower for word in ['lovable cloud', 'lovable', 'plataforma', 'sistema']):
            return """☁️ **Sobre o Lovable Cloud:**

O Lovable Cloud é uma plataforma robusta com dados de:
• **Clientes** e segmentação
• **Pedidos** e transações
• **Clusters** de categorização
• **Séries temporais** mensais

Posso analisar qualquer aspecto desses dados. Que análise você gostaria de ver?"""
        
        # Agradecimentos
        if any(word in message_lower for word in ['obrigado', 'obrigada', 'thanks', 'valeu', 'brigado']):
            return "De nada! Fico feliz em ajudar com conversas ou análises do Lovable Cloud. Precisa de mais alguma coisa?"
        
        # Despedidas
        if any(word in message_lower for word in ['tchau', 'bye', 'até logo', 'falou', 'adeus']):
            return "Até logo! Foi um prazer ajudar. Volte sempre que precisar de análises ou quiser conversar!"
        
        # Tempo
        if any(word in message_lower for word in ['que horas', 'que dia', 'data hoje']):
            return f"Agora são {datetime.now().strftime('%H:%M')} do dia {datetime.now().strftime('%d/%m/%Y')}."
        
        # Piadas
        if any(word in message_lower for word in ['piada', 'conte uma piada', 'algo engraçado']):
            return "Por que os dados nunca mentem? Porque eles sempre falam a verdade... estatística! 📊😄"
        
        # Resposta genérica natural
        return f"""Interessante! Sobre "{message}", posso conversar ou, se for relacionado ao Lovable Cloud, posso analisar dados específicos.

💬 **Para conversas**: Continue perguntando o que quiser
📊 **Para análises**: Pergunte sobre clientes, pedidos, receita, etc.

Como posso ajudar você?"""

    def _format_business_response(self, sql_result: str, original_question: str) -> str:
        """
        Formata resposta de análise de negócios de forma natural
        """
        try:
            # Tentar parsear JSON do SQL Agent
            if sql_result.startswith('{'):
                data = json.loads(sql_result)
                
                # Extrair informações do JSON
                resumo = data.get('resumo', 'Análise concluída')
                insights = data.get('insights', [])
                resultado = data.get('resultado', [])
                
                # Formatar resposta baseada no tipo de consulta
                response = f"📊 **{resumo}**\n\n"
                
                # Adicionar dados se houver
                if resultado:
                    if len(resultado) <= 10:  # Mostrar dados se poucos
                        response += "**Dados encontrados:**\n"
                        for item in resultado:
                            if isinstance(item, dict):
                                response += f"• {', '.join([f'{k}: {v}' for k, v in item.items()])}\n"
                            else:
                                response += f"• {item}\n"
                        response += "\n"
                
                # Adicionar insights
                if insights:
                    response += "💡 **Insights:**\n"
                    for insight in insights:
                        response += f"• {insight}\n"
                
                response += f"\n🔍 **Consulta**: \"{original_question}\""
                response += f"\n⏱️ **Processado**: {datetime.now().strftime('%H:%M')}"
                
                return response
            
            else:
                # Se não for JSON, retornar como texto formatado
                return f"""📊 **Análise do Lovable Cloud**

{sql_result}

🔍 **Consulta**: "{original_question}"
⏱️ **Processado**: {datetime.now().strftime('%H:%M')}"""
                
        except Exception as e:
            print(f"❌ Erro ao formatar resposta de negócios: {e}")
            return f"""📊 **Resultado da Análise**

{sql_result}

🔍 **Consulta**: "{original_question}"
⏱️ **Processado**: {datetime.now().strftime('%H:%M')}"""

    @staticmethod
    def get_agent():
        return OrchestratorAgent()
