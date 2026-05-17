import logging

from flask import Blueprint, abort, redirect, render_template, request, url_for
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

    success_message = (
        "Reorder confirmed. We won't email again until inventory dips below threshold."
        if request.args.get("reordered")
        else None
    )

    return render_template(
        "dashboard.html",
        products=products,
        last_updated=last_updated,
        success_message=success_message,
    )


@dashboard_bp.get("/reorder-confirmed")
def reorder_confirmed():
    try:
        product_id = int(request.args["product_id"])
        shop_id = int(request.args["shop_id"])
    except (KeyError, ValueError):
        abort(400)

    db.session.execute(
        text(
            """
            UPDATE forecasts
            SET reorder_flagged_at = NULL
            WHERE product_id = :pid
              AND product_id IN (SELECT id FROM products WHERE shop_id = :sid)
            """
        ),
        {"pid": product_id, "sid": shop_id},
    )
    db.session.commit()
    return redirect(url_for("dashboard.dashboard", reordered="1"))
