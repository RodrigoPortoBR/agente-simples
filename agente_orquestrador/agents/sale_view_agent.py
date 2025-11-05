"""
Sale View Agent - Especialista em Análise de Vendas
Analisa dados consolidados por id_venda (visão venda)
"""
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

from models import AgentInstruction, AgentResponse, AgentType
from config import settings


class SaleViewAgent:
    """
    Agente Especializado em Visão Venda
    
    RESPONSABILIDADES:
    - Analisar dados consolidados por id_venda (pedido_id)
    - Identificar características de cada venda (valor, margem, categoria, cliente)
    - Analisar vendas por período, categoria, cliente
    - Identificar top vendas, vendas com melhor margem
    - Analisar padrões de vendas
    
    TABELA PRINCIPAL:
    - pedidos: Cada linha = uma venda (id_venda/pedido_id) com métricas
      - pedido_id, cliente_id, data
      - receita_bruta, margem_bruta
      - categoria
    
    EXEMPLOS DE ANÁLISES:
    - "Quais foram as top 20 vendas por receita?"
    - "Mostre vendas do mês de janeiro com margem acima de 50%"
    - "Quais categorias têm maior volume de vendas?"
    - "Compare receita de vendas entre meses"
    - "Quais clientes têm mais vendas?"
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
    
    async def process_instruction(self, instruction: AgentInstruction) -> AgentResponse:
        """
        Processa instrução de análise de vendas
        
        Args:
            instruction: Instrução com parâmetros de análise
        
        Returns:
            AgentResponse com dados de vendas
        """
        start_time = datetime.now()
        
        try:
            params = instruction.parameters
            
            # Extrair parâmetros
            analysis_type = params.get("analysis_type", "list")  # list, aggregate, by_category, by_period
            filters = params.get("filters", {})  # data, categoria, cliente_id
            fields = params.get("fields", [])  # Campos específicos
            order_by = params.get("order_by")  # Ordenação
            limit = params.get("limit", 100)
            aggregation = params.get("aggregation", {})  # Agregações
            group_by = params.get("group_by")  # Agrupar por categoria, data, etc
            
            # Executar análise
            result = await self._analyze_sales(
                analysis_type=analysis_type,
                filters=filters,
                fields=fields,
                order_by=order_by,
                limit=limit,
                aggregation=aggregation,
                group_by=group_by
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return AgentResponse(
                success=result["success"],
                agent_type=AgentType.SALE_VIEW,
                data=result.get("data"),
                error=result.get("error"),
                metadata={
                    "analysis_type": analysis_type,
                    "row_count": result.get("row_count", 0),
                    "execution_time": execution_time
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            print(f"❌ Erro no Sale View Agent: {e}")
            
            return AgentResponse(
                success=False,
                agent_type=AgentType.SALE_VIEW,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _analyze_sales(
        self,
        analysis_type: str,
        filters: Dict[str, Any],
        fields: List[str],
        order_by: Optional[str],
        limit: int,
        aggregation: Dict[str, str],
        group_by: Optional[str]
    ) -> Dict[str, Any]:
        """
        Analisa dados de vendas
        """
        try:
            url = f"{self.supabase_url}/rest/v1/pedidos"
            params = []
            
            # Selecionar campos
            if fields:
                valid_fields = [
                    "id", "pedido_id", "cliente_id", "data",
                    "receita_bruta", "margem_bruta", "categoria"
                ]
                selected_fields = [f for f in fields if f in valid_fields]
                if selected_fields:
                    params.append(f"select={','.join(selected_fields)}")
                else:
                    params.append("select=*")
            else:
                params.append("select=*")
            
            # Aplicar filtros
            for field, value in filters.items():
                if field == "categoria":
                    params.append(f"categoria=eq.{value}")
                elif field == "cliente_id":
                    params.append(f"cliente_id=eq.{value}")
                elif field == "data":
                    # Filtro por data (pode ser range)
                    if isinstance(value, dict):
                        if "gte" in value:
                            params.append(f"data=gte.{value['gte']}")
                        if "lte" in value:
                            params.append(f"data=lte.{value['lte']}")
                    else:
                        params.append(f"data=eq.{value}")
                elif field == "receita_min":
                    params.append(f"receita_bruta=gte.{value}")
                elif field == "margem_min":
                    params.append(f"margem_bruta=gte.{value}")
            
            # Ordenação
            if order_by:
                params.append(f"order={order_by}")
            
            # Limite
            if limit:
                params.append(f"limit={limit}")
            
            if params:
                url += "?" + "&".join(params)
            
            print(f"🔗 Sale View Query URL: {url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=settings.REQUEST_TIMEOUT)
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"API Error {response.status_code}: {response.text}"
                    }
                
                data = response.json()
                
                # Se precisa agrupar
                if group_by and data:
                    grouped_data = self._group_sales_data(data, group_by, aggregation)
                    return {
                        "success": True,
                        "data": {"results": grouped_data},
                        "row_count": len(grouped_data)
                    }
                
                # Se precisa agregar
                if aggregation and data:
                    aggregated_data = self._aggregate_sales_data(data, aggregation)
                    return {
                        "success": True,
                        "data": {"results": aggregated_data},
                        "row_count": len(aggregated_data)
                    }
                
                return {
                    "success": True,
                    "data": {"results": data},
                    "row_count": len(data) if isinstance(data, list) else 1
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _group_sales_data(
        self,
        data: List[Dict[str, Any]],
        group_by: str,
        aggregation: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Agrupa dados de vendas por campo"""
        grouped = {}
        
        for item in data:
            group_key = item.get(group_by, "unknown")
            
            if group_key not in grouped:
                grouped[group_key] = []
            
            grouped[group_key].append(item)
        
        # Agregar cada grupo
        result = []
        for group_key, group_items in grouped.items():
            aggregated = self._aggregate_sales_data(group_items, aggregation)
            if aggregated:
                aggregated[0][group_by] = group_key
                result.extend(aggregated)
        
        return result
    
    def _aggregate_sales_data(self, data: List[Dict[str, Any]], aggregation: Dict[str, str]) -> List[Dict[str, Any]]:
        """Agrega dados de vendas"""
        if not data:
            return []
        
        aggregated = {}
        
        for field, agg_type in aggregation.items():
            values = [
                float(item[field]) if item.get(field) is not None else 0
                for item in data
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
        
        aggregated["total_vendas"] = len(data)
        
        return [aggregated]

