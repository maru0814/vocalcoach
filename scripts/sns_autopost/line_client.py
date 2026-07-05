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


def _image_message(draft: dict) -> dict | None:
    """生成画像を公開URLで指すLINE imageメッセージ。SNS_PUBLIC_BASE_URL未設定なら None。
    （LINEはバイト添付不可＝公開HTTPS URLが必須。webhookの /sns/img/{name} が配信する）"""
    image = draft.get("image")
    base = (os.getenv("SNS_PUBLIC_BASE_URL") or "").rstrip("/")
    if not image or not base:
        return None
    url = f"{base}/sns/img/{os.path.basename(image)}"
    return {"type": "image", "originalContentUrl": url, "previewImageUrl": url}


def _approval_messages(draft: dict) -> list[dict]:
    """下書き本文（＋2部構成ならリプ本体）＋ 承認/却下ボタンのメッセージ配列を組み立てる。
    公開URLが設定済みなら、先頭に投稿画像のプレビューも付ける。"""
    text = draft.get("text", "")
    reply = draft.get("reply") or ""
    slot = draft.get("slot", "")
    pillar = draft.get("pillar", "")
    did = draft.get("id", "")
    image_msg = _image_message(draft)
    # 画像URLを出せない時だけテキストで添付を明記（出せる時は実物を見せるので不要）
    img_note = "（🖼 ブランド画像を添付）" if (draft.get("image") and not image_msg) else ""
    header = (f"📝 投稿の承認待ち（slot{slot} / {pillar}）{img_note}\n"
              "投稿前に確認してください👇")
    # 専門家ゲートの判定を先頭に表示（この承認は専門家チェックを通過したものだけ届く）。
    expert = (draft.get("expert_note") or "").strip()
    if expert:
        header = f"{expert}\n\n{header}"
    # 本投稿は1通目。2部構成ならリプ本体を2通目に分けて見せ、ボタンは最後。
    main_msg = {"type": "text", "text": f"{header}\n\n【本投稿】\n{'─' * 12}\n{text}"}
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
    # 画像→本投稿→(リプ本体)→ボタン の順。LINEは1pushで最大5メッセージ。
    return [m for m in (image_msg, main_msg, reply_msg, buttons) if m]


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


def push_lead_approval(rec: dict) -> tuple[bool, str]:
    """リード承認カードを運用者にpush（docs/58 FR-05）。
    ①相手ツイート ②プロフ要約 ③提案返信 ④専門家判定 ＋ [✅返信する][⏭スキップ]。
    承認しても X には投稿されない（実行は運用者の手動）。"""
    if not enabled():
        return False, "LINE_KEYS_MISSING"
    to = os.getenv("LINE_OPERATOR_USER_ID")
    if not to:
        return False, "LINE_OPERATOR_USER_ID_MISSING"
    lead = rec.get("lead") or {}
    did = rec.get("id", "")
    followers = lead.get("followers")
    prof = f"@{(lead.get('handle') or '?').lstrip('@')}"
    prof += f"（フォロワー {followers:,}人）" if isinstance(followers, int) else "（フォロワー数 不明）"
    expert = (rec.get("expert_note") or "").strip()
    body = (
        (f"{expert}\n\n" if expert else "")
        + f"🎯 リード候補（{lead.get('query_id', '?')} / {lead.get('source', '?')}）\n"
        + f"{prof}\n\n【相手のツイート】\n{'─' * 12}\n{lead.get('source_text', '')}\n\n"
        + f"【提案する返信】\n{'─' * 12}\n{lead.get('reply_text', '')}"
    )
    buttons = {
        "type": "template",
        "altText": "リード返信の確認（返信する / スキップ）",
        "template": {
            "type": "confirm",
            "text": "この人に返信しますか？（実行はあなたの手で）",
            "actions": [
                {"type": "postback", "label": "✅ 返信する",
                 "data": f"act=lead_approve&id={did}", "displayText": "✅ 返信する"},
                {"type": "postback", "label": "⏭ スキップ",
                 "data": f"act=lead_skip&id={did}", "displayText": "⏭ スキップ"},
            ],
        },
    }
    payload = {"to": to, "messages": [{"type": "text", "text": body}, buttons]}
    try:
        r = requests.post(f"{_API}/message/push", headers=_headers(),
                          json=payload, timeout=_TIMEOUT)
        if r.status_code == 200:
            return True, "ok"
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"EXC: {e}"


def push_text(text: str) -> tuple[bool, str]:
    """運用者への単発テキストpush（「本日は該当リードなし」等の通知用）。"""
    if not enabled():
        return False, "LINE_KEYS_MISSING"
    to = os.getenv("LINE_OPERATOR_USER_ID")
    if not to:
        return False, "LINE_OPERATOR_USER_ID_MISSING"
    payload = {"to": to, "messages": [{"type": "text", "text": text}]}
    try:
        r = requests.post(f"{_API}/message/push", headers=_headers(),
                          json=payload, timeout=_TIMEOUT)
        return (r.status_code == 200), (f"HTTP {r.status_code}" if r.status_code != 200 else "ok")
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
