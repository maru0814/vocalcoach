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

# ---- 診断導線パーサ（新仕様: 各タイプの実画像を使う図解）----
# voice_type = spotlight に image(data URI) と desc、title「【{Name}】タイプの声、誰に似てる？」
# （ラベル陳列「【声タイプ図鑑】◯◯」は好奇心ギャップ書式へ刷新済み＝themes.py/expert_review.py 参照）
dv = ig.parse_diagnosis("voice_type", 5)  # 5 = Dramatic
_vt5_name = themes.VOICE_TYPES[5 % len(themes.VOICE_TYPES)][0]  # 期待名を実データから導出（書式非依存）
check("TC-IG30 voice_type spotlight", dv["type"] == "diagnosis"
      and dv.get("spotlight", {}).get("image", "").startswith("data:image/jpeg")
      and dv["title"] == f"【{_vt5_name}】タイプの声、誰に似てる？", f"title={dv['title']}")
# self_type / visual = types 8件・各 image 付き
for pl in ("self_type", "visual"):
    dd = ig.parse_diagnosis(pl, 0)
    ok = (len(dd.get("types", [])) == 8
          and all(t["image"].startswith("data:image/jpeg") for t in dd["types"]))
    check(f"TC-IG31 {pl} 8タイプ画像", ok, f"types={len(dd.get('types', []))}")
# 8タイプ画像が assets/voice_types に存在し data URI 化できる
ids = [n.lower() for n, _e, _d in themes.VOICE_TYPES]
check("TC-IG32 8画像 data URI化", all(ig._voice_image_data_uri(i).startswith("data:image/jpeg") for i in ids),
      f"ids={ids}")
# 画像欠損でも types は返る（image=""）でクラッシュしない
saved_dir = ig._VOICE_DIR
ig._VOICE_DIR = "/nonexistent"
dmiss = ig.parse_diagnosis("self_type", 0)
check("TC-IG33 画像欠損でも継続", len(dmiss["types"]) == 8
      and all(t["image"] == "" for t in dmiss["types"]), "")
ig._VOICE_DIR = saved_dir

# ---- ③ 振り分け（build_image: 全ピラー→図解1600×900）----
import generate_and_post as gp
importlib.reload(gp)
os.environ["SNS_DATA_DIR"] = "/tmp/qa_ig"
os.environ["SNS_IMAGE_AI"] = "0"   # フォールバック時のカードはグラデ（AI課金回避）
gp.IMG_DIR = "/tmp/qa_ig/images"
try:
    from PIL import Image
    for pl in ("tip", "contrarian", "voice_type", "self_type", "visual"):
        p = gp.build_image(pl, 1, 5, "https://x.test")
        sz = Image.open(p).size
        check(f"TC-IG04 全ピラー図解 {pl}", sz == (1600, 900), f"{sz}")
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
