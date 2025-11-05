"""
Period Comparison Agent - Especialista em Comparação de Períodos
Analisa e compara resultados entre diferentes períodos temporais
"""
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from models import AgentInstruction, AgentResponse, AgentType
from config import settings


class PeriodComparisonAgent:
    """
    Agente Especializado em Comparação de Períodos
    
    RESPONSABILIDADES:
    - Comparar métricas entre diferentes períodos (meses, trimestres, anos)
    - Calcular variações percentuais e absolutas
    - Identificar tendências e padrões temporais
    - Analisar crescimento/declínio de receita, margem, clientes, etc
    
    TABELAS PRINCIPAIS:
    - monthly_series: Dados mensais consolidados
    - pedidos: Dados de pedidos por data
    - clientes: Dados de clientes por período
    
    EXEMPLOS DE ANÁLISES:
    - "Compare a receita deste mês com o mês anterior"
    - "Qual foi a variação da margem entre Q1 e Q2?"
    - "Mostre o crescimento de clientes nos últimos 6 meses"
    - "Compare a receita do cluster premium entre este ano e ano passado"
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
        Processa instrução de comparação de períodos
        
        Args:
            instruction: Instrução com parâmetros de comparação
        
        Returns:
            AgentResponse com dados comparativos
        """
        start_time = datetime.now()
        
        try:
            params = instruction.parameters
            
            # Extrair parâmetros de comparação
            metric = params.get("metric", "receita_bruta")  # receita_bruta, margem_bruta, clientes, etc
            period_type = params.get("period_type", "month")  # month, quarter, year
            period1 = params.get("period1")  # "2024-01" ou "2024-Q1" ou "2024"
            period2 = params.get("period2")  # "2024-02" ou "2024-Q2" ou "2023"
            table = params.get("table", "monthly_series")
            filters = params.get("filters", {})  # Filtros adicionais (ex: cluster)
            
            # Executar comparação
            result = await self._compare_periods(
                metric=metric,
                period_type=period_type,
                period1=period1,
                period2=period2,
                table=table,
                filters=filters
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return AgentResponse(
                success=result["success"],
                agent_type=AgentType.PERIOD_COMPARISON,
                data=result.get("data"),
                error=result.get("error"),
                metadata={
                    "metric": metric,
                    "period_type": period_type,
                    "period1": period1,
                    "period2": period2,
                    "comparison": result.get("comparison", {}),
                    "execution_time": execution_time
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            print(f"❌ Erro no Period Comparison Agent: {e}")
            
            return AgentResponse(
                success=False,
                agent_type=AgentType.PERIOD_COMPARISON,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _compare_periods(
        self,
        metric: str,
        period_type: str,
        period1: Optional[str],
        period2: Optional[str],
        table: str,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compara métricas entre dois períodos
        """
        try:
            # Se períodos não foram especificados, usar padrão (últimos 2 meses)
            if not period1 or not period2:
                if table == "monthly_series":
                    # Buscar últimos 2 meses
                    url = f"{self.supabase_url}/rest/v1/{table}"
                    params = ["select=month,receita_bruta,margem_bruta", "order=month.desc", "limit=2"]
                    url += "?" + "&".join(params)
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.get(url, headers=self.headers, timeout=settings.REQUEST_TIMEOUT)
                        
                        if response.status_code != 200:
                            return {"success": False, "error": f"API Error {response.status_code}"}
                        
                        data = response.json()
                        if len(data) < 2:
                            return {"success": False, "error": "Dados insuficientes para comparação"}
                        
                        period2_data = data[0]  # Mais recente
                        period1_data = data[1]  # Anterior
                else:
                    return {"success": False, "error": "Períodos devem ser especificados para esta tabela"}
            else:
                # Buscar dados dos períodos específicos
                period1_data = await self._get_period_data(table, period1, metric, filters)
                period2_data = await self._get_period_data(table, period2, metric, filters)
            
            # Calcular comparação
            value1 = period1_data.get(metric, 0) or 0
            value2 = period2_data.get(metric, 0) or 0
            
            # Calcular variações
            absolute_change = value2 - value1
            if value1 != 0:
                percentage_change = ((value2 - value1) / value1) * 100
            else:
                percentage_change = 100 if value2 > 0 else 0
            
            comparison = {
                "period1": {
                    "period": period1 or period1_data.get("month", "N/A"),
                    "value": value1
                },
                "period2": {
                    "period": period2 or period2_data.get("month", "N/A"),
                    "value": value2
                },
                "absolute_change": round(absolute_change, 2),
                "percentage_change": round(percentage_change, 2),
                "trend": "up" if absolute_change > 0 else "down" if absolute_change < 0 else "stable"
            }
            
            return {
                "success": True,
                "data": {
                    "period1_data": period1_data,
                    "period2_data": period2_data,
                    "comparison": comparison
                },
                "comparison": comparison
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_period_data(
        self,
        table: str,
        period: str,
        metric: str,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Busca dados de um período específico"""
        try:
            url = f"{self.supabase_url}/rest/v1/{table}"
            params = []
            
            # Filtro por período
            if table == "monthly_series":
                params.append(f"month=eq.{period}")
                params.append(f"select=month,receita_bruta,margem_bruta,receita_liquida,cmv")
            elif table == "pedidos":
                # Para pedidos, precisaríamos filtrar por data
                params.append(f"select=receita_bruta,margem_bruta,data")
            
            # Aplicar filtros adicionais
            for field, value in filters.items():
                params.append(f"{field}=eq.{value}")
            
            if params:
                url += "?" + "&".join(params)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, timeout=settings.REQUEST_TIMEOUT)
                
                if response.status_code != 200:
                    return {}
                
                data = response.json()
                
                # Se múltiplos registros, agregar
                if isinstance(data, list):
                    if len(data) == 1:
                        return data[0]
                    elif len(data) > 1:
                        # Agregar dados
                        aggregated = {}
                        for item in data:
                            for key, value in item.items():
                                if isinstance(value, (int, float)):
                                    aggregated[key] = aggregated.get(key, 0) + value
                                elif key not in aggregated:
                                    aggregated[key] = value
                        return aggregated
                    else:
                        return {}
                else:
                    return data if isinstance(data, dict) else {}
                    
        except Exception as e:
            print(f"Erro ao buscar dados do período: {e}")
            return {}

