#!/usr/bin/env bash
# LINE承認フローのセットアップ（本番VPS上で実行する）。
#
# やること:
#   1) scripts/sns_autopost/.env の必須値が埋まっているかチェック
#   2) sns（Webhook常駐）/ caddy コンテナをビルド＆起動
#   3) https://<DOMAIN>/sns/healthz で疎通確認 → LINEに設定するWebhook URLを表示
#   --test : LINE_OPERATOR_USER_ID 設定後、テスト承認メッセージをLINEに送る
#   --cron : 生成（昼12/夜21）＋計測（23時）の cron を登録（重複は入れない）
#
# 使い方:
#   bash scripts/sns_autopost/setup_approval.sh            # 起動＋疎通確認
#   bash scripts/sns_autopost/setup_approval.sh --test     # ＋テスト送信
#   bash scripts/sns_autopost/setup_approval.sh --cron     # ＋cron登録
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKER_DIR="$REPO_ROOT/docker"
ENV_FILE="$SCRIPT_DIR/.env"
COMPOSE=(docker compose -f "$DOCKER_DIR/docker-compose.prod.yml" --env-file "$DOCKER_DIR/.env")

DO_TEST=0; DO_CRON=0
for a in "$@"; do
  case "$a" in
    --test) DO_TEST=1 ;;
    --cron) DO_CRON=1 ;;
    *) echo "不明な引数: $a" >&2; exit 2 ;;
  esac
done

err()  { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; }
ok()   { printf '\033[32m✓ %s\033[0m\n' "$*"; }
info() { printf '— %s\n' "$*"; }

getval() { grep -E "^$1=" "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true; }

# --- 1) .env チェック ---
[ -f "$ENV_FILE" ] || { err "$ENV_FILE がありません。.env.example をコピーして値を入れてください"; exit 1; }

MISSING=0
for k in LINE_CHANNEL_ACCESS_TOKEN LINE_CHANNEL_SECRET \
         X_API_KEY X_API_SECRET X_ACCESS_TOKEN X_ACCESS_SECRET; do
  if [ -z "$(getval "$k")" ]; then err "$k が未設定（$ENV_FILE）"; MISSING=1; else ok "$k OK"; fi
done
[ "$MISSING" = 0 ] || { err "未設定の値を埋めてから再実行してください"; exit 1; }

[ "$(getval DRY_RUN)" = "0" ] || info "注意: DRY_RUN=0 にしないと承認しても実投稿されません"
APPROVAL_VAL="$(getval APPROVAL_MODE)"
[ "${APPROVAL_VAL:-1}" = "0" ] && info "注意: APPROVAL_MODE=0 だと承認を挟まず即投稿になります" || true

DOMAIN="$(grep -E '^DOMAIN=' "$DOCKER_DIR/.env" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
[ -n "$DOMAIN" ] || { err "docker/.env に DOMAIN がありません"; exit 1; }

# --- 2) 起動 ---
info "sns / caddy をビルド＆起動します..."
"${COMPOSE[@]}" up -d --build sns caddy

# --- 3) 疎通確認 ---
info "疎通確認: https://$DOMAIN/sns/healthz"
sleep 3
if curl -fsS "https://$DOMAIN/sns/healthz" >/dev/null 2>&1; then
  ok "Webhookサーバ稼働中"
else
  err "疎通NG。ログ確認: ${COMPOSE[*]} logs --tail=50 sns caddy"
fi

echo
ok "次はLINE Developersコンソールで設定:"
echo "    Webhook URL:  https://$DOMAIN/sns/line/webhook"
echo "    →「Webhookの利用」をON → 公式アカウントを友だち追加"
echo "    → 返信で届く userId を $ENV_FILE の LINE_OPERATOR_USER_ID に設定"
echo "    → このスクリプトを --test 付きで再実行して動作確認"
echo

# --- --cron ---
if [ "$DO_CRON" = 1 ]; then
  C="cd $DOCKER_DIR && docker compose -f docker-compose.prod.yml --env-file .env exec -T sns python"
  declare -a LINES=(
    "0 12 * * * $C generate_and_post.py --slot 1 >> /var/log/sns_autopost.log 2>&1"
    "0 21 * * * $C generate_and_post.py --slot 2 >> /var/log/sns_autopost.log 2>&1"
    "0 23 * * * $C fetch_metrics.py >> /var/log/sns_metrics.log 2>&1"
  )
  CUR="$(crontab -l 2>/dev/null || true)"
  for l in "${LINES[@]}"; do
    if printf '%s\n' "$CUR" | grep -Fq "$l"; then
      info "cron 既存: $l"
    else
      CUR="$CUR"$'\n'"$l"; ok "cron 追加: $l"
    fi
  done
  printf '%s\n' "$CUR" | sed '/^$/d' | crontab -
  ok "cron 登録完了（確認: crontab -l）"
fi

# --- --test ---
if [ "$DO_TEST" = 1 ]; then
  UIDV="$(getval LINE_OPERATOR_USER_ID)"
  [ -n "$UIDV" ] || { err "LINE_OPERATOR_USER_ID が未設定。友だち追加で取得して設定してください"; exit 1; }
  info "テスト承認メッセージをLINEに送信..."
  "${COMPOSE[@]}" exec -T sns python - <<'PY'
import approval_queue as q, line_client
d = q.enqueue("tip", 1, "🔧 これはテスト投稿です。承認/却下ボタンの動作確認用。", None, False)
sent, info = line_client.push_approval(d)
print("push:", sent, info, "draft_id:", d["id"])
PY
  ok "送信しました。LINEで [🗑却下] を押して動作確認してください（テスト本文なので却下推奨）"
fi
