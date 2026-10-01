# Diseño del tablero: investigación y especificación

> Objetivo: que el tablero sirva para **decidir y operar**, no solo para mostrar el análisis una vez.
> Fecha: 2026-10-01 · Fuentes al final.

## 1. Qué dice la investigación (y qué implica aquí)

| Principio | Fuente | Implicación para Finora |
|---|---|---|
| **Un tablero existe para una decisión, un público y una cadencia.** Sin contexto de decisión, "un tablero es un reporte, y los reportes se ignoran". | Plantillas de requisitos de BI (Datawireframe; Looker) | Cada vista declara **para quién**, **qué decide** y **cada cuánto se mira**. |
| **Monitorear de un vistazo, en una pantalla.** "Una pantalla para monitorear de un vistazo". Lo crítico se pierde si hay que desplazarse. | Stephen Few, *Information Dashboard Design* / *Common Pitfalls* | Las vistas operativas caben arriba del pliegue: lo que importa primero y el detalle debajo ("Ver detalle"). |
| **Sin contexto, un número no dice nada.** "¿Comparado con qué? ¿Es bueno o malo?" Se compara contra meta o historia y se da un estado cualitativo. | Few, pitfall #2 | Cada KPI va con: vs. mes anterior, vs. hace 12 meses y **estado (señal o rutina)**. Finora no tiene metas: se muestra "meta por definir" en lugar de inventarla. |
| **Separar señal de ruido antes de reaccionar.** Gráfico de comportamiento del proceso (XmR): límites = media ± 2,66 × rango móvil promedio. Señales: punto fuera de límites, 8 seguidos del mismo lado, 3 de 4 cerca del límite. | Wheeler vía Commoncog; Shewhart (Wikipedia) | Toda serie mensual o semanal lleva límites naturales. Si no hay señal, se marca "**nada que ver aquí**" y se pasa a la siguiente. |
| **Revisión por excepción, con dueños y formato fijo.** En la WBR de Amazon cada métrica tiene dueño. Si solo hay variación rutinaria, el dueño dice "nada que ver aquí" y el grupo sigue. El formato es idéntico cada semana: seis semanas recientes junto a doce meses, para desarrollar "fingertip feel". | Commoncog, *The Amazon Weekly Business Review* | Vista semanal del CRO en formato **6-12** (6 semanas + 12 meses), siempre igual. Columna de **dueño**, **regla de alerta** y **acción**. |
| **Métricas de entrada controlables vs. métricas de salida.** En la WBR se discuten las entradas que un equipo puede mover; las salidas solo se reportan. | Commoncog (WBR); árboles de métricas (KPI Tree, Basedash) | **Árbol de métricas**: MRR neto ← new, expansión, churn… ← clientes nuevos × ticket ← leads × conversión ← speed-to-lead, mezcla de canal, win rate. |
| **El puente (waterfall) es la visualización estándar** para explicar el cambio de MRR/ARR ante el CFO o la junta. Inicio + new + expansión − contracción − churn = cierre. | Guías de board reporting (CFO Pro Analytics, Eru); ChartMogul | Puente del **mes seleccionado** como pieza central de la vista del CFO, con tabla de **monto y número de clientes** por tipo de movimiento (patrón de ChartMogul). |
| **Ganancias arriba de cero, pérdidas abajo**; tabla con monto y clientes por tipo; detalle por clic. | ChartMogul, *MRR Movements* | Se mantiene en el puente mensual. |
| **Cohortes en "layer cake"** para ver cuánto MRR viene de cohortes viejas vs. nuevas y qué tan rápido se desvanecen. | ChartMogul, Exploratory | Vista complementaria del CFO (fase 2). |
| **Volumen, conversión y tiempo** en cada etapa del funnel: una sola fuente de verdad para marketing, ventas, finanzas y CS. | Winning by Design, *Bowtie* | El funnel del CRO se lee en tres familias: volumen, conversión (por cohorte) y tiempo (speed-to-lead, tiempo en etapa). |
| **Revisión semanal de pipeline:** conversión por etapa y segmento, días en etapa (marcando lo que supera la mediana o P90), riesgo (sin actividad en 14 días o más) y cobertura. Debe responder qué deals miran, a quién entrenar y si se va a cumplir. | Guías RevOps (Rework, Weflow, ORM Tech) | La lista operativa de estancados es parte de la vista, no un anexo. |
| **Narrativa junto a los números:** qué cambió, por qué y qué se hace. Comentario del dueño junto a cada grupo de KPI. | Guías de executive dashboards (FanRuan, Domo) | Cada vista abre con un recuadro "**Qué cambió · por qué · qué hacemos**", generado a partir de las señales. |
| **Explicativo ≠ exploratorio.** Para comunicar: una **gran idea** en una frase y una historia de 3 minutos. | Knaflic, *Storytelling with Data* | La historia ejecutiva es una app aparte: una idea por pantalla, de la situación a la acción. Operar y profundizar viven en otras dos apps. |
| **Por qué fallan los tableros:** viven fuera del flujo de trabajo, las métricas no tienen dueño ni umbral, demasiados indicadores trasladan el análisis al lector, las definiciones cambian entre equipos. | Reveal BI, Data Cult, Revelynk | Pocas métricas por vista (≤ 4 KPI), cada una con dueño, umbral y acción; definiciones enlazadas al diccionario. |

