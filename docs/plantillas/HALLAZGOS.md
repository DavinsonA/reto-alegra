# Hallazgos con datos reales

> Documento generado por `pipeline.py` a partir de `app/data/key_figures.csv`. No se edita a mano: la plantilla está en
> `docs/plantillas/HALLAZGOS.md`. Cifras en **millones de COP (MM)**.
> Ventana de análisis: **abr-2022 a {{mes_corte}}**. Enero a marzo de 2022 es periodo de arranque, por censura a la izquierda.
> **Supuesto cero:** un 0 en `Transactions` significa **"no se cobró"**, no "no se facturó". Si significara "sin
> servicio", el modelo de caja tendría razón y la mora no existiría. Sobre este supuesto descansa toda la lógica de mora.
> Regla base: mora tolerada **N = 2** meses.
> - Sensibilidad, una regla a la vez: `app/data/rule_sensitivity.csv`.
> - Puentes mensuales por escenario: `app/data/bridge_monthly.csv`.

## Caso 2 (CFO): el modelo actual cuenta bien el total, pero explica mal el porqué

**Cambio de MRR: {{mrr_ini}} a {{mrr_fin}} MM ({{cambio_neto}} MM).** El modelo actual termina en {{mrr_fin_actual}} MM. Los dos
modelos llegan cerca; la diferencia está en **la explicación**:

| Movimiento (acumulado de la ventana) | Modelo actual (caja) | Modelo corregido | El actual lo exagera |
|---|---|---|---|
| Nuevos | {{act_new}} | **{{cor_new}}** | {{x_new}}× |
| Expansión (cliente) | {{act_expansion}} | **{{cor_expansion}}** | {{x_expansion}}× |
| Subida de precio (decisión de Finora) | — (escondida en expansión) | **{{cor_price}}** | — |
| Contracción | {{act_contraction}} | **{{cor_contraction}}** | {{x_contraction}}× |
| Churn | {{act_churn}} | **{{cor_churn}}** | **{{x_churn}}×** |
| Reactivación | {{act_reactivation}} | **{{cor_reactivation}}** | **{{x_reactivation}}×** |

**Por qué se equivoca el modelo actual:** {{caja_no_mrr}} MM de caja de la ventana no son MRR, y el modelo actual los lee como reactivación,
expansión y luego contracción o churn:
- **Mora y puestas al día:** {{caja_arrears}} MM en {{caja_arrears_n}} pagos.
- **Pagos agrupados:** {{caja_lump}} MM en {{caja_lump_n}} pagos.
- **Picos puntuales:** {{caja_spike}} MM en {{caja_spike_n}} pagos.
- **Prepagos multi-mes** ({{caja_prepaid_clientes}} clientes; p. ej., anual con 25 % de descuento): {{caja_prepaid}} MM.
- **Prepagos en confirmación:** {{caja_prepaid_pending}} MM en {{caja_prepaid_pending_n}} pagos grandes al final de la serie. Todavía no existen los meses en 0 que confirmarían el prepago, así que se reconoce el nivel anterior y el resto queda en confirmación, igual que el churn de los últimos meses.
- **Retroactivos de subidas de precio:** {{caja_retro}} MM.

**Robustez: una regla a la vez.**
- **Qué se probó:** {{sens_n}} variantes de las reglas (tolerancia de mora, mora final, subidas de precio, retroactivos, prepagos, puestas al día, picos y clientes de uso variable).
- **Resultado: ninguna regla cambia el signo ni el orden de magnitud.**

| Indicador | Rango entre variantes | Modelo actual |
|---|---|---|
| Churn corregido | {{sens_churn_min}} a {{sens_churn_max}} MM | {{act_churn}} MM |
| Reactivación | {{sens_react_min}} a {{sens_react_max}} MM | {{act_reactivation}} MM |
| NRR a 12 meses, altas de 2023 | {{sens_nrr_min}} % a {{sens_nrr_max}} % | {{nrr_act_2023}} % |

