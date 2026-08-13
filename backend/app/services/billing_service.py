"""有料プランのプラン判定と利用上限（docs/31 FR-01, docs/33 §2-3）。

billing_enabled=False の間は全関数が「無制限・無料扱いでOK」を返す
（従来挙動のまま。緊急停止スイッチ兼用）。
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.billing import Subscription, UsageCounter
from app.models.user import User

JST = timezone(timedelta(hours=9))

# プレミアム扱いとする Stripe status（docs/33 §2.1）
_ACTIVE_STATUSES = ("active", "trialing")


def current_yyyymm(now: datetime | None = None) -> str:
    """JSTの暦月キー（FR-01: カウントは暦月・JST）。"""
    now = now or datetime.now(JST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(JST).strftime("%Y%m")


def _is_comp_premium(db: Session, user_id: int) -> bool:
    """コンプ枠（docs/101）: allowlist のメールは課金なしで常にプレミアム扱い。"""
    comp_emails = settings.comp_premium_email_set
    if not comp_emails:
        return False
    email = db.query(User.email).filter(User.id == user_id).scalar()
    return bool(email) and email.strip().lower() in comp_emails


def is_premium(db: Session, user_id: int) -> bool:
    if _is_comp_premium(db, user_id):
        return True
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if sub is None or sub.status not in _ACTIVE_STATUSES:
        return False
    if sub.current_period_end is None:
        return False
    return sub.current_period_end > datetime.utcnow()


def get_analysis_used(db: Session, user_id: int) -> int:
    row = (
        db.query(UsageCounter)
        .filter(UsageCounter.user_id == user_id, UsageCounter.yyyymm == current_yyyymm())
        .first()
    )
    return row.analysis_count if row else 0


def analysis_allowed(db: Session, user_id: int) -> bool:
    """解析を開始してよいか。上限到達なら False（呼び出し側で 402 LIMIT_REACHED）。"""
    if not settings.billing_enabled:
        return True
    if is_premium(db, user_id):
        return True
    return get_analysis_used(db, user_id) < settings.free_analysis_limit


def increment_analysis_count(db: Session, user_id: int) -> None:
    """解析完了時のカウントアップ（失敗は数えない）。既加入者は対象外（FR-01）。

    UNIQUE(user_id, yyyymm) 前提の UPSERT。BackgroundTasks からの呼び出しで
    並行実行されうるため、INSERT 競合時は再取得して UPDATE する。
    """
    if not settings.billing_enabled:
        return
    if is_premium(db, user_id):
        return
    yyyymm = current_yyyymm()
    row = (
        db.query(UsageCounter)
        .filter(UsageCounter.user_id == user_id, UsageCounter.yyyymm == yyyymm)
        .with_for_update()
        .first()
    )
    if row:
        row.analysis_count += 1
        db.add(row)
    else:
        try:
            db.add(UsageCounter(user_id=user_id, yyyymm=yyyymm, analysis_count=1))
            db.flush()
        except Exception:
            db.rollback()
            row = (
                db.query(UsageCounter)
                .filter(UsageCounter.user_id == user_id, UsageCounter.yyyymm == yyyymm)
                .with_for_update()
                .first()
            )
            if row:
                row.analysis_count += 1
                db.add(row)
    db.commit()


def billing_me(db: Session, user_id: int) -> dict:
    """S-01バッジ / S-05プラン管理用のサマリ（GET /billing/me）。"""
    premium = settings.billing_enabled and is_premium(db, user_id)
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    return {
        "billing_enabled": settings.billing_enabled,
        "plan": "premium" if premium else "free",
        "period_end": sub.current_period_end if (sub and premium) else None,
        "analysis_used": get_analysis_used(db, user_id),
        "analysis_limit": None if premium or not settings.billing_enabled else settings.free_analysis_limit,
    }