## 2. Diagnóstico de la versión actual

| Lo que ya está bien | Lo que falta para que sea útil |
|---|---|
| Hallazgos con datos reales, títulos que dicen el hallazgo, "Ver datos", fuente | **Es explicativa y de una sola vez:** cuenta el análisis, pero no sirve para la revisión del próximo mes |
| Modelo actual vs. corregido, sensibilidad, simulador del CFO | **No hay selector de periodo:** todo es acumulado o 31 meses juntos |
| Prototipo del funnel con problemas plantados | **No hay estado señal/ruido** en las series mensuales del CFO |
| Marca y accesibilidad validadas | **No hay dueños, umbrales ni acciones** por métrica; tampoco formato fijo de revisión |
| | El CRO no tiene una vista semanal en formato fijo ni un árbol de métricas que conecte entradas con el MRR nuevo |

## 3. Especificación: arquitectura de la app

Tres apps, una por **uso**, sobre el mismo motor y las mismas tablas agregadas (`app/common.py`), para que una cifra se corrija en un solo lugar:

| App | Vista | Público | Decisión | Cadencia |
|---|---|---|---|---|
| **Historia ejecutiva** (`historia.py`) | 6 pantallas: situación, hallazgo del MRR, hallazgo de ventas, implicación, decisión y acción | CEO, CRO, CFO, evaluadores | Aprobar las 3 decisiones (MRR en dos capas, separar caja de MRR, instrumentar el funnel) | Una vez (video 1) |
| **Tablero operativo** (`tablero.py`) | **Revisión mensual del MRR** | CFO + RevOps | ¿El cambio del mes es señal o ruido? ¿Quién investiga qué? | Mensual, en el cierre |
| **Tablero operativo** (`tablero.py`) | **Revisión semanal del funnel** (prototipo sintético) | CRO + líderes SDR/AE | ¿Qué entrada se salió de lo normal? ¿Capacidad, mezcla o post-SQL? | Semanal, 30 minutos |
| **Demo y proceso con IA** (`demo.py`) | Proceso con IA paso a paso | Evaluadores, Analítica | Confiar (o no) en el método: qué hizo la IA, qué decidí yo, cómo se verificó | Una vez (video 2) |
| **Demo y proceso con IA** (`demo.py`) | Caso CFO y Caso CRO | CFO, CRO | Adoptar el modelo de dos capas; qué datos instrumentar | Una vez |
| **Demo y proceso con IA** (`demo.py`) | Modelo de datos, S&M, calidad de datos | Analítica, Finanzas | Cómo se construye y qué no se puede concluir | Consulta |

### 3.1 Revisión mensual del MRR (CFO)
Primero lo que se lee arriba del pliegue:
1. **Selector de mes de cierre** (por defecto, el último).
2. **Recuadro "Qué cambió · por qué · qué hacemos"**, generado a partir de las señales del mes.
3. **4 KPI con contexto:**
   - MRR de cierre.
   - MRR neto nuevo.
   - Churn del mes.
   - Clientes nuevos.
   - Cada uno con: vs. mes anterior, vs. hace 12 meses y **estado XmR** ("dentro de lo normal" o "señal", siempre con la palabra, no solo el color).
