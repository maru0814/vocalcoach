"""QA harness: 返信下書きの復活版（docs/58 FR-03改・2026-07-17 方針再転換）。
外部API・LINE・Geminiは呼ばない（キー未設定前提で走る）。
検証の主眼＝旧廃止理由（歌手名でっち上げ・トーン管理）が出力側ゲートで潰れていること。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

_TMP = tempfile.mkdtemp(prefix="qa_reply_")
os.environ["SNS_DATA_DIR"] = _TMP
os.environ.pop("GEMINI_API_KEY", None)
for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET",
          "LINE_CHANNEL_ACCESS_TOKEN", "LINE_CHANNEL_SECRET"):
    os.environ.pop(k, None)

import leads
import line_client
import reply_drafts

results = []


def check(tc, cond, detail=""):
    results.append((tc, bool(cond), detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {tc} {detail}")


SRC = "高音がどうしても出ない…サビで毎回苦しい"

# TC-R1: 全テンプレが空ソースでも検証を通る（テンプレ＝監修済みの最終防衛線）
bad = [(qid, reply_drafts.validate(t, "")) for qid, t in reply_drafts.TEMPLATES.items()
       if not reply_drafts.validate(t, "")[0]]
check("TC-R1 全テンプレが検証通過", not bad, f"落ちたもの: {bad}" if bad else "")

# TC-R2: 旧廃止理由①＝歌手名のでっち上げを出力側で棄却する
ok, why = reply_drafts.validate("星野源さんみたいに歌うには支えが大事ですよ", SRC)
check("TC-R2a 歌手名(漢字・正本リスト)を棄却", not ok, f"=> {why}")
ok, why = reply_drafts.validate("ヨルシカの曲は高音の練習にいいですよ", SRC)
check("TC-R2b 歌手名(カタカナ・未知語)を棄却", not ok, f"=> {why}")
ok, why = reply_drafts.validate("アイマーという歌手を参考にしてみては", SRC)
check("TC-R2c でっち上げカタカナ名を棄却", not ok, f"=> {why}")

# TC-R3: カタカナ許可の境界 — 発声用語・相手の文の語・許可語の連結は通る
ok, why = reply_drafts.validate("ミックスボイスはハミングから始めるのがおすすめですよ", SRC)
check("TC-R3a 発声用語は通過", ok, f"=> {why}")
ok, why = reply_drafts.validate("ピアノアプリと交互に音を合わせると確実ですよ", SRC)
check("TC-R3b 許可語の連結(ピアノ+アプリ)は通過", ok, f"=> {why}")
ok, why = reply_drafts.validate("カラオケバトルの話、いいですね。まず録音がおすすめです",
                                "カラオケバトルで高音が出ずに悔しかった")
check("TC-R3c 相手の文にある語は通過", ok, f"=> {why}")

# TC-R4: URL・タグ・宣伝・医療断定の棄却（トーン管理の機械化）
ok, why = reply_drafts.validate("こちらで診断できます https://example.com", SRC)
check("TC-R4a URLを棄却", not ok, f"=> {why}")
ok, why = reply_drafts.validate("がんばりましょう #ボイトレ 毎日コツコツが大事です", SRC)
check("TC-R4b ハッシュタグを棄却", not ok, f"=> {why}")
ok, why = reply_drafts.validate("よかったらフォローしてください。高音のコツを毎日呟いてます", SRC)
check("TC-R4c 誘導語(フォロー)を棄却", not ok, f"=> {why}")
ok, why = reply_drafts.validate("それは声帯結節かもしれません。声帯の使いすぎだと思います", SRC)
check("TC-R4d 医療的断定を棄却", not ok, f"=> {why}")
ok, why = reply_drafts.validate("短すぎ", SRC)
check("TC-R4e 長さ範囲外を棄却", not ok, f"=> {why}")

# TC-R5: Geminiキー無しでも全クエリでテンプレ下書きが返る（無音にならない）
for qid in leads.QUERY_BY_ID:
    text, origin = reply_drafts.draft(SRC, qid)
    if not text or origin != "template":
        check(f"TC-R5 {qid} でテンプレ下書き", False, f"=> ({origin}, {text[:30]})")
        break
else:
    check("TC-R5 全クエリでキー無しテンプレ下書き", True, f"({len(leads.QUERY_BY_ID)}クエリ)")

# TC-R6: 同文連投の検出（スパムシグナル対策）
t1, _ = reply_drafts.draft(SRC, "highnote")
check("TC-R6a 同一文は too_similar", reply_drafts.too_similar(t1, [t1]))
check("TC-R6b 別文は similar でない",
      not reply_drafts.too_similar(t1, [reply_drafts.TEMPLATES["longtone"]]))

# TC-R7: LINEダイジェスト行に下書きが載る／無い候補には載らない
CAND = {"handle": "singer_a", "followers": 420, "reason": "高音が出ない悩み",
        "source_text": SRC, "url": "https://x.com/singer_a/status/1",
        "reply_draft": t1}
line = line_client._candidate_line(1, CAND)
check("TC-R7a 下書きあり候補の行に✍️", "✍️ 返信下書き" in line and t1 in line)
line2 = line_client._candidate_line(2, {**CAND, "reply_draft": ""})
check("TC-R7b 下書きなし候補の行は従来通り", "✍️" not in line2)

# TC-R8: 復活後も write 自動化ゼロの不変条件 — リード系モジュールに
#         X API への書き込み呼び出し（POST系）が存在しないことをソースで確認
import inspect
src = "".join(inspect.getsource(m) for m in (reply_drafts, leads))
check("TC-R8 リード系モジュールにX API write なし",
      "api.twitter.com" not in src and "api.x.com" not in src)

print("=" * 56)
ok_all = all(r[1] for r in results)
print(f"{'ALL PASS' if ok_all else 'FAILURES PRESENT'} "
      f"({sum(1 for r in results if r[1])}/{len(results)})")
sys.exit(0 if ok_all else 1)
