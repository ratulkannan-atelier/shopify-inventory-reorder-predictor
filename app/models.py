from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app import db


class Shop(db.Model):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_domain: Mapped[str] = mapped_column(String(255), unique=True)
    access_token: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("shop_id", "shopify_product_id"),
        CheckConstraint("current_inventory >= 0", name="products_current_inventory_check"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"))
    shopify_product_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(Text)
    sku: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_inventory: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Order(db.Model):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("shop_id", "shopify_order_id", "product_id"),
        CheckConstraint("quantity > 0", name="orders_quantity_check"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(Integer, ForeignKey("shops.id"))
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"))
    shopify_order_id: Mapped[int] = mapped_column(BigInteger)
    quantity: Mapped[int] = mapped_column(Integer)
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Forecast(db.Model):
    __tablename__ = "forecasts"
    __table_args__ = (
        CheckConstraint("days_until_stockout > 0", name="forecasts_days_until_stockout_check"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), unique=True)
    sales_velocity: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    days_until_stockout: Mapped[int] = mapped_column(Integer)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
