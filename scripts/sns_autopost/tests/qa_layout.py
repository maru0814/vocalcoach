"""QA: レイアウト不変条件。本文(.content)がキャラ列(.char-col)に絶対重ならない。
Playwrightで実ピクセル測定（1600x900・等倍）。"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import infographic as ig
from playwright.sync_api import sync_playwright

CHAR = ("data:image/svg+xml;base64,"
        "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0NDAiIGhlaWdodD0iNjAwIj48cmVjdCB3aWR0aD0iNDQwIiBoZWlnaHQ9IjYwMCIgZmlsbD0iI2NjYyIvPjwvc3ZnPg==")

LONG = "あ" * 60
cases = {
    "tip_normal": {"type": "tip", "title": "通常タイトル", "subtitle": "サブ見出し",
        "steps": [{"pill": "見出しA", "body": "本文A", "tag": "t", "icon": "mic"},
                  {"pill": "見出しB", "body": "本文B", "tag": "t", "icon": "wave"},
                  {"pill": "見出しC", "body": "本文C", "tag": "t", "icon": "stairs"}],
        "summary": "まとめの一文。", "highlight": "まとめ", "hashtags": "#a #b",
        "character": CHAR},
    "tip_long_4step": {"type": "tip", "title": LONG, "subtitle": LONG,
        "steps": [{"pill": LONG[:20], "body": LONG, "tag": "長いタグ", "icon": "mic"},
                  {"pill": LONG[:20], "body": LONG, "tag": "長いタグ", "icon": "wave"},
                  {"pill": LONG[:20], "body": LONG, "tag": "長いタグ", "icon": "stairs"},
                  {"pill": LONG[:20], "body": LONG, "tag": "長いタグ", "icon": "feather"}],
        "summary": LONG, "highlight": LONG[:10], "hashtags": "#ボイトレ #ボイストレーニング",
        "character": CHAR},
    "contrarian_long": {"type": "contrarian", "title": LONG, "verdict": "半分ウソ",
        "reasons": [{"title": "鍵1" + "x" * 10, "body": LONG}, {"title": "鍵2", "body": LONG}],
        "summary": LONG, "highlight": LONG[:8], "hashtags": "#ボイトレ #高音",
        "character": CHAR},
    # 診断導線（キャラ無し・画像ベース）。横溢れせず描画されること。
    "diagnosis_hero": {"type": "diagnosis", "title": "【声タイプ図鑑】Dramatic",
        "spotlight": {"image": CHAR, "desc": LONG, "artists": "声質が近い例：♀ " + LONG + " ／ ♂ " + LONG},
        "cta": {"main": "あなたは何タイプ？プロフィールから無料で診断🎤", "sub": ""}},
    "diagnosis_gallery": {"type": "diagnosis", "title": LONG, "subtitle": LONG,
        "types": [{"name": "Mysterious" + str(i), "image": CHAR, "featured": i == 5,
                   "artists": LONG} for i in range(8)],
        "cta": {"main": "プロフィールのリンクから無料で診断🎤", "sub": "15秒歌うだけ"}},
}

MEASURE = """() => {
  const card = document.querySelector('.card');
  const scrollW = card.scrollWidth;
  const rendered = document.querySelector('.content').children.length;
  const col = document.querySelector('.char-col');
  if (!col) return { noChar: true, overflowRight: scrollW, rendered };
  const colLeft = col.getBoundingClientRect().left;
  let maxRight = 0, worst = '';
  document.querySelectorAll('.content, .content *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.right > maxRight) { maxRight = r.right; worst = el.className || el.tagName; }
  });
  return { colLeft, maxRight, worst, gap: Math.round(colLeft - maxRight),
           cardW: card.getBoundingClientRect().width, overflowRight: scrollW, rendered };
}"""

fails = 0
with sync_playwright() as pw:
    browser = pw.chromium.launch(args=["--no-sandbox"])
    for name, data in cases.items():
        errs = []
        page = browser.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=1)
        page.on("console", lambda msg, e=errs: e.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc, e=errs: e.append(str(exc)))
        html = ig._build_html(data)
        page.set_content(html, wait_until="networkidle")
        page.wait_for_timeout(150)
        m = page.evaluate(MEASURE)
        if m.get("noChar"):
            # 診断導線（キャラ無し）: 描画されており横溢れしないこと。
            ok = (m["rendered"] >= 2) and (m["overflowRight"] <= 1601) and not errs
            print(f"[{'PASS' if ok else 'FAIL'}] LAYOUT {name} (no-char): "
                  f"rendered={m['rendered']} scrollW={m['overflowRight']} errs={errs[:1]}")
            if not ok:
                fails += 1
            page.close()
            continue
        # 不変条件: 本文の最右端 ≤ キャラ列の左端（重なりゼロ）。さらにcardは横にあふれない。
        ok = (m["maxRight"] <= m["colLeft"] + 0.5) and (m["overflowRight"] <= 1601)
        print(f"[{'PASS' if ok else 'FAIL'}] LAYOUT {name}: "
              f"maxRight={m['maxRight']:.0f} colLeft={m['colLeft']:.0f} "
              f"gap={m['gap']}px worst={m['worst']} scrollW={m['overflowRight']}")
        if not ok:
            fails += 1
        page.close()
    browser.close()

print(f"\n==== LAYOUT: {len(cases)-fails}/{len(cases)} PASS ====")
sys.exit(1 if fails else 0)
