"""Web Push 送信の単一責務ラッパ（pywebpush + VAPID）。docs/75 §2-2 / §5。

- VAPID鍵は環境変数（settings）から。秘密鍵はサーバー専用。
- 失効(404/410)は PushExpired として呼び出し側へ通知し、購読をクリーンアップさせる。
- pywebpush 未導入・VAPID未設定でも import は壊さない（配信スクリプトが起動時に判定）。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger("app.push")


class PushExpired(Exception):
    """endpoint が失効（404/410）。購読を削除/無効化すべき。"""


class PushSendError(Exception):
    """一時的な送信失敗。次バッチで再試行してよい。"""


@dataclass
class Subscription:
    endpoint: str
    p256dh: str
    auth: str


def push_enabled() -> bool:
    """VAPID鍵が揃っていて送信可能か。"""
    return bool(
        settings.vapid_private_key
        and settings.vapid_public_key
        and settings.vapid_subject
    )


def _subscription_info(sub: Subscription) -> dict:
    return {
        "endpoint": sub.endpoint,
        "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
    }


def send_web_push(sub: Subscription, title: str, body: str, url: str) -> None:
    """1件の購読へ通知を送る。失効時は PushExpired を送出。"""
    if not push_enabled():
        raise PushSendError("VAPID鍵が未設定です")

    try:
        from pywebpush import WebPushException, webpush
    except ImportError as e:  # pragma: no cover - 本番では requirements で導入済み
        raise PushSendError(f"pywebpush 未導入: {e}") from e

    payload = json.dumps({"title": title, "body": body, "url": url})
    try:
        webpush(
            subscription_info=_subscription_info(sub),
            data=payload,
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
            timeout=10,
        )
    except WebPushException as e:
        status_code = getattr(getattr(e, "response", None), "status_code", None)
        if status_code in (404, 410):
            raise PushExpired(sub.endpoint) from e
        logger.warning("push送信失敗 endpoint=%s status=%s", sub.endpoint[:40], status_code)
        raise PushSendError(str(e)) from e
