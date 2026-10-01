# Revisión del tablero operativo: qué cambiar para que de verdad se use

> Alcance: el **tablero operativo** (`app/tablero.py`): revisión mensual del MRR (CFO) y revisión semanal del funnel (CRO).
> Método: (1) contrastar cada vista con las preguntas que el tablero debe resolver; (2) investigación en línea para
> respaldar cada cambio; (3) priorizar por impacto y esfuerzo. Fecha: 2026-10-01. Fuentes al final, con su tipo.
> Complementa `docs/diseno_dashboard.md` (principios ya aplicados: XmR, formato 6-12, dueños y reglas).
>
> **Estado:** esta revisión es anterior al cierre final. Desde entonces se aplicaron A (puente en dos capas), C (la
> lectura del mes arriba, en una franja ancha) y parte de B (subidas de precio y prepagos en confirmación). El motor
> también se corrigió por censura a la derecha, así que las cifras del tablero que se citan aquí (p. ej., cliente +3,9 MM
> en oct-2024) son las de ese momento. Las cifras vigentes están en `HALLAZGOS.md` y `app/data/key_figures.csv`.

**Veredicto: la forma está bien; el fondo está incompleto.** El tablero ya separa señal de ruido, tiene formato fijo y
dueños. Pero la pregunta central del CFO no tiene un lugar propio. Además, no se miran como series ni la caja ni el
pricing, y no hay filtros para pasar del "qué" al "dónde".

## 1. Lo que el tablero debe resolver, y si hoy lo hace

| Pregunta | Quién | ¿Lo responde hoy? |
|---|---|---|
| ¿Cuánto del cambio del mes es cliente, cuánto pricing y cuánto descuentos? | CFO | **Parcial.** Está en una nota al pie, debajo de la tabla de movimientos. |
| ¿Los descuentos temporales están comprando crecimiento? | CFO | **No.** Sin registro de descuentos no se puede medir, y el indicio disponible (bajadas exactas a la mitad) no aparece en el tablero. |
| ¿Cuánto MRR está sin cobrar y se está recuperando? | CFO, Cobranza | **Parcial.** Solo aparece como "churn en confirmación" del mes. La regla "MRR en mora > 3 %" está en la tabla de reglas, pero no hay gráfico que la siga. **En oct-2024 la regla está activa (3,2 %) y el tablero no lo muestra.** |
| ¿Cada cohorte conserva su ingreso? | CFO | **No.** NRR y GRR solo están en la demo. |
| ¿Qué entrada del funnel se salió de lo normal? | CRO | **Sí:** formato 6-12, árbol de métricas y señales XmR. |
| ¿En qué canal o camino? | CRO | **No.** No hay filtro; la descomposición mezcla/tasa vive en la demo. |
| ¿Qué decidimos la vez pasada y funcionó? | Ambos | **No.** Hay dueños y reglas, pero no un registro de acciones. |

## 2. Hallazgos y lo que dice la investigación

**1. La pregunta del CFO no tiene un lugar propio.**
- Hoy el puente del mes ordena las barras por signo (azul suma, durazno resta), no por capa. La respuesta (cliente +3,9 MM · pricing +0,4 MM · descuentos sin dato) queda en una línea de texto pequeña.
- Por qué importa: en la práctica de mercado, el vencimiento de un descuento aparece como expansión.
  - ChartMogul: *"A subscription renewing after a discount is removed will result in expansion MRR"*.
  - Si el tablero no separa las capas a la vista, el CFO verá crecer la "expansión" cuando venzan los descuentos que se van a lanzar.
- Lo que se gana: el título del gráfico debe enunciar la respuesta. Borkin et al. (IEEE TVCG, 2016) encontraron que la gente pasa más tiempo leyendo el título y que su contenido define lo que recuerda de la visualización.

**2. La caja y el pricing no se siguen como series.** Hoy hay tres reglas o indicios sin vista:
- **Mora:** la regla de alerta "> 3 % del MRR" ya está activa en oct-2024, y no hay gráfico que la muestre.
- **Bajadas exactas a la mitad:** 85 en la ventana, el único indicio de descuentos con estos datos.
- **Subidas de precio:** existen como movimiento, pero no como serie.

Por qué importa: según investigación de Paddle citada por Baremetrics, el churn involuntario (pagos fallidos) es del 20 % al 40 % del churn total. Es la parte del churn que más se puede recuperar. Es una estimación de un proveedor, así que la uso como orden de magnitud.

**3. Falta el paso de "filtrar".**
- La regla 3-30-300 de SQLBI resume el mantra de Shneiderman (1996), "vista general primero, acercar y filtrar, luego detalle a demanda":
  - 3 segundos para la visión general;
  - 30 segundos para filtrar y encontrar dónde mirar;
  - 300 segundos para el detalle que lleva a la acción.
