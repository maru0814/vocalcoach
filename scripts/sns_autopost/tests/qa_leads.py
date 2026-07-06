"""QA harness: Xフォロー候補パイプライン（docs/58 AC / docs/59 §10 の自動化可能ケース）。
外部API・LINE・Geminiは呼ばない（キー未設定前提で走る）。"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# データ書き込みを一時ディレクトリへ隔離（本物のログを汚さない）
_TMP = tempfile.mkdtemp(prefix="qa_leads_")
os.environ["SNS_DATA_DIR"] = _TMP
os.environ.pop("GEMINI_API_KEY", None)
for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET",
          "LINE_CHANNEL_ACCESS_TOKEN", "LINE_CHANNEL_SECRET"):
    os.environ.pop(k, None)

import approval_queue as q
import leads
import line_client

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

# TC-02i〜l: 「歌以外の音痴」の除外（2026-07-05 初回本番ドライランで実際に混入したケース）
ONCHI = {**GOOD, "query_id": "onchi"}
ok, why = leads.select({**ONCHI, "text": "方向音痴なのを直したい。誰かがいないとまともに外を歩けない"}, set())
check("TC-02i 方向音痴を除外", not ok, f"=> {why}")
ok, why = leads.select({**ONCHI, "text": "機械音痴すぎてメールで小さい「っ」は打てないし音程どころじゃない"}, set())
check("TC-02j 機械音痴を除外(複合語優先)", not ok, f"=> {why}")
ok, why = leads.select({**ONCHI, "text": "自分は音痴だと思う。推し活が忙しくて心が迷子"}, set())
check("TC-02k 歌の文脈なしを除外", not ok, f"=> {why}")
ok, why = leads.select({**ONCHI, "text": "カラオケで音痴って言われた…直したいなあ"}, set())
check("TC-02l 歌文脈の音痴は通過", ok, f"=> {why}")

# TC-02m〜o: 2026-07-06 追加絞り込み — バズった話題への便乗コメント（第三者の音痴ネタ）を除外
ok, why = leads.select({**ONCHI, "text": "@shizuki_ap2 完璧超人なのに音楽方面のセンスが壊滅的な先生、"
                        "本当に愛おしいですね😂ナガノ先生作詞作曲、歌ラッコ先生でガパオライスの"
                        "うた(音痴ver)聴いてみたい…!!"}, set())
check("TC-02m 第三者キャラの音痴ネタを除外", not ok, f"=> {why}")
ok, why = leads.select({**ONCHI, "text": "ラッコさん音痴設定？？？笑 雄馬くんはめちゃくちゃ歌上手いから"
                        "逆にどう表現するのか気になるじゃん😂"}, set())
check("TC-02n 便乗リプも除外", not ok, f"=> {why}")
ok, why = leads.select({**ONCHI, "text": "歌が下手で音痴なのが本当に苦手。カラオケ行くの気まずい"}, set())
check("TC-02o 本人の悩み（下手/苦手）は通過", ok, f"=> {why}")

# TC-14: 優先3テーマ（歌上達/ミックスボイス/カラオケ上達）が選別を通過する
ok, why = leads.select({**GOOD, "query_id": "sing_better",
                        "text": "歌がもっと上手くなりたい。何から練習すればいいんだろう"}, set())
check("TC-14a sing_better は通過", ok, f"=> {why}")
ok, why = leads.select({**GOOD, "query_id": "mixvoice_want",
                        "text": "ミックスボイスをどうしても出したい。地声と裏声が全然繋がらない"}, set())
check("TC-14b mixvoice_want は通過", ok, f"=> {why}")
ok, why = leads.select({**GOOD, "query_id": "karaoke_up",
                        "text": "カラオケでもっと上手く歌いたい。友達に下手って言われた"}, set())
check("TC-14c karaoke_up は通過", ok, f"=> {why}")
check("TC-14d PRIORITY_QUERY_IDS に3テーマが定義済み",
      set(leads.PRIORITY_QUERY_IDS) == {"sing_better", "mixvoice_want", "karaoke_up"})

# TC-10: 返信文モジュールは廃止済み（2026-07-06方針転換）。復活していないことを確認。
check("TC-10 lead_reply.py は削除済み",
      not os.path.exists(os.path.join(os.path.dirname(__file__), "..", "lead_reply.py")))
check("TC-10b expert_review にリード返信ゲートが残っていない",
      not hasattr(__import__("expert_review"), "review_lead_reply"))

# TC-05: suggest_leads → engaged_log の記録経路（フォロー実行APIは存在しない）
digest = [{"handle": "singer_a", "query_id": "highnote", "followers": 420,
          "source_text": GOOD["text"], "url": "https://x.com/singer_a/status/1"}]
recs = q.suggest_leads(digest, batch_id="20260706-100000")
check("TC-05a suggest_leads は status=suggested で記録", recs[0]["status"] == "suggested")
check("TC-05b reply_textフィールドを持たない", "reply_text" not in recs[0])
rows = q.read_engaged()
check("TC-05c engaged_log 追記", len(rows) == 1 and rows[0]["followed_back"] is None)
check("TC-05d engaged_handles に反映", "singer_a" in q.engaged_handles())
check("TC-05e suggested_today カウント", q.suggested_today() == 1)
q.update_engaged(recs[0]["lead_id"], followed_back=True)
check("TC-05f followed_back 更新", q.read_engaged()[0]["followed_back"] is True)

# TC-11: バッチ一括確認（mark_batch_status）— 対象バッチのsuggestedだけを更新
digest2 = [{"handle": "singer_b", "query_id": "onchi", "followers": 200,
           "source_text": "音痴を直したい", "url": "https://x.com/singer_b/status/2"},
          {"handle": "singer_c", "query_id": "pitch", "followers": 300,
           "source_text": "音程が不安定", "url": "https://x.com/singer_c/status/3"}]
q.suggest_leads(digest2, batch_id="20260706-110000")
n = q.mark_batch_status("20260706-110000", "followed")
check("TC-11a バッチ内2件がfollowedに", n == 2)
by_handle = {r["handle"]: r["status"] for r in q.read_engaged()}
check("TC-11b 対象外バッチ(singer_a)は変化なし", by_handle["singer_a"] == "suggested")
check("TC-11c 対象バッチは更新", by_handle["singer_b"] == "followed" and by_handle["singer_c"] == "followed")
n2 = q.mark_batch_status("20260706-110000", "skipped")
check("TC-11d 二重確定は0件（すでにsuggestedでない）", n2 == 0)

# TC-12: LINEダイジェスト本文に返信文が含まれず、プロフィールリンクを含む
os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = "dummy"
os.environ["LINE_CHANNEL_SECRET"] = "dummy"
os.environ["LINE_OPERATOR_USER_ID"] = "Udummy"
sent_payloads = []


class _FakeLineResp:
    status_code = 200


def _fake_post(url, headers=None, json=None, timeout=None):
    sent_payloads.append(json)
    return _FakeLineResp()


import requests as _requests
_orig_post = _requests.post
_requests.post = _fake_post
ok, info = line_client.push_lead_digest(digest, "20260706-100000")
_requests.post = _orig_post
check("TC-12a push_lead_digest 成功", ok, f"=> {info}")
body_texts = " ".join(m.get("text", "") for m in sent_payloads[0]["messages"] if m["type"] == "text")
check("TC-12b 返信文フィールドへの言及なし", "提案する返信" not in body_texts and "返信案" not in body_texts)
check("TC-12c プロフィール/ツイートURLを含む", "x.com/singer_a" in body_texts)
check("TC-12d ボタンpostbackにbatch_idを含む", any(
    "lead_followed_batch&batch=20260706-100000" in a["data"]
    for m in sent_payloads[0]["messages"] if m["type"] == "template"
    for a in m["template"]["actions"]))
os.environ.pop("LINE_CHANNEL_ACCESS_TOKEN", None)
os.environ.pop("LINE_CHANNEL_SECRET", None)
os.environ.pop("LINE_OPERATOR_USER_ID", None)

# TC-13: webhook のバッチ確認処理が X 書込みAPIを一切呼ばないこと（不変条件）
try:
    import webhook

    def _boom(*a, **kw):  # 呼ばれてはいけない
        raise AssertionError("post_to_x が呼ばれた（フォロー候補経路でX書込み発生）")
    webhook.post_to_x = _boom
    webhook.line_client.reply = lambda tok, txt: (True, "ok")
    q.suggest_leads([{"handle": "singer_d", "query_id": "mix", "followers": 100,
                      "source_text": "ミックスできない", "url": "https://x.com/singer_d/status/4"}],
                    batch_id="20260706-120000")
    webhook._handle_lead_batch("lead_followed_batch", "20260706-120000", "tok")
    st = {r["handle"]: r["status"] for r in q.read_engaged()}
    check("TC-13a lead_followed_batch でX書込みなし・記録される", st.get("singer_d") == "followed")
    q.suggest_leads([{"handle": "singer_e", "query_id": "mix", "followers": 100,
                      "source_text": "ミックスできない", "url": "https://x.com/singer_e/status/5"}],
                    batch_id="20260706-130000")
    webhook._handle_lead_batch("lead_skip_batch", "20260706-130000", "tok")
    st = {r["handle"]: r["status"] for r in q.read_engaged()}
    check("TC-13b lead_skip_batch で記録される", st.get("singer_e") == "skipped")
except ImportError as e:
    print(f"[SKIP] TC-13 webhook import不可（依存未導入）: {e}")

# TC-01(AC-01): DRY_RUN で lead_finder が副作用ゼロ（入力0件の正常終了パス）
os.environ["DRY_RUN"] = "1"
import lead_finder
empty = os.path.join(_TMP, "empty.jsonl")
open(empty, "w").close()
before = q.read_engaged()
sys.argv = ["lead_finder.py", "--input", empty, "--dry-run", "--no-search", "--no-mentions"]
code = lead_finder.main()
after = q.read_engaged()
check("TC-01 DRY_RUNで副作用ゼロ・exit0", code == 0 and before == after)

# TC-08: read予算メーターの概算
m = lead_finder.ReadMeter()
m.add("post_read", 100); m.add("user_read", 10)
check("TC-08 read概算 100post+10user=$0.60", abs(m.usd() - 0.60) < 1e-9, f"=> ${m.usd():.3f}")

# TC-15: source_search が優先3テーマを日替わりローテーションに関係なく必ず含める
class _FakeOAuth:
    def __init__(self):
        self.queries = []

    def get(self, url, params=None, timeout=None):
        self.queries.append(params.get("query", ""))

        class _R:
            status_code = 200

            @staticmethod
            def json():
                return {"data": []}
        return _R()


fake = _FakeOAuth()
os.environ["LEAD_QUERIES_PER_RUN"] = "4"
lead_finder.source_search(fake, lead_finder.ReadMeter(), want=10)
priority_texts = [leads.QUERY_BY_ID[i]["query"] for i in leads.PRIORITY_QUERY_IDS]
check("TC-15 優先3テーマが必ず検索される",
      all(any(pt in q for q in fake.queries) for pt in priority_texts),
      f"=> {fake.queries}")
check("TC-15b per_run=4で計4クエリ（優先3+ローテ1）", len(fake.queries) == 4, f"=> {len(fake.queries)}件")

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
