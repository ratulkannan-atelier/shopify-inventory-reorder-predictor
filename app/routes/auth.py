import hashlib
import hmac
import logging
import os
import secrets
from urllib.parse import urlencode

import requests
from flask import Blueprint, redirect, request, session
from sqlalchemy import text

from app import db

log = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

_API_KEY = lambda: os.environ["SHOPIFY_API_KEY"]
_API_SECRET = lambda: os.environ["SHOPIFY_API_SECRET"]
_APP_URL = lambda: os.environ["SHOPIFY_APP_URL"].rstrip("/")
_SCOPES = lambda: os.environ["SHOPIFY_API_SCOPES"]


def _validate_shop(shop: str) -> bool:
    return bool(shop) and shop.endswith(".myshopify.com") and "/" not in shop


def _verify_hmac(params: dict[str, str], secret: str) -> bool:
    received = params.pop("hmac", "")
    message = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    digest = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, received)


@auth_bp.get("/install")
def install():
    shop = request.args.get("shop", "").strip()
    if not _validate_shop(shop):
        return {"error": "invalid shop parameter"}, 400

    nonce = secrets.token_hex(16)
    session["oauth_state"] = nonce

    redirect_uri = f"{_APP_URL()}/callback"
    params = urlencode({
        "client_id": _API_KEY(),
        "scope": _SCOPES(),
        "redirect_uri": redirect_uri,
        "state": nonce,
    })
    auth_url = f"https://{shop}/admin/oauth/authorize?{params}"
    return redirect(auth_url)


@auth_bp.get("/callback")
def callback():
    shop = request.args.get("shop", "")
    code = request.args.get("code", "")
    state = request.args.get("state", "")

    if not _validate_shop(shop):
        return {"error": "invalid shop"}, 400

    if state != session.get("oauth_state"):
        return {"error": "state mismatch"}, 403

    query_params = dict(request.args)
    if not _verify_hmac(query_params, _API_SECRET()):
        return {"error": "hmac verification failed"}, 403

    resp = requests.post(
        f"https://{shop}/admin/oauth/access_token",
        data={"client_id": _API_KEY(), "client_secret": _API_SECRET(), "code": code},
        timeout=10,
    )
    resp.raise_for_status()
    access_token = resp.json()["access_token"]
    log.info("[callback] received access_token for shop=%s token_prefix=%s", shop, access_token[:8])

    log.info("[callback] executing upsert for shop=%s", shop)
    result = db.session.execute(
        text(
            """
            INSERT INTO shops (shop_domain, access_token, email)
            VALUES (:shop, :token, '')
            ON CONFLICT (shop_domain) DO UPDATE
                SET access_token = EXCLUDED.access_token,
                    updated_at   = NOW()
            """
        ),
        {"shop": shop, "token": access_token},
    )
    log.info("[callback] upsert rowcount=%d", result.rowcount)
    db.session.commit()
    log.info("[callback] commit complete")

    return redirect("/dashboard")
