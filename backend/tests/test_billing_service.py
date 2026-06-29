"""課金ロジック（app/services/billing_service.py）のユニットテスト。

インメモリSQLite（conftest の db フィクスチャ）を使い、外部サービス不要。
無料枠ゲート・プレミアム判定・暦月カウンタの境界を検証する。docs/31 FR-01 / docs/33。
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.models.billing import Subscription, UsageCounter
from app.services import billing_service as bs


@pytest.fixture(autouse=True)
def _enable_billing(monkeypatch):
    # 既定は billing_enabled=False（全ゲート無効）。多くのテストは有効前提なのでONにする。
    monkeypatch.setattr(settings, "billing_enabled", True)
    monkeypatch.setattr(settings, "free_analysis_limit", 10)


def _add_sub(db, user_id=1, status="active", days=30):
    end = datetime.utcnow() + timedelta(days=days) if days is not None else None
    db.add(Subscription(user_id=user_id, status=status, current_period_end=end))
    db.commit()


# --- current_yyyymm（JST暦月） ---

class TestCurrentYyyymm:
    def test_naive_treated_as_utc_then_jst(self):
        # UTC 2026-01-31 16:00 は JST だと 2026-02-01 01:00 → "202602"。
        dt = datetime(2026, 1, 31, 16, 0, 0)
        assert bs.current_yyyymm(dt) == "202602"

    def test_aware_utc_converted_to_jst(self):
        dt = datetime(2026, 1, 31, 16, 0, 0, tzinfo=timezone.utc)
        assert bs.current_yyyymm(dt) == "202602"

    def test_within_same_jst_month(self):
        dt = datetime(2026, 6, 15, 0, 0, 0, tzinfo=timezone.utc)
        assert bs.current_yyyymm(dt) == "202606"


# --- is_premium ---

class TestIsPremium:
    def test_no_subscription(self, db):
        assert bs.is_premium(db, 1) is False

    def test_active_with_future_period_end(self, db):
        _add_sub(db, status="active", days=10)
        assert bs.is_premium(db, 1) is True

    def test_trialing_counts_as_premium(self, db):
        _add_sub(db, status="trialing", days=10)
        assert bs.is_premium(db, 1) is True

    def test_inactive_status(self, db):
        _add_sub(db, status="canceled", days=10)
        assert bs.is_premium(db, 1) is False

    def test_expired_period_end(self, db):
        _add_sub(db, status="active", days=-1)
        assert bs.is_premium(db, 1) is False

    def test_null_period_end(self, db):
        _add_sub(db, status="active", days=None)
        assert bs.is_premium(db, 1) is False


# --- analysis_allowed / 無料枠の境界 ---

class TestAnalysisAllowed:
    def test_billing_disabled_always_allowed(self, db, monkeypatch):
        monkeypatch.setattr(settings, "billing_enabled", False)
        # カウンタが上限超でも、ゲート無効なら許可。
        db.add(UsageCounter(user_id=1, yyyymm=bs.current_yyyymm(), analysis_count=999))
        db.commit()
        assert bs.analysis_allowed(db, 1) is True

    def test_premium_always_allowed(self, db):
        _add_sub(db, status="active", days=10)
        db.add(UsageCounter(user_id=1, yyyymm=bs.current_yyyymm(), analysis_count=999))
        db.commit()
        assert bs.analysis_allowed(db, 1) is True

    def test_free_under_limit_allowed(self, db):
        db.add(UsageCounter(user_id=1, yyyymm=bs.current_yyyymm(), analysis_count=9))
        db.commit()
        assert bs.analysis_allowed(db, 1) is True

    def test_free_at_limit_blocked(self, db):
        db.add(UsageCounter(user_id=1, yyyymm=bs.current_yyyymm(), analysis_count=10))
        db.commit()
        assert bs.analysis_allowed(db, 1) is False

    def test_free_no_counter_allowed(self, db):
        assert bs.analysis_allowed(db, 1) is True


# --- increment_analysis_count ---

class TestIncrement:
    def test_creates_counter(self, db):
        bs.increment_analysis_count(db, 1)
        assert bs.get_analysis_used(db, 1) == 1

    def test_increments_existing(self, db):
        bs.increment_analysis_count(db, 1)
        bs.increment_analysis_count(db, 1)
        assert bs.get_analysis_used(db, 1) == 2

    def test_billing_disabled_no_op(self, db, monkeypatch):
        monkeypatch.setattr(settings, "billing_enabled", False)
        bs.increment_analysis_count(db, 1)
        assert bs.get_analysis_used(db, 1) == 0

    def test_premium_not_counted(self, db):
        _add_sub(db, status="active", days=10)
        bs.increment_analysis_count(db, 1)
        assert bs.get_analysis_used(db, 1) == 0


# --- billing_me サマリ ---

class TestBillingMe:
    def test_free_user_summary(self, db):
        out = bs.billing_me(db, 1)
        assert out["plan"] == "free"
        assert out["billing_enabled"] is True
        assert out["analysis_limit"] == 10
        assert out["period_end"] is None

    def test_premium_user_summary(self, db):
        _add_sub(db, status="active", days=10)
        out = bs.billing_me(db, 1)
        assert out["plan"] == "premium"
        assert out["analysis_limit"] is None       # 無制限
        assert out["period_end"] is not None

    def test_billing_disabled_summary(self, db, monkeypatch):
        monkeypatch.setattr(settings, "billing_enabled", False)
        out = bs.billing_me(db, 1)
        assert out["plan"] == "free"
        assert out["analysis_limit"] is None