- El tablero hoy tiene el paso de 3 segundos (KPI) y el de 300 (Ver datos, reglas), pero casi nada del de 30. El único filtro es el mes; no hay filtro por canal, camino ni industria.
- Para el CRO esto es central: la hipótesis "mezcla de canal vs. tasa" solo se prueba cortando por canal.

**4. La lectura del mes está donde se lee al final.**
- Microsoft Learn recomienda poner lo de más alto nivel arriba a la izquierda y el detalle hacia abajo a la derecha. También recomienda caber en una pantalla y dar contexto a cada número.
- Hoy el recuadro "qué cambió · qué hacemos" está en la tercera columna de la segunda fila. Un CFO que lee en Z llega a él de último.

**5. La retención no está en el tablero, y los benchmarks externos no sirven aquí.**
- NRR y GRR son las métricas que un directorio mira primero.
- Los benchmarks públicos más citados se refieren a contratos mucho más grandes que los de Finora. Por ejemplo, SaaS Capital reporta para 2025 una mediana de NRR de 102 % en empresas con ACV de USD 25.000 a 50.000.
- El ticket de entrada de Finora es de unos 45 mil COP al mes. Son unos USD 130 al año, con una tasa aproximada de 4.100 COP por dólar.
- **Conclusión:** comparar contra la propia historia (XmR), no contra esos benchmarks.

**6. No hay memoria de decisiones.**
- En la WBR de Amazon (Commoncog), cada dueño explica la variación excepcional, o dice "nada que ver aquí", y se acuerdan acciones de seguimiento.
- Los scorecards de Power BI (Microsoft Learn) formalizan lo mismo: cada métrica tiene dueño, meta, estado y *check-ins* con notas que quedan en el historial.
- Sin ese registro, la revisión del mes siguiente no puede responder si la acción funcionó.

**7. Confianza: definiciones y frescura.**
- La guía de práctica (Basedash, Metaplane) recomienda mostrar la fecha de actualización tomada del dato (no de la carga de la página) y la definición de cada KPI al alcance del cursor.
- El tablero muestra el corte (oct-2024), pero no las definiciones. Tampoco está escrito cómo se actualiza cada mes.

**8. CRO: la velocidad de respuesta merece su meta a la vista.**
- HBR (Oldroyd, McElheran y Elkington, 2011) estudió 2.241 empresas y 1,25 millones de leads:
  - quien intentó contactar en la primera hora tuvo casi 7 veces más probabilidad de calificar el lead que quien esperó una hora más;
  - y más de 60 veces más que quien esperó 24 horas o más.
- El tablero sigue el SLA de 1 hora, pero no dibuja la meta.
- Además, la **velocidad de ventas** (oportunidades × tasa de cierre × ticket ÷ duración del ciclo) resumiría en una cifra las cuatro palancas del funnel.

**9. Los eventos que explican las series no están anotados.** Ejemplos: subidas de precio y el recorte de S&M del segundo semestre de 2023. Según Rahman et al. (IEEE TVCG, 2025), las anotaciones destacan los aspectos críticos y apoyan la interpretación en grupo, que es justo lo que pasa en una revisión mensual.

## 3. Cambios recomendados, por impacto y esfuerzo

### Hacer primero (los datos ya existen; menos de un día en total)

| # | Cambio | Responde a | Respaldo |
|---|---|---|---|
| A | **Puente en dos capas como pieza central.** Orden: Nuevos, Expansión, Reactivación, Contracción y Churn → **subtotal Cliente** → Precio → Descuentos (*sin dato: instrumentar*) → Neto. El título enuncia la respuesta. | Hallazgo 1 | ChartMogul; Borkin et al. |
| B | **Fila "Caja y pricing" en la revisión mensual**, con 4 gráficos: MRR sin cobrar como % del MRR (con la línea del 3 %), bajadas exactas a la mitad (posible descuento), subidas de precio, y NRR/GRR a 12 meses por cohorte. | Hallazgos 2 y 5 | Paddle vía Baremetrics; SaaS Capital |
| C | **Línea de estado arriba a la izquierda** (los 3 segundos). Ejemplo: "2 señales · 1 regla activa (mora 3,2 %) · dueños: Cobranza, Marketing". | Hallazgo 4 | Microsoft Learn; SQLBI 3-30-300 |
| D | **Filtro por canal y camino en la revisión semanal.** Mes y página quedan en el enlace para pegarlo en la agenda de la reunión. | Hallazgo 3 | Shneiderman; SQLBI |
| E | **Definiciones al pasar el cursor** en cada KPI, **fecha de actualización** del dato y una guía corta "cómo actualizar el tablero" (`python pipeline.py` y push). | Hallazgo 7 | Basedash; Metaplane |
| F | **Meta del SLA de 1 hora dibujada** y **velocidad de ventas** en la revisión semanal (con datos sintéticos, rotulados). | Hallazgo 8 | HBR 2011; fórmula de velocidad de ventas |

