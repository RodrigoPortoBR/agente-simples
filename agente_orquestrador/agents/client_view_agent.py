"""
Client View Agent - Especialista em Análise de Clientes
Analisa dados consolidados por cliente_id (visão cliente)
"""
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

from models import AgentInstruction, AgentResponse, AgentType
from config import settings


class ClientViewAgent:
    """
    Agente Especializado em Visão Cliente
    
    RESPONSABILIDADES:
    - Analisar dados consolidados por cliente_id
    - Identificar perfil de cada cliente (receita, margem, frequência, recência)
    - Comparar clientes entre si
    - Identificar top clientes, clientes em risco, oportunidades
    - Analisar comportamento de clientes por cluster
    
    TABELA PRINCIPAL:
    - Visão_cliente: Cada linha = um cliente_id com métricas consolidadas
      - receita_bruta_12m, receita_liquida_12m
      - gm_12m (margem bruta), gm_pct_12m
      - mcc (margem contribuição), mcc_pct
      - pedidos_12m, recencia_dias
      - cluster, qtde_produtos, cmv_12m
    
    EXEMPLOS DE ANÁLISES:
    - "Quais são os top 10 clientes por receita?"
    - "Mostre clientes do cluster premium com margem acima de 50%"
    - "Quais clientes não compram há mais de 90 dias?"
    - "Compare a receita média entre clusters"
    - "Quais clientes têm maior margem de contribuição?"
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
        Processa instrução de análise de clientes
        
        Args:
            instruction: Instrução com parâmetros de análise
        
        Returns:
            AgentResponse com dados de clientes
        """
        start_time = datetime.now()
        
        try:
            params = instruction.parameters
            
            # Extrair parâmetros
            analysis_type = params.get("analysis_type", "list")  # list, aggregate, compare, filter
            filters = params.get("filters", {})  # cluster, recencia_dias, etc
            fields = params.get("fields", [])  # Campos específicos
            order_by = params.get("order_by")  # Ordenação
            limit = params.get("limit", 100)
            aggregation = params.get("aggregation", {})  # Agregações
            
            # Executar análise
            result = await self._analyze_clients(
                analysis_type=analysis_type,
                filters=filters,
                fields=fields,
                order_by=order_by,
                limit=limit,
                aggregation=aggregation
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return AgentResponse(
                success=result["success"],
                agent_type=AgentType.CLIENT_VIEW,
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
            print(f"❌ Erro no Client View Agent: {e}")
            
            return AgentResponse(
                success=False,
                agent_type=AgentType.CLIENT_VIEW,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _analyze_clients(
        self,
        analysis_type: str,
        filters: Dict[str, Any],
        fields: List[str],
        order_by: Optional[str],
        limit: int,
        aggregation: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Analisa dados de clientes
        """
        try:
            url = f"{self.supabase_url}/rest/v1/Visão_cliente"
            params = []
            
            # Selecionar campos
            if fields:
                valid_fields = [
                    "id", "cluster", "pedidos_12m", "recencia_dias",
                    "receita_bruta_12m", "receita_liquida_12m", "gm_12m",
                    "gm_pct_12m", "mcc", "mcc_pct", "qtde_produtos", "cmv_12m"
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
                if field == "cluster":
                    params.append(f"cluster=eq.{value}")
                elif field == "recencia_dias":
                    # Clientes inativos (recencia alta)
                    if isinstance(value, dict):
                        if "gt" in value:
                            params.append(f"recencia_dias=gt.{value['gt']}")
                        elif "lt" in value:
                            params.append(f"recencia_dias=lt.{value['lt']}")
                    else:
                        params.append(f"recencia_dias=eq.{value}")
                elif field == "receita_min":
                    params.append(f"receita_bruta_12m=gte.{value}")
                elif field == "margem_min":
                    params.append(f"gm_pct_12m=gte.{value}")
            
            # Ordenação
            if order_by:
                params.append(f"order={order_by}")
            
            # Limite
            if limit:
                params.append(f"limit={limit}")
            
            if params:
                url += "?" + "&".join(params)
            
            print(f"🔗 Client View Query URL: {url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=settings.REQUEST_TIMEOUT)
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"API Error {response.status_code}: {response.text}"
                    }
                
                data = response.json()
                
                # Se precisa agregar
                if aggregation and data:
                    aggregated_data = self._aggregate_client_data(data, aggregation)
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
    
    def _aggregate_client_data(self, data: List[Dict[str, Any]], aggregation: Dict[str, str]) -> List[Dict[str, Any]]:
        """Agrega dados de clientes"""
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
        
        aggregated["total_clientes"] = len(data)
        
        return [aggregated]

