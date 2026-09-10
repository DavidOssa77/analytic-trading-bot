"""Carga, validacion y remuestreo de precios ajustados"""

import pandas as pd

def load_fixture(path):
    """Carga el fixture del curso y devuelve la matriz de precios.

    path --> ruta al CSV en formato largo
    Devuelve un DataFrame ancho (fechas x tickers), ordenado y validado.
    """
    long_df = pd.read_csv(path, parse_dates=["date"])
    return validate_prices(wide_from_long(long_df))


import yfinance as yf


def fetch_prices(tickers, start, end):
    """Descarga precios ajustados de yfinance, aislando los fallos

    tickers --> lista de simbolos
    start, end --> fechas del rango
    Devuelve (precios, errores):
      precios --> DataFrame ancho con los tickers que respondieron
      errores --> dict {ticker: motivo} de los que fallaron

    Descarga uno a uno para que un simbolo invalido no arrastre a los
    demas
    """
    series, errores = {}, {}

    for t in tickers:
        try:
            df = yf.download(t, start=start, end=end,
                             auto_adjust=True, progress=False)
        except Exception as e:
            errores[t] = f"fallo la descarga: {e}"
            continue 

        if df is None or df.empty:
            errores[t] = "sin datos en el rango pedido"
            continue

        s = df["Close"].squeeze()
        if s.notna().sum() == 0:
            errores[t] = "todos los precios llegaron vacios"
            continue

        series[t] = s

    if not series:
        return pd.DataFrame(), errores

    return validate_prices(pd.DataFrame(series)), errores

def wide_from_long(long_df, value_col="adjusted_close"):
    """Convierte un DataFrame largo a uno ancho (fechas x tickers)

    long_df --> DataFrame con columnas 'date', 'ticker' y value_col
    value_col --> str, columna de precio a pivotear
    Devuelve DataFrame ancho, indice datetime, una columna por ticker.
    Duplicados de (date, ticker) se resuelven quedandose con el ultimo.
    """
    long_df = long_df.loc[:, ["date", "ticker", value_col]].copy()
    long_df["date"] = pd.to_datetime(long_df["date"])
    long_df = long_df.drop_duplicates(subset=["date", "ticker"], keep="last")
    wide = long_df.pivot(index="date", columns="ticker", values=value_col)
    return wide.rename_axis(columns=None)

PERIODOS_POR_ANIO = {"D": 252, "W-FRI": 52, "ME": 12}

def validate_prices(prices):
    """Aplica sobre un DataFrame ancho de precios (fechas x tickers)

    prices --> DataFrame, indice de fechas, una columna por ticker
    Devuelve el DataFrame validado; los precios no positivos quedan
    como NaN (faltante explicito), no se eliminan filas ni columnas.

     Ante fechas duplicadas se conserva el ultimo registro, aunque su precio
    sea invalido: en ese caso la observacion queda como faltante en lugar
    de recuperar el valor anterior
    """
    prices = prices.sort_index()
    prices = prices[~prices.index.duplicated(keep="last")]
    prices = prices.mask(prices <= 0)
    return prices 

def resample_prices(prices, freq):
    """Remuestrea PRECIOS a la frecuencia pedida, antes de calcular rendimientos.

    prices --> DataFrame o Serie de precios, indice de fechas
    freq   --> "D" diaria, "W-FRI" semanal cierre viernes, "ME" fin de mes
    Devuelve los precios remuestreados, tomando el ultimo valido de cada
    periodo y descartando los periodos sin ningun dato.

    El orden importa: remuestrear precios y luego calcular log-rendimientos
    NO da lo mismo que calcular rendimientos diarios y luego agregarlos.
    """
    if freq not in PERIODOS_POR_ANIO:
        raise ValueError(f"frecuencia desconocida: {freq}; use D, W-FRI o ME")
    if freq == "D":
        return prices
    return prices.resample(freq).last().dropna(how="all")

def coverage(prices):
    """Cobertura temporal y porcentaje de faltantes por activo.

    prices --> DataFrame ancho de precios
    Devuelve un DataFrame con una fila por activo: primera y ultima fecha
    con dato, cuantas observaciones validas tiene y que porcentaje falta.
    """
    return pd.DataFrame({
        "start": prices.apply(lambda s: s.first_valid_index()),
        "end": prices.apply(lambda s: s.last_valid_index()),
        "n": prices.notna().sum(),
        "missing_pct": prices.isna().mean() * 100,
    })

def align(prices):
    """Deja solo las fechas donde todos los activos tienen dato.

    prices --> DataFrame ancho de precios, ya remuestreado
    Devuelve el DataFrame recortado a la interseccion comun de fechas.

    Solo se usa en la vista comparativa: para un activo individual los
    huecos los resuelve log_returns con su dropna, sin sacrificar fechas
    por culpa de los demas activos
    """
    return prices.dropna(how="any")