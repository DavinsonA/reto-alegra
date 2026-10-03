-- Movimientos en dos capas sobre fct_mrr_customer_month: capa cliente (lista) y capa pricing (descuento).

CREATE OR REPLACE VIEW v_two_layer_movements AS
WITH x AS (
    SELECT
        customer_id, month, list_mrr_cop AS l, discount_mrr_cop AS d,
        LAG(list_mrr_cop, 1, 0)     OVER w AS lp,
        LAG(discount_mrr_cop, 1, 0) OVER w AS dp,
        MAX(CASE WHEN list_mrr_cop > 0 THEN 1 ELSE 0 END) OVER (
            PARTITION BY customer_id ORDER BY month
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS active_before,
        ROW_NUMBER() OVER w AS rn
    FROM fct_mrr_customer_month
    WINDOW w AS (PARTITION BY customer_id ORDER BY month)
),
customer_layer AS (
    SELECT customer_id, month, 'customer' AS layer,
        CASE
            WHEN lp = 0 AND l > 0 THEN CASE WHEN COALESCE(active_before, 0) = 1 THEN 'reactivation' ELSE 'new' END
            WHEN lp > 0 AND l = 0 THEN 'churn'
            WHEN l > lp THEN 'expansion'
            WHEN l < lp THEN 'contraction'
        END AS movement,
        l - lp AS amount_cop
    FROM x WHERE rn > 1 AND l <> lp
),
pricing_layer AS (
    SELECT customer_id, month, 'pricing' AS layer,
        CASE
            WHEN lp > 0 AND l = 0 THEN 'discount_release_on_churn'
            WHEN dp = 0           THEN 'discount_start'
            WHEN d = 0            THEN 'discount_end'
            ELSE 'discount_change'
        END AS movement,
        -(d - dp) AS amount_cop
    FROM x WHERE rn > 1 AND d <> dp
)
SELECT * FROM customer_layer
UNION ALL
SELECT * FROM pricing_layer;

CREATE OR REPLACE VIEW v_bridge_two_layer AS
SELECT
    month,
    SUM(CASE WHEN layer = 'customer' THEN amount_cop ELSE 0 END)                 AS customer_behavior_cop,
    SUM(CASE WHEN layer = 'pricing' AND movement <> 'discount_release_on_churn'
             THEN amount_cop ELSE 0 END)                                         AS pricing_discounts_cop,
    SUM(CASE WHEN movement = 'discount_release_on_churn' THEN amount_cop ELSE 0 END) AS churn_discount_release_cop,
    SUM(amount_cop)                                                              AS net_change_cop
FROM v_two_layer_movements
GROUP BY month
ORDER BY month;

CREATE OR REPLACE VIEW v_price_capture AS
SELECT
    month,
    SUM(list_mrr_cop)                          AS list_mrr_cop,
    SUM(discount_mrr_cop)                      AS discount_leakage_cop,
    SUM(net_mrr_cop)                           AS net_mrr_cop,
    SUM(net_mrr_cop) / NULLIF(SUM(list_mrr_cop), 0) AS price_realization
FROM fct_mrr_customer_month
GROUP BY month
ORDER BY month;
