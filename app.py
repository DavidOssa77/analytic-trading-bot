"""Interfaz Streamlit del robot analitico para preseleccion de activos."""

from datetime import date

import pandas as pd
import streamlit as st

import charts
import src.contracts as ct
import src.data as dt
import src.pipeline as pl
import src.compare as cp

FIXTURE = "notebooks/Fixture_20_activos_sintetico_TBS_EIA.csv"
VISTAS = ["Datos", "Resumen", "Precio", "Rendimientos", "Proyeccion",
          "Comparacion", "Metodologia"]
VISTAS_ACTIVO = ("Resumen", "Precio", "Rendimientos", "Proyeccion")
DIAGS = ("jarque_bera", "ljung_box", "brown_forsythe", "arch_lm")

AVISO = (
    "Esta aplicación fue desarrollada exclusivamente como actividad evaluativa "
    "del curso Teoría Moderna de Portafolios de Tech Business School - "
    "Universidad EIA. Sus datos, modelos y resultados tienen fines académicos "
    "y educativos. En ningún momento constituye asesoría financiera, "
    "recomendación de inversión ni una herramienta para tomar decisiones de "
    "inversión en la vida real. Es una herramienta académica que deberá "
    "revisarse, validarse y ajustarse, y puede contener errores, omisiones, "
    "rezagos o información incompleta. El sistema no ejecuta operaciones ni "
    "garantiza resultados.")

st.set_page_config(page_title="Robot analitico", layout="wide")


@st.cache_data
def cargar_fixture(path):
    """Lee el fixture una sola vez por sesion."""
    return dt.load_fixture(path)


@st.cache_data
def descargar(tickers, inicio, fin):
    """Descarga de yfinance, cacheada por combinacion de argumentos."""
    return dt.fetch_prices(list(tickers), inicio, fin)


# ---------------------------------------------------------------- sidebar
st.sidebar.title("Robot analitico")
vista = st.sidebar.radio("Vista", VISTAS)

st.sidebar.divider()
fuente = st.sidebar.radio("Fuente", ["Fixture del curso", "Yahoo Finance"])

if fuente == "Yahoo Finance":
    texto = st.sidebar.text_input("Tickers", "AAPL, MSFT, KO")
    tickers = tuple(t.strip().upper() for t in texto.split(",") if t.strip())
    inicio = st.sidebar.date_input("Desde", date(2021, 1, 1))
    fin = st.sidebar.date_input("Hasta", date.today())

st.sidebar.divider()
st.sidebar.caption("Parametros")
freq = st.sidebar.selectbox("Frecuencia", list(dt.PERIODOS_POR_ANIO))
H = st.sidebar.number_input("Horizonte H", min_value=1, value=20,
                            help="Periodos hacia adelante, en la frecuencia "
                                 "elegida. Un horizonte largo frente a la "
                                 "historia disponible deja sin validar el "
                                 "walk-forward.")
modelo = st.sidebar.selectbox("Modelo", ["A", "B"])

params = ct.Params(
    cost_buy=st.sidebar.number_input("Comision compra", 0.0, 0.05, 0.0, 0.0005, "%.4f"),
    cost_sell=st.sidebar.number_input("Comision venta", 0.0, 0.05, 0.0, 0.0005, "%.4f"),
    BR_min=st.sidebar.number_input("BR minimo", 0.0, 5.0, 1.0, 0.1),
    confidence=st.sidebar.select_slider("Confianza VaR", [0.95, 0.99], 0.95),
    capital=st.sidebar.number_input("Capital", 1000, 1_000_000, 10_000, 1000),
)

# ------------------------------------------------------------------ datos
if fuente == "Fixture del curso":
    precios = cargar_fixture(FIXTURE)
    errores = {}
    origen = "Fixture sintetico del curso — precios simulados, no datos de mercado"
else:
    precios, errores = descargar(tickers, str(inicio), str(fin))
    origen = f"Yahoo Finance — {inicio} a {fin}"

