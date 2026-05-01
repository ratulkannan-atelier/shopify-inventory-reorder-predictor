import logging

from flask import Blueprint, render_template
from sqlalchemy import text

from app import db

log = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/dashboard")
def dashboard():
    rows = db.session.execute(
        text(
            """
            SELECT
                p.title,
                p.current_inventory,
                ROUND(f.sales_velocity::numeric, 2) AS sales_velocity,
                f.days_until_stockout,
                f.computed_at
            FROM forecasts f
            JOIN products p ON p.id = f.product_id
            WHERE p.shop_id = :shop_id
            ORDER BY f.days_until_stockout ASC
            """
        ),
        {"shop_id": 1},
    ).fetchall()

    products = [
        {
            "title": r.title,
            "current_inventory": r.current_inventory,
            "sales_velocity": float(r.sales_velocity),
            "days_until_stockout": r.days_until_stockout,
            "computed_at": r.computed_at,
        }
        for r in rows
    ]

    last_updated = products[0]["computed_at"] if products else None

    return render_template("dashboard.html", products=products, last_updated=last_updated)
