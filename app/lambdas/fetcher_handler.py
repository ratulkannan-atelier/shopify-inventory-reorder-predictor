import json
import logging
import os
from datetime import datetime, timezone

import boto3
from sqlalchemy import text

from app.fetcher import _get_engine, fetch_shop_data
from app.lambdas._db_secret import load_db_secret_into_env

log = logging.getLogger(__name__)

load_db_secret_into_env(os.environ["DB_SECRET_ARN"])

_sqs = boto3.client("sqs")


def lambda_handler(event, context):
    queue_url = os.environ["FORECAST_QUEUE_URL"]
    fetched_at = datetime.now(timezone.utc).isoformat()

    with _get_engine().connect() as conn:
        rows = conn.execute(
            text("SELECT id, shop_domain, access_token FROM shops")
        ).fetchall()

    shops_processed = 0
    messages_enqueued = 0

    for shop_id, shop_domain, access_token in rows:
        try:
            fetch_shop_data(shop_domain, access_token)
            _sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps({"shop_id": shop_id, "fetched_at": fetched_at}),
            )
            messages_enqueued += 1
            log.info("[%s] fetched and enqueued shop_id=%d", shop_domain, shop_id)
        except Exception:
            log.exception("[%s] fetch failed, skipping enqueue", shop_domain)
        shops_processed += 1

    return {"shops_processed": shops_processed, "messages_enqueued": messages_enqueued}
