"""
Product View Agent - Especialista em Análise de Produtos
Analisa dados consolidados por produto
"""
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

from models import AgentInstruction, AgentResponse, AgentType
from config import settings


class ProductViewAgent:
    """
    Agente Especializado em Visão Produto
    
    RESPONSABILIDADES:
    - Analisar dados consolidados por produto
    - Identificar produtos mais vendidos, mais rentáveis
    - Analisar performance de produtos por categoria
    - Comparar produtos entre si
    - Identificar oportunidades e produtos em declínio
    
    NOTA: Este agente pode trabalhar com tabelas de produtos ou 
    agregar dados de pedidos por produto/categoria
    
    TABELAS PRINCIPAIS:
    - pedidos: Agregar por categoria (campo categoria)
    - Se houver tabela produtos: dados consolidados por produto
    
    EXEMPLOS DE ANÁLISES:
    - "Quais são os produtos mais vendidos por receita?"
    - "Mostre produtos com maior margem bruta"
    - "Compare vendas de produtos entre categorias"
    - "Quais categorias têm melhor performance?"
    - "Analise a receita por categoria no último trimestre"
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
        Processa instrução de análise de produtos
        
        Args:
            instruction: Instrução com parâmetros de análise
        
        Returns:
            AgentResponse com dados de produtos
        """
        start_time = datetime.now()
        
        try:
            params = instruction.parameters
            
            # Extrair parâmetros
            analysis_type = params.get("analysis_type", "by_category")  # by_category, by_product, compare
            filters = params.get("filters", {})  # categoria, data
            order_by = params.get("order_by")  # Ordenação
            limit = params.get("limit", 100)
            aggregation = params.get("aggregation", {})  # Agregações
            group_by = params.get("group_by", "categoria")  # Agrupar por categoria ou produto
            
            # Executar análise
            result = await self._analyze_products(
                analysis_type=analysis_type,
                filters=filters,
                order_by=order_by,
                limit=limit,
                aggregation=aggregation,
                group_by=group_by
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return AgentResponse(
                success=result["success"],
                agent_type=AgentType.PRODUCT_VIEW,
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
            print(f"❌ Erro no Product View Agent: {e}")
            
            return AgentResponse(
                success=False,
                agent_type=AgentType.PRODUCT_VIEW,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _analyze_products(
        self,
        analysis_type: str,
        filters: Dict[str, Any],
        order_by: Optional[str],
        limit: int,
        aggregation: Dict[str, str],
        group_by: str
    ) -> Dict[str, Any]:
        """
        Analisa dados de produtos (agregando pedidos por categoria/produto)
        """
        try:
            # Buscar dados de pedidos para agregar por produto/categoria
            url = f"{self.supabase_url}/rest/v1/pedidos"
            params = ["select=categoria,receita_bruta,margem_bruta,data"]
            
            # Aplicar filtros
            for field, value in filters.items():
                if field == "categoria":
                    params.append(f"categoria=eq.{value}")
                elif field == "data":
                    if isinstance(value, dict):
                        if "gte" in value:
                            params.append(f"data=gte.{value['gte']}")
                        if "lte" in value:
                            params.append(f"data=lte.{value['lte']}")
                    else:
                        params.append(f"data=eq.{value}")
            
            if params:
                url += "?" + "&".join(params)
            
            print(f"🔗 Product View Query URL: {url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=settings.REQUEST_TIMEOUT)
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"API Error {response.status_code}: {response.text}"
                    }
                
                data = response.json()
                
                if not data:
                    return {
                        "success": True,
                        "data": {"results": []},
                        "row_count": 0
                    }
                
                # Agrupar por categoria/produto
                grouped_data = self._group_product_data(data, group_by, aggregation)
                
                # Ordenar
                if order_by and grouped_data:
                    # Ordenar por campo especificado
                    order_field = order_by.replace(".desc", "").replace(".asc", "")
                    reverse = ".desc" in order_by
                    
                    # Tentar encontrar campo de agregação correspondente
                    for key in grouped_data[0].keys():
                        if order_field in key:
                            grouped_data.sort(key=lambda x: x.get(key, 0), reverse=reverse)
                            break
                
                # Limitar
                if limit:
                    grouped_data = grouped_data[:limit]
                
                return {
                    "success": True,
                    "data": {"results": grouped_data},
                    "row_count": len(grouped_data)
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _group_product_data(
        self,
        data: List[Dict[str, Any]],
        group_by: str,
        aggregation: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Agrupa dados por produto/categoria e agrega"""
        grouped = {}
        
        for item in data:
            group_key = item.get(group_by, "unknown")
            
            if group_key not in grouped:
                grouped[group_key] = []
            
            grouped[group_key].append(item)
        
        # Agregar cada grupo
        result = []
        for group_key, group_items in grouped.items():
            # Agregação padrão se não especificada
            if not aggregation:
                aggregation = {
                    "receita_bruta": "sum",
                    "margem_bruta": "sum"
                }
            
            aggregated = {}
            aggregated[group_by] = group_key
            
            for field, agg_type in aggregation.items():
                values = [
                    float(item[field]) if item.get(field) is not None else 0
                    for item in group_items
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
            
            aggregated["total_vendas"] = len(group_items)
            
            # Calcular margem percentual se possível
            if "receita_bruta_total" in aggregated and "margem_bruta_total" in aggregated:
                if aggregated["receita_bruta_total"] > 0:
                    aggregated["margem_pct"] = round(
                        (aggregated["margem_bruta_total"] / aggregated["receita_bruta_total"]) * 100,
                        2
                    )
            
            result.append(aggregated)
        
        return result

