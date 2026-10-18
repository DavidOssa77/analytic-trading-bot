"""Vista Datos: cobertura y ultimos precios."""

import streamlit as st

import src.data as dt


def render(ctx):
    """Dibuja la vista con el contexto comun."""
    precios = ctx.precios
    st.subheader("Cobertura")
    st.dataframe(dt.coverage(precios), width="stretch")

    st.subheader("Ultimos precios")
    st.dataframe(precios.tail(50), width="stretch")
