import logging
import os
import sys

from sqlalchemy import create_engine, text

log = logging.getLogger(__name__)

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        url = os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}".format(
                user=os.environ.get("POSTGRES_USER", "reorder_user"),
                password=os.environ.get("POSTGRES_PASSWORD", ""),
                host=os.environ.get("POSTGRES_HOST", "localhost"),
                port=os.environ.get("POSTGRES_PORT", "5432"),
                db=os.environ.get("POSTGRES_DB", "reorder_predictor"),
            ),
        )
        _engine = create_engine(url)
    return _engine


def compute_forecasts(shop_id: int, conn) -> int:
    rows = conn.execute(
        text(
            """
            SELECT product_id, SUM(quantity) AS total_sold
            FROM orders
            WHERE shop_id = :shop_id
              AND ordered_at >= NOW() - INTERVAL '30 days'
            GROUP BY product_id
            """
        ),
        {"shop_id": shop_id},
    ).fetchall()

    written = 0
    for product_id, total_sold in rows:
        sales_velocity = total_sold / 30.0
        if sales_velocity == 0:
            continue

        inventory_row = conn.execute(
            text("SELECT current_inventory FROM products WHERE id = :pid"),
            {"pid": product_id},
        ).fetchone()
        if inventory_row is None:
            continue
        current_inventory = inventory_row[0]

        if current_inventory == 0:
            days = 0
        else:
            days = int(current_inventory / (sales_velocity * 1.2))

        conn.execute(
            text(
                """
                INSERT INTO forecasts (product_id, sales_velocity, days_until_stockout, computed_at)
                VALUES (:product_id, :velocity, :days, NOW())
                ON CONFLICT (product_id) DO UPDATE
                    SET sales_velocity      = EXCLUDED.sales_velocity,
                        days_until_stockout = EXCLUDED.days_until_stockout,
                        computed_at         = NOW()
                """
            ),
            {"product_id": product_id, "velocity": sales_velocity, "days": days},
        )
        written += 1

    return written


def run_worker() -> None:
    with _get_engine().connect() as conn:
        shops = conn.execute(text("SELECT id FROM shops")).fetchall()

    log.info("running worker for %d shop(s)", len(shops))

    for (shop_id,) in shops:
        try:
            with _get_engine().begin() as conn:
                count = compute_forecasts(shop_id, conn)
            log.info("[shop_id=%d] wrote %d forecast(s)", shop_id, count)
        except Exception:
            log.exception("[shop_id=%d] forecast failed", shop_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    from dotenv import load_dotenv
    load_dotenv()

    run_worker()
