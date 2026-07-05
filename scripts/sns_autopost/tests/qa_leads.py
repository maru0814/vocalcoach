"""QA harness: Xリード獲得半自動化（docs/58 AC / docs/59 §10 の自動化可能ケース）。
外部API・LINE・Geminiは呼ばない（キー未設定前提で走る）。"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# データ書き込みを一時ディレクトリへ隔離（本物のキュー/ログを汚さない）
_TMP = tempfile.mkdtemp(prefix="qa_leads_")
os.environ["SNS_DATA_DIR"] = _TMP
os.environ.pop("GEMINI_API_KEY", None)
for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET",
          "LINE_CHANNEL_ACCESS_TOKEN", "LINE_CHANNEL_SECRET"):
    os.environ.pop(k, None)

import approval_queue as q
import expert_review
import lead_reply
import leads

results = []


def check(tc, cond, detail=""):
    results.append((tc, bool(cond), detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {tc} {detail}")


GOOD = {"text": "高音がどうしても出ない…サビで毎回苦しい", "handle": "singer_a",
        "query_id": "highnote", "source": "search", "followers": 420, "bio": "歌の練習中"}

# TC-02(AC-02): 選別基準 — 各NGケースが除外され、良候補が通過する
ok, note = leads.select(dict(GOOD), set())
check("TC-02a 良候補は通過", ok, f"=> {note}")
ok, why = leads.select({**GOOD, "text": "I cannot hit the high notes"}, set())
check("TC-02b 非日本語を除外", not ok, f"=> {why}")
ok, why = leads.select({**GOOD, "bio": "相互フォロー歓迎！フォロバ100"}, set())
check("TC-02c 相互狙いを除外", not ok, f"=> {why}")
ok, why = leads.select({**GOOD, "followers": 50000}, set())
check("TC-02d フォロワー範囲外を除外", not ok, f"=> {why}")
ok, why = leads.select(dict(GOOD), {"singer_a"})
check("TC-02e 対応済みhandleを除外", not ok, f"=> {why}")
ok, note = leads.select({**GOOD, "followers": None}, set())
check("TC-02f followers不明はスキップ通過", ok and "unknown" in note, f"=> {note}")
ok, why = leads.select({**GOOD, "text": "今日のライブ告知です！チケット発売中"}, set())
check("TC-02g 文脈不一致を除外", not ok, f"=> {why}")
ok, why = leads.select({**GOOD, "text": "うたが下手で高音も出ないの、なやみ", "source": "mention",
                        "query_id": "mention"}, set())
check("TC-02h mentionは文脈判定スキップ", ok, f"=> {why}")

# TC-07(AC-07): Geminiキー無しでもテンプレ返信が出る・URLを含まない
text, generated = lead_reply.draft(GOOD["text"], "highnote")
check("TC-07 キー無し=テンプレ返信", (not generated) and len(text) > 10 and "http" not in text,
      f"=> {text[:40]}…")

# TC-03(AC-03): URL入り返信は GEMINI_API_KEY 無しでも必ず失格
gate = expert_review.review_lead_reply("高音が出ない", "ここで診断できます https://example.com")
check("TC-03a URL入りは即失格", not gate["approved"], f"=> {gate['report'][:40]}")
gate = expert_review.review_lead_reply("高音が出ない", "詳しくはDMで！フォローしてくださいね")
check("TC-03b 誘導ワードは即失格", not gate["approved"], f"=> {gate['report'][:40]}")
gate = expert_review.review_lead_reply(GOOD["text"], text)
check("TC-03c キー無し=未レビューでfail-open", gate["approved"] and gate["skipped"],
      f"=> {gate['report'][:40]}")

# TC-04: 同文連投の検出
check("TC-04a 酷似を検出", lead_reply.too_similar(text, [text + "🎤"]))
check("TC-04b 別文は通す", not lead_reply.too_similar(
    "ピッチは息の支えから安定しますよ。", ["高音は当てる位置をおでこ側へ。"]))

# TC-05(AC-05相当): enqueue_lead → engaged_log の記録経路（X APIは存在しない）
lead = {"url": "https://x.com/singer_a/status/1", "handle": "singer_a",
        "query_id": "highnote", "source": "search", "source_text": GOOD["text"],
        "followers": 420, "reply_text": text}
rec = q.enqueue_lead(lead, expert_note="✅ テスト")
check("TC-05a enqueue_lead kind=lead", rec["kind"] == "lead" and rec["status"] == "pending")
check("TC-05b 既存enqueueは kind=post",
      q.enqueue("tip", 1, "本文", None, None, False)["kind"] == "post")
q.append_engaged({"lead_id": rec["id"], "handle": "singer_a", "query_id": "highnote",
                  "reply_text": text, "status": "approved"})
rows = q.read_engaged()
check("TC-05c engaged_log 追記", len(rows) == 1 and rows[0]["followed_back"] is None)
check("TC-05d engaged_handles に反映", "singer_a" in q.engaged_handles())
q.update_engaged(rec["id"], followed_back=True)
check("TC-05e followed_back 更新", q.read_engaged()[0]["followed_back"] is True)
check("TC-05f 同文検出プールに反映", text in q.recent_lead_reply_texts())
check("TC-05g leads_today カウント", q.leads_today() == 1)

# TC-06: webhook のリード分岐が X 書込みAPIを一切呼ばないこと（AC-05 不変条件）。
# post_to_x が呼ばれたら即FAILさせる monkeypatch で担保する。
try:
    import webhook

    def _boom(*a, **kw):  # 呼ばれてはいけない
        raise AssertionError("post_to_x が呼ばれた（リード経路でX書込み発生）")
    webhook.post_to_x = _boom
    webhook.line_client.reply = lambda tok, txt: (True, "ok")
    webhook._handle_lead_postback("lead_approve", q.get(rec["id"]), "tok")
    check("TC-06a lead_approve でX書込みなし", q.get(rec["id"])["status"] == "approved")
    rec2 = q.enqueue_lead(lead, expert_note="")
    webhook._handle_lead_postback("lead_skip", q.get(rec2["id"]), "tok")
    check("TC-06b lead_skip 記録", q.get(rec2["id"])["status"] == "skipped")
    approved = [r for r in q.read_engaged() if r.get("status") == "approved"]
    skipped = [r for r in q.read_engaged() if r.get("status") == "skipped"]
    check("TC-06c engaged_log に approved/skipped", len(approved) >= 1 and len(skipped) == 1)
except ImportError as e:
    print(f"[SKIP] TC-06 webhook import不可（依存未導入）: {e}")

# TC-01(AC-01)/TC-05h: DRY_RUN で lead_finder が副作用ゼロ（入力0件の正常終了パス）
os.environ["DRY_RUN"] = "1"
import lead_finder
empty = os.path.join(_TMP, "empty.jsonl")
open(empty, "w").close()
before = open(q.QUEUE_PATH, encoding="utf-8").read()
code = lead_finder.main.__wrapped__() if hasattr(lead_finder.main, "__wrapped__") else None
# main() は argparse を使うので argv を差し替えて実行
sys.argv = ["lead_finder.py", "--input", empty, "--dry-run", "--no-search", "--no-mentions"]
code = lead_finder.main()
after = open(q.QUEUE_PATH, encoding="utf-8").read()
check("TC-01 DRY_RUNで副作用ゼロ・exit0", code == 0 and before == after)

# TC-08: read予算メーターの概算
m = lead_finder.ReadMeter()
m.add("post_read", 100); m.add("user_read", 10)
check("TC-08 read概算 100post+10user=$0.60", abs(m.usd() - 0.60) < 1e-9, f"=> ${m.usd():.3f}")

# TC-09: oEmbedレスポンスのパース（実HTTPはproxy遮断環境でも検証できるよう固定レスポンス）
class _FakeResp:
    status_code = 200

    @staticmethod
    def json():
        return {"author_name": "うたこ", "author_url": "https://twitter.com/utako_sing",
                "html": ('<blockquote class="twitter-tweet"><p lang="ja">高音が出ない…'
                         'サビで毎回苦しい</p>&mdash; うたこ (@utako_sing) '
                         '<a href="https://twitter.com/utako_sing/status/1">July 1, 2026</a>'
                         '</blockquote>')}


_orig_get = lead_finder.requests.get
lead_finder.requests.get = lambda *a, **kw: _FakeResp()
got = lead_finder._fetch_oembed("https://x.com/utako_sing/status/1")
lead_finder.requests.get = _orig_get
check("TC-09 oEmbedパース（本文+handle）",
      got is not None and "高音が出ない" in got[0] and got[1] == "utako_sing",
      f"=> {got}")

print("-" * 56)
fails = [tc for tc, okk, _ in results if not okk]
print(f"{len(results) - len(fails)}/{len(results)} PASS" + (f" / FAIL: {fails}" if fails else ""))
sys.exit(1 if fails else 0)