- **El factor de exageración del churn sí depende de la regla:** va de {{sens_xchurn_min}}× a {{sens_xchurn_max}}×. Con la regla base es {{x_churn}}×.
- **La regla que más pesa es la de puestas al día.** Sin ella, la contracción sube a {{sin_catchup_contr}} MM y la expansión a {{sin_catchup_exp}} MM.

**Retención a 12 meses** (ponderada por MRR inicial):

| Cohorte | Modelo | NRR | GRR | Retención de clientes |
|---|---|---|---|---|
| Altas 2022 | Actual | {{nrr_act_2022}} % | {{grr_act_2022}} % | {{logo_act_2022}} % |
| Altas 2022 | **Corregido** | **{{nrr_cor_2022}} %** | **{{grr_cor_2022}} %** | {{logo_cor_2022}} % |
| Altas 2023 | Actual | {{nrr_act_2023}} % | {{grr_act_2023}} % | {{logo_act_2023}} % |
| Altas 2023 | **Corregido** | **{{nrr_cor_2023}} %** | **{{grr_cor_2023}} %** | {{logo_cor_2023}} % |

El modelo actual hace ver la retención en ingresos **mucho peor de lo que es**. Eso puede llevar a invertir en
retención en lugar de en adquisición o pricing.

**¿Cuánto es comportamiento del cliente y cuánto pricing o descuentos?** (respuesta honesta con estos datos)
- **Comportamiento del cliente:** {{cliente}} MM neto (nuevos + expansión + reactivación − contracción − churn).
- **Pricing (subidas de precio):** {{cor_price}} MM, cerca del {{precio_pct}} % del cambio.
  - De ese monto, {{precio_pend}} MM son {{precio_pend_n}} subidas de {{mes_corte}} (la mayoría de +{{precio_pend_pct}} %).
  - Esas subidas están **en confirmación**: sin el mes siguiente no se puede comprobar que el alza persista.
- **Descuentos: hoy no se pueden medir.** No hay precio de lista ni registro de descuentos.
  - Hay {{half_n}} bajadas exactas a la mitad ({{half_clientes}} clientes, {{half_contr}} MM de "contracción"). Pueden ser descuentos o downgrades.
  - **Cota superior ilustrativa:** si todas fueran descuentos que se mantuvieron, el revenue no capturado acumulado llegaría a {{half_techo}} MM.
  - **No es una estimación.** Muestra cuánto puede estar en juego y por qué hace falta el modelo de dos capas.
- **Revenue en riesgo de cobro:**
  - {{mora_impaga}} MM de MRR en meses de mora que nunca se pagaron ({{mora_impaga_n}} meses-cliente), contra {{mora_pagada}} MM que sí se pagaron después.
  - {{mora_abierta}} MM del MRR de {{mes_corte}} ({{mora_abierta_pct}} %, {{mora_abierta_clientes}} clientes) está en mora abierta sin confirmar. Supera la regla de alerta del 3 %.

## Caso 1 (CRO): lo que dice el lado "Won" del funnel

| | 2022 (abr–dic) | 2023 | 2024 (ene–oct) |
|---|---|---|---|
| Clientes nuevos por mes | {{nuevos_mes_2022}} | {{nuevos_mes_2023}} | {{nuevos_mes_2024}} |
| MRR nuevo por mes (MM) | {{mrr_nuevo_mes_2022}} | {{mrr_nuevo_mes_2023}} | {{mrr_nuevo_mes_2024}} |
| Ticket de entrada promedio (COP) | {{ticket_2022}} | {{ticket_2023}} | {{ticket_2024}} |
| MRR promedio al 3.er mes (COP) | {{m3_2022}} | {{m3_2023}} | {{m3_2024}} |

