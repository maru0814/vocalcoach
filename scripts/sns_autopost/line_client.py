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


def _candidate_line(i: int, c: dict) -> str:
    followers = c.get("followers")
    fol = f"{followers:,}人" if isinstance(followers, int) else "不明"
    reason = c.get("reason", "")
    excerpt = (c.get("source_text") or "").replace("\n", " ").strip()
    if len(excerpt) > 50:
        excerpt = excerpt[:50] + "…"
    base = (f"{i}. @{c.get('handle', '?')}（フォロワー{fol} / {reason}）\n"
            f"   「{excerpt}」\n"
            f"   {c.get('url', '')}")
    # 返信下書き（docs/58 FR-03改）。長押しコピー→リンク先で貼って送る（送信は人間）。
    draft = (c.get("reply_draft") or "").strip()
    if draft:
        base += f"\n   ✍️ 返信下書き（このままコピペOK・編集歓迎）:\n   {draft}"
    return base


_CHUNK_SIZE = 8       # 1メッセージに乗せる候補数（5000字上限に対する安全マージン）
_MAX_LIST_MSGS = 4    # LINEの1push=最大5メッセージのうち、ボタン用に1枠残す


def push_lead_digest(candidates: list[dict], batch_id: str) -> tuple[bool, str]:
    """フォロー候補の一覧をpushする（docs/58 FR-05改）。

    上位候補には返信下書きが付く（docs/58 FR-03改・2026-07-17再転換）が、
    フォロー・返信の実行は常にXアプリで運用者の指で行う前提。
    末尾の[✅全員フォローした]は「実行した」という自己申告の記録ボタン
    （X APIは一切呼ばない。webhook._handle_lead_batch 参照）。
    候補が多い日でも1push=5メッセージ上限に収まるようチャンク分割する。"""
    if not enabled():
        return False, "LINE_KEYS_MISSING"
    to = os.getenv("LINE_OPERATOR_USER_ID")
    if not to:
        return False, "LINE_OPERATOR_USER_ID_MISSING"
    lines = [_candidate_line(i, c) for i, c in enumerate(candidates, 1)]
    chunks = [lines[i:i + _CHUNK_SIZE] for i in range(0, len(lines), _CHUNK_SIZE)][:_MAX_LIST_MSGS]
    has_draft = any((c.get("reply_draft") or "").strip() for c in candidates)
    draft_note = ("✍️付きの人は下書きを長押しコピー→そのまま返信できます。\n"
                  if has_draft else "")
    header = (f"🎯 今日のフォロー候補（{len(candidates)}人）\n"
              "気になる人のリンクをタップ→Xアプリでご自身の指でフォロー/返信してください。\n"
              + draft_note + ("─" * 16))
    messages = [{"type": "text", "text": header + "\n\n" + "\n\n".join(chunks[0])}]
    for chunk in chunks[1:]:
        messages.append({"type": "text", "text": "\n\n".join(chunk)})
    messages.append({
        "type": "template",
        "altText": "今日のフォロー候補（フォローした / 見送る）",
        "template": {
            "type": "confirm",
            "text": "今日の候補、フォローしましたか？（実行はあなたの手で）",
            "actions": [
                {"type": "postback", "label": "✅ 全員フォローした",
                 "data": f"act=lead_followed_batch&batch={batch_id}",
                 "displayText": "✅ 全員フォローした"},
                {"type": "postback", "label": "⏭ 今回は見送る",
                 "data": f"act=lead_skip_batch&batch={batch_id}",
                 "displayText": "⏭ 今回は見送る"},
            ],
        },
    })
    payload = {"to": to, "messages": messages}
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
