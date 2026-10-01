-- =====================================================================================
-- 02 · Modelo PROPUESTO: valor de la suscripción (lista) separado del precio pagado (neto)
-- El descuento es una entidad con vigencia; el MRR se deriva del contrato y se concilia
-- contra lo facturado y cobrado. Diagrama y diccionario: docs/modelo_datos.md
-- =====================================================================================

-- Catálogo de planes con vigencia (permite reconstruir el precio de lista de cualquier mes)
CREATE TABLE IF NOT EXISTS dim_plan (
    plan_id            VARCHAR,
    plan_name          VARCHAR,
    billing_interval_m INTEGER,          -- 1 = mensual, 12 = anual
    list_price_cop     DECIMAL(14, 2),   -- precio de catálogo por unidad y periodo
    valid_from         DATE,
    valid_to           DATE,             -- NULL = vigente
    PRIMARY KEY (plan_id, valid_from)
);

-- Suscripción como historia (SCD tipo 2): un registro por cada cambio de plan, cantidad o uso
CREATE TABLE IF NOT EXISTS fct_subscription_version (
    subscription_id    VARCHAR,
    customer_id        INTEGER,
    plan_id            VARCHAR,
    quantity           DECIMAL(12, 2),   -- usuarios, documentos, módulos… (el "uso" que mueve el valor)
    list_mrr_cop       DECIMAL(14, 2),   -- valor mensualizado a precio de lista
    change_reason      VARCHAR,          -- new | upgrade | downgrade | usage | repricing | renewal | cancel
    valid_from         DATE,
    valid_to           DATE,
    PRIMARY KEY (subscription_id, valid_from)
);

-- Catálogo de descuentos: QUÉ se regala, POR QUÉ y QUIÉN lo aprobó
CREATE TABLE IF NOT EXISTS dim_discount (
    discount_id        VARCHAR PRIMARY KEY,
    discount_type      VARCHAR,          -- percent | fixed
    discount_value     DECIMAL(10, 4),
    duration_type      VARCHAR,          -- once | repeating | forever
    duration_months    INTEGER,
    reason             VARCHAR,          -- promo | onboarding | retention | negotiation | partner | annual_prepay
    campaign_id        VARCHAR,
    approved_by        VARCHAR
);

-- Asignación de un descuento a una suscripción, con inicio y fin (el fin programado es conocido)
CREATE TABLE IF NOT EXISTS fct_discount_assignment (
    assignment_id      VARCHAR PRIMARY KEY,
    discount_id        VARCHAR REFERENCES dim_discount (discount_id),
    subscription_id    VARCHAR,
    start_month        DATE,
    scheduled_end      DATE,             -- fin pactado → "discount-end pipeline"
    actual_end         DATE,
    end_reason         VARCHAR,          -- expired | removed | churn | renegotiated
    owner_sales_rep    VARCHAR
);

-- Facturas y cobros: la caja, separada del MRR (mora, puesta al día, cargos únicos, prepagos)
CREATE TABLE IF NOT EXISTS fct_invoice (
    invoice_id         VARCHAR PRIMARY KEY,
    customer_id        INTEGER,
    period_start       DATE,
    period_end         DATE,             -- cubre 1 o varios meses (prepago anual)
    recurring_cop      DECIMAL(14, 2),
    discount_cop       DECIMAL(14, 2),
    one_time_cop       DECIMAL(14, 2),   -- setup, retroactivos de precio, ajustes
    tax_cop            DECIMAL(14, 2),
    amount_paid_cop    DECIMAL(14, 2),
    due_date           DATE,
    paid_at            DATE,
    status             VARCHAR           -- paid | open | past_due | void | refunded
);

-- Tabla de hechos que responde al CFO: un registro por cliente y mes con las dos capas
CREATE TABLE IF NOT EXISTS fct_mrr_customer_month (
    customer_id        INTEGER,
    month              DATE,
    list_mrr_cop       DECIMAL(14, 2),   -- comportamiento del cliente
    discount_mrr_cop   DECIMAL(14, 2),   -- decisión comercial
    net_mrr_cop        DECIMAL(14, 2),   -- = list − discount  (cifra oficial)
    billing_status     VARCHAR,          -- current | past_due | prepaid
    PRIMARY KEY (customer_id, month)
);
