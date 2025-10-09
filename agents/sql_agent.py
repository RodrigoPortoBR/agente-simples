"""
SQL Agent - REFATORADO PARA DADOS DE NEGÓCIO
CAMADA 2: Executor de queries nas tabelas: clientes, clusters, pedidos, monthly_series
"""
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

from models import AgentInstruction, AgentResponse, AgentType, SQLQueryRequest, SQLQueryResult
from config import settings

class SQLAgent:
    """
    Agente especialista em queries SQL - DADOS DE NEGÓCIO
    
    RESPONSABILIDADES:
    - Executar queries nas tabelas: clientes, clusters, pedidos, monthly_series
    - Retornar dados de NEGÓCIO (receita, margem bruta, margem contribuicao cliente, clientes, pedidos, etc)
    - NÃO tem lógica de negócio
    - NÃO interpreta linguagem natural
    
    TABELAS DISPONÍVEIS:
    • clientes: receita_bruta_12m, gm_12m, mcc, cluster, pedidos_12m, etc
    • clusters: label, gm_total, gm_pct_medio, clientes, tendencia
    • monthly_series: receita_bruta, margem_bruta por mês
    • pedidos: pedido_id, cliente_id, receita_bruta, categoria
    """
    
    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_ANON_KEY
        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # Mapeamento de tabelas e colunas CORRETAS
        self.table_schemas = {
            "clientes": {
                "id": "text",
                "cluster": "integer",
                "pedidos_12m": "integer",
                "recencia_dias": "integer",
                "receita_bruta_12m": "numeric",
                "receita_bruta_antes_desconto": "numeric",
                "impostos": "numeric",
                "receita_liquida_12m": "numeric",
                "qtde_produtos": "integer",
                "cmv_12m": "numeric",
                "desconto": "numeric",
                "gm_12m": "numeric",  # Margem bruta
                "gm_pct_12m": "numeric",  # % Margem bruta
                "despesas": "numeric",
                "mcc": "numeric",  # Margem contribuição cliente
                "mcc_pct": "numeric",  # % MCC
                "created_at": "timestamp"
            },
            "clusters": {
                "id": "integer",
                "label": "text",
                "gm_total": "numeric",
                "gm_pct_medio": "numeric",
                "clientes": "integer",
                "freq_media": "numeric",
                "recencia_media": "numeric",
                "gm_cv": "numeric",
                "tendencia": "numeric",
                "updated_at": "timestamp"
            },
            "monthly_series": {
                "id": "uuid",
                "month": "text",
                "receita_bruta": "numeric",
                "receita_liquida": "numeric",
                "cmv": "numeric",
                "margem_bruta": "numeric",
                "clusters": "jsonb",
                "created_at": "timestamp"
            },
            "pedidos": {
                "id": "uuid",
                "pedido_id": "text",
                "cliente_id": "text",
                "data": "date",
                "receita_bruta": "numeric",
                "margem_bruta": "numeric",
                "categoria": "text",
                "created_at": "timestamp"
            }
        }
    
    async def process_instruction(self, instruction: AgentInstruction) -> AgentResponse:
        """
        Processa instrução do Orquestrador
        
        Args:
            instruction: Instrução estruturada com parâmetros da query
        
        Returns:
            AgentResponse com dados de negócio
        """
        start_time = datetime.now()
        
        try:
            # Extrair parâmetros
            query_request = SQLQueryRequest(**instruction.parameters)
            
            # Validar tabela
            if query_request.table not in self.table_schemas:
                return AgentResponse(
                    success=False,
                    agent_type=AgentType.SQL,
                    error=f"Tabela inválida: {query_request.table}. Disponíveis: {list(self.table_schemas.keys())}"
                )
            
            # Executar query baseado no tipo
            if query_request.query_type == "aggregate":
                result = await self._execute_aggregate(query_request)
            elif query_request.query_type == "count":
                result = await self._execute_count(query_request)
            elif query_request.query_type == "select":
                result = await self._execute_select(query_request)
            elif query_request.query_type == "filter":
                result = await self._execute_filter(query_request)
            else:
                result = SQLQueryResult(
                    success=False,
                    error=f"Tipo não suportado: {query_request.query_type}"
                )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return AgentResponse(
                success=result.success,
                agent_type=AgentType.SQL,
                data={"results": result.data} if result.data else None,
                error=result.error,
                metadata={
                    "row_count": result.row_count,
                    "execution_time": execution_time,
                    "query_info": result.query_info,
                    "query_type": query_request.query_type,
                    "table": query_request.table
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            print(f"❌ Erro no SQL Agent: {e}")
            
            return AgentResponse(
                success=False,
                agent_type=AgentType.SQL,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _execute_aggregate(self, request: SQLQueryRequest) -> SQLQueryResult:
        """
        Executa agregação (SUM, AVG, COUNT, MIN, MAX)
        Busca dados e agrega em Python
        """
        try:
            url = f"{self.supabase_url}/rest/v1/{request.table}"
            params = []
            
            # Selecionar campos para agregação
            if request.aggregation:
                fields = list(request.aggregation.keys())
                params.append(f"select={','.join(fields)}")
            
            # Aplicar filtros
            if request.filters:
                for field, value in request.filters.items():
                    # Validar campo existe na tabela
                    if field in self.table_schemas[request.table]:
                        params.append(f"{field}=eq.{value}")
            
            if params:
                url += "?" + "&".join(params)
            
            print(f"🔗 SQL Query URL: {url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    timeout=settings.REQUEST_TIMEOUT
                )
                
                if response.status_code != 200:
                    return SQLQueryResult(
                        success=False,
                        error=f"API Error {response.status_code}: {response.text}"
                    )
                
                raw_data = response.json()
                
                if not raw_data:
                    return SQLQueryResult(
                        success=True,
                        data=[{"message": "Nenhum dado encontrado com os filtros aplicados"}],
                        row_count=0,
                        query_info={"url": url, "method": "aggregate", "table": request.table}
                    )
                
                # Agregar dados
                aggregated = {}
                
                for field, agg_type in request.aggregation.items():
                    values = [
                        float(item[field]) if item.get(field) is not None else 0
                        for item in raw_data
                        if item.get(field) is not None
                    ]
                    
                    if values:
                        if agg_type == "sum":
                            aggregated[f"{field}_total"] = round(sum(values), 2)
                        elif agg_type == "avg":
                            aggregated[f"{field}_media"] = round(sum(values) / len(values), 2)
                        elif agg_type == "count":
                            aggregated[f"{field}_count"] = len(values)
                        elif agg_type == "min":
                            aggregated[f"{field}_minimo"] = round(min(values), 2)
                        elif agg_type == "max":
                            aggregated[f"{field}_maximo"] = round(max(values), 2)
                    else:
                        aggregated[f"{field}_{agg_type}"] = 0
                
                # Metadados
                aggregated["total_registros"] = len(raw_data)
            return SQLQueryResult(
                success=True,
                data=[aggregated],
                row_count=len(raw_data),
                query_info={"url": url, "method": "aggregate", "table": request.table}
            )
        except Exception as e:
            return SQLQueryResult(
                success=False,
                error=f"Erro ao executar agregação: {str(e)}"
            )