### Planear (alto impacto; requieren datos o infraestructura)

| # | Cambio | Qué hace falta |
|---|---|---|
| G | Realización de precio (neto ÷ lista) y MRR que vuelve por descuentos que vencen | Registro de descuentos (`dim_discount`, ya diseñado en `docs/modelo_datos.md`) |
| H | Desglose y filtro por industria en la revisión mensual | Una tabla agregada nueva en el pipeline: puente por industria y mes, sin detalle por cliente |
| I | Registro de acciones con *check-ins* (dueño, estado, nota) y alertas por correo cuando aparece una señal | Persistencia (base de datos u hoja compartida) y un envío programado |

### Victoria rápida
- **J. Anotar eventos en las series:** subidas de precio y el recorte de S&M. Fuentes: Borkin et al.; Rahman et al.

### No priorizar
- **K. Benchmarks externos de NRR:** no son comparables por el tamaño del contrato (hallazgo 5).

## 4. Lo que no cambiaría
- **XmR con dueños y reglas:** es lo que convierte el tablero en revisión y no en reporte (WBR de Amazon).
- **Formato fijo 6-12:** la repetición es la que forma el criterio del equipo.
- **Máximo 4 KPI por fila y lectura generada a partir de las señales:** son la base de los 3 segundos.
- **Datos sintéticos rotulados en el funnel:** la honestidad sobre el origen de los datos es parte de la confianza.

## 5. Fuentes
| Fuente | Tipo | Qué respalda |
|---|---|---|
| Microsoft Learn, [Tips for designing a great Power BI dashboard](https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards-design-tips) | Documentación oficial | Arriba a la izquierda, una pantalla, contexto, tarjetas para lo importante |
| K. Buhler, SQLBI, [Introducing the 3-30-300 rule for better reports](https://www.sqlbi.com/articles/introducing-the-3-30-300-rule-for-better-reports/) (2024) | Práctica experta | Jerarquía de 3 s, 30 s y 300 s |
| B. Shneiderman, *The Eyes Have It* (IEEE VL 1996), vía [Craft et al.](https://faculty.cc.gatech.edu/~john.stasko/8001/craft05.pdf) | Académica | Vista general, filtrar, detalle a demanda |
| ChartMogul, [Should discounts be included in MRR?](https://chartmogul.com/blog/should-discounts-be-included-in-mrr/) | Proveedor de referencia | El vencimiento de un descuento se registra como expansión |
| Borkin et al., [Beyond Memorability](http://olivalab.mit.edu/Papers/07192646.pdf) (IEEE TVCG 2016) | Académica (33 participantes, 393 visualizaciones) | El título define lo que se recuerda |
| Rahman et al., [A Qualitative Analysis of Common Practices in Annotations](https://arxiv.org/abs/2306.06043) (IEEE TVCG 2025) | Académica | Las anotaciones destacan lo crítico y apoyan la interpretación en grupo |
| Baremetrics, [Involuntary churn](https://baremetrics.com/blog/involuntary-churn) (cita a Paddle) | Proveedor | Churn involuntario: 20 % a 40 % del churn total |
| SaaS Capital, [What is a good retention rate…](https://www.saas-capital.com/blog-posts/what-is-a-good-retention-rate-for-a-private-saas-company/) (2025) | Encuesta | NRR mediana de 102 % con ACV de USD 25.000 a 50.000 |
| Oldroyd, McElheran y Elkington, [The Short Life of Online Sales Leads](https://hbr.org/2011/03/the-short-life-of-online-sales-leads) (HBR 2011) | Académica aplicada | Contactar en la primera hora: casi 7 veces más probabilidad de calificar. La cifra viene del resumen público del artículo; el texto completo requiere suscripción. |
| Commoncog, [The Amazon Weekly Business Review](https://commoncog.com/the-amazon-weekly-business-review/) | Práctica documentada | Dueños, "nada que ver aquí", acciones de seguimiento |
| Microsoft Learn, [Power BI metrics y check-ins](https://learn.microsoft.com/en-us/power-bi/create-reports/service-goals-check-in); [alertas de datos](https://learn.microsoft.com/en-us/power-bi/create-reports/service-set-data-alerts) | Documentación oficial | Dueño, meta, estado e historial de notas; alertas por umbral |
| Basedash, [Data freshness explained for BI](https://www.basedash.com/blog/data-freshness-how-current-your-dashboard-data-really-is); Metaplane, [Data freshness](https://www.metaplane.dev/blog/data-freshness-definition-examples) | Práctica (proveedores) | Fecha de actualización del dato y definiciones accesibles |
| Apollo, [Sales velocity formula](https://www.apollo.io/insights/sales-velocity-formula) | Práctica | Fórmula de velocidad de ventas |
