"""Estructuras de datos compartidas por los modulos del motor."""

from dataclasses import dataclass

@dataclass(frozen=True)
class Params:
    """Parametros del analisis.

    Equivalencia con la guia:
        c_b -> cost_buy      c_s -> cost_sell
        c-> confidence    C-> capital
    """

    p_L: float = 0.05
    p_U: float = 0.95
    BR_min: float = 1.0
    cost_buy: float = 0.0
    cost_sell: float = 0.0
    confidence: float = 0.95
    capital: float = 10000.0

@dataclass(frozen=True)
class CapmParams:
    """Parametros del CAPM.

    freq --> frecuencia de la regresion; semanal por defecto porque con
             datos diarios la diferencia de horarios entre bolsas sesga
             la beta hacia abajo
    erp --> prima de riesgo de mercado anual, E[Rm] - rf
    market_method --> "prima" usa E[Rm] = rf + erp; "historico" usa la
                      media historica del indice
    beta_kind --> "ajustada" (Blume) o "cruda" para el rendimiento requerido
    rf_fixed --> tasa libre de riesgo anual cuando no hay serie de mercado
                 (fixture o descarga fallida)
    """

    freq: str = "W-FRI"
    erp: float = 0.05
    market_method: str = "prima"
    beta_kind: str = "ajustada"
    rf_fixed: float = 0.04
