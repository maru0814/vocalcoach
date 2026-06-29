#!/usr/bin/env bash
# 動くグラデ背景を“一度だけ”ffmpegで焼く（assets/bg/motion.mp4）。
# 本番の動画生成(video_assembler)はこの動画を読んで切るだけ＝毎フレーム計算ゼロで軽い。
# 低スペックVPSでも、これ1回（数十秒〜数分）走らせれば、以後の毎日の生成は軽いまま“動く背景”になる。
#
# 使い方:
#   ./make_motion_bg.sh            # 既定35秒・ティール配色で生成
#   SECONDS_LEN=40 ./make_motion_bg.sh   # 長さを変える（動画の最大尺以上にすること）
#
# 配色を変えたいときは下の C0/C1/C2（0xRRGGBB）を編集。
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$DIR/assets/bg"
OUT="$OUT_DIR/motion.mp4"
mkdir -p "$OUT_DIR"

LEN="${SECONDS_LEN:-35}"        # 秒。動画の最大尺(34s)以上にしておく
C0="0x0B2E33"                   # ティール（声・水・呼吸の連想）
C1="0x06141A"                   # ほぼ黒
C2="0x10414A"                   # 明るめティール（グロー）

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "❌ ffmpeg が見つかりません。先に: sudo apt install -y ffmpeg" >&2
  exit 1
fi

echo "🎨 モーション背景を生成中（${LEN}秒）... 1回だけ・少し時間がかかります"

# ── Tier1: ドリフト(gradients) ＋ ゆっくりズーム(zoompan) ────────────
try1() {
  ffmpeg -y -f lavfi -i \
    "gradients=s=1080x1920:c0=${C0}:c1=${C1}:c2=${C2}:nb_colors=3:seed=11:speed=0.006:x0=200:y0=300:x1=900:y1=1700:duration=${LEN}:rate=30" \
    -vf "zoompan=z='min(1+0.0003*in,1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,format=yuv420p" \
    -t "${LEN}" "$OUT" 2>/dev/null
}

# ── Tier2: ドリフトのみ（zoompanが無い/失敗する環境向け）────────────
try2() {
  ffmpeg -y -f lavfi -i \
    "gradients=s=1080x1920:c0=${C0}:c1=${C1}:c2=${C2}:nb_colors=3:seed=11:speed=0.006:duration=${LEN}:rate=30" \
    -vf "format=yuv420p" -t "${LEN}" "$OUT" 2>/dev/null
}

# ── Tier3: ラジアルのドリフト（最小機能）──────────────────────────
try3() {
  ffmpeg -y -f lavfi -i \
    "gradients=s=1080x1920:c0=${C0}:c1=${C1}:type=radial:speed=0.004:duration=${LEN}:rate=30" \
    -vf "format=yuv420p" -t "${LEN}" "$OUT" 2>/dev/null
}

if try1; then
  echo "✅ 生成しました（ドリフト＋ズーム）: $OUT"
elif try2; then
  echo "✅ 生成しました（ドリフトのみ。zoompan非対応環境）: $OUT"
elif try3; then
  echo "✅ 生成しました（ラジアル簡易版）: $OUT"
else
  echo "⚠️ ffmpegのgradientsフィルタが使えませんでした。" >&2
  echo "   → 背景は静止グラデにフォールバックします（動画生成は問題なく動きます）。" >&2
  exit 1
fi

# サイズ確認
ls -lh "$OUT" 2>/dev/null | awk '{print "   サイズ:", $5}'
echo "これで video_assembler が自動でこの背景を使います（assets/bg/ を自動検出）。"