4. **Puente del mes:** apertura → nuevos → expansión → subida de precio → reactivación → contracción → churn → cierre. Debajo, la tabla de **monto y número de clientes** por movimiento.
5. **¿Señal o ruido?:** gráficos pequeños XmR por movimiento (nuevos, expansión, contracción, churn), 31 meses, con límites naturales calculados sobre una línea base de 18 meses.
6. **Dueños y reglas:** tabla métrica → dueño → regla de alerta → acción.

Al final de la vista: **Comportamiento del cliente vs. pricing vs. descuentos** del mes (descuentos = "sin dato: instrumentar").

### 3.2 Revisión semanal del funnel (CRO, prototipo sintético)
1. **Recuadro "Qué cambió"** a partir de las señales de la semana.
2. **Árbol de métricas:**
   - Salida: MRR nuevo = clientes nuevos × ticket.
   - Clientes nuevos = leads × conversión por camino.
   - Entradas controlables: speed-to-lead (SLA de 1 hora), mezcla de canal (% de leads de alto ajuste), Working → Engaged, win rate post-SQL.
   - Cada nodo con valor, variación y estado.
3. **Formato 6-12** para 4 entradas y 1 salida: últimas 6 semanas | últimos 12 meses, con límites XmR. Siempre el mismo orden, colores y escala.
4. **Diagnóstico** (cuando hay señal): mezcla vs. tasa por canal.
5. **Lista operativa:** leads estancados por etapa y owner (> P90).
6. **Dueños y reglas.**

## 4. Reglas de diseño (se mantienen)
- Título = hallazgo; subtítulo = qué, unidad y periodo; "Ver datos"; fuente y fecha de corte.
- Máximo 4 KPI por fila, la principal en mint; toda variación dice contra qué se compara.
- Paleta validada por tema; un solo eje Y; el estado siempre lleva palabra o ícono, nunca solo color.
- **Formato fijo semana a semana:** mismos gráficos, mismo orden, mismos colores (WBR).

## 5. Fuentes
- Stephen Few, *Common Pitfalls in Dashboard Design* (Perceptual Edge, 2006): [PDF](https://www.perceptualedge.com/articles/Whitepapers/Common_Pitfalls.pdf)
- Commoncog, [The Amazon Weekly Business Review](https://commoncog.com/the-amazon-weekly-business-review/) y [Process Behaviour Charts: More Than You Need To Know](https://commoncog.com/process-behaviour-charts-more-than-you-need/)
- [Shewhart individuals control chart](https://en.wikipedia.org/wiki/Shewhart_individuals_control_chart) (constantes 2,66 y 3,267)
- ChartMogul, [MRR Movements](https://help.chartmogul.com/hc/en-us/articles/6245832909852-Chart-MRR-Movements) y [Layer cake cohort analysis](https://help.chartmogul.com/article/226-creating-a-layer-cake-cohort-analysis)
- Winning by Design, [Bowtie data model](https://winningbydesign.com/design/bowtie-data-model/)
- Board reporting: [CFO Pro Analytics](https://cfoproanalytics.com/cfo-wiki/saas/saas-board-reporting-best-practices/), [Eru](https://www.joineru.com/blog/board-reporting-guide.html)
- Pipeline review: [Rework](https://resources.rework.com/libraries/pipeline-management/pipeline-reviews), [Weflow](https://www.weflow.ai/blog/revops-pipeline-health-dashboards-deal-risk)
- Árboles de métricas: [KPI Tree, SaaS](https://kpitree.co/guides/by-industry/metric-trees-for-saas), [Basedash](https://www.basedash.com/blog/how-to-design-a-metric-tree-a-practical-framework-for-saas-analytics)
- Requisitos de tableros: [Datawireframe](https://www.datawirefra.me/blog/dashboard-requirements-gathering)
- Por qué fallan los tableros: [Reveal BI](https://www.revealbi.io/blog/dashboard-adoption-problem), [Data Cult](https://www.datacult.ai/2026/03/02/what-is-decision-grade-analytics-and-why-dashboards-fail/)
- Narrativa en tableros ejecutivos: [FanRuan](https://www.fanruan.com/en/blog/executive-summary-dashboard)
- Cole Nussbaumer Knaflic, *Storytelling with Data* (2015): explicativo vs. exploratorio, la gran idea y la historia de 3 minutos.
