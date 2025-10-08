"""Orchestrator Agent - Coordenador principal do sistema"""
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
        Método principal - APENAS coordena, NÃO acessa dados
        """
        try:
            print(f"🧠 Orquestrador analisando: '{message}' (sessão: {session_id})")
            
            # Análise de intenção
            needs_data = self._analyze_intent(message)
            
            if needs_data:
                print(f"🔍 Delegando para SQL Agent")
                return await self._delegate_to_sql_agent(message, session_id)
            else:
                print(f"💬 Processando conversa geral")
                return self._handle_general_conversation(message, session_id)
                
        except Exception as e:
            print(f"❌ Erro no Orquestrador: {e}")
            return f"Desculpe, ocorreu um erro: {str(e)}"
    
    def _analyze_intent(self, message: str) -> bool:
        """
        Analisa se a mensagem precisa de consulta de dados
        """
        message_lower = message.lower()
        
        # Palavras-chave que indicam necessidade de dados
        data_keywords = [
            # Métricas e análises
            'receita', 'faturamento', 'vendas', 'valor', 'dinheiro', 'lucro',
            'cliente', 'usuário', 'user', 'customer',
            'análise', 'relatório', 'dashboard', 'métrica', 'kpi', 'estatística',
            'total', 'quantidade', 'número', 'count', 'sum', 'média',
            'cluster', 'premium', 'básico', 'médio', 'segmento',
            'dados', 'informação', 'consulta', 'busca',
            # Específicas do sistema
            'conversa', 'conversas', 'sessão', 'sessões', 'mensagem', 'mensagens',
            'chat', 'interação', 'interações', 'histórico', 'log'
        ]
        
        return any(keyword in message_lower for keyword in data_keywords)
    
    async def _delegate_to_sql_agent(self, message: str, session_id: str) -> str:
        """
        Delega para SQL Agent e formata resposta
        """
        try:
            # Importar SQL Agent dinamicamente
            from .sql_agent import get_sql_agent
            
            if not self.sql_agent:
                self.sql_agent = get_sql_agent()
            
            # Chamar SQL Agent
            sql_result = await self.sql_agent.process_data_request(message, session_id)
            
            # Formatar resposta final
            return self._format_data_response(sql_result, message)
            
        except Exception as e:
            print(f"❌ Erro ao delegar para SQL Agent: {e}")
            return f"""❌ **Erro ao acessar dados**

Desculpe, não consegui consultar o banco de dados no momento.

🔧 **Detalhes técnicos**: {str(e)}

💡 **Sugestão**: Tente novamente em alguns instantes ou faça uma pergunta geral sobre o sistema.

🔗 **Projeto**: RodrigoPortoBR/agente-simples"""
    
    def _format_data_response(self, sql_result: Dict, original_message: str) -> str:
        """
        Formata resposta com dados do SQL Agent
        """
        try:
            if sql_result.get('success', False):
                analysis = sql_result.get('analysis', '')
                
                # Adicionar contexto do projeto
                response = f"""{analysis}

🔗 **Fonte**: Projeto RodrigoPortoBR/agente-simples
⏱️ **Processado**: {datetime.now().strftime('%H:%M:%S')}
🎯 **Consulta**: "{original_message}"
📊 **Dados**: Extraídos em tempo real do Supabase"""

                return response
            else:
                error = sql_result.get('error', 'Erro desconhecido')
                return f"""❌ **Não foi possível obter os dados**

🔧 **Erro**: {error}

💡 **Sugestões**:
• Verifique se o banco de dados está acessível
• Tente uma consulta mais específica
• Faça uma pergunta geral sobre o sistema

🔗 **Projeto**: RodrigoPortoBR/agente-simples"""
                
        except Exception as e:
            return f"""❌ **Erro ao processar resposta**

🔧 **Detalhes**: {str(e)}

💡 **Sugestão**: Tente reformular sua pergunta ou pergunte sobre o funcionamento do sistema.

🔗 **Projeto**: RodrigoPortoBR/agente-simples"""
    
    def _handle_general_conversation(self, message: str, session_id: str) -> str:
        """
        Processa conversas que não precisam de dados
        """
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['olá', 'oi', 'hello', 'hi', 'ola']):
            return """👋 **Olá! Bem-vindo ao agente-simples!**

