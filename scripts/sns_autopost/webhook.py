#!/usr/bin/env python3
"""LINE Webhook 常駐サーバ（ツイート承認フロー）。

LINEで [✅承認して投稿] / [🗑却下] のボタンが押されると、その postback が
ここに届く。署名を検証し、承認なら X に投稿（予算ガードを通す）、却下なら破棄。
結果は同じトークでLINEに返信する。

起動:
  uvicorn webhook:app --host 0.0.0.0 --port 8088
公開:
  Caddy で  https://<DOMAIN>/sns/line/webhook  → このサーバ:8088 へ。
  そのURLを LINE Developers の Webhook URL に設定する。

環境変数: line_client.py / generate_and_post.py と同じ .env を読む。
"""
import os
import sys
from urllib.parse import parse_qs

from fastapi import FastAPI, Header, Request, Response
from fastapi.responses import FileResponse

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

import approval_queue as q
import line_client
from generate_and_post import IMG_DIR, _budget_check, _log_post, post_to_x

app = FastAPI(title="sns-approval-webhook")


@app.get("/sns/healthz")
def healthz() -> dict:
    return {"status": "ok", "line": line_client.enabled()}


@app.get("/sns/img/{name}")
def serve_image(name: str) -> Response:
    """承認プレビュー用に生成画像(PNG)を配信する。LINEのimageメッセージは公開URLが要るため。
    path traversal防止: basenameのみ・.png限定・IMG_DIR内の実在ファイルのみ。"""
    safe = os.path.basename(name)
    if safe != name or not safe.lower().endswith(".png"):
        return Response(status_code=404, content="not found")
    path = os.path.join(IMG_DIR, safe)
    if not os.path.isfile(path):
        return Response(status_code=404, content="not found")
    return FileResponse(path, media_type="image/png",
                        headers={"Cache-Control": "public, max-age=86400"})


def _handle_lead_postback(act: str, draft: dict, reply_token: str) -> None:
    """リード承認/スキップの処理（docs/55 FR-05）。

    バン安全性の不変条件: ここでは X の書込みAPI（返信/フォロー）を一切呼ばない。
    承認＝engaged_log への記録＋返信文の再表示のみ。実行は運用者がXアプリで手動。"""
    lead = draft.get("lead") or {}
    did = draft.get("id", "")
    base = {"lead_id": did,
            "handle": (lead.get("handle") or "").lstrip("@"),
            "query_id": lead.get("query_id", ""),
            "reply_text": lead.get("reply_text", "")}

    if act == "lead_skip":
        q.mark_decided(did, "skipped")
        q.append_engaged({**base, "status": "skipped"})
        line_client.reply(reply_token, "⏭ スキップしました（返信・フォローはしていません）。")
        return

    # lead_approve: 記録して返信文を渡すだけ。X APIは叩かない。
    q.mark_decided(did, "approved")
    q.append_engaged({**base, "status": "approved"})
    url = lead.get("url", "")
    line_client.reply(
        reply_token,
        "✅ 承認を記録しました（自動投稿はしていません）。\n\n"
        "【返信文（長押しでコピー）】\n"
        f"{lead.get('reply_text', '')}\n\n"
        "【相手のツイート】\n"
        f"{url}\n\n"
        "Xアプリで開いて、ご自身の指で返信（＋必要ならフォロー）してください。",
    )


def _handle_postback(data: str, reply_token: str) -> None:
    """承認/却下ボタンの処理。"""
    params = {k: v[0] for k, v in parse_qs(data or "").items()}
    act = params.get("act")
    draft_id = params.get("id", "")
    draft = q.get(draft_id)

    if draft is None:
        line_client.reply(reply_token, "⚠️ 対象の下書きが見つかりませんでした。")
        return
    if draft.get("status") != "pending":
        line_client.reply(reply_token,
                          f"この投稿は処理済みです（{draft.get('status')}）。")
        return

    if act in ("lead_approve", "lead_skip"):
        _handle_lead_postback(act, draft, reply_token)
        return

    if act == "reject":
        q.mark_decided(draft_id, "rejected")
        line_client.reply(reply_token, "🗑 却下しました。投稿はしていません。")
        return

    if act != "approve":
        line_client.reply(reply_token, "⚠️ 不明な操作です。")
        return

    # --- 承認 → 予算ガードを通して実投稿（2部構成ならリプ本体も投稿）---
    post_link = bool(draft.get("post_link"))
    reply_body = draft.get("reply")
    ok_budget, why = _budget_check(post_has_link=post_link,
                                   post_has_reply=bool(reply_body), force=False)
    if not ok_budget:
        q.mark_decided(draft_id, "failed", info=why)
        line_client.reply(reply_token, f"⏸ 投稿を中止: {why}")
        return

    ok, tweet_id, info = post_to_x(draft.get("text", ""), reply_body,
                                   draft.get("link"), post_link, draft.get("image"))
    if ok:
        _log_post(tweet_id, draft.get("pillar", ""), post_link, bool(reply_body))
        q.mark_decided(draft_id, "posted", tweet_id=tweet_id, info=info)
        line_client.reply(reply_token, f"✅ 投稿しました！\nid={tweet_id}（{why}）")
    else:
        q.mark_decided(draft_id, "failed", info=info)
        line_client.reply(reply_token, f"❌ 投稿に失敗しました: {info}")


@app.post("/sns/line/webhook")
async def line_webhook(request: Request,
                       x_line_signature: str | None = Header(default=None)):
    body = await request.body()
    if not line_client.verify_signature(body, x_line_signature):
        # 署名不一致は拒否（なりすまし防止）。
        return Response(status_code=403, content="bad signature")

    try:
        payload = await request.json()
    except Exception:
        return Response(status_code=200, content="ok")  # 検証pingなど

    for ev in payload.get("events", []):
        etype = ev.get("type")
        reply_token = ev.get("replyToken", "")
        if etype == "postback":
            _handle_postback(ev.get("postback", {}).get("data", ""), reply_token)
        elif etype == "follow":
            # 友だち追加時、設定用に userId を本人へ返す。
            uid = ev.get("source", {}).get("userId", "")
            line_client.reply(
                reply_token,
                "友だち追加ありがとうございます🎤\n"
                "この userId を .env の LINE_OPERATOR_USER_ID に設定してください:\n"
                f"{uid}",
            )
    return Response(status_code=200, content="ok")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("WEBHOOK_PORT", "8088"))
    uvicorn.run("webhook:app", host="0.0.0.0", port=port,
                reload="--reload" in sys.argv)
