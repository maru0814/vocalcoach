"""ウェルカムメール送信の単一責務ラッパ（Brevo REST API）。docs/85 §5。

- APIキー等は環境変数（settings）から。未設定なら送信スキップ＝現行動作（FR-03）。
- 例外はこのモジュール内で必ず握りつぶす。登録処理へは絶対に伝播させない（FR-02）。
- 文面の正本は docs/86_メール文面_ウェルカム便.md。変更時は86番→ここの順で両方更新。
"""
from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger("app.mail")

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"

WELCOME_SUBJECT = "ご登録ありがとうございます。最初の1曲、聴かせてください"

WELCOME_BODY = """こんにちは、AIボーカルトレーナーのソラです。
ご登録ありがとうございます🎵

わたしにできるのは、あなたの歌の録音を聴いて、
「今どこまでできていて、次に何を練習すればいいか」を
具体的にお返しすることです。

スマホの録音そのままで大丈夫です。
30秒のワンフレーズでも、最初の1曲として十分ですよ。

▼ 録音を聴かせてください
{cta_url}

それでは、お待ちしていますね。

--
ソラ先生（Vocal Coach）
お問い合わせ: {contact_email}
このメールはご登録手続きの完了をお知らせする通知です。
"""


def mail_enabled() -> bool:
    """APIキーと送信者アドレスが揃っていて送信可能か。"""
    return settings.mail_enabled


def build_welcome_email() -> tuple[str, str]:
    """（件名, 本文）を返す。CTAは frontend_base_url に追随（AC-06）。"""
    cta_url = settings.frontend_base_url.rstrip("/") + "/coach"
    body = WELCOME_BODY.format(cta_url=cta_url, contact_email=settings.mail_from_address)
    return WELCOME_SUBJECT, body


def send_welcome_email(user_id: int, to_email: str) -> None:
    """登録直後のウェルカムメールを1通送る。例外は外に漏らさない（FR-02）。

    BackgroundTasks から呼ばれる前提。戻り値なし、raise なし。
    結果は必ずログに残す（FR-05: sent / skip / failed）。
    """
    if not mail_enabled():
        logger.info("welcome mail skip（未設定） user_id=%s", user_id)
        return

    try:
        import requests

        subject, body = build_welcome_email()
        resp = requests.post(
            BREVO_SEND_URL,
            headers={"api-key": settings.mail_api_key, "content-type": "application/json"},
            json={
                "sender": {"name": settings.mail_from_name, "email": settings.mail_from_address},
                "to": [{"email": to_email}],
                "subject": subject,
                "textContent": body,
            },
            timeout=settings.mail_timeout_sec,
        )
        if 200 <= resp.status_code < 300:
            logger.info("welcome mail sent user_id=%s", user_id)
        else:
            # 4xx（キー無効・無料枠超過等）もリトライしない（docs/85 §7）
            logger.warning(
                "welcome mail failed user_id=%s status=%s", user_id, resp.status_code
            )
    except Exception as e:  # noqa: BLE001 — 登録を守るため全例外を隔離（FR-02）
        logger.warning("welcome mail failed user_id=%s error=%s", user_id, type(e).__name__)
