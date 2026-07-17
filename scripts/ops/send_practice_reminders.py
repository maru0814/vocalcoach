#!/usr/bin/env python3
"""練習リマインドのWeb Push配信（1日1バッチ）。docs/73 FR-05 / docs/75 §2-2, §5。

対象: 通知ON(enabled=true)の購読を持ち、最後の録音から reminder_idle_days 日以上
      練習がない（または録音ゼロの）ユーザー。1ユーザーにつき最大1通。
失効(404/410)の購読はその場で削除してクリーンアップする。

実行（backendコンテナ内。`from app ...` が解決できる環境で動かす）:
    python3 scripts/ops/send_practice_reminders.py
    DRY_RUN=1 python3 scripts/ops/send_practice_reminders.py   # 送信せず対象だけ表示

cron 登録は SRE 側（既存 sns_autopost / daily_metrics と同じ VPS cron 方式）。docs/75 §11。
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# backend/ を import パスに追加（コンテナ外/リポジトリ直下実行でも動くように）。
# すでに `from app` が通る環境（backendコンテナ）ではこの追加は無害。
_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if _BACKEND.is_dir() and str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.push import PushSubscription  # noqa: E402
from app.models.recording import Recording  # noqa: E402
from app.services import push_sender  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reminders")

DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"

# 通知文（MVP・ソラ先生監修は docs/73 Q-04）。docs/74 SCR-05。
TITLE = "そろそろ声、出してみよ🎤"
BODY = "しばらく練習してないみたい。3分でいいから、今日の声を録ってみない？"
CLICK_URL = "/coach"


def _eligible_user_ids(db) -> list[int]:
    """通知ONの購読者のうち、idle日数以上録音していないユーザーIDを返す。"""
    cutoff = datetime.utcnow() - timedelta(days=settings.reminder_idle_days)

    # 通知ONの購読を持つユーザー
    subscriber_ids = {
        uid
        for (uid,) in db.query(PushSubscription.user_id)
        .filter(PushSubscription.enabled.is_(True))
        .distinct()
        .all()
    }
    if not subscriber_ids:
        return []

    # 直近 cutoff 以降に録音があるユーザー（＝アクティブなので送らない）
    active_ids = {
        uid
        for (uid,) in db.query(Recording.user_id)
        .filter(Recording.user_id.in_(subscriber_ids), Recording.created_at >= cutoff)
        .distinct()
        .all()
    }
    return sorted(subscriber_ids - active_ids)


def main() -> int:
    if not settings.push_enabled and not DRY_RUN:
        logger.warning("VAPID鍵が未設定のため配信をスキップします（DRY_RUN=1で対象だけ確認可）")
        return 0

    db = SessionLocal()
    try:
        target_ids = _eligible_user_ids(db)
        logger.info("リマインド対象ユーザー: %d 人 (idle>=%d日)", len(target_ids), settings.reminder_idle_days)

        sent = 0
        expired = 0
        failed = 0
        for uid in target_ids:
            # ユーザーの有効な購読すべてに送る（複数端末対応）。1ユーザー1バッチ1回。
            subs = (
                db.query(PushSubscription)
                .filter(PushSubscription.user_id == uid, PushSubscription.enabled.is_(True))
                .all()
            )
            delivered_to_user = False
            for sub in subs:
                if DRY_RUN:
                    logger.info("[DRY_RUN] would send to user=%s endpoint=%s", uid, sub.endpoint[:40])
                    delivered_to_user = True
                    continue
                try:
                    push_sender.send_web_push(
                        push_sender.Subscription(sub.endpoint, sub.p256dh, sub.auth),
                        TITLE, BODY, CLICK_URL,
                    )
                    delivered_to_user = True
                except push_sender.PushExpired:
                    db.delete(sub)
                    expired += 1
                except push_sender.PushSendError as e:
                    logger.warning("送信失敗 user=%s: %s", uid, e)
                    failed += 1
            if delivered_to_user:
                sent += 1

        if not DRY_RUN:
            db.commit()
        logger.info("完了: 送信=%d人 失効削除=%d件 失敗=%d件 (DRY_RUN=%s)", sent, expired, failed, DRY_RUN)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
