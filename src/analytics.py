"""Estadistica descriptiva y diagnosticos sobre log-rendimientos."""

import numpy as np
from scipy import stats 
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch

def log_returns(prices):
    """Log-rendimientos g_t = ln(P_t / P_{t-1}).

    prices -- Serie de precios ajustados, ya remuestreada
    Devuelve una Serie con una observacion menos (se descarta el primer nulo).
    """
    return np.log(prices / prices.shift(1)).dropna()


def sample_stats(g):
    """Media, varianza y desviacion muestrales con ddof=1.

    g -- Serie de log-rendimientos
    Devuelve (media, varianza, desviacion).
    """
    return g.mean(), g.var(ddof=1), g.std(ddof=1)


def annualize(mean, sd, m):
    """Escala media y desviacion por periodo a base anual.

    mean, sd -- estimadores por periodo
    m        -- periodos por año (252 diaria, 52 semanal, 12 mensual)
    Devuelve (media anual, desviacion anual).
    """
    return m * mean, np.sqrt(m) * sd


def drawdown(prices):
    """Caida relativa desde el maximo previo y caida maxima.

    prices -- Serie de PRECIOS, nunca de rendimientos
    Devuelve (Serie D_t, caida maxima como numero negativo).
    """
    d = prices / prices.cummax() - 1
    return d, d.min()


def descriptives(g, m):
    """Estadistica descriptiva de los log-rendimientos.

    g -- Serie de log-rendimientos
    m -- periodos por anio (252 diaria, 52 semanal, 12 mensual)
    Devuelve un diccionario con las metricas descriptivas.

    La ventana de cobertura y el porcentaje de faltantes NO se calculan aqui:
    son propiedades de la serie de precios, que esta funcion no recibe.
    """
    mean, var, sd = sample_stats(g)
    mean_annual, sd_annual = annualize(mean, sd, m)
    return {
        "n": len(g),
        "mean_period": mean,
        "var_period": var,
        "sd_period": sd,
        "mean_annual": mean_annual,
        "sd_annual": sd_annual,
        "q05": g.quantile(0.05),
        "q95": g.quantile(0.95),
        "skew": stats.skew(g, bias=False),
        "kurtosis": stats.kurtosis(g, fisher=True, bias=False),
    }


def diagnostics(g, alpha=0.05, blocks=3):
    """Cuatro contrastes sobre los supuestos de los log-rendimientos.

    g      -- Serie de log-rendimientos
    alpha  -- nivel de significancia (la guia fija 0.05)
    blocks -- bloques cronologicos para Brown-Forsythe (la guia fija 3)
    Devuelve un diccionario con los parametros usados y, por contraste,
    su estadistico, p-valor y si rechaza.
    """
    n = len(g)
    lags = min(10, n // 5)
    centered = g - g.mean()
    partes = np.array_split(g.to_numpy(), blocks)

    jb = stats.jarque_bera(g)
    lb = acorr_ljungbox(g, lags=[lags])
    bf = stats.levene(*partes, center="median")
    ar = het_arch(centered, nlags=lags)

    lb_stat = lb["lb_stat"].iloc[0]
    lb_p = lb["lb_pvalue"].iloc[0]

    return {
        "alpha": alpha,
        "lags": lags,
        "blocks": blocks,
        "jarque_bera": {"statistic": jb.statistic, "pvalue": jb.pvalue,
                        "reject": jb.pvalue < alpha},
        "ljung_box": {"statistic": lb_stat, "pvalue": lb_p,
                      "reject": lb_p < alpha},
        "brown_forsythe": {"statistic": bf.statistic, "pvalue": bf.pvalue,
                           "reject": bf.pvalue < alpha},
        "arch_lm": {"statistic": ar[0], "pvalue": ar[1],
                    "reject": ar[1] < alpha},
    }