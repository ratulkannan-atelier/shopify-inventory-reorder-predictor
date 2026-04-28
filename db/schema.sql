CREATE TABLE shops (
    id              SERIAL PRIMARY KEY,
    shop_domain     VARCHAR(255) NOT NULL UNIQUE,
    access_token    TEXT NOT NULL,
    email           TEXT NOT NULL,
    installed_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE products (
    id                    SERIAL PRIMARY KEY,
    shop_id               INTEGER NOT NULL REFERENCES shops(id),
    shopify_product_id    BIGINT NOT NULL,
    title                 TEXT NOT NULL,
    sku                   TEXT,
    current_inventory     INTEGER NOT NULL DEFAULT 0 CHECK (current_inventory >= 0),
    updated_at            TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(shop_id, shopify_product_id)
);

CREATE TABLE orders (
    id                  SERIAL PRIMARY KEY,
    shop_id             INTEGER NOT NULL REFERENCES shops(id),
    product_id          INTEGER NOT NULL REFERENCES products(id),
    shopify_order_id    BIGINT NOT NULL,
    quantity            INTEGER NOT NULL CHECK (quantity > 0),
    ordered_at          TIMESTAMPTZ NOT NULL,
    UNIQUE(shop_id, shopify_order_id, product_id)
);

CREATE TABLE forecasts (
    id                    SERIAL PRIMARY KEY,
    product_id            INTEGER NOT NULL UNIQUE REFERENCES products(id),
    sales_velocity        NUMERIC(10,4) NOT NULL,
    days_until_stockout   INTEGER NOT NULL CHECK (days_until_stockout > 0),
    computed_at           TIMESTAMPTZ DEFAULT NOW()
);