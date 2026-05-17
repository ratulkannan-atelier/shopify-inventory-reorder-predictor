import logging
import os
from urllib.parse import urlencode

import boto3
from sqlalchemy import text

REORDER_THRESHOLD_DAYS = 14
log = logging.getLogger(__name__)
_ses = None


def _get_ses():
    global _ses
    if _ses is None:
        _ses = boto3.client("ses")
    return _ses


def send_reorder_alerts(shop_id: int, conn) -> int:
    sender = os.environ.get("SES_SENDER_EMAIL")
    base_url = os.environ.get("APP_BASE_URL")
    if not sender or not base_url:
        log.info("SES_SENDER_EMAIL or APP_BASE_URL unset; skipping alerts")
        return 0

    recipient_row = conn.execute(
        text("SELECT email FROM shops WHERE id = :sid"),
        {"sid": shop_id},
    ).fetchone()
    if not recipient_row or not recipient_row[0]:
        return 0
    recipient = recipient_row[0]

    rows = conn.execute(
        text(
            """
            SELECT p.id, p.title, p.current_inventory, f.days_until_stockout
            FROM forecasts f
            JOIN products p ON p.id = f.product_id
            WHERE p.shop_id = :sid
              AND f.days_until_stockout < :threshold
              AND f.reorder_flagged_at IS NULL
            """
        ),
        {"sid": shop_id, "threshold": REORDER_THRESHOLD_DAYS},
    ).fetchall()

    sent = 0
    for product_id, title, inventory, days in rows:
        confirm_url = (
            f"{base_url.rstrip('/')}/reorder-confirmed?"
            + urlencode({"product_id": product_id, "shop_id": shop_id})
        )
        try:
            _send_email(sender, recipient, title, days, inventory, confirm_url)
            conn.execute(
                text("UPDATE forecasts SET reorder_flagged_at = NOW() WHERE product_id = :pid"),
                {"pid": product_id},
            )
            sent += 1
        except Exception:
            log.exception("[product_id=%d] SES send failed", product_id)
    return sent


def _send_email(sender, recipient, title, days, inventory, confirm_url):
    subject = f"Time to reorder: {title}"
    text_body = (
        f"{title} is running low.\n\n"
        f"Days until stockout: {days}\n"
        f"Current inventory: {inventory}\n\n"
        f"Once you've placed a reorder, click:\n{confirm_url}\n"
    )
    html_body = (
        "<html><body>"
        f"<h2>Time to reorder: {title}</h2>"
        f"<p><strong>Days until stockout:</strong> {days}<br>"
        f"<strong>Current inventory:</strong> {inventory}</p>"
        f'<p><a href="{confirm_url}"'
        ' style="background:#008060;color:#fff;padding:10px 20px;'
        'text-decoration:none;border-radius:4px;display:inline-block;">'
        "I've placed a reorder</a></p>"
        "</body></html>"
    )
    _get_ses().send_email(
        Source=sender,
        Destination={"ToAddresses": [recipient]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": text_body}, "Html": {"Data": html_body}},
        },
    )
