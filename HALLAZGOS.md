# Hallazgos con datos reales (v1, 2026-10-01)

> Generados por `pipeline.py` (motor en `finora/mrr.py`, 48 pruebas en `tests/`). Cifras en **millones de COP (MM)**.
> Ventana de análisis: **abr-2022 → oct-2024** (ene–mar 2022 = periodo de arranque por censura a la izquierda).
> Regla base: mora tolerada **N = 2** meses; las sensibilidades con N = 1 y N = 3 están en `outputs/rule_impact.csv`.

## Caso 2 (CFO): el modelo actual cuenta bien el total, pero explica mal el porqué

**Cambio de MRR: 42,6 → 97,6 MM (+55,0 MM).** Los dos modelos llegan casi al mismo MRR final. La diferencia está en **la explicación**:

| Movimiento (acumulado de la ventana) | Modelo actual (caja) | Modelo corregido | El actual lo exagera |
|---|---|---|---|
| New | +91,6 | **+67,1** | 1,4× |
| Expansión (cliente) | +38,5 | **+29,3** | 1,3× |
| Subida de precio (decisión Finora) | — (escondida en expansión) | **+1,7** | — |
| Contracción | −84,4 | **−31,7** | 2,7× |
| Churn | −72,9 | **−17,9** | **4,1×** |
| Reactivación | +84,7 | **+6,6** | **12,8×** |

**Por qué el actual se equivoca** (caja que no es MRR, en la ventana):
- **Mora y puestas al día:** 53,8 MM en 291 pagos que ponen al día meses atrasados.
- **Pagos agrupados:** 9,3 MM.
- **Picos puntuales:** 7,2 MM.
- **Prepagos multi-mes** (16 clientes, p. ej., anual con 25% de descuento): 9,0 MM.
- **Retroactivos de subidas de precio:** 0,9 MM.

Todo eso, el modelo actual lo lee como reactivación, expansión y luego contracción o churn.

**Robustez:** con N = 1, 2 y 3, el churn corregido va de −20,9 a −15,7 MM, y en todos los casos está muy lejos del −72,9 del modelo actual. **La conclusión no depende de la regla.**

**Retención a 12 meses:**

| Cohorte | Modelo | NRR | GRR | Retención de clientes |
|---|---|---|---|---|
| Altas 2022 | Actual | 50% | 48% | 87% |
| Altas 2022 | **Corregido** | **84%** | **80%** | 88% |
| Altas 2023 | Actual | 82% | 78% | 89% |
| Altas 2023 | **Corregido** | **91%** | **87%** | 91% |

→ El modelo actual hace ver la retención en ingresos **mucho peor de lo que es**. Eso puede llevar a decisiones equivocadas, como invertir en retención en lugar de en adquisición o pricing.

**¿Cuánto es comportamiento del cliente y cuánto pricing o descuentos?** (respuesta honesta con estos datos):
- **Comportamiento del cliente:** +53,4 MM neto (new + expansión + reactivación − contracción − churn).
- **Pricing (subidas de precio):** +1,7 MM (~3% del cambio).
- **Descuentos: hoy no se puede medir.** No hay precio de lista ni registro de descuentos. Las **85 bajadas exactas al 50%** (80 clientes, −4,2 MM de "contracción") pueden ser descuentos o downgrades. **Si fueran descuentos, el revenue no capturado acumulado llegaría hasta 40,8 MM.** El rango es de 0 a 40,8 MM, y esa incertidumbre es justamente la razón para pasar al modelo de dos capas.
- **Revenue en riesgo de cobro:**
  - 18,8 MM de MRR en meses de mora que nunca se pagaron (225 meses-cliente), contra 24,4 MM que sí se pagaron después.
  - 3,1 MM del MRR de oct-2024 (3%) está en mora abierta sin confirmar.

## Caso 1 (CRO): lo que dice el lado "Won" del funnel

| | 2022 (abr–dic) | 2023 | 2024 (ene–oct) |
|---|---|---|---|
| Clientes nuevos por mes | 26,9 | 54,2 | 55,4 |
| MRR nuevo por mes (MM) | 1,6 | 2,3 | 2,5 |
| Ticket de entrada promedio (COP) | 60.480 | 42.426 | 44.880 |
| MRR mediano al 3er mes (COP) | 51.450 | 35.007 | 36.750 |

- **Los clientes nuevos se duplicaron (+106%), pero el MRR nuevo creció solo +53%: el ticket de entrada cayó entre 25% y 29%, según la medida** (promedio al 1.er mes −26%, promedio al 3.er mes −25%, mediana al 3.er mes −29%). "No estamos vendiendo más" es, en ingresos, "**estamos vendiendo más clientes, pero más pequeños**".
- **Dónde se concentra** (descomposición mix/tasa del ticket 2022 → 2024, −15.600 COP):
  - **97% ocurre dentro de cada industria**; solo 3% se explica por mezcla de industrias.
  - **Retail** tiene la mayor caída (ticket −44%: 54,7 mil → 30,4 mil) y además ganó participación (de 18,6% a 24,0% de las altas).
  - Le siguen Restaurantes (−3.433) y Producción (−2.077 dentro de la industria, −2.708 por mezcla).
- **Lectura:** no es "llegan industrias peores". Es que **dentro de cada industria entran clientes más pequeños o en planes más baratos.** Eso es consistente con la hipótesis de *calidad/tamaño* o de *más self-serve*. **No se puede distinguir sin canal, plan ni etapa del funnel.**

## S&M y eficiencia (con advertencias)
- **S&M ≈ 2× el MRR total:** ~200 MM/mes de S&M contra 97,6 MM de MRR en oct-2024.
- **CAC combinado por trimestre:** 2,2–13,0 MM por cliente nuevo. **Payback sin margen bruto: 52–201 meses.**
- **El S&M cayó a la mitad en el 2S-2023 y las altas subieron:** correlación en niveles −0,58; en diferencias ≈ 0.
- **Advertencias:**
  - El S&M incluye nómina y equipo, que no son solo adquisición.
  - No hay atribución por canal ni separación self-serve/ventas.
  - Las unidades se tomaron del enunciado. Este punto debe validarse con Finanzas antes de concluir.

## Calidad de datos (tabla de tratamiento)

| Hallazgo | Magnitud | Tratamiento |
|---|---|---|
| Malla completa cliente × mes (0 = no pagó) | 1.961 × 34 | Se usa como malla de fechas |
| Huecos de pago internos | 468 huecos en 340 clientes (17%) | Mora ≤ N = 2 meses, o cualquier hueco pagado completo después = cliente activo |
| Pagos de puesta al día (k × monto) | 291 eventos, 53,8 MM | El exceso es cobro de mora, no MRR |
| Retroactivo en subidas de precio | 245 eventos | La subida es pricing; el retroactivo es un cargo único |
| Prepagos multi-mes | 16 clientes | Se reparten en min(12, meses cubiertos) |
| Picos o pagos agrupados | 133 eventos | Se aíslan; nivel = recurrente local |
| Bajadas exactas al 50% | 85 eventos | Contracción **marcada como ambigua** (descuento vs. downgrade) |
| Clientes que ya existían en ene-2022 | 377 | Base de apertura; ventana desde abr-2022 |
| PayrollExpenses negativo | 5 meses | Se mantiene (ajustes contables); se reporta |
| Industry | 100% de cobertura | — |