if precios.empty:
    st.error("No se pudo cargar ningun activo.")
    st.stop()

precios = dt.resample_prices(precios, freq)
m = dt.PERIODOS_POR_ANIO[freq]

# --------------------------------------------------------------- cabecera
st.title("Robot analitico para preseleccion de activos")
st.caption(origen)

if errores:
    st.warning(
        f"No se pudieron descargar {len(errores)} de "
        f"{len(errores) + precios.shape[1]} tickers: "
        + ", ".join(errores)
        + ". El analisis continua con los que si respondieron.")
    with st.expander("Ver el motivo de cada fallo"):
        for t, motivo in errores.items():
            st.write(f"**{t}** — {motivo}")
        st.caption(
            "yfinance no distingue un simbolo inexistente de uno sin datos "
            "en el rango: en ambos casos devuelve una tabla vacia. Revisa la "
            "escritura del ticker y el periodo pedido.")

# ----------------------------------------------------------------- vistas
if vista in VISTAS_ACTIVO:
    ticker = st.selectbox("Activo", list(precios.columns))
    serie = precios[ticker].dropna()
    r = pl.analyze(serie, params, modelo, H, m) #punto de entrada del bot

if vista == "Datos":
    st.subheader("Cobertura")
    st.dataframe(dt.coverage(precios), width="stretch")

    st.subheader("Ultimos precios")
    st.dataframe(precios.tail(50), width="stretch")

elif vista == "Resumen":
    puerta = r["gate"]
    niveles = r["levels"]

    if puerta["signal"]:
        st.success(f"SEÑAL — pronostico {puerta['label']}")
    else:
        st.error("SIN SEÑAL")
        st.write("Reglas incumplidas:")
        for regla in puerta["failed"]:
            st.write(f"- {regla}")

    if puerta["warnings"]:
        st.warning("Advertencias: " + ", ".join(puerta["warnings"]))

    st.subheader("Niveles")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Entrada", f"{niveles['E']:.2f}")
    c2.metric("Stop-loss", f"{niveles['SL']:.2f}",
              f"{niveles['SL'] / niveles['E'] - 1:.2%}")
    c3.metric("Take-profit", f"{niveles['TP']:.2f}",
              f"{niveles['TP'] / niveles['E'] - 1:.2%}")
    c4.metric("Equilibrio", f"{niveles['P_BE']:.2f}")

    st.subheader("Riesgo y recompensa")
    d1, d2, d3 = st.columns(3)
    br = niveles["BR_neto"]
    d1.metric("BR neto", f"{br:.3f}" if br is not None else "n/d")
    d2.metric(f"VaR {params.confidence:.0%}", f"{r['var_frac']:.2%}",
              f"-{r['var_money']:,.0f} de {params.capital:,.0f}",
              delta_color="inverse")
    d3.metric("Pr(ganar)", f"{r['probs']['win']:.1%}")

    st.subheader("Validacion temporal")
    wf = r["walk_forward"]
    if wf["sufficient"]:
        e1, e2, e3 = st.columns(3)
        e1.metric("Cobertura", f"{wf['coverage']:.2f}",
                  f"{wf['coverage'] - (params.p_U - params.p_L):+.2f} vs lo prometido")
        e2.metric("MAE", f"{wf['mae']:.4f}")
        direccion = wf["direction"]
        e3.metric("Direccion",
                  f"{direccion:.0%}" if direccion is not None else "n/d",
                  help="El modelo A no predice direccion: impone mu = 0, "
                       "asi que no hay signo que acertar.")
    else:
        st.info(f"Muestra insuficiente: {wf['T']} rendimientos, "
                f"hacen falta {wf['required']}.")

elif vista == "Precio":
    st.plotly_chart(charts.price_chart(serie, r["drawdown"], ticker),
                    width="stretch")
    st.caption(f"Caida maxima desde maximos: {r['max_drawdown']:.2%}. "
               "El drawdown se calcula sobre precios, no sobre rendimientos.")

elif vista == "Rendimientos":
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

