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
    - Retornar dados de NEGÓCIO (receita, margem, clientes)
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
            # Log detalhado da instrução recebida
            print(f"\n🔍 SQL AGENT RECEBEU:")
            print(f"   Task: {instruction.task_description}")
            print(f"   Parameters: {json.dumps(instruction.parameters, indent=2)}")
            print(f"   Context: {instruction.context}")
            
            # Extrair parâmetros
            query_request = SQLQueryRequest(**instruction.parameters)
            
            # Log da query request
            print(f"\n📋 QUERY REQUEST:")
            print(f"   Type: {query_request.query_type}")
            print(f"   Table: {query_request.table}")
            print(f"   Filters: {query_request.filters}")
            print(f"   Fields: {query_request.fields}")
            print(f"   Aggregation: {query_request.aggregation}")
            
            # Validar tabela
            if query_request.table not in self.table_schemas:
                error_msg = f"Tabela inválida: {query_request.table}. Disponíveis: {list(self.table_schemas.keys())}"
                print(f"❌ {error_msg}")
                return AgentResponse(
                    success=False,
                    agent_type=AgentType.SQL,
                    error=error_msg
                )
            
            # Validar e normalizar filtros
            if query_request.filters:
                normalized_filters = {}
                schema = self.table_schemas[query_request.table]
                
                for key, value in query_request.filters.items():
                    if key not in schema:
                        print(f"⚠️ Campo '{key}' não existe na tabela {query_request.table}")
                        print(f"   Campos disponíveis: {list(schema.keys())}")
                        # Continuar mesmo assim, Supabase vai retornar vazio se campo não existir
                    normalized_filters[key] = value
                
                query_request.filters = normalized_filters
                print(f"✅ Filtros normalizados: {normalized_filters}")
            
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
                error_msg = f"Tipo não suportado: {query_request.query_type}"
                print(f"❌ {error_msg}")
                result = SQLQueryResult(
                    success=False,
                    error=error_msg
                )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Log do resultado
            print(f"\n✅ RESULTADO:")
            print(f"   Success: {result.success}")
            print(f"   Row count: {result.row_count}")
            print(f"   Execution time: {execution_time:.2f}s")
            if result.data:
                print(f"   Data preview: {json.dumps(result.data[:1] if isinstance(result.data, list) else result.data, indent=2)[:200]}...")
            if result.error:
                print(f"   Error: {result.error}")
            
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
                    "table": query_request.table,
                    "filters_applied": query_request.filters
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            print(f"\n❌ ERRO NO SQL AGENT: {e}")
            print(f"   Tipo: {type(e).__name__}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            
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
                if request.filters:
                    aggregated["filtros_aplicados"] = request.filters
                
                return SQLQueryResult(
                    success=True,
                    data=[aggregated],
                    row_count=1,
                    query_info={
                        "url": url,
                        "method": "aggregate_manual",
                        "table": request.table,
                        "raw_count": len(raw_data)
                    }
                )
                
        except Exception as e:
            return SQLQueryResult(
                success=False,
                error=f"Erro na agregação: {str(e)}"
            )
    
    async def _execute_count(self, request: SQLQueryRequest) -> SQLQueryResult:
        """Conta registros com filtros"""
        try:
            url = f"{self.supabase_url}/rest/v1/{request.table}"
            params = ["select=id"]
            
            # Aplicar filtros
            if request.filters:
                for field, value in request.filters.items():
                    if field in self.table_schemas[request.table]:
                        params.append(f"{field}=eq.{value}")
            
            if params:
                url += "?" + "&".join(params)
            
            print(f"🔗 Count Query URL: {url}")
            
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
                
                data = response.json()
                count = len(data)
                
                result = {
                    "total": count,
                    "tabela": request.table
                }
                
                if request.filters:
                    result["filtros_aplicados"] = request.filters
                
                return SQLQueryResult(
                    success=True,
                    data=[result],
                    row_count=1,
                    query_info={"url": url, "method": "count", "table": request.table}
                )
                
        except Exception as e:
            return SQLQueryResult(
                success=False,
                error=f"Erro na contagem: {str(e)}"
            )
    
    async def _execute_select(self, request: SQLQueryRequest) -> SQLQueryResult:
        """Seleciona registros com ordenação e limite"""
        try:
            url = f"{self.supabase_url}/rest/v1/{request.table}"
            params = []
            
            # Campos a selecionar (validar se existem)
            if request.fields:
                valid_fields = [
                    f for f in request.fields 
                    if f in self.table_schemas[request.table]
                ]
                if valid_fields:
                    params.append(f"select={','.join(valid_fields)}")
                else:
                    params.append("select=*")
            else:
                params.append("select=*")
            
            # Filtros
            if request.filters:
                for field, value in request.filters.items():
                    if field in self.table_schemas[request.table]:
                        params.append(f"{field}=eq.{value}")
            
            # Ordenação
            if request.order_by:
                params.append(f"order={request.order_by}")
            
            # Limite
            if request.limit:
                params.append(f"limit={request.limit}")
            
            if params:
                url += "?" + "&".join(params)
            
            print(f"🔗 Select Query URL: {url}")
            
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
                
                data = response.json()
                
                return SQLQueryResult(
                    success=True,
                    data=data,
                    row_count=len(data),
                    query_info={
                        "url": url,
                        "method": "select",
                        "table": request.table
                    }
                )
                
        except Exception as e:
            return SQLQueryResult(
                success=False,
                error=f"Erro no select: {str(e)}"
            )
    
    async def _execute_filter(self, request: SQLQueryRequest) -> SQLQueryResult:
        """Filtra registros (redirecionado para select)"""
        return await self._execute_select(request)
    
    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """
        Retorna schema de uma tabela
        
        Args:
            table_name: Nome da tabela
        
        Returns:
            Dicionário com colunas e tipos
        """
        return self.table_schemas.get(table_name, {})
    
    def get_available_tables(self) -> List[str]:
        """Retorna lista de tabelas disponíveis"""
        return list(self.table_schemas.keys())
    
    def validate_query(self, query_request: SQLQueryRequest) -> Dict[str, Any]:
        """
        Valida uma query antes de executar
        
        Args:
            query_request: Requisição de query
        
        Returns:
            Dicionário com validação
        """
        errors = []
        warnings = []
        
        # Validar tabela
        if query_request.table not in self.table_schemas:
            errors.append(f"Tabela '{query_request.table}' não existe")
        else:
            schema = self.table_schemas[query_request.table]
            
            # Validar campos
            if query_request.fields:
                for field in query_request.fields:
                    if field not in schema:
                        warnings.append(f"Campo '{field}' não existe na tabela")
            
            # Validar filtros
            if query_request.filters:
                for field in query_request.filters.keys():
                    if field not in schema:
                        warnings.append(f"Filtro em campo '{field}' que não existe")
            
            # Validar agregações
            if query_request.aggregation:
                for field in query_request.aggregation.keys():
                    if field not in schema:
                        warnings.append(f"Agregação em campo '{field}' que não existe")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
