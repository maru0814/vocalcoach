"""QA harness: 図解インフォグラフィック。パーサ/振り分け/フォールバック/不変条件。"""
import os
import sys
import importlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import themes
import infographic as ig

results = []


def check(tc, cond, detail=""):
    results.append((tc, bool(cond), detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {tc} {detail}")


# ---- ① パーサ正常系: TIPS全8件 ----
for i, tip in enumerate(themes.TIPS):
    d = ig.parse_tip(tip)
    ok = (d["title"] and 2 <= len(d["steps"]) <= 4 and d["summary"]
          and all(s["pill"] for s in d["steps"]))
    check(f"TC-IG01 TIPS[{i}]", ok,
          f"steps={len(d['steps'])} title={d['title'][:12]}")

# highlight が summary の部分文字列（⑥ <mark>が必ず当たる）
for i, tip in enumerate(themes.TIPS):
    d = ig.parse_tip(tip)
    hl = d["highlight"]
    check(f"TC-IG06 TIPS[{i}] highlight⊂summary", hl and hl in d["summary"],
          f"hl={hl!r}")

# ---- CONTRARIAN 全3件 → reasons2枚 ----
for i, (hook, body) in enumerate(themes.CONTRARIAN):
    d = ig.parse_contrarian(hook, body)
    ok = (d["title"] and d["verdict"] and len(d["reasons"]) == 2
          and all(r["title"] and r["body"] for r in d["reasons"])
          and d["highlight"] in d["summary"])
    check(f"TC-IG02 CONTRARIAN[{i}]", ok, f"verdict={d['verdict']}")

# ---- ② パーサ異常系 ----
# 番号①なし
d = ig.parse_tip("番号がない普通の文。これだけ。")
check("TC-IG03a 番号なし", d["title"] and d["steps"] == [], f"steps={len(d['steps'])}")
# 空文字
d = ig.parse_tip("")
check("TC-IG03b 空文字", isinstance(d, dict) and d["type"] == "tip", "no crash")
# introなし（step直後）＝TIPS[4]
d = ig.parse_tip(themes.TIPS[4])
check("TC-IG03c intro無→subtitle補完", bool(d["subtitle"]), f"sub={d['subtitle'][:14]}")
# 2ステップ
d = ig.parse_tip("二手順テストの人へ。\n① まず吸う\n② 次に吐く\n締めの一言。")
check("TC-IG03d 2ステップ", len(d["steps"]) == 2, f"steps={len(d['steps'])}")
# 4ステップ
d = ig.parse_tip("四手順へ。\n① a\n② b\n③ c\n④ d\nまとめ。")
check("TC-IG03e 4ステップ", len(d["steps"]) == 4, f"steps={len(d['steps'])}")
# 引用なしbodyのcontrarian
d = ig.parse_contrarian("誤解タイトル\n↑ウソ", "引用記号のない説明文。二文目もある。三文目で締める。")
check("TC-IG03f 引用なしcontrarian", len(d["reasons"]) == 2 and d["highlight"] in d["summary"],
      f"r1={d['reasons'][0]['title']}")

# ---- ③ 振り分け（build_image: 寸法で判定）----
import generate_and_post as gp
importlib.reload(gp)
os.environ["SNS_DATA_DIR"] = "/tmp/qa_ig"
os.environ["SNS_IMAGE_AI"] = "0"   # カードはグラデ（AI課金回避）
gp.IMG_DIR = "/tmp/qa_ig/images"
try:
    from PIL import Image
    routing = {"tip": (1600, 900), "contrarian": (1600, 900),
               "self_type": (1080, 1350), "visual": (1080, 1350)}
    for pl, exp in routing.items():
        p = gp.build_image(pl, 1, 5, "https://x.test")
        sz = Image.open(p).size
        check(f"TC-IG04 振り分け {pl}", sz == exp, f"{sz} exp={exp}")
except Exception as e:
    check("TC-IG04 振り分け", False, f"EXC {e}")

# ---- ④ フォールバック: infographic.generate→None なら tip もカード ----
_orig = ig.generate
gp.infographic.generate = lambda *a, **k: None
try:
    p = gp.build_image("tip", 1, 5, "https://x.test")
    from PIL import Image
    check("TC-IG05 図解不可→カード", Image.open(p).size == (1080, 1350),
          f"{Image.open(p).size}")
finally:
    gp.infographic.generate = _orig

# ---- ⑦ SNS_IMAGE=0 → None ----
os.environ["SNS_IMAGE"] = "0"
p = gp.build_image("tip", 1, 5, "https://x.test")
check("TC-IG07 SNS_IMAGE=0", p is None, f"{p}")
os.environ["SNS_IMAGE"] = "1"

print("\n==== SUMMARY (parser/routing/fallback) ====")
passed = sum(1 for _, ok, _ in results if ok)
print(f"{passed}/{len(results)} PASS")
sys.exit(0 if passed == len(results) else 1)
