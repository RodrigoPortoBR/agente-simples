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
        Funciona como LLM normal, delega para SQL Agent quando necessário
        """
        try:
            print(f"🧠 Orquestrador analisando: '{message}' (sessão: {session_id})")
            
            # Análise de intenção - só detecta necessidade de dados
            needs_data = self._analyze_intent(message)
            
            if needs_data:
                print(f"📊 Delegando para SQL Agent")
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
        Retorna True APENAS se realmente precisar de dados do Supabase
        """
        message_lower = message.lower()
        
        # Palavras-chave ESPECÍFICAS que indicam necessidade de dados
        data_keywords = [
            # Consultas diretas
            'quantas conversas', 'quantos usuários', 'quantas mensagens',
            'total de', 'número de', 'count', 'sum', 'média',
            
            # Análises específicas
            'estatística', 'relatório', 'dashboard', 'métrica',
            'dados do sistema', 'informações do banco',
            
            # Consultas específicas do sistema
            'conversas no sistema', 'mensagens registradas', 'usuários ativos',
            'histórico de', 'logs de', 'registros de'
        ]
        
        # Só retorna True se encontrar palavras-chave ESPECÍFICAS
        return any(keyword in message_lower for keyword in data_keywords)

    async def _delegate_to_sql_agent(self, message: str, session_id: str) -> str:
        """
        Delega para SQL Agent e formata resposta de forma natural
        """
        try:
            # Importar SQL Agent dinamicamente
            from .sql_agent import get_sql_agent
            
            if not self.sql_agent:
                self.sql_agent = get_sql_agent()
            
            # Chamar SQL Agent
            sql_result = await self.sql_agent.process_data_request(message, session_id)
            
            # Formatar resposta de forma natural
            return self._format_data_response(sql_result, message)
            
        except Exception as e:
            print(f"❌ Erro ao chamar SQL Agent: {e}")
            return f"Desculpe, não consegui acessar os dados no momento. Erro: {str(e)}"

    def _handle_general_conversation(self, message: str, session_id: str) -> str:
        """
        Processa conversas gerais - funciona como LLM normal
        """
        message_lower = message.lower()
        
        # Saudações
        if any(greeting in message_lower for greeting in ['olá', 'oi', 'hello', 'hi', 'bom dia', 'boa tarde', 'boa noite']):
            return f"👋 Olá! Sou seu assistente inteligente. Como posso ajudar você hoje?"
        
        # Perguntas sobre funcionamento
        if any(word in message_lower for word in ['como funciona', 'como você funciona', 'o que você faz', 'quem é você']):
            return """🤖 Sou um assistente inteligente que pode:

💬 **Conversar** sobre diversos assuntos
📊 **Consultar dados** quando você precisar de informações específicas do sistema
🔍 **Ajudar** com perguntas e dúvidas

Como posso ajudar você?"""
        
        # Perguntas sobre o projeto
        if any(word in message_lower for word in ['projeto', 'agente-simples', 'sistema', 'arquitetura']):
            return """📋 **Sobre o Projeto Agente-Simples:**

🏗️ **Arquitetura**: Sistema modular com agentes especializados
🤖 **Orquestrador**: Coordena conversas e delega tarefas
📊 **SQL Agent**: Especialista em consultas de dados
💾 **Supabase**: Banco de dados em tempo real
🚀 **Deploy**: Railway com integração contínua

Quer saber mais sobre algum aspecto específico?"""
        
        # Ajuda
        if any(word in message_lower for word in ['ajuda', 'help', 'comandos', 'o que posso fazer']):
            return """🆘 **Como posso ajudar:**

💬 **Conversas gerais**: Posso conversar sobre diversos temas
📊 **Consultas de dados**: Pergunte sobre estatísticas do sistema
❓ **Dúvidas**: Tire dúvidas sobre o projeto ou funcionamento
🔍 **Informações**: Posso explicar como tudo funciona

**Exemplos de perguntas:**
• "Quantas conversas temos no sistema?"
• "Como funciona a arquitetura?"
• "Explique o projeto agente-simples"

O que você gostaria de saber?"""
        
        # Agradecimentos
        if any(word in message_lower for word in ['obrigado', 'obrigada', 'thanks', 'valeu', 'brigado']):
            return "😊 De nada! Fico feliz em ajudar. Se precisar de mais alguma coisa, é só perguntar!"
        
        # Despedidas
        if any(word in message_lower for word in ['tchau', 'bye', 'até logo', 'falou', 'adeus']):
            return "👋 Até logo! Foi um prazer conversar com você. Volte sempre que precisar!"
        
        # Resposta genérica para outras mensagens
        return f"""💭 Entendi sua mensagem: "{message}"

🤖 Sou seu assistente e posso ajudar de várias formas:

💬 **Conversas**: Posso conversar sobre diversos assuntos
📊 **Dados**: Se precisar de informações específicas do sistema, é só perguntar
🔍 **Dúvidas**: Posso esclarecer questões sobre o projeto

Como posso ajudar você especificamente?"""

    def _format_data_response(self, sql_result: str, original_question: str) -> str:
        """
        Formata resposta do SQL Agent de forma natural
        """
        try:
            # Se o resultado for JSON, tentar parsear
            if sql_result.startswith('{'):
                data = json.loads(sql_result)
                
                # Formatar baseado no tipo de pergunta
                if 'conversas' in original_question.lower():
                    return f"""📊 **Informações sobre Conversas:**

{sql_result}

💡 Estes dados foram consultados em tempo real no sistema."""
                
                elif 'mensagens' in original_question.lower():
                    return f"""📨 **Informações sobre Mensagens:**

{sql_result}

💡 Dados atualizados em tempo real."""
                
                else:
                    return f"""📊 **Resultado da Consulta:**

{sql_result}

💡 Informações extraídas do sistema em tempo real."""
            
            else:
                # Se não for JSON, retornar como texto formatado
                return f"""📊 **Resultado:**

{sql_result}

💡 Dados consultados em tempo real no sistema."""
                
        except Exception as e:
            print(f"❌ Erro ao formatar resposta: {e}")
            return f"""📊 **Resultado da Consulta:**

{sql_result}

💡 Dados do sistema atualizados em tempo real."""

    @staticmethod
    def get_agent():
        return OrchestratorAgent()
