#!/usr/bin/env python3
"""リリース告知メルマガの一斉送信バッチ（docs/88 FR-05 / docs/89 §5）。

対象: newsletter_opt_in=true の実会員（@example.com 除外）のうち、
      この campaign_key でまだ送っていない人。1実行の送信上限 250 通
      （Brevo無料枠300/日の安全マージン）。台帳（newsletter_sends）は
      成功時のみ記録＝失敗・上限打ち切り分は再実行で続きから送れる（冪等）。

実行（backendコンテナ内。VPSなら:
  cd /opt/vocalcoach/docker && docker compose -f docker-compose.prod.yml --env-file .env \
    exec -T backend python3 scripts/ops/send_newsletter.py \
    --campaign-key release-2026-08-xxx --subject "件名" --body-file /tmp/body.txt ）

    DRY_RUN=1 … 送信せず対象者数と本文プレビューだけ表示（AC-07）
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# backend/ を import パスに追加（send_practice_reminders.py と同じ方式）
_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if _BACKEND.is_dir() and str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.newsletter import NewsletterSend  # noqa: E402
from app.models.user import User  # noqa: E402
from app.security.tokens_util import new_unsubscribe_token  # noqa: E402
from app.services import mail_service  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("newsletter")

DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"
BATCH_LIMIT = 250  # Brevo無料枠300/日の安全マージン（docs/88 FR-05）


def main() -> int:
    ap = argparse.ArgumentParser(description="お知らせメール一斉送信（docs/88/89）")
    ap.add_argument("--campaign-key", required=True, help="冪等性キー（例: release-2026-08-xxx）")
    ap.add_argument("--subject", required=True, help="件名")
    ap.add_argument("--body-file", required=True, help="本文テキストファイル（フッターは自動付加）")
    args = ap.parse_args()

    body = Path(args.body_file).read_text(encoding="utf-8")

    if not mail_service.mail_enabled() and not DRY_RUN:
        # AC-09: 未設定環境では何もせず正常終了（誤爆防止）
        logger.info("mail未設定のため送信せず終了（MAIL_API_KEY/MAIL_FROM_ADDRESS を確認）")
        return 0

    db = SessionLocal()
    try:
        sent_ids = {
            r[0]
            for r in db.query(NewsletterSend.user_id).filter(
                NewsletterSend.campaign_key == args.campaign_key
            )
        }
        targets = [
            u
            for u in db.query(User)
            .filter(User.newsletter_opt_in.is_(True), ~User.email.like("%@example.com"))
            .order_by(User.id)
            if u.id not in sent_ids
        ]
        capped = targets[:BATCH_LIMIT]
        logger.info(
            "campaign=%s 対象 %d人（送信済み %d人を除外、上限%dで今回 %d人）",
            args.campaign_key, len(targets), len(sent_ids), BATCH_LIMIT, len(capped),
        )

        if DRY_RUN:
            sample_url = f"{settings.frontend_base_url.rstrip('/')}/api/v1/mail/unsubscribe?token=<個人別>"
            print("---- 本文プレビュー ----")
            print(mail_service.build_newsletter_text(body, sample_url))
            print(f"[dry-run] 対象 {len(capped)}人。送信は行いません")
            return 0

        ok = ng = 0
        for u in capped:
            if not u.unsubscribe_token:  # 旧データ救済（設定画面以外でopt_inになった場合）
                u.unsubscribe_token = new_unsubscribe_token()
                db.commit()
            unsubscribe_url = (
                f"{settings.frontend_base_url.rstrip('/')}/api/v1/mail/unsubscribe"
                f"?token={u.unsubscribe_token}"
            )
            text = mail_service.build_newsletter_text(body, unsubscribe_url)
            if mail_service.send_mail(u.id, u.email, args.subject, text):
                db.add(NewsletterSend(user_id=u.id, campaign_key=args.campaign_key))
                db.commit()  # 1通ごとに確定（途中クラッシュでも台帳は正確）
                ok += 1
            else:
                ng += 1
        remaining = len(targets) - len(capped)
        logger.info(
            "完了: 成功 %d / 失敗 %d / 上限持ち越し %d（失敗・持ち越しは再実行で続きから）",
            ok, ng, remaining,
        )
        return 0 if ng == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
