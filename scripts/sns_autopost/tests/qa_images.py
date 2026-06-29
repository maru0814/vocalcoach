"""QA harness: X投稿画像添付（automatable cases）。各TCをassertしPASS/FAILを出す。"""
import os
import sys
import importlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from PIL import Image

results = []


def check(tc, cond, detail=""):
    results.append((tc, bool(cond), detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {tc} {detail}")


# TC-01: build_headline 5ピラー = 短文・絵文字なし・<=40字・誘導行除去
os.environ.pop("SNS_FONT_PATH", None)
import themes, images
importlib.reload(images)
for pl in ["tip", "contrarian", "voice_type", "self_type", "visual"]:
    base = themes.template_post(pl, 4, "https://x.test")
    hl = images.build_headline(pl, base["text"], base.get("reply"))
    ok = (0 < len(hl) <= 41 and "👇" not in hl and "プロフィ" not in hl
          and "http" not in hl)
    check(f"TC-01:{pl}", ok, f"=> {hl!r}")

# TC-02: 絵文字ストリップ
hl = images.build_headline("tip", "高音が裏返る人へ🎤🔥\n👇 手順はリプ", None)
check("TC-02 emoji除去", "🎤" not in hl and "🔥" not in hl, f"=> {hl!r}")

# TC-03: グラデ背景=4:5/1080x1350 のPNGを出力
os.environ["SNS_IMAGE_AI"] = "0"
os.environ["SNS_IMAGE"] = "1"
p = images.generate_image("tip", "テスト見出し", "/tmp/qa_grad.png")
im = Image.open(p) if p else None
check("TC-03 4:5寸法", im is not None and im.size == (1080, 1350),
      f"=> {p} {im.size if im else None}")

# TC-04: SNS_IMAGE=0 → 画像なし(None)
os.environ["SNS_IMAGE"] = "0"
p0 = images.generate_image("tip", "x", "/tmp/qa_none.png")
check("TC-04 SNS_IMAGE=0でNone", p0 is None, f"=> {p0}")
os.environ["SNS_IMAGE"] = "1"

# TC-05: 不正モデル → AI失敗→グラデにフォールバックで画像は出る
os.environ["SNS_IMAGE_AI"] = "1"
os.environ["SNS_IMAGE_MODEL"] = "imagen-does-not-exist-xyz"
os.environ.setdefault("GEMINI_API_KEY", "dummy-for-fallback-test")
p = images.generate_image("contrarian", "フォールバック確認", "/tmp/qa_badmodel.png")
check("TC-05 不正モデル→フォールバック", p is not None and os.path.exists(p), f"=> {p}")
os.environ["SNS_IMAGE_AI"] = "0"

# TC-06: フォント未検出 → クラッシュせず文字なしで4:5画像を出す
saved = images._FONT_CANDIDATES
images._FONT_CANDIDATES = []          # システムフォント候補を空に
os.environ.pop("SNS_FONT_PATH", None)
# assetsフォントも無い前提（存在すれば拾うが本リポは未追跡）
p = images.generate_image("tip", "フォント無しテスト", "/tmp/qa_nofont.png")
imn = Image.open(p) if p else None
check("TC-06 フォント無→文字なし出力", imn is not None and imn.size == (1080, 1350),
      f"=> {p}")
images._FONT_CANDIDATES = saved

# TC-07: post_to_x は X キー無しで X_KEYS_MISSING（クラッシュしない）
import generate_and_post as gp
importlib.reload(gp)
for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
    os.environ.pop(k, None)
ok, tid, info = gp.post_to_x("t", None, None, False, "/tmp/qa_grad.png")
check("TC-07 Xキー無→KEYS_MISSING", (ok is False and info == "X_KEYS_MISSING"),
      f"=> {info}")

# TC-08: enqueue が image フィールドを保持
import tempfile
import importlib as il
qdir = tempfile.mkdtemp(prefix="qa_q_")
os.environ["SNS_DATA_DIR"] = qdir
import approval_queue as q
il.reload(q)
rec = q.enqueue("tip", 1, "本文", "リプ本体", "https://x.test", False, "/tmp/qa_grad.png")
got = q.get(rec["id"])
check("TC-08 enqueueにimage保持", got and got.get("image") == "/tmp/qa_grad.png",
      f"=> {got.get('image') if got else None}")

# TC-09: build_headline 長文AI風 → 40字以内に省略（…付与）
longtext = "「" + "あ" * 80 + "」と悩んでいませんか？" + "👇 手順はリプ"
hl = images.build_headline("tip", longtext, None)
check("TC-09 長文→<=41字に省略", len(hl) <= 41, f"=> len={len(hl)} {hl!r}")

print("\n==== SUMMARY ====")
passed = sum(1 for _, ok, _ in results if ok)
print(f"{passed}/{len(results)} PASS")
sys.exit(0 if passed == len(results) else 1)
