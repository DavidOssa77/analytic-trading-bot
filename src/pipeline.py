"""Orquestador: encadena el motor completo sobre un activo."""

from .analytics import log_returns, descriptives, diagnostics, drawdown
from .forecasting import fit, cumulative_moments, path, walk_forward
from .risk_rules import var, levels, terminal_probs, signal_gate


def analyze(prices, params, model, H, m):
    """Corre el motor completo sobre una serie de precios.

    prices --> Serie de precios de un activo, sin huecos
    params --> Params con las colas, los costos y el capital
    model --> "A" o "B"
    H --> horizonte de proyeccion
    m --> periodos por año, segun la frecuencia

    Devuelve un diccionario con todo lo que una vista puede necesitar:
    el ultimo precio y los log-rendimientos, los descriptivos y los
    diagnosticos, los parametros ajustados y los momentos acumulados,
    los niveles con costos, las probabilidades terminales, el VaR
    fraccional y monetario, la trayectoria, la validacion temporal y
    la puerta de señal.
    """
    g = log_returns(prices)
    P_t = prices.iloc[-1]
    mu, sigma = fit(g, model)
    m_H, v_H = cumulative_moments(mu, sigma, H)

    niveles = levels(P_t, m_H, v_H, params.p_L, params.p_U,
                     params.cost_buy, params.cost_sell)
    diag = diagnostics(g)
    wf = walk_forward(g, model, H, m, params)
    dd, dd_max = drawdown(prices)
    frac, dinero = var(m_H, v_H, params.confidence, params.capital)

    return {
        "P_t": P_t, "g": g,
        "descriptives": descriptives(g, m),
        "diagnostics": diag,
        "drawdown": dd, "max_drawdown": dd_max,
        "mu": mu, "sigma": sigma, "m_H": m_H, "v_H": v_H,
        "levels": niveles,
        "probs": terminal_probs(P_t, niveles["P_BE"], m_H, v_H),
        "var_frac": frac, "var_money": dinero,
        "path": path(P_t, mu, sigma, H, params),
        "walk_forward": wf,
        "gate": signal_gate(niveles, diag, wf["sufficient"], params.BR_min),
    }