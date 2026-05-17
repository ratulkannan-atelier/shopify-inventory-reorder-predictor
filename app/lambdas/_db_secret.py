import json
import os

import boto3


def load_db_secret_into_env(secret_arn: str) -> None:
    client = boto3.client("secretsmanager")
    secret = json.loads(client.get_secret_value(SecretId=secret_arn)["SecretString"])
    os.environ.setdefault("POSTGRES_USER", secret["username"])
    os.environ.setdefault("POSTGRES_PASSWORD", secret["password"])
    os.environ.setdefault("POSTGRES_HOST", secret["host"])
    os.environ.setdefault("POSTGRES_PORT", secret.get("port", "5432"))
    os.environ.setdefault("POSTGRES_DB", secret.get("dbname", "reorder_predictor"))
