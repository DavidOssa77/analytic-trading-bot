"""Figuras de Plotly para la interfaz."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

TEMA = "plotly_white"

def price_chart(prices, drawdown, ticker):
    """Precio y caida desde maximos, en dos paneles con eje de fechas comun

    prices --> Serie de precios ajustados
    drawdown --> Serie D_t, la primera salida de analytics.drawdown
    ticker --> nombre del activo, solo para el titulo

    Devuelve una figura de Plotly; no la muestra
    """
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7, 0.3], vertical_spacing=0.07,
                        subplot_titles=("precio ajustado", "caida desde maximos"))

    fig.add_trace(go.Scatter(x=prices.index, y=prices, name="precio",
                             line=dict(width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=drawdown.index, y=drawdown, name="drawdown",
                             fill="tozeroy", line=dict(width=1)), row=2, col=1)

    fig.update_yaxes(title_text="USD", row=1, col=1)
    fig.update_yaxes(title_text="caida", tickformat=".0%", row=2, col=1)
    fig.update_layout(template=TEMA, height=540, showlegend=False,
                      hovermode="x unified",
                      title=f"{ticker} - precio y drawdown")
    return fig

def comparison_map(comp):
    """Mapa media-volatilidad con la frontera de activos no dominados.

    comp --> DataFrame como el que devuelve compare.preselect, indexado
             por ticker y con las columnas volatility_annual,
             mean_log_annual, individual_rvr, non_dominated y
             selected_max_rvr
    """
    nd = comp["non_dominated"]
    fig = go.Figure()

    for sub, nombre, simbolo, tam in ((comp[~nd], "dominados", "circle-open", 9),
                                      (comp[nd], "no dominados", "circle", 13)):
        posiciones = ["middle right" if sel else "top center"
                      for sel in sub["selected_max_rvr"]]
        fig.add_trace(go.Scatter(
            x=sub["volatility_annual"], y=sub["mean_log_annual"],
            mode="markers+text", text=sub.index, textposition=posiciones,
            textfont=dict(size=10), name=nombre,
            marker=dict(size=tam, symbol=simbolo, line=dict(width=1.5)),
            customdata=sub["individual_rvr"],
            hovertemplate="<b>%{text}</b><br>volatilidad %{x:.2%}"
                          "<br>retorno %{y:.2%}<br>rvr %{customdata:.3f}"
                          "<extra></extra>"))

    elegido = comp[comp["selected_max_rvr"]]
    fig.add_trace(go.Scatter(
        x=elegido["volatility_annual"], y=elegido["mean_log_annual"],
        mode="markers", name="mayor rvr", hoverinfo="skip",
        marker=dict(size=26, symbol="star-open", line=dict(width=2))))

    fig.update_layout(
        template=TEMA, height=560,
        title="Mapa media-volatilidad - activos no dominados",
        xaxis=dict(title="volatilidad anual", tickformat=".1%"),
        yaxis=dict(title="retorno anual", tickformat=".1%"),
        legend=dict(orientation="h", y=-0.15))
    return fig

def projection_chart(P_t, trayectoria, ticker, p_L, p_U):
    """Banda de cuantiles, mediana y media a lo largo del horizonte.

    P_t --> ultimo precio, el punto de partida
    trayectoria --> DataFrame como el que devuelve forecasting.path,
                    con columnas h, median, mean, q_L y q_U
    ticker --> nombre del activo, para el titulo
    p_L, p_U --> probabilidades de cola, solo para rotular la banda
    """
    t = trayectoria
    banda = f"{p_U - p_L:.0%} central"
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=t["h"], y=t["q_U"], mode="lines",
                             line=dict(width=0), hoverinfo="skip",
                             showlegend=False))
    fig.add_trace(go.Scatter(x=t["h"], y=t["q_L"], mode="lines", name=banda,
                             line=dict(width=0), fill="tonexty",
                             fillcolor="rgba(42,120,214,0.15)",
                             hoverinfo="skip"))

    fig.add_trace(go.Scatter(x=t["h"], y=t["median"], mode="lines",
                             name="mediana", line=dict(width=2)))
    fig.add_trace(go.Scatter(x=t["h"], y=t["mean"], mode="lines", name="media",
                             line=dict(width=1.5, dash="dot")))

    fig.add_hline(y=P_t, line=dict(width=1, dash="dash", color="gray"),
                  annotation_text=f"P_t = {P_t:.2f}",
                  annotation_position="bottom right")

    fig.update_layout(
        template=TEMA, height=480, hovermode="x unified",
        title=f"{ticker} - proyeccion a {int(t['h'].max())} periodos",
        xaxis=dict(title="horizonte h"), yaxis=dict(title="precio (USD)"),
        legend=dict(orientation="h", y=-0.18))
    return fig

def returns_hist(g, ticker, bins=40):
    """Distribucion de los log-rendimientos contra la normal ajustada.

    g --> Serie de log-rendimientos
    ticker --> nombre del activo, para el titulo
    bins --> numero aproximado de barras

    Devuelve una figura de Plotly; no la muestra.

    La curva es la normal con la media y la desviacion de la propia
    muestra: hace visible el supuesto que contrasta Jarque-Bera. Si las
    barras se despegan de la curva en las colas o en el centro, ahi esta
    la razon por la que ese contraste rechaza.
    """
    media, sd = g.mean(), g.std(ddof=1)
    x = np.linspace(g.min(), g.max(), 200)
    normal = np.exp(-((x - media) ** 2) / (2 * sd ** 2)) / (sd * np.sqrt(2 * np.pi))

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=g, nbinsx=bins, histnorm="probability density",
                               name="observados", opacity=0.75,
                               hovertemplate="rendimiento %{x:.2%}"
                                             "<br>densidad %{y:.1f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=normal, mode="lines", name="normal ajustada",
                             line=dict(width=2), hoverinfo="skip"))

    fig.add_vline(x=media, line=dict(width=1, dash="dash", color="gray"),
                  annotation_text=f"media {media:.3%}", annotation_position="top")

    fig.update_layout(
        template=TEMA, height=440, bargap=0.02,
        title=f"{ticker} - distribucion de los log-rendimientos",
        xaxis=dict(title="log-rendimiento", tickformat=".1%"),
        yaxis=dict(title="densidad"),
        legend=dict(orientation="h", y=-0.2))
    return fig