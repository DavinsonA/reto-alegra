# Finora: del dato a la decisión

Solución al reto de Business Analytics de Alegra. Responde dos preguntas de negocio:
- **CFO:** ¿por qué cambió el MRR, y cuánto es cliente vs. pricing o descuentos?
- **CRO:** más leads, pero no más ventas: ¿dónde se pierde el crecimiento?

Tres apps, una por uso, sobre el mismo motor y las mismas tablas agregadas:

| App | Para qué | Link |
|---|---|---|
| **Historia ejecutiva** (`app/historia.py`) | Video 1: situación, hallazgos, implicación, decisión y acción, una idea por pantalla | [finora-historia](https://finora-historia.streamlit.app/) |
| **Demo y proceso con IA** (`app/demo.py`) | Video 2: cómo trabajé con IA y el análisis completo de los dos casos | [finora-demo](https://finora-demo.streamlit.app/) |
| **Tablero operativo** (`app/tablero.py`) | Revisiones futuras: mensual del MRR (CFO) y semanal del funnel (CRO) | [finora-tablero](https://finora-tablero.streamlit.app/) |

Si una app tarda en despertar (el plan gratuito de Streamlit las suspende sin tráfico), hay capturas de cada vista en
[`docs/capturas/`](docs/capturas/).

**Bitácora de IA:** [`AI_LOG.md`](AI_LOG.md) · **Hallazgos:** [`HALLAZGOS.md`](HALLAZGOS.md) · **Nota corta:** [`NOTA_CORTA.md`](NOTA_CORTA.md) · **Modelo de datos:** [`docs/modelo_datos.md`](docs/modelo_datos.md)

## La idea central

Finora ve números, pero no los entiende lo suficiente para decidir. En los dos casos el problema es el mismo: **el modelo actual mezcla lo que hace el cliente con lo que hacemos nosotros** (calendario de cobro, precios, descuentos, mezcla de canales).

- **CFO:**
  - El modelo actual (cliente + mes + monto pagado) usa la **caja como si fuera MRR**.
  - Lee la mora, las puestas al día, los prepagos y los retroactivos de precio como churn, reactivación y expansión.
  - Así exagera el churn 4,1 veces (entre 2,6 y 4,6 según la regla) y la reactivación 14,4 veces.
  - Propuesta: **MRR en dos capas** (lista − descuento = neto), con el descuento como entidad con vigencia. **El fin de un descuento no es expansión.**
- **CRO:**
  - Con datos reales, Finora gana el doble de clientes por mes (+106 %), pero **más pequeños**: el MRR nuevo crece +51 %. El 97 % de la caída del ticket ocurre dentro de cada industria.
  - Sin datos del funnel, se entrega el **diseño** (tres caminos, conversión por cohorte, mezcla vs. tasa, speed-to-lead, control estadístico) y un **prototipo sintético** que demuestra que el tablero detecta problemas plantados.

## Estructura

```
finora/      motor: carga y unidades (load), modelo actual vs. corregido (mrr), dos capas (two_layer), agregados y
             sensibilidad (aggregates), cifras clave y documentos (figures), funnel y prototipo sintético (funnel,
             funnel_synth), gráfico XmR (xmr)
sql/         el mismo análisis en DuckDB/Postgres y el DDL del modelo de dos capas
tests/       59 pruebas: casos del CFO, conciliación, SQL = Python, XmR, documentos y las 3 apps
app/         las tres apps en Streamlit (historia, demo, tablero) sobre app/data/, solo agregados
docs/        modelo de datos, diseño del tablero, plantillas de los documentos y capturas
notebooks/   5 notebooks con salidas: del perfilado a las conclusiones (notebooks/README.md)
pipeline.py  corre todo, regenera app/data/ y genera README, HALLAZGOS y NOTA_CORTA desde docs/plantillas/
```

## Reproducir

Los CSV del reto no están en el repositorio. Para reproducir, copia `Transactions.csv`, `S&M_spend.csv` e `Industry.csv` en `data/`.

```bash
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows
pip install -r requirements.txt
python pipeline.py                 # regenera app/data/ y los documentos con sus cifras
pytest -q                          # 59 pruebas
streamlit run app/historia.py      # o app/demo.py, o app/tablero.py
```

**Actualizar el tablero cada mes:** agregar el mes nuevo a los CSV de `data/`, correr `python pipeline.py` y `pytest -q`, y hacer push. Las apps se actualizan solas.

## Decisiones de modelado (resumen)

| Regla | Por qué |
|---|---|
| **Supuesto cero:** un 0 en `Transactions` es "no se cobró", no "no se facturó" | Si el 0 significara "sin servicio", el modelo de caja tendría razón y la mora no existiría. Toda la lógica de mora descansa en este supuesto |
| La caja no es MRR. Una mora de ≤ 2 meses (o pagada completa después) mantiene al cliente activo | Práctica de ChartMogul: las suscripciones en mora cuentan en el MRR hasta su cancelación |
| El exceso de una puesta al día es cobro de mora, no expansión | Normalizar el MRR independiente del momento de pago |
| Prepagos: se reparten en min(12, meses cubiertos); al final de la serie quedan en confirmación | Los pagos multi-período se mensualizan |
| Las subidas de precio van en su propia línea; el retroactivo es un cargo único; las del último mes quedan en confirmación | Separar decisiones de Finora del comportamiento del cliente |
| Bajadas exactas a la mitad: contracción **marcada como ambigua** | Con caja no se puede distinguir un descuento de un downgrade: por eso se propone el modelo de dos capas |
| Ventana desde abr-2022 | Censura a la izquierda (los clientes de ene-2022 ya existían) |

**Sensibilidad:** cada regla se apaga una a la vez en `app/data/rule_sensitivity.csv` (10 variantes). Ninguna cambia el signo ni el orden de magnitud: el churn corregido va de −15,7 a −27,6 MM, contra −72,9 MM del modelo actual.

## Privacidad de datos

Las apps públicas solo usan tablas **agregadas** (por mes, industria, cohorte o escenario). El exportador falla si alguna tabla trae `customer_id`. El funnel es **sintético** y está rotulado como tal.
