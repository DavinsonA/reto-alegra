# Bitácora de uso de IA

> El reto pide compartir el proceso. Aquí queda cómo trabajé con la IA, qué verificó cada entrega y qué errores de la IA
> se detectaron y corrigieron. Todo lo que se publica (apps, documentos, Power BI) sale de las mismas tablas agregadas,
> sin identificadores de cliente.

**Herramientas:** Claude Code (modelo Claude) con búsqueda web; skills de marca, visualización, revisión de diseño
(avoid-ai-design, general-design-review) y grill-me (interrogar el plan antes de construir); Power BI Authoring MCP de
Microsoft; pytest, Playwright (capturas) y DuckDB para las validaciones.

## 1. Cómo trabajé

| Fase | Qué hizo la IA | Qué hice yo |
|---|---|---|
| Preparar | Investigación con fuentes (58 referencias: ChartMogul, Stripe, Baremetrics, Few, Wheeler, Scale VP…), lectura del enunciado, ronda de preguntas al plan (grill-me) | Elegir qué decisiones tomar y cuáles documentar como deliberadas |
| Explorar | Perfilado de los tres CSV y notebooks que reproducen el camino a cada conclusión | Revisar series reales una a una y decidir qué patrón era mora, prepago o cambio de plan |
| Proponer | Motor de MRR corregido con reglas explícitas, modelo de dos capas, prototipo sintético del funnel, métricas de S&M | Fijar las reglas (N = 2 meses de mora, prepagos, subidas de precio aparte) y sus supuestos |
| Revisar | Pruebas con respuesta conocida, conciliación mes a mes, SQL contra Python, sensibilidad de cada regla, revisión visual con capturas | Leer cada cifra contra los documentos y pedir corrección cuando algo no cuadraba |
| Comunicar | Tres apps de Streamlit, documentos generados desde una sola fuente de cifras, equivalente en Power BI, guiones | Decidir la narrativa (dos preguntas, CFO primero), el plan a 90 días y qué no concluir |

## 2. Cómo se verificó cada entrega

- **Pruebas con respuesta conocida** (65 en total): los tres casos del CFO, mora, retroactivo, prepagos, bordes, cada regla del motor, cada pantalla de las tres apps y cada visual del Power BI contra el modelo.
- **Conciliación:** en cada mes, la suma de movimientos es igual al cambio del MRR en ambos modelos; en los meses pagados, caja = MRR + extra.
- **Validación cruzada:** el puente del modelo actual y los casos de dos capas dan lo mismo en SQL (DuckDB) y en Python.
- **Sensibilidad:** cada regla se cambia una a la vez (10 variantes); ninguna cambia el signo ni el orden de magnitud. El factor de exageración del churn queda entre 2,6 y 4,6 veces.
- **Una sola fuente de cifras:** README, HALLAZGOS y NOTA_CORTA se generan desde `app/data/key_figures.csv`; una prueba exige que las cifras de la nota aparezcan tal cual en las apps, y la última celda de cada notebook falla si su cifra no coincide.
- **Renderizar y mirar:** capturas automáticas de cada pantalla con Playwright, revisadas a 1440 y 1280 px; paleta validada con un script de daltonismo.
- **Power BI:** consultas DAX contra el modelo abierto en Desktop (MRR 95,7 MM; neto +2,4; mora 3,1 MM en 46 clientes; acumulados iguales a key_figures.csv).

## 3. Errores de la IA que se detectaron, y cómo

