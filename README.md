# Finora: del dato a la decisión

Solución al reto de Business Analytics de Alegra: dos preguntas de negocio, una del **CFO** (¿por qué cambió el MRR y cuánto es cliente vs. pricing o descuentos?) y una del **CRO** (más leads, pero no más ventas).

Tres apps, una por uso, sobre el mismo motor y las mismas tablas agregadas:

| App | Para qué | Link |
|---|---|---|
| **Historia ejecutiva** (`app/historia.py`) | Video 1: situación, hallazgos, implicación, decisión y acción, una idea por pantalla | [finora-historia](https://finora-historia.streamlit.app/) |
| **Demo y proceso con IA** (`app/demo.py`) | Video 2: cómo trabajé con IA y el análisis completo de los dos casos | [finora-demo](https://finora-demo.streamlit.app/) |
| **Tablero operativo** (`app/tablero.py`) | Revisiones futuras: mensual del MRR (CFO) y semanal del funnel (CRO) | [finora-tablero](https://finora-tablero.streamlit.app/) |

**Bitácora de IA:** [`AI_LOG.md`](AI_LOG.md) · **Hallazgos:** [`HALLAZGOS.md`](HALLAZGOS.md) · **Modelo de datos:** [`docs/modelo_datos.md`](docs/modelo_datos.md)

## La idea central

Finora ve números, pero no los entiende lo suficiente para decidir. En los dos casos el problema es el mismo: **el modelo actual mezcla lo que hace el cliente con lo que hacemos nosotros** (calendario de cobro, precios, descuentos, mezcla de canales).

- **CFO:**
  - El modelo actual (cliente + mes + monto pagado) usa la **caja como si fuera MRR**. Lee la mora, las puestas al día, los prepagos y los retroactivos de precio como churn, reactivación y expansión, y exagera el churn ~4× y la reactivación ~13×.
  - Propuesta: **MRR en dos capas** (lista − descuento = neto), con el descuento como entidad con vigencia. **El fin de un descuento no es expansión.**
- **CRO:**
  - Con datos reales, Finora gana el doble de clientes por mes, pero **más pequeños**: el MRR nuevo crece la mitad y el 97% de la caída del ticket ocurre dentro de cada industria.
  - Sin datos del funnel, se entrega el **diseño** (tres caminos, conversión por cohorte, mezcla vs. tasa, speed-to-lead, control estadístico) y un **prototipo sintético** que demuestra que el tablero detecta problemas plantados.

## Estructura

```
finora/            motor de análisis
  load.py            carga y conversión a COP (×10.000 ingresos; ×100.000.000 S&M)
  mrr.py             modelo actual vs. corregido (mora, puestas al día, prepagos, retroactivos, subidas de precio)
  two_layer.py       modelo propuesto de dos capas (cliente vs. pricing/descuentos)
  aggregates.py      tablas agregadas para la demo (sin detalle por cliente)
  funnel.py          métricas del funnel (cohortes, Kitagawa, speed-to-lead, gráfico de control, estancados)
  funnel_synth.py    generador SINTÉTICO del funnel con problemas plantados
  xmr.py             gráfico de comportamiento del proceso (señal vs. ruido, Wheeler)
sql/               mismo análisis en SQL (DuckDB/Postgres) + DDL del modelo de dos capas
tests/             48 pruebas: casos del CFO, conciliación, SQL = Python, XmR, smoke test de las 3 apps
app/               las tres apps en Streamlit (leen solo app/data/, agregados)
  historia.py        historia ejecutiva (video 1)
  demo.py            proceso con IA y análisis completo (video 2)
  tablero.py         tablero operativo para revisiones futuras
  operar.py          vistas del tablero: revisión mensual del MRR (CFO) y semanal del funnel (CRO)
  common.py          datos, constantes y navegación compartidos por las tres apps
  brand.py           marca (un solo tema, claro) y componentes de gráfico
docs/              modelo de datos, diccionario de métricas y diseño del tablero (investigación)
notebooks/         exploración inicial (perfilado)
pipeline.py        corre todo y regenera app/data/
```

## Reproducir

Los CSV del reto no están en el repositorio. Para reproducir, copia `Transactions.csv`, `S&M_spend.csv` e `Industry.csv` en `data/`.

```bash
python -m venv .venv && .venv/Scripts/activate        # en Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python pipeline.py                 # imprime hallazgos y regenera app/data/
pytest -q                          # 48 pruebas
streamlit run app/historia.py      # o app/demo.py, o app/tablero.py
```

## Decisiones de modelado (resumen)

| Regla | Por qué |
|---|---|
| La caja no es MRR. Una mora de ≤ 2 meses (o pagada completa después) mantiene al cliente activo | Práctica de ChartMogul: las suscripciones en mora cuentan en el MRR hasta su cancelación |
| El exceso de una puesta al día es cobro de mora, no expansión | Normalizar el MRR independiente del momento de pago |
| Prepagos: se reparten en min(12, meses cubiertos) | Los pagos multi-período se mensualizan |
| Las subidas de precio van en su propia línea; el retroactivo es un cargo único | Separar decisiones de Finora del comportamiento del cliente |
| Bajadas exactas a la mitad: contracción **marcada como ambigua** | Con caja no se puede distinguir un descuento de un downgrade: por eso se propone el modelo de dos capas |
| Ventana desde abr-2022 | Censura a la izquierda (los clientes de ene-2022 ya existían) |

Cada regla tiene un análisis de sensibilidad (`app/data/bridge_monthly.csv`, escenarios N = 1/2/3, sin separar precio, mora final = churn).

## Privacidad de datos

La demo pública solo usa tablas **agregadas** (por mes, industria, cohorte o escenario). El exportador falla si alguna tabla trae `customer_id`. El funnel es **sintético** y está rotulado como tal.
