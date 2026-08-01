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

わたしは、あなたの歌の録音から「直す場所」と「直し方」を
具体的にお返しするAIボーカルトレーナーです。

使い方は3ステップです。
1. スマホでワンフレーズ録音する（30秒でOK）
2. チャットにアップロードする
3. その場でフィードバックが届く

▼ 無料で歌を見てもらう
{cta_url}

それでは、お待ちしていますね。

--
ソラ先生（Vocal Coach）
お問い合わせ: {contact_email}
このメールはご登録手続きの完了をお知らせする通知です。
"""


# HTML版（docs/86 §HTML版デザイン仕様）。テーブルレイアウト＋全インラインCSS＋https絶対URL画像
# （Gmailは<style>ブロック・data URIが不安定/不可）。テキスト版とのマルチパートで送る。
WELCOME_HTML = """\
<!DOCTYPE html>
<html lang="ja">
<body style="margin:0;padding:0;background-color:#f4f5f7;">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;">\
登録ありがとうございます。録音1本で、次に練習することが分かります。</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f5f7;">
<tr><td align="center" style="padding:32px 16px;">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" \
style="max-width:600px;width:100%;background-color:#ffffff;border-radius:12px;overflow:hidden;">
    <tr><td align="center" style="background-color:#171045;padding:28px 24px 24px;">
      <img src="{logo_url}" width="64" height="64" alt="ソラ先生" \
style="display:block;border-radius:50%;margin:0 auto 10px;">
      <div style="font-family:-apple-system,BlinkMacSystemFont,'Hiragino Sans',Meiryo,sans-serif;\
font-size:16px;font-weight:bold;color:#ffffff;">AIボーカルトレーナー ソラ先生</div>
      <div style="font-family:-apple-system,BlinkMacSystemFont,'Hiragino Sans',Meiryo,sans-serif;\
font-size:12px;color:#c7d2fe;margin-top:4px;">歌をAIが解析・添削</div>
    </td></tr>
    <tr><td style="padding:32px 32px 8px;font-family:-apple-system,BlinkMacSystemFont,\
'Hiragino Sans',Meiryo,sans-serif;font-size:15px;line-height:1.9;color:#1f2937;">
      <p style="margin:0 0 16px;">こんにちは、AIボーカルトレーナーのソラです。<br>ご登録ありがとうございます🎵</p>
      <p style="margin:0 0 16px;">わたしは、あなたの歌の録音から「直す場所」と「直し方」を具体的にお返しするAIボーカルトレーナーです。</p>
      <p style="margin:0 0 8px;font-weight:bold;">使い方は3ステップです。</p>
      <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 16px;">
        <tr><td style="font-family:-apple-system,BlinkMacSystemFont,'Hiragino Sans',Meiryo,\
sans-serif;font-size:15px;line-height:2.1;color:#1f2937;">
          <span style="color:#0891b2;font-weight:bold;">1.</span> スマホでワンフレーズ録音する（30秒でOK）<br>
          <span style="color:#0891b2;font-weight:bold;">2.</span> チャットにアップロードする<br>
          <span style="color:#0891b2;font-weight:bold;">3.</span> その場でフィードバックが届く
        </td></tr>
      </table>
    </td></tr>
    <tr><td align="center" style="padding:8px 32px 24px;">
      <table role="presentation" cellpadding="0" cellspacing="0">
        <tr><td align="center" style="background-color:#22d3ee;border-radius:8px;">
          <a href="{cta_url}" style="display:inline-block;padding:14px 36px;\
font-family:-apple-system,BlinkMacSystemFont,'Hiragino Sans',Meiryo,sans-serif;\
font-size:15px;font-weight:bold;color:#0f0a2e;text-decoration:none;">無料で歌を見てもらう</a>
        </td></tr>
      </table>
    </td></tr>
    <tr><td style="padding:0 32px 28px;font-family:-apple-system,BlinkMacSystemFont,\
'Hiragino Sans',Meiryo,sans-serif;font-size:15px;line-height:1.9;color:#1f2937;">
      <p style="margin:0;">それでは、お待ちしていますね。</p>
    </td></tr>
    <tr><td style="padding:20px 32px 28px;border-top:1px solid #e5e7eb;\
font-family:-apple-system,BlinkMacSystemFont,'Hiragino Sans',Meiryo,sans-serif;\
font-size:12px;line-height:1.8;color:#6b7280;">
      ソラ先生（Vocal Coach）<br>
      お問い合わせ: {contact_email}<br>
      録音ページ: <a href="{cta_url}" style="color:#6b7280;">{cta_url}</a><br>
      このメールはご登録手続きの完了をお知らせする通知です。
    </td></tr>
  </table>
</td></tr>
</table>
</body>
</html>
"""


def mail_enabled() -> bool:
    """APIキーと送信者アドレスが揃っていて送信可能か。"""
    return settings.mail_enabled


def build_welcome_email() -> tuple[str, str, str]:
    """（件名, テキスト本文, HTML本文）を返す。CTAは frontend_base_url に追随（AC-06）。

    src=welcome_mail はメール経由の流入計測用（daily_metrics_line.py がCaddyログで突合）。
    """
    base = settings.frontend_base_url.rstrip("/")
    cta_url = base + "/coach?src=welcome_mail"
    logo_url = base + "/icons/icon-192.png"
    body = WELCOME_BODY.format(cta_url=cta_url, contact_email=settings.mail_from_address)
    html = WELCOME_HTML.format(
        cta_url=cta_url, logo_url=logo_url, contact_email=settings.mail_from_address
    )
    return WELCOME_SUBJECT, body, html


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

        subject, body, html = build_welcome_email()
        resp = requests.post(
            BREVO_SEND_URL,
            headers={"api-key": settings.mail_api_key, "content-type": "application/json"},
            json={
                "sender": {"name": settings.mail_from_name, "email": settings.mail_from_address},
                "to": [{"email": to_email}],
                "subject": subject,
                "textContent": body,
                "htmlContent": html,
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
