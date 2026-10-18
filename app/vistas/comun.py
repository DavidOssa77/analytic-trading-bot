"""Piezas que comparten varias vistas."""

import streamlit as st

import src.pipeline as pl


def analisis_activo(ctx):
    """Selector del activo y motor completo sobre su serie.

    Lo usan Resumen, Precio, Rendimientos y Proyeccion.
    Devuelve (ticker, serie de precios, salida de pipeline.analyze).
    """
    ticker = st.selectbox("Activo", list(ctx.precios.columns))
    serie = ctx.precios[ticker].dropna()
    r = pl.analyze(serie, ctx.params, ctx.modelo, ctx.H, ctx.m)  # punto de entrada del bot
    return ticker, serie, r
