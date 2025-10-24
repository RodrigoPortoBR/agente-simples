"""
SQL Agent - REFATORADO PARA DADOS DE NEGÓCIO
CAMADA 2: Executor de queries nas tabelas: clientes, clusters, pedidos, monthly_series
"""
import httpx
import json # <--- CORREÇÃO APLICADA: Importar a biblioteca json
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
                        float(item.get(field, 0)) for item in raw_data if item.get(field) is not None
                    ]
                    
                    if agg_type.lower() == 'sum':
                        aggregated[f'{field}_sum'] = sum(values)
                    elif agg_type.lower() == 'avg':
                        aggregated[f'{field}_avg'] = sum(values) / len(values) if values else 0
                    elif agg_type.lower() == 'count':
                        aggregated[f'{field}_count'] = len(values)
                    elif agg_type.lower() == 'max':
                        aggregated[f'{field}_max'] = max(values) if values else None
                    elif agg_type.lower() == 'min':
                        aggregated[f'{field}_min'] = min(values) if values else None
                
                return SQLQueryResult(
                    success=True,
                    data=[aggregated],
                    row_count=len(raw_data),
                    query_info={"url": url, "method": "aggregate", "table": request.table},
                    query_info_detail=f"Agregado em Python: {request.aggregation}"
                )
            
        except Exception as e:
            return SQLQueryResult(
                success=False,
                error=f"Erro na execução da agregação: {str(e)}",
                query_info={"url": url, "method": "aggregate", "table": request.table}
            )

    async def _execute_count(self, request: SQLQueryRequest) -> SQLQueryResult:
        """Executa contagem de registros (COUNT)"""
        url = f"{self.supabase_url}/rest/v1/{request.table}"
        
        headers = self.headers.copy()
        headers["Prefer"] = "count=exact" # Solicita a contagem total no header
        
        params = []
        
        # Aplicar filtros
        if request.filters:
            for field, value in request.filters.items():
                if field in self.table_schemas[request.table]:
                    params.append(f"{field}=eq.{value}")
        
        if params:
            url += "?" + "&".join(params)
        
        print(f"🔗 SQL Count URL: {url}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.head( # HEAD é mais eficiente para contagem
                    url,
                    headers=headers,
                    timeout=settings.REQUEST_TIMEOUT
                )
                
                if response.status_code != 200 and response.status_code != 206:
                    return SQLQueryResult(
                        success=False,
                        error=f"API Error {response.status_code}: {response.text}"
                    )

                # A contagem total vem no header Content-Range
                content_range = response.headers.get("Content-Range")
                if content_range:
                    # Exemplo: "0-13/14" -> total é 14
                    total_count = int(content_range.split('/')[-1])
                else:
                    # Fallback para contagem no body (menos eficiente)
                    response_get = await client.get(url, headers=self.headers)
                    total_count = len(response_get.json())
                
                return SQLQueryResult(
                    success=True,
                    data=[{"total_count": total_count}],
                    row_count=total_count,
                    query_info={"url": url, "method": "count", "table": request.table}
                )
            
        except Exception as e:
            return SQLQueryResult(
                success=False,
                error=f"Erro na execução da contagem: {str(e)}",
                query_info={"url": url, "method": "count", "table": request.table}
            )

    async def _execute_select(self, request: SQLQueryRequest) -> SQLQueryResult:
        """Executa select simples com filtros e campos"""
        url = f"{self.supabase_url}/rest/v1/{request.table}"
        
        params = []
        
        # Selecionar campos
        select_fields = request.fields if request.fields else ["*"]
        params.append(f"select={','.join(select_fields)}")
        
        # Aplicar filtros
        if request.filters:
            for field, value in request.filters.items():
                if field in self.table_schemas[request.table]:
                    params.append(f"{field}=eq.{value}")
        
        # Limite
        params.append("limit=100") # Limite para evitar sobrecarga
        
        if params:
            url += "?" + "&".join(params)
        
        print(f"🔗 SQL Select URL: {url}")
        
        try:
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
                    query_info={"url": url, "method": "select", "table": request.table}
                )
            
        except Exception as e:
            return SQLQueryResult(
                success=False,
                error=f"Erro na execução do select: {str(e)}",
                query_info={"url": url, "method": "select", "table": request.table}
            )
    
    async def _execute_filter(self, request: SQLQueryRequest) -> SQLQueryResult:
        """Filtra registros (redirecionado para select)"""
        return await self._execute_select(request)

    # ... (outros métodos auxiliares como get_table_schema, get_available_tables, validate_query) ...
    # (Não incluídos aqui para brevidade, mas devem estar no arquivo final)
    
    # Adicionando um método auxiliar para garantir que o arquivo seja completo
    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """Retorna schema de uma tabela"""
        return self.table_schemas.get(table_name, {})
    
    def get_available_tables(self) -> List[str]:
        """Retorna lista de tabelas disponíveis"""
        return list(self.table_schemas.keys())
    
    def validate_query(self, query_request: SQLQueryRequest) -> Dict[str, Any]:
        """Valida uma query antes de executar (stub)"""
        return {"success": True, "errors": []}

