"""Vista Rendimientos: distribucion y diagnosticos de los log-rendimientos."""

import pandas as pd
import streamlit as st

from app import charts
from .comun import analisis_activo

DIAGS = ("jarque_bera", "ljung_box", "brown_forsythe", "arch_lm")


def render(ctx):
    """Dibuja la vista con el contexto comun."""
    ticker, _, r = analisis_activo(ctx)
    st.plotly_chart(charts.returns_hist(r["g"], ticker), width="stretch")

    st.subheader("Diagnosticos")
    diag = r["diagnostics"]
    st.dataframe(pd.DataFrame(
        {k: {"estadistico": diag[k]["statistic"],
             "p-valor": diag[k]["pvalue"],
             "rechaza": diag[k]["reject"]}
         for k in DIAGS}).T,
        width="stretch")
    st.caption(f"Nivel de significancia {diag['alpha']:.0%}. "
               "Un rechazo advierte sobre los supuestos del modelo, "
               "pero no suprime la señal.")
