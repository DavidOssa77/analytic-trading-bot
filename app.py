"""Interfaz Streamlit del robot analitico para preseleccion de activos."""

from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

import charts
import src.contracts as ct
import src.data as dt
import src.pipeline as pl
import src.compare as cp
import src.capm as cm

FIXTURE = "notebooks/Fixture_20_activos_sintetico_TBS_EIA.csv"
VISTAS = ["Datos", "Resumen", "Precio", "Rendimientos", "Proyeccion",
          "Comparacion", "CAPM", "Metodologia"]
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


@st.cache_data
def descargar_mercado(nombres, inicio, fin):
    """Indices de mercado, cacheados igual que los activos."""
    return dt.fetch_market(list(nombres), inicio, fin)


@st.cache_data
def descargar_tasa(plazo, inicio, fin):
    """Rendimiento del bono del Tesoro al plazo pedido."""
    return dt.fetch_rate(plazo, inicio, fin)


@st.cache_data
def descargar_fx(monedas, inicio, fin):
    """Tipos de cambio contra el dolar."""
    return dt.fetch_fx(list(monedas), inicio, fin)


# ---------------------------------------------------------------- sidebar
st.sidebar.title("Robot analitico")
vista = st.sidebar.radio("Vista", VISTAS, index=VISTAS.index("Metodologia"))

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

if vista == "CAPM":
    st.sidebar.divider()
    st.sidebar.caption("CAPM")
    freq_capm = st.sidebar.selectbox(
        "Frecuencia de la regresion", list(dt.PERIODOS_POR_ANIO), index=1,
        help="Semanal por defecto: con datos diarios, la diferencia de "
             "horarios entre bolsas sesga la beta hacia abajo.")
    if fuente == "Yahoo Finance":
        plazo = st.sidebar.selectbox(
            "Plazo de la tasa libre de riesgo",
            ["Automatico"] + list(dt.TASAS),
            help="Bono del Tesoro de EE.UU. Automatico elige el plazo mas "
                 "cercano al horizonte H. Los excesos de la regresion usan "
                 "siempre la letra a 13 semanas.")
        indice = st.sidebar.selectbox(
            "Indice de mercado",
            ["Automatico por pais"] + [v[1] for v in dt.MERCADOS.values()],
            help="Automatico asigna a cada activo el indice de su bolsa "
                 "segun el sufijo del ticker (.CL Colombia, .T Japon...).")
        en_usd = st.sidebar.checkbox(
            "Expresar todo en USD", True,
            help="Convierte activos e indices extranjeros a dolares, para "
                 "que sean consistentes con la tasa del Tesoro.")
    metodo_rm = st.sidebar.radio(
        "Rendimiento esperado del mercado", ["prima", "historico"],
        format_func={"prima": "rf + prima de riesgo",
                     "historico": "media historica del indice"}.get)
    params_capm = ct.CapmParams(
        freq=freq_capm,
        erp=st.sidebar.number_input(
            "Prima de riesgo de mercado", 0.0, 0.15, 0.05, 0.0025, "%.4f",
            disabled=metodo_rm != "prima",
            help="E[Rm] - rf anual. Referencia: la prima implicita que "
                 "publica Damodaran para EE.UU. ronda 4-5 %."),
        market_method=metodo_rm,
        beta_kind=st.sidebar.radio("Beta para el rendimiento requerido",
                                   ["ajustada", "cruda"]),
        rf_fixed=st.sidebar.number_input(
            "Tasa libre de riesgo (respaldo)" if fuente == "Yahoo Finance"
            else "Tasa libre de riesgo", 0.0, 0.20, 0.04, 0.0025, "%.4f",
            help="Tasa anual constante. Con Yahoo solo se usa si la "
                 "descarga del bono falla."),
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

precios_diarios = precios
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
                  f"{len(wf['origins'])} origenes solapados",
                  delta_color="off",
                  help=f"Proporcion de origenes donde el rendimiento real cayo "
                       f"dentro de la banda {params.p_L:.0%}-{params.p_U:.0%}. "
                       "Los origenes son consecutivos, asi que sus ventanas "
                       "comparten casi todas sus observaciones: la metrica "
                       "tiende a 0 o a 1 y no mide calibracion.")
        sd_H = np.sqrt(r["v_H"])
        e2.metric("MAE", f"{wf['mae']:.2%}",
                  f"{wf['mae'] / sd_H:.2f}x la volatilidad a H",
                  delta_color="off",
                  help="Error absoluto medio del pronostico central contra el "
                       "rendimiento logaritmico acumulado que realmente ocurrio, "
                       "promediado sobre los origenes.")
        direccion = wf["direction"]
        n_dir = wf["direction_n"]
        e3.metric("Direccion",
                  f"{direccion:.0%}" if direccion is not None else "n/d",
                  f"{round(direccion * n_dir)} de {n_dir} origenes"
                  if direccion is not None else "el modelo A no tiene deriva",
                  delta_color="off",
                  help="Proporcion de origenes donde el pronostico central "
                       "acerto el signo del rendimiento acumulado. El modelo A "
                       "impone mu = 0, asi que no hay signo que acertar y la "
                       "metrica queda sin definir. En el modelo B el pronostico "
                       "apunta siempre en el sentido de la deriva estimada, asi "
                       "que la metrica termina midiendo cuantas ventanas se "
                       "movieron en ese sentido, no la capacidad predictiva del "
                       "modelo.")
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

