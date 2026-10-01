# Hallazgos con datos reales

> Documento generado por `pipeline.py` a partir de `app/data/key_figures.csv`. No se edita a mano: la plantilla está en
> `docs/plantillas/HALLAZGOS.md`. Cifras en **millones de COP (MM)**.
> Ventana de análisis: **abr-2022 a oct-2024**. Enero a marzo de 2022 es periodo de arranque, por censura a la izquierda.
> **Supuesto cero:** un 0 en `Transactions` significa **"no se cobró"**, no "no se facturó". Si significara "sin
> servicio", el modelo de caja tendría razón y la mora no existiría. Sobre este supuesto descansa toda la lógica de mora.
> Regla base: mora tolerada **N = 2** meses.
> - Sensibilidad, una regla a la vez: `app/data/rule_sensitivity.csv`.
> - Puentes mensuales por escenario: `app/data/bridge_monthly.csv`.

## Caso 2 (CFO): el modelo actual cuenta bien el total, pero explica mal el porqué

**Cambio de MRR: 42,6 a 95,7 MM (+53,1 MM).** El modelo actual termina en 97,0 MM. Los dos
modelos llegan cerca; la diferencia está en **la explicación**:

| Movimiento (acumulado de la ventana) | Modelo actual (caja) | Modelo corregido | El actual lo exagera |
|---|---|---|---|
| Nuevos | +91,6 | **+66,8** | 1,4× |
| Expansión (cliente) | +38,5 | **+28,4** | 1,4× |
| Subida de precio (decisión de Finora) | — (escondida en expansión) | **+1,7** | — |
| Contracción | −84,4 | **−31,7** | 2,7× |
| Churn | −72,9 | **−18,0** | **4,1×** |
| Reactivación | +84,7 | **+5,9** | **14,4×** |

**Por qué se equivoca el modelo actual:** 82,1 MM de caja de la ventana no son MRR, y el modelo actual los lee como reactivación,
expansión y luego contracción o churn:
- **Mora y puestas al día:** 52,7 MM en 288 pagos.
- **Pagos agrupados:** 9,3 MM en 88 pagos.
- **Picos puntuales:** 5,5 MM en 42 pagos.
- **Prepagos multi-mes** (15 clientes; p. ej., anual con 25 % de descuento): 9,0 MM.
- **Prepagos en confirmación:** 4,7 MM en 9 pagos grandes al final de la serie. Todavía no existen los meses en 0 que confirmarían el prepago, así que se reconoce el nivel anterior y el resto queda en confirmación, igual que el churn de los últimos meses.
- **Retroactivos de subidas de precio:** 0,9 MM.

**Robustez: una regla a la vez.**
- **Qué se probó:** 10 variantes de las reglas (tolerancia de mora, mora final, subidas de precio, retroactivos, prepagos, puestas al día, picos y clientes de uso variable).
- **Resultado: ninguna regla cambia el signo ni el orden de magnitud.**

| Indicador | Rango entre variantes | Modelo actual |
|---|---|---|
| Churn corregido | −15,7 a −27,6 MM | −72,9 MM |
| Reactivación | 3,9 a 12,8 MM | +84,7 MM |
| NRR a 12 meses, altas de 2023 | 87 % a 92 % | 82 % |

- **El factor de exageración del churn sí depende de la regla:** va de 2,6× a 4,6×. Con la regla base es 4,1×.
- **La regla que más pesa es la de puestas al día.** Sin ella, la contracción sube a −61,9 MM y la expansión a +53,2 MM.

**Retención a 12 meses** (ponderada por MRR inicial):

| Cohorte | Modelo | NRR | GRR | Retención de clientes |
|---|---|---|---|---|
| Altas 2022 | Actual | 50 % | 48 % | 87 % |
| Altas 2022 | **Corregido** | **84 %** | **80 %** | 88 % |
| Altas 2023 | Actual | 82 % | 78 % | 89 % |
| Altas 2023 | **Corregido** | **91 %** | **87 %** | 91 % |

El modelo actual hace ver la retención en ingresos **mucho peor de lo que es**. Eso puede llevar a invertir en
retención en lugar de en adquisición o pricing.

**¿Cuánto es comportamiento del cliente y cuánto pricing o descuentos?** (respuesta honesta con estos datos)
- **Comportamiento del cliente:** +51,5 MM neto (nuevos + expansión + reactivación − contracción − churn).
- **Pricing (subidas de precio):** +1,7 MM, cerca del 3 % del cambio.
  - De ese monto, 0,4 MM son 94 subidas de oct-2024 (la mayoría de +8,5 %).
  - Esas subidas están **en confirmación**: sin el mes siguiente no se puede comprobar que el alza persista.
