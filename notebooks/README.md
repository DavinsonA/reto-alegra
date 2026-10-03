# Notebooks: el camino de los datos a las conclusiones

Cinco notebooks, en orden. Cada uno parte de los CSV originales, muestra la evidencia y termina en la decisión que
alimentó. Los números que citan README, HALLAZGOS y NOTA_CORTA se recalculan aquí y se contrastan contra
`app/data/key_figures.csv` en la última celda de cada notebook.

| # | Notebook | Pregunta | Qué salió de aquí |
|---|---|---|---|
| 01 | `01_perfilado_y_calidad.ipynb` | ¿Qué hay en los tres CSV y qué les falta? | Supuesto cero, unidades, ventana desde abr-2022, cobertura de Industry, signos del S&M |
| 02 | `02_la_caja_no_es_mrr.ipynb` | ¿Un mes en 0 es churn? | Huecos, puestas al día, 751 churns falsos: regla de mora (D1) |
| 03 | `03_precio_y_descuentos.ipynb` | ¿Fue el cliente o fue Finora? | Patrón retroactivo 1 + k·p, bajadas a la mitad ambiguas: líneas de pricing (D2) y dos capas (D3) |
| 04 | `04_modelo_corregido_vs_actual.ipynb` | ¿Cuánto cambia la lectura del MRR? | Puente actual vs. corregido (4,1× / 14,4×), caja que no es MRR, sensibilidad, retención, respuesta al CFO |
| 05 | `05_lado_won_del_funnel_y_sm.ipynb` | ¿Dónde se pierde el crecimiento? | Más clientes pero más pequeños, Kitagawa (97 % dentro de industria), S&M y CAC |

## Reproducir

Los CSV del reto no están en el repositorio: copiarlos en `data/`.

```bash
pip install -r requirements.txt -r requirements-dev.txt
jupyter lab notebooks/
```

Los notebooks están guardados con sus salidas. Ninguna salida muestra el identificador de un cliente: los ejemplos
se imprimen como series anónimas y todas las tablas son agregadas.