| Error | Cómo se detectó | Corrección |
|---|---|---|
| El motor habría marcado como «pago agrupado» a un cliente que duplica su plan y se queda ahí | Revisión del código antes de aceptarlo | Condición «el monto alto no se mantiene» y una prueba |
| Prepagos anuales (pago grande y 6 o más meses en 0) contados como «nuevo + churn» | Prueba de robustez: el ticket al 3er mes no cuadraba con el del 1er mes | Regla de prepago y 2 pruebas; el churn corregido pasó de −27,6 a −17,9 MM |
| Una prueba esperaba churn con solo 2 ceros al final, que la regla N = 2 trata como mora abierta | La prueba fallaba contra el motor correcto | Se corrigió la prueba, no el motor |
| 94 subidas de precio de oct-2024 dadas por persistentes sin mes siguiente; 9 pagos grandes al final leídos como MRR (una «reactivación» de 1,1 MM de un cliente que paga cada 12 a 14 meses) | Revisión final de las series detrás de las cifras raras del tablero | Ambos quedan «en confirmación»; el MRR de oct-2024 pasó de 97,6 a 95,7 MM |
| El tablero mostraba churn = 0 «dentro de lo normal» en sep y oct 2024, cuando el churn de los últimos 2 meses no se puede confirmar | Revisión visual de las capturas | Se muestra «en confirmación» con el MRR en mora, y esos meses salen del cálculo de límites |
| Cifras distintas entre la app y HALLAZGOS (87 frente a 85 bajadas; NRR 53 % frente a 50 %; MRR nuevo +56 %, +53 % y por fin +51 %) | Revisión visual y lectura cruzada de documentos | Ventana única (abr-2022 a oct-2024), cifras generadas desde una sola fuente y prueba de consistencia |
| El gráfico de control solo con límites ±3σ casi no alertaba en el prototipo del funnel | Problemas plantados que las métricas debían detectar | Regla de rachas de 8 puntos (Western Electric) y cierres «Lost» |
| El funnel sintético era una caricatura (SLA 0,6 %, 1.661 estancados) | Revisión de la demo con ojos de evaluador | Problemas plausibles (SLA de 30 a 8 %, P50 de 1,8 a 5 h) y prueba que exige la detección con 4 semillas |
| Paleta: naranja + magenta para pérdidas y el gris del modelo actual contra el mint | Script de daltonismo (ΔE 9,1 < 15) | Naranja + violeta; lavanda para el modelo actual |
| Un reemplazo con regex vació el nombre de una sección de la demo; estuvo publicada con una opción en blanco | Revisión de la app desplegada | Restaurado y prueba que falla si una sección queda sin nombre |
| El script que simplificó comentarios duplicó una edición y borró líneas de código | Compilación de los 25 archivos | Restaurado desde git y corregido antes de volver a correr |
| Dos parches anclados en la definición de `pager()` en vez de su llamada; una variable definida dentro del bloque que el modo compacto omite | Compilación y pruebas de cada pantalla (UnboundLocalError) | Restaurar desde git; mover la definición |
| La demo decía «el mismo puente de MRR en SQL y en Python»; el SQL cubre el modelo actual y los casos de dos capas, no el corregido | Revisión del guion contra el código | Frase corregida en la demo y en el guion |
| En DAX: una medida como filtro booleano dentro de CALCULATE, MAX sobre booleano, `post` como nombre de variable, tarjetas que ignoran el escalado del formato («95.704.590,9,, MM»), el segmentador de mes filtraba las series XmR, formatos dinámicos que rompían las tarjetas | Errores del modelo al abrir en Desktop y capturas de cada ciclo | Literales en los filtros, COUNTROWS, nombre nuevo, KPI como medidas de texto, interacciones de página sin filtro, formatos fijos |
| Cifra «100× en 5 minutos» atribuida a HBR en la investigación | Búsqueda de la fuente original | Marcada como no rastreable y no usada |
| Un modelo de rezagos (adstock) por rubro de S&M | 31 puntos y 7 rubros colineales; ningún rubro correlaciona con las altas | Descartado; se usan magic number, payback por cohorte y CAC variable |

## 4. Bitácora por sesión