elif vista == "CAPM":
    avisos = []
    if fuente == "Fixture del curso":
        proxy = "Proxy equiponderado"
        activos = {t: precios_diarios[t].dropna() for t in precios_diarios}
        indice_de = {t: proxy for t in activos}
        moneda_de = {t: "USD" for t in activos}
        indices = {proxy: cm.equal_weight_index(precios_diarios)}
        simbolos = {proxy: "promedio de los activos"}
        rf_serie = rf_now = params_capm.rf_fixed
        plazo_usado = "constante"
        avisos.append(
            "El fixture no trae indice de mercado: se usa como proxy un "
            "portafolio equiponderado de los activos cargados, y cada activo "
            "forma parte del mercado contra el que se mide. La tasa libre de "
            "riesgo es la constante del panel.")
    else:
        activos = {t: precios_diarios[t].dropna() for t in precios_diarios}
        moneda_de = {t: dt.market_info(t)[0] for t in activos}
        indice_de = {t: dt.market_info(t)[1] if indice == "Automatico por pais"
                     else indice for t in activos}
        moneda_indice = {v[1]: v[0] for v in dt.MERCADOS.values()}

        descargados, err_idx = descargar_mercado(
            tuple(sorted(set(indice_de.values()))), str(inicio), str(fin))
        indices = {n: s for n, (_, s) in descargados.items()}
        simbolos = {n: sym for n, (sym, _) in descargados.items()}
        for n, motivo in err_idx.items():
            avisos.append(f"No se pudo descargar el indice {n} ({motivo}).")

        extranjeras = ({moneda_de[t] for t in activos}
                       | {moneda_indice[n] for n in indices}) - {"USD"}
        if en_usd and extranjeras:
            fx, err_fx = descargar_fx(tuple(sorted(extranjeras)),
                                      str(inicio), str(fin))
            for c, motivo in err_fx.items():
                avisos.append(f"Sin tipo de cambio {c}=X ({motivo}): se "
                              f"omiten los activos e indices en {c}.")
            activos = {t: dt.to_usd(s, moneda_de[t], fx)
                       for t, s in activos.items() if moneda_de[t] not in err_fx}
            indices = {n: dt.to_usd(s, moneda_indice[n], fx)
                       for n, s in indices.items()
                       if moneda_indice[n] not in err_fx}
            moneda_de = {t: "USD" for t in activos}
        elif extranjeras:
            avisos.append(
                "Hay activos o indices en " + ", ".join(sorted(extranjeras))
                + " que se analizan en moneda local contra una tasa del "
                "Tesoro en dolares: el exceso de rendimiento mezcla monedas.")

        plazo_usado = dt.tenor_for(H, m) if plazo == "Automatico" else plazo
        rf_serie, motivo = descargar_tasa("13 semanas", str(inicio), str(fin))
        if motivo:
            avisos.append(f"No se pudo descargar la letra a 13 semanas "
                          f"({motivo}): los excesos usan la tasa de respaldo.")
            rf_serie = params_capm.rf_fixed
        serie_plazo, motivo = descargar_tasa(plazo_usado, str(inicio), str(fin))
        if motivo:
            avisos.append(f"No se pudo descargar el bono a {plazo_usado} "
                          f"({motivo}): se usa la tasa de respaldo.")
            rf_now = params_capm.rf_fixed
        else:
            rf_now = float(serie_plazo.dropna().iloc[-1])

    resultados, omitidos = {}, {}
    for t, serie in activos.items():
        n = indice_de[t]
        if n not in indices:
            omitidos[t] = f"sin indice {n}"
            continue
        try:
            r = cm.analyze_asset(serie, indices[n], rf_serie, rf_now,
                                 params_capm)
        except Exception as e:
            omitidos[t] = f"la regresion fallo: {e}"
            continue
        if r["n"] < 20:
            omitidos[t] = f"solo {r['n']} periodos en comun con el indice"
            continue
        resultados[t] = r

    for a in avisos:
        st.warning(a)
    if omitidos:
        st.warning("Activos sin CAPM: " + "; ".join(
            f"{t} ({motivo})" for t, motivo in omitidos.items()))
    if not resultados:
        st.error("Ningun activo tiene datos suficientes para el CAPM.")
        st.stop()

    tabla = cm.capm_table(resultados, indice_de, moneda_de)
    tabla[tabla.columns[2:]] = tabla[tabla.columns[2:]].apply(pd.to_numeric)

    st.subheader("Tasa libre de riesgo y mercado")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tasa libre de riesgo", f"{rf_now:.2%}",
              f"plazo {plazo_usado}", delta_color="off")
    por_mercado = {indice_de[t]: r["E_Rm"] for t, r in resultados.items()}
    if len(set(por_mercado.values())) == 1:
        E_Rm = next(iter(por_mercado.values()))
        c2.metric("E[Rm]", f"{E_Rm:.2%}",
                  "rf + prima" if params_capm.market_method == "prima"
                  else "media historica", delta_color="off")
        c3.metric("Prima de mercado", f"{E_Rm - rf_now:.2%}")
    else:
        c2.metric("E[Rm]", "varia por indice")
        c3.write("  \n".join(f"**{n}**: {v:.2%}"
                              for n, v in por_mercado.items()))
    st.caption("Indices usados: " + ", ".join(
        f"{n} ({simbolos.get(n, '?')})" for n in sorted(set(tabla["market"]))))

    st.plotly_chart(charts.sml_chart(tabla), width="stretch")
    st.caption(
        "LMV ex post: exceso de rendimiento realizado contra beta. La recta "
        "une el activo libre de riesgo con el mercado realizado, asi que la "
        "distancia vertical de cada activo a su recta es su alfa de Jensen. "
        "Estar por encima significa que el activo rindio mas de lo que su "
        "riesgo sistematico justificaba en esta muestra, no que vaya a "
        "seguir haciendolo.")

    st.subheader("Tabla CAPM")
    nombres = {
        "market": "indice", "currency": "moneda", "n": "periodos",
        "beta": "beta", "beta_adj": "beta ajustada", "beta_p": "p beta",
        "alpha_annual": "alfa anual", "alpha_p": "p alfa", "r2": "R2",
        "share_systematic": "riesgo sistematico",
        "mean_annual": "rend. historico", "volatility_annual": "volatilidad",
        "required_return": "rend. requerido", "sharpe": "Sharpe",
        "treynor": "Treynor"}
    vista_tabla = tabla[list(nombres)].rename(columns=nombres)
    st.dataframe(
        vista_tabla.sort_values("beta", ascending=False).style.format({
            "beta": "{:.3f}", "beta ajustada": "{:.3f}", "p beta": "{:.4f}",
            "alfa anual": "{:.2%}", "p alfa": "{:.4f}", "R2": "{:.3f}",
            "riesgo sistematico": "{:.1%}", "rend. historico": "{:.2%}",
            "volatilidad": "{:.2%}", "rend. requerido": "{:.2%}",
            "Sharpe": "{:.3f}", "Treynor": "{:.4f}"}),
        width="stretch")
    st.caption(
        f"Rendimientos simples, frecuencia {params_capm.freq}, anualizados. "
        f"El rendimiento requerido usa la beta {params_capm.beta_kind}: "
        "rf + beta (E[Rm] - rf). Un p-valor de alfa alto significa que no "
        "se puede distinguir el alfa de cero.")

    st.subheader("Detalle por activo")
    ticker = st.selectbox("Activo", list(resultados))
    r = resultados[ticker]
    st.plotly_chart(charts.regression_chart(
        r["excess"], r["alpha_period"], r["beta"], ticker, indice_de[ticker]),
        width="stretch")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Beta", f"{r['beta']:.3f}",
              f"ajustada {r['beta_adj']:.3f}", delta_color="off",
              help="Ajuste de Blume: 0.67 beta + 0.33. Las betas tienden a "
                   "regresar a 1 con el tiempo.")
    d2.metric("Alfa de Jensen anual", f"{r['alpha_annual']:.2%}",
              f"p-valor {r['alpha_p']:.3f}", delta_color="off")
    d3.metric("R2", f"{r['r2']:.3f}",
              f"{r['share_systematic']:.0%} del riesgo es sistematico",
              delta_color="off",
              help="El resto es riesgo idiosincratico: el que se puede "
                   "eliminar diversificando y que el CAPM no remunera.")
    d4.metric("Rendimiento requerido", f"{r['required_return']:.2%}",
              f"historico {r['mean_annual']:.2%}", delta_color="off")

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

    st.subheader("CAPM")
    st.markdown(
        "La vista CAPM mide cada activo contra el indice de su mercado con "
        "el **modelo de mercado en excesos**, sobre rendimientos **simples** "
        "(el CAPM es lineal en rendimientos y los log-rendimientos no se "
        "suman entre activos):")
    st.latex(r"R_{i,t} - r_{f,t} = \alpha_i + \beta_i\,(R_{m,t} - r_{f,t})"
             r" + \varepsilon_{i,t}")
    st.markdown(
        "- **Mercado.** Con Yahoo, el indice de la bolsa del activo segun el "
        "sufijo del ticker (S&P 500 sin sufijo, COLCAP para `.CL`, Nikkei "
        "para `.T`...). Con el fixture, un proxy equiponderado de los "
        "activos cargados. Ningun indice es el portafolio de mercado del "
        "CAPM, que contiene todos los activos riesgosos y no es observable "
        "(critica de Roll).\n"
        "- **Moneda.** Activos e indices extranjeros se convierten a dolares "
        "con el tipo de cambio del dia, para ser consistentes con la tasa "
        "del Tesoro de EE.UU.\n"
        "- **Tasa libre de riesgo.** Los excesos de la regresion restan la "
        "letra del Tesoro a 13 semanas vigente al inicio de cada periodo, "
        "convertida a tasa por periodo. El rendimiento requerido usa el bono "
        "cuyo plazo se acerca mas al horizonte de inversion.\n"
        "- **Frecuencia.** Semanal por defecto: con datos diarios, los "
        "horarios distintos de cada bolsa sesgan la beta hacia cero.\n"
        "- **Beta ajustada de Blume**, `0.67 beta + 0.33`: corrige la "
        "tendencia de las betas a regresar a 1.")
    st.latex(r"E[R_i] = r_f + \beta_i\,(E[R_m] - r_f)")
    st.markdown(
        "`E[Rm]` sale de sumar a `rf` una prima de riesgo de mercado "
        "declarada, o de la media historica del indice, que es mucho mas "
        "ruidosa. La varianza del activo se separa en una parte "
        "**sistematica**, `beta^2 var(Rm)`, que el mercado remunera, y una "
        "**idiosincratica**, que se elimina diversificando.")

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
        "- **El CAPM se estima con historia.** La beta cambia en el "
        "tiempo y el alfa realizado no predice el alfa futuro; con pocos "
        "anios de datos casi ningun alfa es estadisticamente distinto de "
        "cero.\n"
        "- **El perfil de riesgo no entra en el calculo.** Un activo puede "
        "tener el mejor cociente retorno-volatilidad y aun asi ser inadecuado "
        "para quien lo mire.")

    st.subheader("Origen de los datos")
    st.info(origen)


else:
    st.info(f"Vista '{vista}' pendiente.")