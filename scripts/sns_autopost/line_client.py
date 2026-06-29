#!/usr/bin/env python3
"""LINE Messaging API クライアント（承認フロー用）。

- push_approval(): 生成した下書きを「本文＋[承認][却下]ボタン」で運用者にpush
- reply(): Webhookの replyToken に対する返信（押下後の結果通知など）
- verify_signature(): Webhook受信時の X-Line-Signature 検証

必要な環境変数（scripts/sns_autopost/.env）:
  LINE_CHANNEL_ACCESS_TOKEN … Messaging APIのチャネルアクセストークン（長期）
  LINE_CHANNEL_SECRET       … 署名検証用のチャネルシークレット
  LINE_OPERATOR_USER_ID     … push先（あなた）のuserId。follow時にWebhookが教える
"""
import base64
import hashlib
import hmac
import os

import requests

_API = "https://api.line.me/v2/bot"
_TIMEOUT = 15


def _token() -> str | None:
    return os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or None


def _secret() -> str:
    return os.getenv("LINE_CHANNEL_SECRET", "")


def enabled() -> bool:
    return bool(_token() and _secret())


def verify_signature(body: bytes, signature: str | None) -> bool:
    """X-Line-Signature を検証。secret未設定や不一致は False。"""
    secret = _secret()
    if not secret or not signature:
        return False
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
    }


def _public_media_url(image_path: str | None) -> str | None:
    """画像をLINEで表示するための公開HTTPS URLを組み立てる。
    SNS_PUBLIC_BASE（例: https://<DOMAIN>）未設定なら None（プレビュー省略）。"""
    base = os.getenv("SNS_PUBLIC_BASE", "").rstrip("/")
    if not base or not image_path:
        return None
    return f"{base}/sns/media/{os.path.basename(image_path)}"


def _approval_messages(draft: dict) -> list[dict]:
    """下書き本文（＋2部構成ならリプ本体）＋ 承認/却下ボタンのメッセージ配列を組み立てる。
    本投稿に添付する解説画像があれば、本文の直後にプレビュー表示する。"""
    text = draft.get("text", "")
    reply = draft.get("reply") or ""
    slot = draft.get("slot", "")
    pillar = draft.get("pillar", "")
    did = draft.get("id", "")
    image_path = draft.get("image_path") or None
    img_url = _public_media_url(image_path)
    header = f"📝 投稿の承認待ち（slot{slot} / {pillar}）\n投稿前に確認してください👇"
    if image_path and not img_url:
        # 画像は付くがプレビューURL未設定。添付される旨だけ伝える。
        header += "\n🖼 解説画像が本投稿に添付されます（SNS_PUBLIC_BASE未設定でプレビュー省略）"
    # 本投稿は1通目。添付画像→（2部構成なら）リプ本体、の順で見せ、ボタンは最後。
    main_msg = {"type": "text", "text": f"{header}\n\n【本投稿】\n{'─' * 12}\n{text}"}
    image_msg = ({"type": "image", "originalContentUrl": img_url,
                  "previewImageUrl": img_url} if img_url else None)
    reply_msg = ({"type": "text", "text": f"【リプ＝大事な中身】\n{'─' * 12}\n{reply}"}
                 if reply else None)
    buttons = {
        "type": "template",
        "altText": "ツイートの承認（承認 / 却下）",
        "template": {
            "type": "confirm",
            "text": "この内容で投稿しますか？",
            "actions": [
                {"type": "postback", "label": "✅ 承認して投稿",
                 "data": f"act=approve&id={did}",
                 "displayText": "✅ 承認して投稿"},
                {"type": "postback", "label": "🗑 却下",
                 "data": f"act=reject&id={did}",
                 "displayText": "🗑 却下"},
            ],
        },
    }
    return [m for m in (main_msg, image_msg, reply_msg, buttons) if m]


def push_approval(draft: dict) -> tuple[bool, str]:
    """承認待ちの下書きを運用者にpush。returns (ok, info)。"""
    if not enabled():
        return False, "LINE_KEYS_MISSING"
    to = os.getenv("LINE_OPERATOR_USER_ID")
    if not to:
        return False, "LINE_OPERATOR_USER_ID_MISSING"
    payload = {"to": to, "messages": _approval_messages(draft)}
    try:
        r = requests.post(f"{_API}/message/push", headers=_headers(),
                          json=payload, timeout=_TIMEOUT)
        if r.status_code == 200:
            return True, "ok"
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"EXC: {e}"


def reply(reply_token: str, text: str) -> tuple[bool, str]:
    """Webhookイベントへの返信（押下結果の通知など）。"""
    if not enabled() or not reply_token:
        return False, "skip"
    payload = {"replyToken": reply_token,
               "messages": [{"type": "text", "text": text}]}
    try:
        r = requests.post(f"{_API}/message/reply", headers=_headers(),
                          json=payload, timeout=_TIMEOUT)
        return (r.status_code == 200), (f"HTTP {r.status_code}" if r.status_code != 200 else "ok")
    except Exception as e:
        return False, f"EXC: {e}"
