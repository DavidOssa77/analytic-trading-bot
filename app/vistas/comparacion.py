"""Vista Comparacion: mapa media-volatilidad y dominancia entre activos."""

import streamlit as st

import src.compare as cp
import src.data as dt
from app import charts


def render(ctx):
    """Dibuja la vista con el contexto comun."""
    precios, m = ctx.precios, ctx.m
    if precios.shape[1] < 2:
        st.warning(
            "Con un solo activo no hay comparacion posible: la dominancia "
            "compara cada activo contra los demas, y aqui no hay contra quien. "
            "Agrega mas tickers en el panel de la izquierda.")
        st.stop()

    alineado = dt.align(precios)
    perdidas = len(precios) - len(alineado)
    comp = cp.preselect(cp.summary(alineado, m))

    st.plotly_chart(charts.comparison_map(comp), width="stretch")
    st.caption(
        f"{int(comp['non_dominated'].sum())} de {len(comp)} activos no "
        "dominados.  \n"
        "Nota: esto no es una frontera eficiente de Markowitz, son activos "
        "individuales, sin pesos ni matriz de covarianzas")

    st.subheader("Tabla comparativa")
    st.dataframe(
        comp[["last_adjusted_close", "mean_log_annual", "volatility_annual",
              "individual_rvr", "max_drawdown", "non_dominated",
              "selected_max_rvr"]].sort_values("individual_rvr",
                                               ascending=False),
        width="stretch")

    if perdidas:
        st.caption(f"Se alinearon las series a fechas comunes: {perdidas} de "
                   f"{len(precios)} fechas quedaron fuera porque algun activo "
                   "no cotizo ese dia.")