- **Descuentos: hoy no se pueden medir.** No hay precio de lista ni registro de descuentos.
  - Hay 85 bajadas exactas a la mitad (80 clientes, −4,2 MM de "contracción"). Pueden ser descuentos o downgrades.
  - **Cota superior ilustrativa:** si todas fueran descuentos que se mantuvieron, el revenue no capturado acumulado llegaría a 40,8 MM.
  - **No es una estimación.** Muestra cuánto puede estar en juego y por qué hace falta el modelo de dos capas.
- **Revenue en riesgo de cobro:**
  - 18,8 MM de MRR en meses de mora que nunca se pagaron (225 meses-cliente), contra 24,1 MM que sí se pagaron después.
  - 3,1 MM del MRR de oct-2024 (3,2 %, 46 clientes) está en mora abierta sin confirmar. Supera la regla de alerta del 3 %.

## Caso 1 (CRO): lo que dice el lado "Won" del funnel

| | 2022 (abr–dic) | 2023 | 2024 (ene–oct) |
|---|---|---|---|
| Clientes nuevos por mes | 26,9 | 54,2 | 55,4 |
| MRR nuevo por mes (MM) | 1,6 | 2,3 | 2,5 |
| Ticket de entrada promedio (COP) | 60.480 | 42.426 | 44.348 |
| MRR promedio al 3.er mes (COP) | 55.280 | 41.359 | 41.711 |

- **Los clientes nuevos crecieron +106 %, pero el MRR nuevo solo +51 %.**
  - El ticket de entrada cayó entre 25 % y 29 % según la medida: promedio al primer mes −27 %, promedio al 3.er mes −25 %, mediana al 3.er mes −29 % (51.450 a 36.750 COP).
  - En ingresos, "no estamos vendiendo más" quiere decir "**estamos vendiendo más clientes, pero más pequeños**".
- **Dónde se concentra** (descomposición mezcla/tasa del ticket de 2022 a 2024, −16.132 COP):
  - **El 97 % ocurre dentro de cada industria**; el resto se explica por la mezcla de industrias.
  - **Retail** tiene la mayor caída (ticket −44 %: de 54,7 mil a 30,4 mil) y además ganó participación (de 18,6 % a 24,0 % de las altas).
- **Lectura:** no es que lleguen industrias peores. **Dentro de cada industria entran clientes más pequeños o en planes más baratos.**
  - Es consistente con la hipótesis de calidad o tamaño, o con la de más self-serve.
  - **No se puede distinguir sin canal, plan ni etapa del funnel.**

## S&M y eficiencia (con advertencias)
- **S&M ≈ 2,1 veces el MRR total:** cerca de 198 MM al mes de S&M en 2024, contra 95,7 MM de MRR en oct-2024.
- **CAC combinado por trimestre:** 2,2 a 13,0 MM por cliente nuevo. **Payback sin margen bruto: 52 a 201 meses.**
- **El S&M cayó a la mitad en el segundo semestre de 2023 y las altas subieron.** La correlación mensual en niveles es −0,58; en diferencias, 0,20 (débil). No hay evidencia agregada de que más gasto traiga más clientes.
- **Advertencias:**
  - El S&M incluye nómina y equipo, que no son solo adquisición.
  - No hay atribución por canal ni separación entre self-serve y ventas.
  - Las unidades se tomaron del enunciado. **Con ellas, el S&M duplica el MRR: antes de cualquier decisión de inversión hay que confirmarlas con Finanzas.**

## Calidad de datos (tabla de tratamiento)

| Hallazgo | Magnitud | Tratamiento |
|---|---|---|
| Malla completa cliente × mes (0 = no pagó) | 1.961 × 34 | Se usa como malla de fechas; supuesto cero = no se cobró |
| Huecos de pago internos | 468 huecos en 340 clientes (17 %) | Mora ≤ N = 2 meses, o cualquier hueco pagado completo después = cliente activo |
| Pagos de puesta al día (k × monto) | 288 pagos, 52,7 MM | El exceso es cobro de mora, no MRR |
| Retroactivo en subidas de precio | 245 pagos | La subida es pricing; el retroactivo es un cargo único |
| Prepagos multi-mes | 15 clientes | Se reparten en min(12, meses cubiertos) |
| Pagos grandes al final de la serie | 9 pagos | Prepago en confirmación: se reconoce el nivel anterior |
| Subidas de precio del último mes | 94 clientes | En confirmación: falta el mes siguiente |
| Picos y pagos agrupados | 42 picos y 88 pagos agrupados | Se aíslan; nivel = recurrente local |
| Bajadas exactas al 50 % | 85 eventos | Contracción **marcada como ambigua** (descuento vs. downgrade) |
| Clientes que ya existían en ene-2022 | 377 | Base de apertura; ventana desde abr-2022 |
| PayrollExpenses negativo | 5 meses | Se mantiene (ajustes contables); se reporta |
| Industry | 100 % de cobertura | — |
