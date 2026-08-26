"""QA harness: 同一内容の永久再登場禁止（docs/108）。
使用済み弾の除外・--text の重複ブロック・承認時の最終ゲート（自動却下）を検証する。
ネットワーク（Gemini/X/LINE）は呼ばない。"""
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# 実行時データを一時ディレクトリに隔離（本物のキュー/ログに触れない）
_TMP = tempfile.mkdtemp(prefix="qa_no_repeat_")
os.environ["SNS_DATA_DIR"] = _TMP
os.environ["SNS_IMAGE"] = "0"
os.environ.pop("GEMINI_API_KEY", None)  # 生成はテンプレ経路 / expert_review はskip=approved

import themes
import dedup
import approval_queue as q
import generate_and_post as gp

results = []


def check(tc, cond, detail=""):
    results.append((tc, bool(cond), detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {tc} {detail}")


APP = "https://x.test"

# ---- TC-NR01: ammo_key は決定論的で、弾ごと・型ごとに異なる ----
keys = set()
for pillar in ("tip", "contrarian", "self_type", "visual", "voice_type", "artist_analysis"):
    for i in range(themes.pool_size(pillar)):
        keys.add(dedup.ammo_key(pillar, i, APP))
total = sum(themes.pool_size(p) for p in
            ("tip", "contrarian", "self_type", "visual", "voice_type", "artist_analysis"))
check("TC-NR01 全弾のammo_keyが一意", len(keys) == total, f"=> {len(keys)}/{total}")
check("TC-NR01 決定論", dedup.ammo_key("tip", 0, APP) == dedup.ammo_key("tip", 0, APP))

# ---- TC-NR02: 一度キューに載った弾は二度と選ばれない ----
i0 = dedup.pick_unused_index("contrarian", 0, APP)
check("TC-NR02 初回は起点の弾", i0 == 0)
p0 = themes.template_post("contrarian", 0, APP)
q.enqueue("contrarian", 1, p0["text"], p0["reply"], None, False,
          ammo_key=dedup.ammo_key("contrarian", 0, APP))
i1 = dedup.pick_unused_index("contrarian", 0, APP)
check("TC-NR02 使用済み弾はスキップ", i1 == 1, f"=> {i1}")
# 却下された弾も「作った」扱いで再利用しない
rec = q.enqueue("contrarian", 1, "x", None, None, False,
                ammo_key=dedup.ammo_key("contrarian", 1, APP))
q.mark_decided(rec["id"], "rejected")
check("TC-NR02 却下弾も再利用しない", dedup.pick_unused_index("contrarian", 0, APP) == 2)

# ---- TC-NR03: 全弾使用済みなら None（弾切れ判定） ----
for i in range(themes.pool_size("visual")):
    q.enqueue("visual", 2, f"v{i}", None, None, False,
              ammo_key=dedup.ammo_key("visual", i, APP))
check("TC-NR03 弾切れ→None", dedup.pick_unused_index("visual", 0, APP) is None)

# ---- TC-NR04: 弾切れ＋Gemini無し → 投稿を見送る（同内容は出さない）rc=0 ----
old_argv = sys.argv
sys.argv = ["generate_and_post.py", "--pillar", "visual", "--dry-run"]
buf = io.StringIO()
try:
    with redirect_stdout(buf):
        rc = gp.main()
finally:
    sys.argv = old_argv
out = buf.getvalue()
check("TC-NR04 弾切れは見送り", rc == 0 and "弾切れ" in out, f"=> rc={rc}")
check("TC-NR04 本文を出していない", "【本投稿】" not in out)

# ---- TC-NR05: 投稿済みと同文の --text は受け付けない（rc=2） ----
posted = q.enqueue("contrarian", 1, "同じ内容のテスト本文です。", "リプ", None, False)
q.mark_decided(posted["id"], "posted", tweet_id="t1")
sys.argv = ["generate_and_post.py", "--text", "同じ内容の テスト本文です。",  # 空白揺れは同一視
            "--pillar", "contrarian", "--dry-run"]
buf = io.StringIO()
try:
    with redirect_stdout(buf):
        rc = gp.main()
finally:
    sys.argv = old_argv
check("TC-NR05 同文の完成稿はrc=2", rc == 2)
check("TC-NR05 dedup判定", dedup.is_posted_duplicate("同じ内容のテスト本文です。"))

# ---- TC-NR06: 承認の最終ゲート — 投稿済みと同文の下書きは承認しても自動却下 ----
# webhook は fastapi 依存（コンテナには同梱）。未導入環境ではSKIP。
try:
    import fastapi  # noqa: F401
    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False
    print("[SKIP] TC-NR06 fastapi未導入のためスキップ（コンテナ/CIでは実行される）")
if _HAS_FASTAPI:
    import line_client
    dup = q.enqueue("contrarian", 2, "同じ内容のテスト本文です。", "リプ", None, False)
    replies = []
    _orig_reply, _orig_post = line_client.reply, None
    line_client.reply = lambda tok, text: replies.append(text) or (True, "ok")
    try:
        import webhook
        _orig_post = webhook.post_to_x
        webhook.post_to_x = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("must not post"))
        webhook._handle_postback(f"act=approve&id={dup['id']}", "tok")
    finally:
        line_client.reply = _orig_reply
        if _orig_post is not None:
            webhook.post_to_x = _orig_post
    after = q.get(dup["id"])
    check("TC-NR06 自動却下", after and after.get("status") == "rejected"
          and after.get("info") == "duplicate_of_posted",
          f"=> {after and after.get('status')}")
    check("TC-NR06 LINEに理由を返信", any("投稿済み" in r for r in replies))

# ---- TC-NR07: 未投稿の別内容は通常どおり選ばれ、ゲートにも引っかからない ----
check("TC-NR07 別内容はduplicateでない", not dedup.is_posted_duplicate("全く別の新しい本文"))
i_tip = dedup.pick_unused_index("tip", 0, APP)
check("TC-NR07 tipは未使用弾が残っている", i_tip is not None)

# ---- TC-NR08: バックフィル — 過去履歴から使用済み弾を特定して焼却（docs/108） ----
import backfill_used_ammo as bf
hist = [
    {"pillar": "tip", "text": themes.template_post("tip", 3, APP)["text"], "reply": ""},
    {"pillar": "tip", "text": "Geminiが完全に書き換えたフック",
     "reply": themes.template_post("tip", 4, APP)["reply"]},
    {"pillar": "artist_analysis",
     "text": "Mrs. GREEN APPLEの高音について（リライト済みの本文）", "reply": ""},
]
burned = bf.find_burned(hist)
got = {(b["pillar"], b["reason"].split(":", 1)[1]) for b in burned}
check("TC-NR08 本文一致で焼却", ("tip", "text_exact") in got, f"=> {sorted(got)}")
check("TC-NR08 リプ一致で焼却", ("tip", "reply_exact") in got)
check("TC-NR08 実名一致で焼却",
      any(p == "artist_analysis" and r.startswith("artist:") for p, r in got))
check("TC-NR08 無関係な弾は焼かない", len(burned) == 3, f"=> {len(burned)}")
dedup.record_used(burned)
check("TC-NR08 記録後は使用済み",
      all(b["ammo_key"] in dedup.used_ammo_keys() for b in burned))

failed = [tc for tc, ok, _ in results if not ok]
print("\n" + "─" * 40)
print(f"{len(results) - len(failed)}/{len(results)} PASS")
if failed:
    print("FAILED:", ", ".join(failed))
    sys.exit(1)
