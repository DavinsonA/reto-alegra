-- Modelo propuesto: MRR en dos capas (lista − descuento = neto). Diccionario en docs/modelo_datos.md.

CREATE TABLE IF NOT EXISTS dim_plan (
    plan_id            VARCHAR,
    plan_name          VARCHAR,
    billing_interval_m INTEGER,
    list_price_cop     DECIMAL(14, 2),
    valid_from         DATE,
    valid_to           DATE,
    PRIMARY KEY (plan_id, valid_from)
);

CREATE TABLE IF NOT EXISTS fct_subscription_version (
    subscription_id    VARCHAR,
    customer_id        INTEGER,
    plan_id            VARCHAR,
    quantity           DECIMAL(12, 2),
    list_mrr_cop       DECIMAL(14, 2),
    change_reason      VARCHAR,
    valid_from         DATE,
    valid_to           DATE,
    PRIMARY KEY (subscription_id, valid_from)
);

CREATE TABLE IF NOT EXISTS dim_discount (
    discount_id        VARCHAR PRIMARY KEY,
    discount_type      VARCHAR,
    discount_value     DECIMAL(10, 4),
    duration_type      VARCHAR,
    duration_months    INTEGER,
    reason             VARCHAR,
    campaign_id        VARCHAR,
    approved_by        VARCHAR
);

CREATE TABLE IF NOT EXISTS fct_discount_assignment (
    assignment_id      VARCHAR PRIMARY KEY,
    discount_id        VARCHAR REFERENCES dim_discount (discount_id),
    subscription_id    VARCHAR,
    start_month        DATE,
    scheduled_end      DATE,
    actual_end         DATE,
    end_reason         VARCHAR,
    owner_sales_rep    VARCHAR
);

CREATE TABLE IF NOT EXISTS fct_invoice (
    invoice_id         VARCHAR PRIMARY KEY,
    customer_id        INTEGER,
    period_start       DATE,
    period_end         DATE,
    recurring_cop      DECIMAL(14, 2),
    discount_cop       DECIMAL(14, 2),
    one_time_cop       DECIMAL(14, 2),
    tax_cop            DECIMAL(14, 2),
    amount_paid_cop    DECIMAL(14, 2),
    due_date           DATE,
    paid_at            DATE,
    status             VARCHAR
);

CREATE TABLE IF NOT EXISTS fct_mrr_customer_month (
    customer_id        INTEGER,
    month              DATE,
    list_mrr_cop       DECIMAL(14, 2),
    discount_mrr_cop   DECIMAL(14, 2),
    net_mrr_cop        DECIMAL(14, 2),
    billing_status     VARCHAR,
    PRIMARY KEY (customer_id, month)
);
