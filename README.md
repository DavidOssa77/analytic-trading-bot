# Robot Analítico para la Preselección de Activos

> Esta aplicación fue desarrollada exclusivamente como actividad evaluativa del
> curso Teoría Moderna de Portafolios de Tech Business School - Universidad EIA.
> Sus datos, modelos y resultados tienen fines académicos y educativos. En
> ningún momento constituye asesoría financiera, recomendación de inversión ni
> una herramienta para tomar decisiones de inversión en la vida real. Es una
> herramienta académica que deberá revisarse, validarse y ajustarse, y puede
> contener errores, omisiones, rezagos o información incompleta. El sistema no
> ejecuta operaciones ni garantiza resultados.

Herramienta que estima rendimiento y riesgo de un conjunto de activos, comprueba
si una operación es viable una vez pagadas las comisiones y reporta **qué regla
incumple** cuando no lo es.
---
## Qué hace

Sobre una serie de precios ajustados, para cada activo:

1. Calcula log-rendimientos y estadística descriptiva anualizada
2. Contrasta cuatro supuestos del modelo (normalidad, independencia, varianza
   constante y volatilidad condicional)
3. Ajusta una caminata aleatoria **con** o **sin** deriva y proyecta precios a
   un horizonte `H` mediante fórmula cerrada, sin simulación
4. Deriva stop-loss, take-profit, precio de equilibrio con costos y VaR
   paramétrico
5. Valida el modelo contra lo que realmente ocurrió (walk-forward)
6. Decide si hay señal y, si no la hay, dice cuál de las siete reglas falló

Y sobre el conjunto: descarta los activos dominados en el plano
media-volatilidad y señala el de mejor razón retorno-volatilidad.

---

## Estructura

```
src/                  motor financiero — no conoce la interfaz
  contracts.py        parámetros del análisis
  data.py             carga, validación, remuestreo, cobertura, alineación
  analytics.py        descriptivos y diagnósticos
  forecasting.py      modelos A y B, trayectoria, walk-forward
  risk_rules.py       VaR, niveles con costos, probabilidades, puerta de señal
  compare.py          coordenadas históricas y dominancia
  pipeline.py         orquestador: encadena el motor sobre un activo
charts.py             figuras de Plotly
app.py                interfaz Streamlit
notebooks/            cuadernos de verificación
```

La separación es estricta: **`src/` nunca importa Streamlit ni Plotly**. El
motor se puede ejecutar entero desde un notebook, sin necesidad de la interfaz.

---

## Instalación

Requiere **Python 3.12**.

> **Clona el repositorio en una ruta sin tildes ni símbolos.** En Windows,
> yfinance descarga a través de libcurl, que no sabe abrir rutas con caracteres
> no ASCII. Si el proyecto vive en una carpeta como `D:\7°semestre\Teoría...`,
> **todas** las descargas fallan con un error de certificados difícil de
> diagnosticar, porque el error que se reporta es «sin datos en el rango
> pedido».

```bash
git clone https://github.com/DavidOssa77/analytic-trading-bot.git
```

```bash
cd analytic-trading-bot
```

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## Uso

### La aplicación

Para abrir la app ejecutar lo siguiente en consola:
```bash
.venv\Scripts\python.exe -m streamlit run app.py
```

- Siete vistas: datos, resumen, precio, rendimientos, proyección, comparación y
metodología. 
- Los parámetros: fuente, frecuencia, horizonte, modelo, comisiones,razón beneficio-riesgo mínima, confianza y capital, se ajustan desde el panel lateral y recalculan todo al instante.

### Los cuadernos

```bash
.venv\Scripts\python.exe -m jupyter notebook
```

- **`notebooks/exploracion.ipynb`** recorre el motor completo sobre el fixture
  del curso y reproduce los casos de prueba.
- **`notebooks/datos_reales.ipynb`** ejercita lo que el fixture no puede probar:
  descarga desde Yahoo Finance, cobertura con huecos, alineación de calendarios
  distintos y remuestreo.

---

## Fuentes de datos

**Fixture del curso** (`notebooks/Fixture_20_activos_sintetico_TBS_EIA.csv`) —
veinte activos sintéticos y deterministas. Usa nombres de tickers reales como
etiquetas, pero **los precios no son datos de mercado**: AAPL cotiza a 73.63 en
el fixture y a 248.62 en la realidad. Su virtud es ser reproducible al decimal,
lo que permite verificar el motor contra resultados esperados.

**Yahoo Finance** — precios ajustados por dividendos y splits (`auto_adjust=True`).
Los tickers que fallan se aíslan: los válidos conservan su análisis y la
aplicación informa cuáles no respondieron.

---

## Verificación

El motor se contrasta contra los resultados esperados publicados por el curso.
Las quince columnas de los veinte activos coinciden con un error máximo de
`7.77e-16`, muy por debajo de la tolerancia exigida (`atol=1e-8`).

La sección final de `exploracion.ipynb` ejecuta esa comparación.

---

## Limitaciones conocidas

Medidas sobre los datos del proyecto y declaradas en la vista *Metodología* de la app:

- **La homocedasticidad no se cumple.** ARCH-LM rechaza en los veinte activos:
  la volatilidad viene por rachas. El modelo usa una volatilidad única, así que
  los intervalos son correctos en promedio pero mal calibrados en cada momento.
- **El VaR paramétrico supone normalidad** y subestima la pérdida extrema:
  2.84 % frente a 5.25 % del cuantil histórico sobre el mismo activo.
- **El walk-forward usa diez orígenes solapados**, que comparten casi todas sus
  observaciones; la cobertura tiende a salir cerca de 0 o de 1.
  individuales: no hay pesos ni matriz de covarianzas.
- **El perfil de riesgo del usuario no entra en ningún cálculo.**

---

## Equipo

### ** David Ossa, Maria Camila Gaviria, María Arango **

### Universidad EIA · 2026