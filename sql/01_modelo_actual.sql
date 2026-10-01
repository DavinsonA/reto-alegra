-- =====================================================================================
-- 01 · Modelo ACTUAL de Finora: cliente + mes + monto pagado → movimientos de MRR
-- Dialecto: DuckDB (compatible con Postgres salvo read_csv/strptime).
-- Es la lógica que hoy usa Finora: el MRR es la caja del mes.
-- Sirve para (a) reproducir el modelo actual y (b) validar de forma independiente
-- el motor en Python (tests/test_sql.py compara ambos puentes mes a mes).
-- =====================================================================================

CREATE OR REPLACE TABLE stg_transactions AS
SELECT
    ID                                              AS customer_id,
    date_trunc('month', strptime(month, '%m/%d/%Y'))::DATE AS month,
    amount * 10000                                  AS cash_cop          -- enunciado: ×10.000 = COP
FROM read_csv('data/Transactions.csv', header = true, columns = {'ID': 'INTEGER', 'month': 'VARCHAR', 'amount': 'DOUBLE'});

-- Movimiento por cliente-mes según el modelo actual
CREATE OR REPLACE TABLE fct_mrr_movement_actual AS
WITH x AS (
    SELECT
        customer_id, month, cash_cop,
        LAG(cash_cop, 1, 0) OVER w                         AS prev_cop,
        ROW_NUMBER() OVER w                                AS rn,
        -- ¿pagó alguna vez ANTES de este mes?
        MAX(CASE WHEN cash_cop > 0 THEN 1 ELSE 0 END) OVER (
            PARTITION BY customer_id ORDER BY month
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS paid_before
    FROM stg_transactions
    WINDOW w AS (PARTITION BY customer_id ORDER BY month)
)
SELECT
    customer_id, month, cash_cop AS mrr_cop, prev_cop,
    CASE WHEN rn = 1 THEN 0 ELSE cash_cop - prev_cop END AS delta_cop,
    CASE
        WHEN rn = 1 THEN CASE WHEN cash_cop > 0 THEN 'opening' ELSE 'none' END
        WHEN prev_cop = 0 AND cash_cop > 0 THEN
             CASE WHEN COALESCE(paid_before, 0) = 1 THEN 'reactivation' ELSE 'new' END
        WHEN prev_cop > 0 AND cash_cop = 0 THEN 'churn'
        WHEN cash_cop > prev_cop THEN 'expansion'
        WHEN cash_cop < prev_cop THEN 'contraction'
        ELSE 'none'
    END AS movement
FROM x;

-- Puente mensual + conciliación (mrr_open + Σ movimientos − mrr_close = 0)
CREATE OR REPLACE TABLE rpt_bridge_actual AS
WITH m AS (
    SELECT month,
        SUM(mrr_cop)                                                     AS mrr_close,
        SUM(CASE WHEN movement = 'new'          THEN delta_cop ELSE 0 END) AS new,
        SUM(CASE WHEN movement = 'expansion'    THEN delta_cop ELSE 0 END) AS expansion,
        SUM(CASE WHEN movement = 'contraction'  THEN delta_cop ELSE 0 END) AS contraction,
        SUM(CASE WHEN movement = 'churn'        THEN delta_cop ELSE 0 END) AS churn,
        SUM(CASE WHEN movement = 'reactivation' THEN delta_cop ELSE 0 END) AS reactivation
    FROM fct_mrr_movement_actual
    GROUP BY month
)
SELECT *,
    LAG(mrr_close) OVER (ORDER BY month) AS mrr_open,
    LAG(mrr_close) OVER (ORDER BY month) + new + expansion + contraction + churn + reactivation - mrr_close AS check_cop
FROM m
ORDER BY month;
