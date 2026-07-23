#!/usr/bin/env python3
"""動的OG画像用フォントのサブセット再生成（docs/28 §11）。

Noto Sans JP 可変フォントから Bold を静的化し、OG画像で使うグリフだけを
抜き出して `frontend/src/assets/og/NotoSansJP-OG-Bold.subset.ttf` を出力する。

含めるグリフ:
- ASCII 印字可能文字・ひらがな・カタカナ・記号類（固定の安全集合）
- voiceTypes.ts と OGルート（route.tsx）に現れる全ての非ASCII文字（漢字ここ由来）

OGカードの文言を変えた（＝新しい漢字を使った）ときは、このスクリプトを再実行して
サブセットを更新すること。豆腐（□）が出たらグリフ不足のサイン。

使い方:
  pip install fonttools brotli
  curl -sL -o /tmp/NotoSansJP-var.ttf \
    "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"
  python3 frontend/scripts/subset_og_font.py /tmp/NotoSansJP-var.ttf
"""
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

FRONTEND = Path(__file__).resolve().parent.parent
SOURCES = [
    FRONTEND / "src/components/voice/voiceTypes.ts",
    FRONTEND / "src/app/og/voice-type/[id]/route.tsx",
]
OUT = FRONTEND / "src/assets/og/NotoSansJP-OG-Bold.subset.ttf"

# 固定の安全集合（かな・記号は全部入れておく＝軽微な文言変更なら再生成不要）
FIXED = (
    [chr(c) for c in range(0x20, 0x7F)]          # ASCII 印字可能
    + [chr(c) for c in range(0x3041, 0x30FF + 1)]  # ひらがな・カタカナ・句読記号の一部
    + list("、。・ー「」『』（）【】！？：；…※→←↑↓〜～％◯○●◎")
)


def collect_chars() -> set[str]:
    chars = set(FIXED)
    for p in SOURCES:
        text = p.read_text(encoding="utf-8")
        chars.update(ch for ch in text if ord(ch) > 0x7F)
    return chars


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(f"usage: {sys.argv[0]} <NotoSansJP[wght].ttf>")
    src = sys.argv[1]

    font = TTFont(src)
    if "fvar" in font:
        instantiateVariableFont(font, {"wght": 700}, inplace=True)

    chars = collect_chars()
    options = subset.Options()
    options.layout_features = []  # OGは横書き単純描画のみ。合字・カーニング不要
    options.hinting = False
    options.name_IDs = ["*"]  # OFL: 著作権表記・フォント名は残す
    options.drop_tables += ["FFTM"]
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text="".join(sorted(chars)))
    subsetter.subset(font)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(OUT))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.1f} KB, {len(chars)} chars)")


if __name__ == "__main__":
    main()
