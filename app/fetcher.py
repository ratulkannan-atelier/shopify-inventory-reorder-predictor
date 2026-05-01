import logging
import os
import re
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy import create_engine, text

log = logging.getLogger(__name__)

_API_VERSION = "2026-04"
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


def _headers(access_token: str) -> dict[str, str]:
    return {"X-Shopify-Access-Token": access_token}


def _next_link(response: requests.Response) -> str | None:
    link_header = response.headers.get("Link", "")
    for part in link_header.split(","):
        if 'rel="next"' in part:
            match = re.search(r"<([^>]+)>", part)
            if match:
                return match.group(1)
    return None


def _fetch_orders(shop: str, access_token: str) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    url = f"https://{shop}/admin/api/{_API_VERSION}/graphql.json"
    headers = {**_headers(access_token), "Content-Type": "application/json"}
    gql = """
        query GetOrders($cursor: String, $query: String) {
          orders(first: 50, after: $cursor, query: $query) {
            edges {
              node {
                legacyResourceId
                createdAt
                lineItems(first: 50) {
                  edges {
                    node {
                      quantity
                      title
                      sku
                      product {
                        legacyResourceId
                      }
                    }
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
    """
    orders: list[dict] = []
    cursor: str | None = None
    has_next = True

    while has_next:
        resp = requests.post(
            url,
            headers=headers,
            json={"query": gql, "variables": {"cursor": cursor, "query": f"created_at:>='{since}'"}},
            timeout=30,
        )
        resp.raise_for_status()
        orders_data = resp.json()["data"]["orders"]

        for edge in orders_data["edges"]:
            node = edge["node"]
            line_items = []
            for li_edge in node["lineItems"]["edges"]:
                li = li_edge["node"]
                product = li.get("product")
                line_items.append({
                    "product_id": int(product["legacyResourceId"]) if product else None,
                    "title": li["title"],
                    "sku": li.get("sku"),
                    "quantity": li["quantity"],
                })
            orders.append({
                "id": int(node["legacyResourceId"]),
                "created_at": node["createdAt"],
                "line_items": line_items,
            })

        has_next = orders_data["pageInfo"]["hasNextPage"]
        cursor = orders_data["pageInfo"].get("endCursor")

    log.info("[%s] fetched %d orders", shop, len(orders))
    return orders


def _fetch_products(shop: str, access_token: str) -> list[dict]:
    url: str | None = f"https://{shop}/admin/api/{_API_VERSION}/products.json"
    params: dict = {"limit": 250}
    products: list[dict] = []

    while url:
        resp = requests.get(url, headers=_headers(access_token), params=params, timeout=30)
        resp.raise_for_status()
        products.extend(resp.json().get("products", []))
        url = _next_link(resp)
        params = {}

    log.info("[%s] fetched %d products", shop, len(products))
    return products


def fetch_shop_data(shop_domain: str, access_token: str) -> None:
    orders = _fetch_orders(shop_domain, access_token)
    products = _fetch_products(shop_domain, access_token)

    with _get_engine().begin() as conn:
        row = conn.execute(
            text("SELECT id FROM shops WHERE shop_domain = :domain"),
            {"domain": shop_domain},
        ).fetchone()
        if row is None:
            log.error("[%s] shop not found in database", shop_domain)
            return
        shop_id: int = row[0]

        line_item_count = 0
        for order in orders:
            shopify_order_id = order["id"]
            ordered_at = order["created_at"]

            for item in order.get("line_items", []):
                shopify_product_id = item.get("product_id")
                if not shopify_product_id:
                    continue  # product was deleted from the store

                quantity = item.get("quantity", 0)
                if quantity <= 0:
                    continue

                result = conn.execute(
                    text(
                        """
                        INSERT INTO products (shop_id, shopify_product_id, title, sku, current_inventory)
                        VALUES (:shop_id, :spid, :title, :sku, 0)
                        ON CONFLICT (shop_id, shopify_product_id) DO UPDATE
                            SET title = EXCLUDED.title,
                                sku   = EXCLUDED.sku
                        RETURNING id
                        """
                    ),
                    {
                        "shop_id": shop_id,
                        "spid": shopify_product_id,
                        "title": item.get("title") or "",
                        "sku": item.get("sku") or None,
                    },
                )
                product_id: int = result.fetchone()[0]

                conn.execute(
                    text(
                        """
                        INSERT INTO orders (shop_id, product_id, shopify_order_id, quantity, ordered_at)
                        VALUES (:shop_id, :product_id, :order_id, :qty, :ordered_at)
                        ON CONFLICT (shop_id, shopify_order_id, product_id) DO NOTHING
                        """
                    ),
                    {
                        "shop_id": shop_id,
                        "product_id": product_id,
                        "order_id": shopify_order_id,
                        "qty": quantity,
                        "ordered_at": ordered_at,
                    },
                )
                line_item_count += 1

        log.info("[%s] upserted %d order line items", shop_domain, line_item_count)

        inventory_count = 0
        for product in products:
            shopify_product_id = product.get("id")
            if not shopify_product_id:
                continue

            total_inventory = sum(
                v.get("inventory_quantity") or 0
                for v in product.get("variants", [])
            )

            conn.execute(
                text(
                    """
                    UPDATE products
                    SET current_inventory = :qty, updated_at = NOW()
                    WHERE shop_id = :shop_id AND shopify_product_id = :spid
                    """
                ),
                {"qty": total_inventory, "shop_id": shop_id, "spid": shopify_product_id},
            )
            inventory_count += 1

        log.info("[%s] updated inventory for %d products", shop_domain, inventory_count)


def run_fetcher() -> None:
    with _get_engine().connect() as conn:
        shops = conn.execute(
            text("SELECT shop_domain, access_token FROM shops")
        ).fetchall()

    log.info("running fetcher for %d shop(s)", len(shops))

    for shop_domain, access_token in shops:
        try:
            fetch_shop_data(shop_domain, access_token)
            log.info("[%s] fetch complete", shop_domain)
        except Exception:
            log.exception("[%s] fetch failed", shop_domain)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    from dotenv import load_dotenv
    load_dotenv()

    run_fetcher()
