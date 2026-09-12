"""Robot analitico para preseleccion de activos."""

from .contracts import Params, Window
from .analytics import log_returns, sample_stats, annualize, drawdown, descriptives, diagnostics
from .forecasting import fit, cumulative_moments, terminal, path, walk_forward
from .data import load_fixture, fetch_prices, resample_prices, coverage, align
from .risk_rules import var, levels, terminal_probs, signal_gate

__all__ = [
        "Params", "Window", "load_fixture", "fetch_prices", "resample_prices", "coverage", 
        "align", "log_returns", "sample_stats", "annualize", "drawdown", "descriptives", 
        "diagnostics", "fit", "cumulative_moments", "terminal", "path", "walk_forward", 
        "var", "levels", "terminal_probs", "signal_gate"]