"""QA harness: アーティスト発声解説型 artist_analysis（docs/84 TC-AA01〜06）。
各TCをassertしPASS/FAILを出す。ネットワーク（Gemini/X/LINE）は呼ばない。"""
import io
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# 画像生成とゲートのネットワークを無効化（安全・高速）。
os.environ["SNS_IMAGE"] = "0"
os.environ.pop("GEMINI_API_KEY", None)  # expert_review はキー無しでskip＝approved

import themes
import infographic
import generate_and_post as gp

results = []


def check(tc, cond, detail=""):
    results.append((tc, bool(cond), detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {tc} {detail}")


# ---- TC-AA01: ローテ — 週4枠（docs/84 §9）・同日3スロットに型の重複なし ----
week_all = [themes.pillar_for(wd, sl) for wd in range(7) for sl in (1, 2, 3)]
check("TC-AA01 週4枠", week_all.count("artist_analysis") == 4,
      f"=> {week_all.count('artist_analysis')}枠")
dup_days = [wd for wd in range(7)
            if len({themes.pillar_for(wd, sl) for sl in (1, 2, 3)}) != 3]
check("TC-AA01 同日重複なし", not dup_days, f"=> 重複曜日{dup_days}")

# ---- TC-AA02: 弾倉 — artist が正本と一致・type が8タイプに存在 ----
canon_names = {name for a in themes.ARTISTS_BY_ID.values()
               for names in a.values() for name in names}
type_ids = {n.lower() for n, _, _ in themes.VOICE_TYPES}
for e in themes.ARTIST_ANALYSIS:
    check(f"TC-AA02 正本実名: {e['artist']}", e["artist"] in canon_names)
    check(f"TC-AA02 タイプ実在: {e['artist']}", e["type"] in type_ids,
          f"=> {e['type']}")
    # 実名がタイプの正本と同じ声タイプに紐づいているか（診断ブリッジの整合）
    a = themes.ARTISTS_BY_ID.get(e["type"], {})
    in_type = e["artist"] in (a.get("female", []) + a.get("male", []))
    check(f"TC-AA02 タイプ整合: {e['artist']}", in_type, f"=> type={e['type']}")

# ---- TC-AA03: 安全 — URLなし・貶し/優劣比較なし・推定の作法あり ----
_BANNED = ("下手", "音痴", "より上手", "より劣", "たいしたこと")
for e in themes.ARTIST_ANALYSIS:
    full = e["hook"] + e["body"]
    check(f"TC-AA03 URLなし: {e['artist']}", "http" not in full)
    hits = [w for w in _BANNED if w in full]
    check(f"TC-AA03 禁止語なし: {e['artist']}", not hits, f"=> {hits}")
    check(f"TC-AA03 推定の作法: {e['artist']}",
          ("推定" in e["body"]) and ("聞こえ" in e["body"]))

# ---- TC-AA04: template_post — 2部構成・実名・診断ブリッジ ----
for i, e in enumerate(themes.ARTIST_ANALYSIS):
    post = themes.template_post("artist_analysis", i, "https://x.test")
    check(f"TC-AA04 実名がhookに: {e['artist']}", e["artist"] in post["text"])
    ok_reply = (post.get("reply") and "①" in post["reply"]
                and "8タイプ診断" in post["reply"]
                and themes._type_label(e["type"]) in post["reply"])
    check(f"TC-AA04 リプ=分解＋ブリッジ: {e['artist']}", bool(ok_reply))
    check(f"TC-AA04 リプにURLなし: {e['artist']}", "http" not in (post["reply"] or ""))

# ---- TC-AA05: 図解 — 手順図解データを返し診断ブリッジが混入しない ----
for i, e in enumerate(themes.ARTIST_ANALYSIS):
    data = infographic.build_data("artist_analysis", i)
    check(f"TC-AA05 手順図解: {e['artist']}",
          data.get("type") == "tip" and len(data.get("steps", [])) >= 2,
          f"=> steps={len(data.get('steps', []))}")
    flat = data.get("title", "") + data.get("subtitle", "") + data.get("summary", "")
    check(f"TC-AA05 ブリッジ非混入: {e['artist']}", "8タイプ診断" not in flat)
    check(f"TC-AA05 見出しに実名: {e['artist']}", e["artist"] in data.get("title", ""))

# ---- TC-AA06: 通し — --pillar artist_analysis --dry-run が rc=0 ----
old_argv = sys.argv
sys.argv = ["generate_and_post.py", "--pillar", "artist_analysis", "--dry-run"]
buf = io.StringIO()
try:
    with redirect_stdout(buf):
        rc = gp.main()
finally:
    sys.argv = old_argv
out = buf.getvalue()
check("TC-AA06 dry-run rc=0", rc == 0)
check("TC-AA06 pillar表示", "pillar=artist_analysis" in out)
check("TC-AA06 リプ本体が出る", "【リプ（自己返信）＝大事な中身】" in out)
check("TC-AA06 投稿していない", "承認キュー・LINE・投稿はいずれもしていません" in out)

failed = [tc for tc, ok, _ in results if not ok]
print("\n" + "─" * 40)
print(f"{len(results) - len(failed)}/{len(results)} PASS")
if failed:
    print("FAILED:", ", ".join(failed))
    sys.exit(1)
