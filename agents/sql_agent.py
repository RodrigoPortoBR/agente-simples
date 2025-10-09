"""
SQL Agent - Especialista em análises do Lovable Cloud
Acessa dados de clientes, pedidos, clusters e séries temporais
"""
from typing import Any, Dict, List
import json
import os
from datetime import datetime
import httpx

class SQLAgent:
    def __init__(self, config: Any = None):
        self.config = config
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        # Schema do Lovable Cloud
        self.schema = {
            "clientes": {
                "columns": ["id", "nome", "email", "cluster_id", "data_criacao", "status"],
                "description": "Dados dos clientes do Lovable Cloud"
            },
            "clusters": {
                "columns": ["id", "nome", "tipo", "valor_mensal", "descricao"],
                "description": "Segmentação e categorização de clientes"
            },
            "pedidos": {
                "columns": ["id", "cliente_id", "valor", "data", "status", "produto"],
                "description": "Transações e pedidos dos clientes"
            },
            "monthly_series": {
                "columns": ["id", "cliente_id", "mes", "valor", "metricas", "data_ref"],
                "description": "Séries temporais mensais de métricas"
            }
        }
    
    def start(self):
        return "started"
    
    async def process_business_query(self, message: str, session_id: str) -> str:
        """
        Processa consulta de negócios e retorna JSON estruturado
        """
        try:
            print(f"🔍 SQL Agent analisando: '{message}' (sessão: {session_id})")
            
            # Gerar query SQL baseada na mensagem
            sql_query = self._generate_sql_query(message)
            
            if not sql_query:
                return self._create_error_response("Não consegui entender a consulta solicitada.")
            
            print(f"📝 Query gerada: {sql_query}")
            
            # Executar query no Supabase
            result = await self._execute_query(sql_query)
            
            # Processar e formatar resultado
            return self._format_business_result(result, message, sql_query)
            
        except Exception as e:
            print(f"❌ Erro no SQL Agent: {e}")
            return self._create_error_response(f"Erro ao processar consulta: {str(e)}")

    def _generate_sql_query(self, message: str) -> str:
        """
        Gera query SQL baseada na mensagem do usuário
        """
        message_lower = message.lower()
        
        # CLIENTES
        if any(word in message_lower for word in ['quantos clientes', 'número de clientes', 'total de clientes']):
            if 'ativo' in message_lower:
                return "SELECT COUNT(*) as total FROM clientes WHERE status = 'ativo'"
            elif 'inativo' in message_lower:
                return "SELECT COUNT(*) as total FROM clientes WHERE status = 'inativo'"
            else:
                return "SELECT COUNT(*) as total FROM clientes"
        
        if any(word in message_lower for word in ['lista de clientes', 'dados dos clientes', 'clientes premium']):
            if 'premium' in message_lower:
                return """
                SELECT c.nome, c.email, cl.nome as cluster, c.data_criacao 
                FROM clientes c 
                JOIN clusters cl ON c.cluster_id = cl.id 
                WHERE cl.tipo = 'premium' 
                ORDER BY c.data_criacao DESC 
                LIMIT 20
                """
            else:
                return """
                SELECT c.nome, c.email, cl.nome as cluster, c.data_criacao 
                FROM clientes c 
                LEFT JOIN clusters cl ON c.cluster_id = cl.id 
                ORDER BY c.data_criacao DESC 
                LIMIT 20
                """
        
        # PEDIDOS
        if any(word in message_lower for word in ['quantos pedidos', 'número de pedidos', 'total de pedidos']):
            if 'aberto' in message_lower or 'pendente' in message_lower:
                return "SELECT COUNT(*) as total FROM pedidos WHERE status IN ('aberto', 'pendente')"
            elif 'fechado' in message_lower or 'concluído' in message_lower:
                return "SELECT COUNT(*) as total FROM pedidos WHERE status IN ('fechado', 'concluido')"
            else:
                return "SELECT COUNT(*) as total FROM pedidos"
        
        # RECEITA E FATURAMENTO
        if any(word in message_lower for word in ['receita', 'faturamento', 'valor total', 'quanto faturamos']):
            if 'mês' in message_lower or 'mensal' in message_lower:
                return """
                SELECT 
                    DATE_TRUNC('month', data) as mes,
                    SUM(valor) as receita_mensal,
                    COUNT(*) as pedidos
                FROM pedidos 
                WHERE data >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '6 months')
                GROUP BY DATE_TRUNC('month', data)
                ORDER BY mes DESC
                """
            else:
                return "SELECT SUM(valor) as receita_total, COUNT(*) as total_pedidos FROM pedidos"
        
        # TOP CLIENTES
        if any(word in message_lower for word in ['top clientes', 'maiores clientes', 'ranking']):
            return """
            SELECT 
                c.nome,
                c.email,
                SUM(p.valor) as valor_total,
                COUNT(p.id) as total_pedidos
            FROM clientes c
            JOIN pedidos p ON c.id = p.cliente_id
            GROUP BY c.id, c.nome, c.email
            ORDER BY valor_total DESC
            LIMIT 10
            """
        
        # CLUSTERS
        if any(word in message_lower for word in ['cluster', 'segmentação', 'categorias']):
            return """
            SELECT 
                cl.nome as cluster,
                cl.tipo,
                COUNT(c.id) as total_clientes,
                AVG(cl.valor_mensal) as valor_medio
            FROM clusters cl
            LEFT JOIN clientes c ON cl.id = c.cluster_id
            GROUP BY cl.id, cl.nome, cl.tipo
            ORDER BY total_clientes DESC
            """
        
        # ANÁLISE MENSAL
        if any(word in message_lower for word in ['dados mensais', 'série temporal', 'evolução']):
            return """
            SELECT 
                mes,
                AVG(valor) as valor_medio,
                COUNT(*) as registros
            FROM monthly_series
            WHERE mes >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '12 months')
            GROUP BY mes
            ORDER BY mes DESC
            """
        
        # RELATÓRIO GERAL
        if any(word in message_lower for word in ['relatório', 'dashboard', 'resumo geral']):
            return """
            SELECT 
                'clientes' as categoria,
                COUNT(*) as total
            FROM clientes
            UNION ALL
            SELECT 
                'pedidos' as categoria,
                COUNT(*) as total
            FROM pedidos
            UNION ALL
            SELECT 
                'receita_total' as categoria,
                COALESCE(SUM(valor), 0) as total
            FROM pedidos
            """
        
        # Query não reconhecida
        return None

    async def _execute_query(self, sql_query: str) -> Dict:
        """
        Executa query no Supabase e retorna resultado
        """
        try:
            # Configurar headers
            headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json"
            }
            
            # Executar query via RPC (se disponível) ou REST API
            async with httpx.AsyncClient() as client:
                # Tentar usar RPC para queries complexas
                rpc_payload = {
                    "query": sql_query
                }
                
                response = await client.post(
                    f"{self.supabase_url}/rest/v1/rpc/execute_sql",
                    headers=headers,
                    json=rpc_payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                else:
                    # Fallback: tentar query simples via REST
                    return await self._execute_simple_query(sql_query, headers, client)
                    
        except Exception as e:
            print(f"❌ Erro ao executar query: {e}")
            return {"success": False, "error": str(e)}

    async def _execute_simple_query(self, sql_query: str, headers: Dict, client) -> Dict:
        """
        Fallback para queries simples via REST API
        """
        try:
            # Detectar tipo de query e tabela
            if "FROM clientes" in sql_query:
                table = "clientes"
            elif "FROM pedidos" in sql_query:
                table = "pedidos"
            elif "FROM clusters" in sql_query:
                table = "clusters"
            elif "FROM monthly_series" in sql_query:
                table = "monthly_series"
            else:
                return {"success": False, "error": "Tabela não identificada"}
            
            # Query simples de contagem
            if "COUNT(*)" in sql_query and "WHERE" not in sql_query:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/{table}?select=*",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, "data": [{"total": len(data)}]}
            
            # Query de listagem simples
            response = await client.get(
                f"{self.supabase_url}/rest/v1/{table}?select=*&limit=20",
                headers=headers
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _format_business_result(self, result: Dict, original_message: str, sql_query: str) -> str:
        """
        Formata resultado em JSON estruturado para o Orquestrador
        """
        try:
            if not result.get("success"):
                return self._create_error_response(result.get("error", "Erro desconhecido"))
            
            data = result.get("data", [])
            
            # Gerar resumo baseado nos dados
            resumo = self._generate_summary(data, original_message)
            
            # Gerar insights
            insights = self._generate_insights(data, original_message)
            
            # Criar resposta JSON estruturada
            response = {
                "query": sql_query,
                "resultado": data,
                "resumo": resumo,
                "insights": insights,
                "timestamp": datetime.now().isoformat(),
                "total_registros": len(data) if isinstance(data, list) else 1
            }
            
            return json.dumps(response, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"❌ Erro ao formatar resultado: {e}")
            return self._create_error_response(f"Erro ao formatar resultado: {str(e)}")

    def _generate_summary(self, data: List, message: str) -> str:
        """
        Gera resumo baseado nos dados retornados
        """
        if not data:
            return "Nenhum dado encontrado para a consulta"
        
        message_lower = message.lower()
        
        if 'cliente' in message_lower:
            if isinstance(data[0], dict) and 'total' in data[0]:
                return f"Total de {data[0]['total']} clientes encontrados"
            else:
                return f"{len(data)} clientes encontrados"
        
        elif 'pedido' in message_lower:
            if isinstance(data[0], dict) and 'total' in data[0]:
                return f"Total de {data[0]['total']} pedidos encontrados"
            else:
                return f"{len(data)} pedidos encontrados"
        
        elif 'receita' in message_lower or 'faturamento' in message_lower:
            if isinstance(data[0], dict) and 'receita_total' in data[0]:
                return f"Receita total: R$ {data[0]['receita_total']:,.2f}"
            else:
                return "Análise de receita concluída"
        
        else:
            return f"Análise concluída - {len(data)} registros encontrados"

    def _generate_insights(self, data: List, message: str) -> List[str]:
        """
        Gera insights baseados nos dados
        """
        insights = []
        
        if not data:
            insights.append("Nenhum dado disponível para análise")
            return insights
        
        message_lower = message.lower()
        
        # Insights para clientes
        if 'cliente' in message_lower:
            if isinstance(data[0], dict) and 'total' in data[0]:
                total = data[0]['total']
                if total > 100:
                    insights.append("Base de clientes robusta com mais de 100 registros")
                elif total > 50:
                    insights.append("Base de clientes em crescimento")
                else:
                    insights.append("Oportunidade de expansão da base de clientes")
        
        # Insights para receita
        elif 'receita' in message_lower:
            insights.append("Dados de receita atualizados em tempo real")
            insights.append("Recomenda-se análise mensal para identificar tendências")
        
        # Insights gerais
        else:
            insights.append("Dados extraídos diretamente do Lovable Cloud")
            insights.append("Informações atualizadas em tempo real")
        
        return insights

    def _create_error_response(self, error_message: str) -> str:
        """
        Cria resposta de erro em formato JSON
        """
        response = {
            "query": None,
            "resultado": [],
            "resumo": f"Erro: {error_message}",
            "insights": ["Verifique a consulta e tente novamente"],
            "timestamp": datetime.now().isoformat(),
            "total_registros": 0,
            "error": True
        }
        
        return json.dumps(response, ensure_ascii=False, indent=2)

    @staticmethod
    def get_sql_agent():
        return SQLAgent()

# Função para compatibilidade
def get_sql_agent():
    return SQLAgent()
