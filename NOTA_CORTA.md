# Nota corta: reto Business Analytics (Finora)

Davinson Arteaga · octubre de 2026

- Historia ejecutiva: https://finora-historia.streamlit.app/
- Demo y proceso con IA: https://finora-demo.streamlit.app/
- Tablero operativo: https://finora-tablero.streamlit.app/
- Repositorio: https://github.com/DavinsonA/reto-alegra
- Respaldo si una app tarda en despertar: capturas de cada vista en `docs/capturas/`

**La idea en una frase:** Finora mide caja y la llama MRR. Por eso confunde lo que hace el cliente con lo que decide
la empresa (cobro, precios, descuentos, canales), y separar las dos cosas cambia dónde invertir.

## 1. Qué preguntas prioricé

1. **¿El modelo actual (cliente + mes + monto pagado) separa el comportamiento del cliente de las decisiones comerciales?** Empecé por el CFO porque sin un MRR confiable cualquier lectura del funnel hereda el error.
2. **¿Cuánto del cambio del MRR es cliente, cuánto pricing y cuánto descuentos?** Medí lo medible y acoté lo que no.
3. **¿Dónde se pierde el crecimiento?** Con los datos disponibles respondí el extremo "Won" (cuántos clientes entran y de qué tamaño, por industria). Para el resto del funnel diseñé cómo medirlo.
4. **¿Cómo se opera cada mes y cada semana?** Construí una revisión mensual del MRR y una semanal del funnel, con señales estadísticas, dueños y reglas.

## 2. Supuestos

- **Un 0 en `Transactions` significa "no se cobró", no "no se facturó".** Toda la lógica de mora depende de esto. Si el 0 significara "sin servicio", el modelo de caja tendría razón y la mora no existiría.
- **Unidades:** `Transactions` es caja cobrada en el mes (× 10.000 = COP) y `S&M` está en cientos de millones de COP, como dice el enunciado.
- **Mora:** un cliente con hasta 2 meses sin pago, o que después paga todo lo atrasado, sigue activo. El churn se confirma después de 2 meses sin pago.
- **Pagos de varios meses:**
  - Un pago de k veces el monto después de k − 1 meses en cero es una puesta al día, no expansión.
  - Un pago de 200 mil COP o más seguido de 6 o más meses en cero es un prepago, y se reparte en hasta 12 meses.
- **Subida de precio:** se reconoce por el cobro retroactivo (confianza alta) o por un alza persistente de 2 % a 10 % (confianza media). El retroactivo es un cargo único.
- **Lo que pasa en el último mes no se puede confirmar, y se marca "en confirmación":**
  - El churn de 46 clientes en mora abierta.
  - 94 subidas de precio (0,4 MM), porque falta el mes siguiente para ver si persisten.
  - 9 pagos grandes que pueden ser prepagos.
- **Inicio de la serie:** enero a marzo de 2022 es base de apertura, porque esos clientes ya existían.
- **Funnel:** los datos del prototipo son sintéticos y solo prueban el diseño.

## 3. Información que hizo falta

- **CFO:**
  - Precio de lista y plan por cliente y mes.
  - Registro de descuentos (inicio, fin, motivo, aprobador).
  - Estado de la suscripción y fecha de cancelación.
  - Facturas con cargos únicos y mora; margen bruto.
- **CRO:**
  - Eventos de etapa con fecha y hora; canal y fuente del lead; dueño; primer contacto.
  - Motivos de descalificación y de pérdida.
  - Eventos de producto y enlace entre lead y cliente.
  - Gasto por canal y capacidad de SDR y AE.
- **Validar con Finanzas las unidades del S&M:** con las del enunciado, cada peso de S&M devuelve entre 2 y 27 centavos de ARR nuevo (magic number; el mercado exige 75) y ninguna cohorte ha devuelto su S&M en 24 meses. Si las unidades estuvieran infladas 10 veces, el magic number quedaría en rango normal. Antes de cualquier decisión de inversión hay que confirmarlas.

