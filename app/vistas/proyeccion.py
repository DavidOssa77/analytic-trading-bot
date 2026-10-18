"""Vista Proyeccion: banda de cuantiles a lo largo del horizonte."""

import streamlit as st

from app import charts
from .comun import analisis_activo


def render(ctx):
    """Dibuja la vista con el contexto comun."""
    ticker, _, r = analisis_activo(ctx)
    params = ctx.params
    st.plotly_chart(
        charts.projection_chart(r["P_t"], r["path"], ticker,
                                params.p_L, params.p_U),
        width="stretch")
    st.caption("Cuantiles terminales en cada h, no un camino posible: el "
               "precio puede salirse de la banda y volver a entrar.")

    with st.expander("Ver la tabla"):
        st.dataframe(r["path"], width="stretch")
