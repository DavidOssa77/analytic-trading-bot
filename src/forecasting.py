"""Modelos homocedasticos, trayectoria analitica y validacion walk-forward."""

import numpy as np
from .analytics import sample_stats
import pandas as pd
from scipy.stats import norm

def fit(g_train, model):
    """Estima los parametros por periodo con el bloque de entrenamiento

    g_train --> Serie de log-rendimientos, SOLO del entrenamiento
    model --> "A" caminata aleatoria sin deriva, "B" caminata aleatoria lognormal con deriva
    Devuelve (mu, sigma) por periodo, nunca anualizados
    """
    if model not in ("A", "B"): #con esto valido que alguien no ingrese C o D o cualquier cosa
        raise ValueError(f"modelo desconocido: {model}; use 'A' o 'B'")
    mean, sigma = sample_stats(g_train)

    if(model == 'A'):
        mu = 0
    else:
        mu = mean
    return mu, sigma

def cumulative_moments(mu, sigma, h):

    """Media y varianza del log-rendimiento acumulado a h periodos
        Convierte los parámetros de un periodo (los obtenidos con fit) en parámetros 
        para H periodos

    mu, sigma --> estimadores por periodo, tal como los devuelve fit()
    h --> numero de periodos hacia adelante
    Devuelve (m, v) 
    """
    return h * mu, h * sigma ** 2

def terminal(P_t, m, v, params):
    """Distribucion del precio dados los momentos acumulados

    P_t --> ultimo precio observado
    m, v --> momentos acumulados, como los devuelve cumulative_moments
    params --> Params; se leen p_L y p_U para los cuantiles
    Devuelve un diccionario con mediana, media y los dos cuantiles

    Funciona con m y v escalares o como arrays: en el segundo caso
    devuelve un array por clave, que es lo que aprovecha path()
    """
    sd = np.sqrt(v)
    return {
        "median": P_t * np.exp(m),
        "mean": P_t * np.exp(m + v / 2),
        "q_L": P_t * np.exp(m + norm.ppf(params.p_L) * sd),
        "q_U": P_t * np.exp(m + norm.ppf(params.p_U) * sd),
    }

def path(P_t, mu, sigma, H, params):
    """Trayectoria analitica de 1 a H.

    P_t --> ultimo precio observado
    mu, sigma --> estimadores por periodo, como los devuelve fit()
    H --> horizonte maximo
    params --> Params; se leen p_L y p_U
    Devuelve un DataFrame con una fila por paso y columnas
    h, median, mean, q_L, q_U.
    """
    h = np.arange(1, H + 1)
    m, v = cumulative_moments(mu, sigma, h)
    df = pd.DataFrame(terminal(P_t, m, v, params))
    df.insert(0, "h", h)
    return df

def walk_forward(g, model, H, m, params):
    """Validacion temporal sin mirar el futuro (look ahead bias)

    Reestima el modelo en los diez ultimos origenes con ventana expansiva
    y mide el error contra lo que realmente paso.

    g --> Serie completa de log-rendimientos
    model --> "A" o "B"
    H --> horizonte
    m --> periodos por año, para el criterio de suficiencia
    params --> Params; se leen p_L y p_U para la cobertura
    Devuelve un diccionario con la suficiencia y, si se cumple, las metricas
    """
    T = len(g)
    n_min = max(2 * m, 5 * H)
    if T < n_min + H + 9:
        return {"sufficient": False, "T": T, "n_min": n_min,
                "required": n_min + H + 9}

    origins = [T - H - 9 + j for j in range(10)]
    errors, inside, dir_ok, dir_n = [], 0, 0, 0

    for o in origins:
        mu, sigma = fit(g.iloc[:o], model)
        m_H, v_H = cumulative_moments(mu, sigma, H)
        Y = g.iloc[o:o + H].sum()
        errors.append(Y - m_H)

        sd = np.sqrt(v_H)
        lo = m_H + norm.ppf(params.p_L) * sd
        hi = m_H + norm.ppf(params.p_U) * sd
        inside += (lo <= Y <= hi)

        if abs(m_H) > 1e-12 and abs(Y) > 1e-12:
            dir_n += 1
            dir_ok += (np.sign(m_H) == np.sign(Y))

    errors = np.array(errors)
    return {
        "sufficient": True,
        "origins": origins,
        "errors": errors,
        "mae": np.abs(errors).mean(),
        "rmse": np.sqrt((errors ** 2).mean()),
        "coverage": inside / len(origins),
        "direction": None if dir_n == 0 else dir_ok / dir_n,
        "direction_n": dir_n,
    }