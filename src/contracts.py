"""Estructuras de datos compartidas por los modulos del motor."""

from dataclasses import dataclass
from datetime import date


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
class Window:
    """Ventana de analisis: periodo, frecuencia y horizonte."""

    start: date
    end: date
    freq: str
    m: int
    H: int = 5