- **Los clientes nuevos crecieron +{{crec_nuevos}} %, pero el MRR nuevo solo +{{crec_mrr_nuevo}} %.**
  - El ticket de entrada cayó entre {{caida_min}} % y {{caida_max}} % según la medida: promedio al primer mes −{{caida_ticket}} %, promedio al 3.er mes −{{caida_m3}} %, mediana al 3.er mes −{{caida_m3_med}} % ({{m3_med_2022}} a {{m3_med_2024}} COP).
  - En ingresos, "no estamos vendiendo más" quiere decir "**estamos vendiendo más clientes, pero más pequeños**".
- **Dónde se concentra** (descomposición mezcla/tasa del ticket de 2022 a 2024, {{kit_total}} COP):
  - **El {{kit_dentro}} % ocurre dentro de cada industria**; el resto se explica por la mezcla de industrias.
  - **Retail** tiene la mayor caída (ticket −{{retail_caida}} %: de {{retail_t0}} mil a {{retail_t1}} mil) y además ganó participación (de {{retail_s0}} % a {{retail_s1}} % de las altas).
- **Lectura:** no es que lleguen industrias peores. **Dentro de cada industria entran clientes más pequeños o en planes más baratos.**
  - Es consistente con la hipótesis de calidad o tamaño, o con la de más self-serve.
  - **No se puede distinguir sin canal, plan ni etapa del funnel.**

## S&M y eficiencia (con advertencias)
- **S&M ≈ {{sm_vs_mrr}} veces el MRR total:** cerca de {{sm_mes}} MM al mes de S&M en 2024, contra {{mrr_fin}} MM de MRR en {{mes_corte}}.
- **CAC combinado por trimestre:** {{cac_min}} a {{cac_max}} MM por cliente nuevo. **Payback sin margen bruto: {{payback_min}} a {{payback_max}} meses.**
- **El S&M cayó a la mitad en el segundo semestre de 2023 y las altas subieron.** La correlación mensual en niveles es {{corr_niveles}}; en diferencias, {{corr_dif}} (débil). No hay evidencia agregada de que más gasto traiga más clientes.
- **Advertencias:**
  - El S&M incluye nómina y equipo, que no son solo adquisición.
  - No hay atribución por canal ni separación entre self-serve y ventas.
  - Las unidades se tomaron del enunciado. **Con ellas, el S&M duplica el MRR: antes de cualquier decisión de inversión hay que confirmarlas con Finanzas.**

## Calidad de datos (tabla de tratamiento)

| Hallazgo | Magnitud | Tratamiento |
|---|---|---|
| Malla completa cliente × mes (0 = no pagó) | {{clientes}} × {{meses}} | Se usa como malla de fechas; supuesto cero = no se cobró |
| Huecos de pago internos | {{huecos}} huecos en {{huecos_clientes}} clientes ({{huecos_pct}} %) | Mora ≤ N = 2 meses, o cualquier hueco pagado completo después = cliente activo |
| Pagos de puesta al día (k × monto) | {{caja_arrears_n}} pagos, {{caja_arrears}} MM | El exceso es cobro de mora, no MRR |
| Retroactivo en subidas de precio | {{caja_retro_n}} pagos | La subida es pricing; el retroactivo es un cargo único |
| Prepagos multi-mes | {{caja_prepaid_clientes}} clientes | Se reparten en min(12, meses cubiertos) |
| Pagos grandes al final de la serie | {{caja_prepaid_pending_n}} pagos | Prepago en confirmación: se reconoce el nivel anterior |
| Subidas de precio del último mes | {{precio_pend_n}} clientes | En confirmación: falta el mes siguiente |
| Picos y pagos agrupados | {{caja_spike_n}} picos y {{caja_lump_n}} pagos agrupados | Se aíslan; nivel = recurrente local |
| Bajadas exactas al 50 % | {{half_n}} eventos | Contracción **marcada como ambigua** (descuento vs. downgrade) |
| Clientes que ya existían en ene-2022 | {{base_inicial}} | Base de apertura; ventana desde abr-2022 |
| PayrollExpenses negativo | {{payroll_neg}} meses | Se mantiene (ajustes contables); se reporta |
| Industry | 100 % de cobertura | — |
