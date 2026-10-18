"""Vista Metodologia: aviso, supuestos, modelos y limitaciones."""

import streamlit as st

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


def render(ctx):
    """Dibuja la vista con el contexto comun."""
    params, modelo, origen = ctx.params, ctx.modelo, ctx.origen
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
