#!/usr/bin/env bash
# ソラ先生 TikTok自動化のcronを一括登録する（4本）。冪等: 何度実行しても重複しない。
#
#   毎日21:00  generate_and_render.py  動画生成→(承認通知 or 投稿)
#   毎日23:00  fetch_metrics.py         指標を取得して記録
#   毎週月09:00 trends.py --refresh      トレンド(尺/音源)を更新
#   毎週日22:00 weekly_report.py         週次レポートをLINE/Discordに送信
#
# 使い方:
#   ./install_cron.sh            # 登録（venvのpythonを自動検出）
#   PYTHON=/usr/bin/python3 ./install_cron.sh   # python を明示指定
#   ./install_cron.sh --remove   # 登録解除
#
# 注意: cronはサーバのタイムゾーンで動く。JSTで運用するなら `TZ` を crontab 冒頭か
#       システムに設定すること（例: サーバを Asia/Tokyo に）。
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAG="# vocalcoach-tiktok"

# python を決める: 環境変数 PYTHON > venv > system python3
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  if [ -x "$DIR/.venv/bin/python" ]; then
    PY="$DIR/.venv/bin/python"
  else
    PY="$(command -v python3 || command -v python)"
  fi
fi

mkdir -p "$DIR/out"

# 既存の vocalcoach-tiktok 行を一旦すべて除去
TMP="$(mktemp)"
crontab -l 2>/dev/null | grep -v "$TAG" > "$TMP" || true

if [ "${1:-}" = "--remove" ]; then
  crontab "$TMP"
  rm -f "$TMP"
  echo "🗑 vocalcoach-tiktok の cron を解除しました。"
  exit 0
fi

cat >> "$TMP" <<EOF
0 21 * * * cd $DIR && $PY generate_and_render.py >> $DIR/out/cron_generate.log 2>&1 $TAG
0 23 * * * cd $DIR && $PY fetch_metrics.py >> $DIR/out/cron_metrics.log 2>&1 $TAG
0 9 * * 1 cd $DIR && $PY trends.py --refresh >> $DIR/out/cron_trends.log 2>&1 $TAG
0 22 * * 0 cd $DIR && $PY weekly_report.py >> $DIR/out/cron_weekly.log 2>&1 $TAG
EOF

crontab "$TMP"
rm -f "$TMP"

echo "✅ cron を登録しました（python: $PY）:"
crontab -l | grep "$TAG" | sed 's/^/  /'
echo ""
echo "ログは $DIR/out/cron_*.log に出ます。"
echo "解除: ./install_cron.sh --remove"