| Fecha | Tarea | Produjo | Verificación |
|---|---|---|---|
| 2026-09 | Investigación de buenas prácticas (funnel híbrido, MRR con descuentos, speed-to-lead, Kitagawa) | `research/reto-tecnico.md` | Fuentes enlazadas y contrastadas entre herramientas |
| 2026-10-01 | Perfilado de los tres CSV | Primer barrido (reemplazado luego por los notebooks) | Series de 11 clientes revisadas a mano; pagos de puesta al día múltiplos enteros |
| 2026-10-01 | Motor de MRR actual y corregido, dos capas, pruebas | `finora/`, `tests/`, `pipeline.py`, `HALLAZGOS.md` | Respuesta conocida, conciliación, caja = MRR + extra, sensibilidad |
| 2026-10-01 | Decisiones de modelado D1–D8 y validación cruzada en SQL | `docs/modelo_datos.md`, `sql/`, `tests/test_sql.py` | Documentación de ChartMogul y dbt; SQL = Python mes a mes |
| 2026-10-01 | Prototipo sintético del funnel y métricas | `finora/funnel_synth.py`, `finora/funnel.py` | Dos problemas plantados y detectados; post-SQL estable |
| 2026-10-01 | Demo en Streamlit con datos agregados, marca propia, modo claro | `app/`, `finora/aggregates.py`, `tools/screenshot.py` | AppTest por sección; sin `customer_id` en ninguna tabla; paleta validada; capturas |
| 2026-10-01 | Investigación de diseño del tablero (decidir y operar) y XmR | `docs/diseno_dashboard.md`, `finora/xmr.py`, `app/operar.py` | 13 principios con fuente; pruebas del XmR; revisión visual |
| 2026-10-01 | Nota corta y separación en tres apps | `NOTA_CORTA.md`, `app/historia.py`, `app/demo.py`, `app/tablero.py` | Prueba de cada pantalla; cifras de la nota contra HALLAZGOS |
| 2026-10-01 | Auditoría de «diseño de plantilla» y rediseño con líneas finas | `app/brand.py`, las tres apps | Catálogo de patrones: 0 graves, 4 medios, 3 menores; capturas antes y después |
| 2026-10-01 | Revisión final en bloques: credibilidad del motor, tablero, historia, demo, despliegue, consistencia documental | 3 reglas nuevas, `rule_sensitivity`, cifras generadas, `tools/keep_awake.py`, workflow, capturas | Sensibilidad de 10 variantes; pruebas por regla; prueba de consistencia; 59 pruebas sin advertencias |
| 2026-10-03 | Notebooks que reproducen el camino a las conclusiones | `notebooks/01…05.ipynb` con salidas | Última celda de cada uno contra key_figures.csv; sin identificadores |
| 2026-10-03 | Simplificación de comentarios, docstrings, documentación y código | 25 archivos (−215 líneas) | Diff auditado línea a línea; pruebas y notebooks reejecutados |
| 2026-10-03 | Eficiencia del S&M: magic number, payback por cohorte, CAC variable | `finora/aggregates.py`, `finora/figures.py`, `tests/test_sm.py`, notebook 05 | Fuentes del umbral 0,75 y del payback; tablas reconstruidas en prueba |
| 2026-10-03 | Narrativa del proceso con IA y tabla de referencias → decisiones | `app/demo.py` › Proceso, guion del video 2 | Cada fila apunta a una fuente y a una regla concreta |
| 2026-10-03 | Historia ejecutiva en 7 pasos guiados por las dos preguntas; tablero simplificado con la regla 3-30-300 | `app/historia.py`, `app/operar.py` reescrito, capturas | Prueba por paso; la mensual pasa de 8 gráficos a 1 visible; 62 pruebas |
| 2026-10-03 | Equivalente del tablero en Power BI con el MCP de Microsoft | `dashboard/equivalent_dashboard.pbip` (13 tablas, 76 medidas, 66 visuales generados por `build_report.py`), `tests/test_powerbi.py` | Consultas DAX contra el modelo; cada visual referencia campos existentes; 65 pruebas |
| 2026-10-03 | Limpieza de la historia y guiones en tono natural; teleprompter para grabar | `app/historia.py`, guiones, capturas | Pruebas en verde; guion contado: 679 palabras sin recortables (4:51) |
