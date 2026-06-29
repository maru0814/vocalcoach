"""Stripe連携（app/services/stripe_service.py）のユニットテスト。

webhookの署名検証ガード・新旧APIのperiod_end両対応・subscription同期と
状態遷移ログを、dictフィクスチャ＋インメモリSQLiteで検証する（Stripeへは通信しない）。
"""
from datetime import datetime

import pytest

from app.core.config import settings
from app.models.billing import Subscription
from app.services import stripe_service as ss


# --- _extract_period_end（新旧API両対応） ---

class TestExtractPeriodEnd:
    def test_top_level_field(self):
        assert ss._extract_period_end({"current_period_end": 1700000000}) == 1700000000

    def test_items_fallback_new_api(self):
        sub = {"items": {"data": [
            {"current_period_end": 1700000000},
            {"current_period_end": 1700009999},
        ]}}
        assert ss._extract_period_end(sub) == 1700009999   # 最大を採用

    def test_none_when_absent(self):
        assert ss._extract_period_end({}) is None
        assert ss._extract_period_end({"items": {"data": []}}) is None


# --- _as_dict ---

class TestAsDict:
    def test_dict_passthrough(self):
        d = {"a": 1}
        assert ss._as_dict(d) is d


# --- parse_event の署名検証ガード ---

class TestParseEvent:
    def test_missing_webhook_secret_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "stripe_webhook_secret", None)
        with pytest.raises(RuntimeError, match="WEBHOOK_SECRET_NOT_CONFIGURED"):
            ss.parse_event(b"{}", "sig")


# --- _sync_from_subscription ---

class TestSyncFromSubscription:
    def test_updates_existing_row_by_customer(self, db):
        db.add(Subscription(user_id=1, stripe_customer_id="cus_1", status="none"))
        db.commit()
        ss._sync_from_subscription(db, {
            "id": "sub_1", "customer": "cus_1", "status": "active",
            "current_period_end": 1700000000,
        })
        row = db.query(Subscription).filter_by(user_id=1).one()
        assert row.status == "active"
        assert row.stripe_subscription_id == "sub_1"
        assert row.current_period_end == datetime.utcfromtimestamp(1700000000)

    def test_rescue_by_metadata_user_id(self, db):
        # customer未紐付けでも metadata.user_id で行を作って救済する。
        ss._sync_from_subscription(db, {
            "id": "sub_2", "customer": "cus_unknown", "status": "trialing",
            "current_period_end": 1700000000, "metadata": {"user_id": "5"},
        })
        row = db.query(Subscription).filter_by(user_id=5).one()
        assert row.status == "trialing"
        assert row.stripe_customer_id == "cus_unknown"

    def test_no_match_and_no_metadata_is_noop(self, db):
        ss._sync_from_subscription(db, {
            "id": "sub_3", "customer": "cus_ghost", "status": "active",
        })
        assert db.query(Subscription).count() == 0

    def test_subscribed_transition_logged(self, db, caplog):
        db.add(Subscription(user_id=1, stripe_customer_id="cus_1", status="none"))
        db.commit()
        with caplog.at_level("INFO"):
            ss._sync_from_subscription(db, {
                "id": "sub_1", "customer": "cus_1", "status": "active",
                "current_period_end": 1700000000,
            })
        assert "event=subscribed" in caplog.text

    def test_canceled_transition_logged(self, db, caplog):
        db.add(Subscription(user_id=1, stripe_customer_id="cus_1", status="active"))
        db.commit()
        with caplog.at_level("INFO"):
            ss._sync_from_subscription(db, {
                "id": "sub_1", "customer": "cus_1", "status": "canceled",
            })
        assert "event=canceled" in caplog.text


# --- handle_event のディスパッチ ---

class TestHandleEvent:
    def test_unhandled_type_ignored(self, db):
        ss.handle_event(db, {"type": "ping", "data": {"object": {}}})
        assert db.query(Subscription).count() == 0

    def test_subscription_updated_syncs(self, db):
        db.add(Subscription(user_id=1, stripe_customer_id="cus_1", status="none"))
        db.commit()
        ss.handle_event(db, {
            "type": "customer.subscription.updated",
            "data": {"object": {
                "id": "sub_1", "customer": "cus_1", "status": "active",
                "current_period_end": 1700000000,
            }},
        })
        assert db.query(Subscription).filter_by(user_id=1).one().status == "active"

    def test_payment_failed_is_log_only(self, db, caplog):
        with caplog.at_level("INFO"):
            ss.handle_event(db, {
                "type": "invoice.payment_failed",
                "data": {"object": {"customer": "cus_1"}},
            })
        assert "invoice.payment_failed" in caplog.text
        assert db.query(Subscription).count() == 0
