import json
import logging
import os

logging.basicConfig(level=logging.INFO)

from app.lambdas._db_secret import load_db_secret_into_env
from app.notifications import send_reorder_alerts
from app.worker import _get_engine, compute_forecasts

log = logging.getLogger(__name__)

load_db_secret_into_env(os.environ["DB_SECRET_ARN"])


def lambda_handler(event, context):
    for record in event["Records"]:
        body = json.loads(record["body"])
        shop_id = body["shop_id"]
        with _get_engine().begin() as conn:
            count = compute_forecasts(shop_id, conn)
            alerts = send_reorder_alerts(shop_id, conn)
        log.info("[shop_id=%d] wrote %d forecast(s), sent %d alert(s)", shop_id, count, alerts)