🤖 Sou o assistente inteligente do projeto **RodrigoPortoBR/agente-simples**.

📊 **Posso ajudar com análises de dados reais**:
• 💬 Estatísticas de conversas e sessões
• 📨 Análise de mensagens e interações
• 📈 Métricas gerais do sistema
• 📊 Relatórios personalizados

💬 **Também posso conversar sobre**:
• Como funciona o projeto
• Arquitetura do sistema
• Tecnologias utilizadas

🔍 **Exemplos de perguntas**:
• "Quantas conversas temos?"
• "Qual o total de mensagens?"
• "Como funciona o sistema?"

Como posso ajudar? 😊"""

        elif any(word in message_lower for word in ['projeto', 'arquitetura', 'sistema', 'agente-simples']):
            return """🏗️ **Projeto agente-simples** (RodrigoPortoBR/agente-simples)

📋 **Arquitetura Real - Sem Hardcode**:
• 🧠 **Orquestrador**: Coordena e analisa intenções
• 🔍 **SQL Agent**: Especialista em dados Supabase
• 📊 **Supabase**: PostgreSQL com dados reais
• ⚡ **FastAPI**: API moderna e performática
• 🔗 **N8N**: Workflows e automações

✨ **Diferencial**: Todos os dados vêm do Supabase em tempo real!

🎯 **Fluxo de Dados**:
1. Usuário faz pergunta
2. Orquestrador analisa intenção
3. Se precisa dados → SQL Agent consulta Supabase
4. SQL Agent processa e formata resultados
5. Orquestrador entrega resposta final

🔧 **Tecnologias**:
• Backend: FastAPI + Python
• IA: OpenAI GPT (análise de intenção)
• Banco: Supabase (PostgreSQL)
• Deploy: Railway

🔗 **GitHub**: https://github.com/RodrigoPortoBR/agente-simples"""

        elif any(word in message_lower for word in ['ajuda', 'help', 'comandos', 'funcionalidades']):
            return """🆘 **Guia de Uso do Sistema**

📊 **Para análises de dados** (consulto Supabase real):
• "Quantas conversas temos?"
• "Qual o total de mensagens?"
• "Estatísticas gerais do sistema"
• "Análise de interações"

💬 **Para informações do projeto**:
• "Como funciona o projeto?"
• "Explique a arquitetura"
• "Quais tecnologias são usadas?"

🔧 **Características Técnicas**:
• **Dados Reais**: Sem hardcode, tudo vem do Supabase
• **Tempo Real**: Consultas diretas ao banco
• **Arquitetura Modular**: Orquestrador + SQL Agent
• **Escalável**: Preparado para crescer

🎯 **Dica**: Seja específico nas perguntas sobre dados para obter análises detalhadas!

📊 **Tabelas Disponíveis**:
• agent_conversations (sessões)
• agent_messages (mensagens)"""

        elif any(word in message_lower for word in ['obrigado', 'obrigada', 'thanks', 'valeu']):
            return """😊 **De nada! Foi um prazer ajudar!**

🤖 Estou sempre aqui para auxiliar com:
• 📊 Análises de dados reais do Supabase
• 💬 Informações sobre o projeto
• 🔧 Explicações técnicas

🔄 **Precisa de mais alguma coisa?**
• Consultas de dados específicas
• Informações sobre arquitetura
• Ajuda com funcionalidades

🔗 **Projeto**: RodrigoPortoBR/agente-simples
✨ **Diferencial**: Dados reais, sem hardcode!"""

        else:
            return f"""💭 **Recebi sua mensagem**: "{message}"

🤖 Sou o assistente do projeto **agente-simples** e posso ajudar de duas formas:

📊 **Para análises de dados** (consulto Supabase em tempo real):
• Estatísticas de conversas e mensagens
• Métricas do sistema
• Relatórios personalizados

💬 **Para conversas gerais**:
• Explicações sobre o projeto
• Arquitetura e tecnologias
• Como usar o sistema

🔍 **Como posso ajudar especificamente?**

💡 **Dica**: Se você quer dados, seja específico! Exemplo: "Quantas conversas temos?" ou "Total de mensagens"

🔗 **Projeto**: RodrigoPortoBR/agente-simples"""

def get_agent():
    """Factory function para criar instância do Orquestrador"""
    return OrchestratorAgent()
