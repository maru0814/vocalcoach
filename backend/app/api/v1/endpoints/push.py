"""Web Push 購読の登録/解除（練習リマインド通知）。docs/75 §3。

配信は本APIでは行わず、cron の scripts/ops/send_practice_reminders.py が行う。
ここは購読情報の保存/削除だけを担う。認証は既存JWT（ログインユーザー単位）。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user
from app.models.push import PushSubscription
from app.models.user import User
from app.schemas.push import SubscribeIn, UnsubscribeIn

router = APIRouter(prefix="/api/v1/push", tags=["push"])


@router.post("/subscribe")
def subscribe(
    payload: SubscribeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """購読を登録（endpoint一意でupsert＝冪等）。docs/73 FR-04。"""
    if not payload.keys.p256dh or not payload.keys.auth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "購読キーが不足しています"},
        )

    existing = (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint == payload.endpoint)
        .first()
    )
    if existing is not None:
        # 同じブラウザの再購読。所有者・キー・有効状態を最新へ更新する。
        existing.user_id = user.id
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
        existing.enabled = True
    else:
        db.add(
            PushSubscription(
                user_id=user.id,
                endpoint=payload.endpoint,
                p256dh=payload.keys.p256dh,
                auth=payload.keys.auth,
                enabled=True,
            )
        )
    db.commit()
    return {"status": "subscribed"}


@router.post("/unsubscribe")
def unsubscribe(
    payload: UnsubscribeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """購読を解除（該当なしでも200＝冪等）。自分の購読 or endpoint一致のみ削除。docs/75 §9。"""
    sub = (
        db.query(PushSubscription)
        .filter(
            PushSubscription.endpoint == payload.endpoint,
            PushSubscription.user_id == user.id,
        )
        .first()
    )
    if sub is not None:
        db.delete(sub)
        db.commit()
    return {"status": "unsubscribed"}