## 4. Qué cambiaría del modelo actual

- **Separar la caja del MRR.** Los cobros viven en facturas, y la mora, los prepagos y los cargos únicos no son MRR.
- **MRR en dos capas: lista − descuento = neto.** El descuento se registra como una entidad con inicio, fin, motivo y aprobador.
  - El inicio y el fin de un descuento se clasifican en la capa de pricing: **el fin de un descuento no es expansión**.
  - La subida de precio de catálogo va en su propia línea.
- **Churn confirmado con regla de mora,** con el MRR en mora visible para Cobranza.
- **Funnel medido por eventos y por camino** (self-serve, directo a SQL, recorrido SDR), con conversión por cohorte de creación y tiempo al primer contacto.
- **Revisión recurrente:** mensual para el CFO y semanal para el CRO. Cada métrica lleva límites de variación normal (gráfico XmR), dueño, regla de alerta y acción.

## 5. Cómo usé la IA, qué validé y cómo aseguré la calidad

- **Herramientas:**
  - **Claude con búsqueda web** para investigar buenas prácticas, siempre con fuentes (ChartMogul, dbt, a16z, Winning by Design, la Weekly Business Review de Amazon y Stephen Few).
  - **Claude Code** para perfilar los datos y escribir el motor de MRR, el SQL y las apps.
  - Yo definí las preguntas, las reglas y las decisiones, y revisé cada resultado.
- **Qué validé:**
  - 61 pruebas automáticas: los casos del CFO, la conciliación del puente mes a mes y cada vista de las 3 apps.
  - **El mismo cálculo en SQL y en Python, con el mismo resultado.**
  - **Sensibilidad por regla, una a la vez (10 variantes): ninguna cambia el signo ni el orden de magnitud.** El churn corregido va de −15,7 a −27,6 MM, contra −72,9 MM en el modelo actual.
  - Revisión manual de las series de 11 clientes y revisión visual de cada vista.
  - Cada cifra de este documento sale de una sola tabla (`app/data/key_figures.csv`), y una prueba falla si un documento no coincide.
- **Errores que detecté y corregí:**
  - Una regla que leía un upgrade real como pago agrupado.
  - Prepagos anuales contados como "nuevo + churn": al corregirlo, el churn pasó de −27,6 a −18,0 MM.
  - Pagos grandes al final de la serie leídos como MRR. Al tratarlos como prepagos en confirmación, el MRR de oct-2024 pasó de 97,6 a 95,7 MM.
  - Subidas de precio del último mes dadas por confirmadas sin el mes siguiente.
  - Churn en cero en meses que todavía no se pueden confirmar.
  - Cifras distintas entre documentos y una ventana distinta para el NRR de 2022.
  - Una paleta de colores que fallaba la prueba de daltonismo.
- **Datos:** las apps públicas usan solo tablas agregadas, sin detalle por cliente.

**Resultado principal (abr-2022 a oct-2024):**
- El cambio neto del MRR es parecido en ambos modelos (corregido: +53,1 MM).
- El modelo actual exagera el churn 4,1 veces y la reactivación 14,4 veces. Entre las variantes de las reglas, el churn va de 2,6 a 4,6 veces.
- **Respuesta al CFO:**
  - Comportamiento del cliente: +51,5 MM.
  - Subidas de precio: +1,7 MM (0,4 MM aún en confirmación).
  - Descuentos: no se pueden medir con caja. Hay 85 bajadas exactas al 50 % que pueden ser descuentos o downgrades. Su **cota superior ilustrativa**, 40,8 MM, no es una estimación: es el argumento para medir en dos capas.
- La retención a 12 meses de las altas de 2023 es 91 %, no 82 %.
- Los clientes nuevos por mes se duplicaron (+106 %), pero entran más pequeños. El ticket de entrada cayó entre 25 % y 29 % según la medida, y el 97 % de esa caída ocurre dentro de cada industria.