elif vista == "Proyeccion":
    st.plotly_chart(
        charts.projection_chart(r["P_t"], r["path"], ticker,
                                params.p_L, params.p_U),
        width="stretch")
    st.caption("Cuantiles terminales en cada h, no un camino posible: el "
               "precio puede salirse de la banda y volver a entrar.")

    with st.expander("Ver la tabla"):
        st.dataframe(r["path"], width="stretch")

elif vista == "Comparacion":
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

elif vista == "Metodologia":
    st.subheader("Aviso")
    st.warning(AVISO)

    st.subheader("Que calcula este robot")
    st.markdown(
        "Preselecciona activos: no recomienda comprar ni vender. Estima "
        "rendimiento y riesgo bajo un modelo declarado, comprueba si la "
        "operacion es viable una vez pagadas las comisiones, y muestra **que "
        "regla incumple** cuando no lo es.")

    st.subheader("Convencion de rendimientos")
    st.latex(r"g_t = \ln\left(\frac{P_t}{P_{t-1}}\right)")
    st.markdown(
        "Log-rendimientos sobre precios **ajustados** por dividendos y splits. "
        "Los estadisticos usan varianza muestral (`ddof=1`), cuantiles de "
        "interpolacion lineal y asimetria y curtosis de Fisher sin sesgo.")

    st.subheader("Modelo")
    st.markdown(
        f"Se ajusta el modelo **{modelo}** sobre toda la muestra:\n\n"
        "- **A** — caminata aleatoria sin deriva: impone `mu = 0`\n"
        "- **B** — caminata con deriva: estima `mu` de la muestra\n\n"
        "Ambos comparten la misma volatilidad, constante en el tiempo. Los "
        "momentos se acumulan linealmente y la trayectoria es **analitica**, "
        "no simulada:")
    st.latex(r"m = h\,\mu \qquad v = h\,\sigma^2 \qquad "
             r"P_{t+h} = P_t\,e^{\,m + z_p\sqrt{v}}")

    st.subheader("Niveles, costos y señal")
    st.markdown(
        f"Con colas {params.p_L:.0%} y {params.p_U:.0%} se obtienen el "
        "stop-loss y el take-profit **terminales** en `t+H`, no barreras que "
        "se vigilen durante el camino. El precio de equilibrio incorpora las "
        "dos comisiones:")
    st.latex(r"P_{BE} = P_t\,\frac{1 + c_b}{1 - c_s}")
    st.markdown(
        "La puerta exige **siete condiciones** de geometria y viabilidad "
        "economica. Si alguna falla, no hay señal y se reporta cual. Los "
        "diagnosticos y la insuficiencia de muestra **advierten pero no "
        "bloquean**: etiquetan el pronostico como condicional y dejan la "
        "decision en manos de quien opera.")

    st.subheader("Limitaciones conocidas")
    st.markdown(
        "- **La homocedasticidad no se cumple.** ARCH-LM rechaza en "
        "practicamente cualquier serie financiera: la volatilidad viene por "
        "rachas. El modelo usa una volatilidad unica, asi que los intervalos "
        "son correctos en promedio pero mal calibrados en cada momento. La "
        "extension natural seria un GARCH, a costa de perder la forma cerrada.\n"
        "- **El VaR parametrico supone normalidad.** Con colas gruesas "
        "subestima la perdida extrema. No es la perdida maxima posible ni dice "
        "cuanto se pierde mas alla del cuantil.\n"
        "- **El walk-forward usa diez origenes solapados.** Comparten casi "
        "todas sus observaciones, asi que la cobertura tiende a salir cerca de "
        "0 o de 1 en vez de aproximarse al nivel prometido.\n"
        "- **El perfil de riesgo no entra en el calculo.** Un activo puede "
        "tener el mejor cociente retorno-volatilidad y aun asi ser inadecuado "
        "para quien lo mire.")

    st.subheader("Origen de los datos")
    st.info(origen)


else:
    st.info(f"Vista '{vista}' pendiente.")