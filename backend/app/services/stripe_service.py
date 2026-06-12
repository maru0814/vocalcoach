"""Stripe決済（docs/31 FR-02/03, docs/33 §3-4）。

- Checkout（subscription mode）/ Customer Portal のセッション生成
- Webhook受信 → subscriptions テーブルへ同期
真実の源泉はStripe。DBはそのキャッシュで、プラン判定は billing_service.is_premium が使う。
"""
from __future__ import annotations

import logging
from datetime import datetime

import stripe
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.billing import Subscription
from app.models.user import User

logger = logging.getLogger(__name__)


def _client() -> None:
    if not settings.stripe_enabled:
        raise RuntimeError("STRIPE_NOT_CONFIGURED")
    stripe.api_key = settings.stripe_secret_key


def _get_or_create_row(db: Session, user_id: int) -> Subscription:
    row = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if row is None:
        row = Subscription(user_id=user_id, status="none")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _ensure_customer(db: Session, user: User) -> str:
    """StripeのCustomerを用意（既存があれば再利用）。"""
    row = _get_or_create_row(db, user.id)
    if row.stripe_customer_id:
        return row.stripe_customer_id
    customer = stripe.Customer.create(email=user.email, metadata={"user_id": str(user.id)})
    row.stripe_customer_id = customer["id"]
    db.add(row)
    db.commit()
    return customer["id"]


def create_checkout_session(db: Session, user: User) -> str:
    """サブスク加入のCheckout Session URLを返す。既にpremiumなら呼ぶ前に弾く想定。"""
    _client()
    customer_id = _ensure_customer(db, user)
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        client_reference_id=str(user.id),
        line_items=[{"price": settings.stripe_price_id_premium, "quantity": 1}],
        success_url=f"{settings.frontend_base_url}/billing/success",
        cancel_url=f"{settings.frontend_base_url}/billing/cancel",
        metadata={"user_id": str(user.id)},
    )
    return session["url"]


def create_portal_session(db: Session, user: User) -> str:
    """解約・カード変更用のCustomer Portal URLを返す。"""
    _client()
    row = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if row is None or not row.stripe_customer_id:
        raise RuntimeError("NO_CUSTOMER")
    session = stripe.billing_portal.Session.create(
        customer=row.stripe_customer_id,
        return_url=f"{settings.frontend_base_url}/settings",
    )
    return session["url"]


# --- Webhook ---

_HANDLED = {
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_failed",
}


def _extract_period_end(sub_obj: dict) -> int | None:
    """current_period_end を取得。新API版(2026-04-22 dahlia〜)は items 配下に移動したため両対応。"""
    if sub_obj.get("current_period_end"):
        return sub_obj["current_period_end"]
    items = (sub_obj.get("items") or {}).get("data") or []
    ends = [it["current_period_end"] for it in items if it.get("current_period_end")]
    return max(ends) if ends else None


def parse_event(payload: bytes, sig_header: str | None) -> stripe.Event:
    """署名検証してEventを返す。失敗は例外（呼び出し側で400）。"""
    if not settings.stripe_webhook_secret:
        raise RuntimeError("WEBHOOK_SECRET_NOT_CONFIGURED")
    return stripe.Webhook.construct_event(
        payload=payload, sig_header=sig_header, secret=settings.stripe_webhook_secret
    )


def _as_dict(obj) -> dict:
    """StripeObject（属性アクセスをkey lookupに横取りする）をプレーンdictに正規化。

    stripe-python 15系は to_dict_recursive を持たないため、JSON経由で再帰的にdict化する。
    すでにdictならそのまま返す（オフラインテスト用）。
    """
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict_recursive"):
        return obj.to_dict_recursive()
    import json as _json
    return _json.loads(str(obj))


def _sync_from_subscription(db: Session, sub_obj: dict) -> None:
    """Stripeのsubscriptionオブジェクトでsubscriptions行を更新。"""
    sub_obj = _as_dict(sub_obj)
    customer_id = sub_obj.get("customer")
    row = (
        db.query(Subscription)
        .filter(Subscription.stripe_customer_id == customer_id)
        .first()
    )
    if row is None:
        # customer未紐付け（稀）。metadataのuser_idで救済。
        user_id = (sub_obj.get("metadata") or {}).get("user_id")
        if not user_id:
            logger.warning("subscription同期: 対象customerが見つからない customer=%s", customer_id)
            return
        row = _get_or_create_row(db, int(user_id))
        row.stripe_customer_id = customer_id
    row.stripe_subscription_id = sub_obj.get("id")
    row.status = sub_obj.get("status", row.status)
    period_end = _extract_period_end(sub_obj)
    if period_end:
        row.current_period_end = datetime.utcfromtimestamp(period_end)
    db.add(row)
    db.commit()


def handle_event(db: Session, event: stripe.Event) -> None:
    etype = event["type"]
    if etype not in _HANDLED:
        return
    obj = _as_dict(event["data"]["object"])
    if etype == "checkout.session.completed":
        # セッションには subscription ID があるので取得して同期
        _client()
        sub_id = obj.get("subscription")
        if sub_id:
            sub_obj = _as_dict(stripe.Subscription.retrieve(sub_id))
            # metadataを引き継いで救済できるよう付与
            if not sub_obj.get("metadata") and obj.get("client_reference_id"):
                sub_obj["metadata"] = {"user_id": obj["client_reference_id"]}
            _sync_from_subscription(db, sub_obj)
    elif etype in (
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        _sync_from_subscription(db, obj)
    elif etype == "invoice.payment_failed":
        # status変更は subscription.updated(past_due) で届く。ここはログのみ。
        logger.info("invoice.payment_failed customer=%s", obj.get("customer"))
