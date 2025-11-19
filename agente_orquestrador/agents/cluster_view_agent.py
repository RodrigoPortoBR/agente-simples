"""
Cluster View Agent - Especialista em Análise de Clusters
Analisa dados consolidados por cluster (comportamento de cada cluster)
"""
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

from app_models import AgentInstruction, AgentResponse, AgentType
from config import settings


class ClusterViewAgent:
    """
    Agente Especializado em Visão Cluster
    
    RESPONSABILIDADES:
    - Analisar dados consolidados por cluster
    - Identificar características de cada cluster (receita total, margem média, quantidade de clientes)
    - Comparar clusters entre si
    - Analisar tendências e volatilidade de clusters
    - Identificar padrões de comportamento por cluster
    - Analisar performance e saúde de cada cluster
    
    TABELA PRINCIPAL:
    - Visão_cluster: Cada linha = um cluster com métricas consolidadas
      - id, label (nome do cluster)
      - gm_total (margem bruta total)
      - gm_pct_medio (margem bruta média em %)
      - clientes (quantidade de clientes)
      - freq_media (frequência média de compras)
      - recencia_media (recência média em dias)
      - gm_cv (coeficiente de variação - volatilidade)
      - tendencia (tendência de crescimento)
    
    CLUSTERS EXISTENTES:
    1. Premium - Clientes top de receita
    2. Alto Valor - Bom faturamento
    3. Médio - Performance regular
    4. Baixo - Menor faturamento
    5. Novos - Clientes recentes
    
    EXEMPLOS DE ANÁLISES:
    - "Quais são os clusters com maior receita total?"
    - "Compare a margem média entre os clusters"
    - "Qual cluster tem mais clientes?"
    - "Mostre o cluster com maior volatilidade"
    - "Quais clusters têm tendência de crescimento?"
    - "Analise a performance de cada cluster"
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
        
        # Mapeamento de labels dos clusters
        self.cluster_labels = {
            1: "Premium",
            2: "Alto Valor",
            3: "Médio",
            4: "Baixo",
            5: "Novos"
        }
    
    async def process_instruction(self, instruction: AgentInstruction) -> AgentResponse:
        """
        Processa instrução de análise de clusters
        
        Args:
            instruction: Instrução com parâmetros de análise
        
        Returns:
            AgentResponse com dados de clusters
        """
        start_time = datetime.now()
        
        try:
            params = instruction.parameters
            
            # Extrair parâmetros
            analysis_type = params.get("analysis_type", "list")  # list, compare, aggregate, filter
            filters = params.get("filters", {})  # id, label, tendencia
            fields = params.get("fields", [])  # Campos específicos
            order_by = params.get("order_by")  # Ordenação
            limit = params.get("limit", 10)
            aggregation = params.get("aggregation", {})  # Agregações
            
            # Executar análise
            result = await self._analyze_clusters(
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
                agent_type=AgentType.CLUSTER_VIEW,
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
            print(f"❌ Erro no Cluster View Agent: {e}")
            
            return AgentResponse(
                success=False,
                agent_type=AgentType.CLUSTER_VIEW,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _analyze_clusters(
        self,
        analysis_type: str,
        filters: Dict[str, Any],
        fields: List[str],
        order_by: Optional[str],
        limit: int,
        aggregation: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Analisa dados de clusters
        """
        try:
            url = f"{self.supabase_url}/rest/v1/Visão_cluster"
            params = []
            
            # Selecionar campos
            if fields:
                valid_fields = [
                    "id", "gm_total", "gm_pct_medio",
                    "clientes", "freq_media", "recencia_media",
                    "gm_cv", "tendencia", "updated_at"
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
                if field == "id":
                    params.append(f"id=eq.{value}")
                elif field == "tendencia":
                    # Filtro por tendência (positiva/negativa)
                    if isinstance(value, dict):
                        if "gt" in value:
                            params.append(f"tendencia=gt.{value['gt']}")
                        elif "lt" in value:
                            params.append(f"tendencia=lt.{value['lt']}")
                    else:
                        params.append(f"tendencia=eq.{value}")
                elif field == "gm_pct_min":
                    params.append(f"gm_pct_medio=gte.{value}")
                elif field == "clientes_min":
                    params.append(f"clientes=gte.{value}")
            
            # Ordenação
            if order_by:
                params.append(f"order={order_by}")
            
            # Limite
            if limit:
                params.append(f"limit={limit}")
            
            if params:
                url += "?" + "&".join(params)
            
            print(f"🔗 Cluster View Query URL: {url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=settings.REQUEST_TIMEOUT)
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"API Error {response.status_code}: {response.text}"
                    }
                
                data = response.json()
                
                # Enriquecer dados com labels se necessário
                if isinstance(data, list):
                    for item in data:
                        cluster_id = item.get("id")
                        if cluster_id and cluster_id in self.cluster_labels and not item.get("label"):
                            item["label"] = self.cluster_labels[cluster_id]
                
                # Se precisa agregar
                if aggregation and data:
                    aggregated_data = self._aggregate_cluster_data(data, aggregation)
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
    
    def _aggregate_cluster_data(self, data: List[Dict[str, Any]], aggregation: Dict[str, str]) -> List[Dict[str, Any]]:
        """Agrega dados de clusters"""
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
        
        aggregated["total_clusters"] = len(data)
        
        return [aggregated]
    
    def get_cluster_info(self, cluster_id: int) -> Dict[str, Any]:
        """
        Retorna informações de um cluster específico
        
        Args:
            cluster_id: ID do cluster
        
        Returns:
            Dicionário com informações do cluster
        """
        return {
            "id": cluster_id,
            "label": self.cluster_labels.get(cluster_id, "Desconhecido"),
            "description": self._get_cluster_description(cluster_id)
        }
    
    def _get_cluster_description(self, cluster_id: int) -> str:
        """Retorna descrição do cluster"""
        descriptions = {
            1: "Clientes top de receita - maior valor e melhor performance",
            2: "Alto Valor - bom faturamento e performance acima da média",
            3: "Médio - performance regular, clientes estáveis",
            4: "Baixo - menor faturamento, necessitam atenção",
            5: "Novos - clientes recentes, potencial de crescimento"
        }
        return descriptions.get(cluster_id, "Cluster não identificado")

