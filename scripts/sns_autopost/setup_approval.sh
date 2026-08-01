#!/usr/bin/env bash
# LINE承認フローのセットアップ（本番VPS上で実行する）。
#
# 使い方:
#   bash scripts/sns_autopost/setup_approval.sh --init   # 対話でキーを.envに書く（画面非表示）
#   bash scripts/sns_autopost/setup_approval.sh          # 起動＋疎通確認＋Webhook URL表示
#   bash scripts/sns_autopost/setup_approval.sh --test   # ＋テスト承認をLINEに送信
#   bash scripts/sns_autopost/setup_approval.sh --cron   # ＋生成/計測cronを登録
# フラグは併用可（例: --init --test --cron）。
#
# --init はキーを画面に表示せず（read -s）.env に直接書き込む。
# キー類はこのスクリプトの外（チャット等）に出さないこと。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOCKER_DIR="$REPO_ROOT/docker"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"
COMPOSE=(docker compose -f "$DOCKER_DIR/docker-compose.prod.yml" --env-file "$DOCKER_DIR/.env")

DO_INIT=0; DO_TEST=0; DO_CRON=0
for a in "$@"; do
  case "$a" in
    --init) DO_INIT=1 ;;
    --test) DO_TEST=1 ;;
    --cron) DO_CRON=1 ;;
    *) echo "不明な引数: $a" >&2; exit 2 ;;
  esac
done

err()  { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; }
ok()   { printf '\033[32m✓ %s\033[0m\n' "$*"; }
info() { printf '— %s\n' "$*"; }

getval() { grep -E "^$1=" "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true; }

# KEY=value を .env に追記/置換（コメントや他行は保持。値の特殊文字も安全）。
set_kv() {
  local key="$1" val="$2" tmp found=0 line
  tmp="$(mktemp)"
  if [ -f "$ENV_FILE" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
      if [[ "$line" == "$key="* ]]; then
        printf '%s=%s\n' "$key" "$val" >> "$tmp"; found=1
      else
        printf '%s\n' "$line" >> "$tmp"
      fi
    done < "$ENV_FILE"
  fi
  [ "$found" = 1 ] || printf '%s=%s\n' "$key" "$val" >> "$tmp"
  mv "$tmp" "$ENV_FILE"
}

# 秘密値を画面に出さずに読み取り、入力があれば .env に保存（空Enterは現状維持）。
prompt_secret() {
  local key="$1" label="$2" cur v state
  cur="$(getval "$key")"
  [ -n "$cur" ] && state="設定済み・Enterで維持" || state="未設定"
  printf '  %s [%s]: ' "$label" "$state"
  read -rs v; echo
  [ -n "$v" ] && { set_kv "$key" "$v"; ok "$key を保存"; } || true
}

# --- --init: 対話でキーを書き込む ---
if [ "$DO_INIT" = 1 ]; then
  if [ ! -f "$ENV_FILE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"; info ".env を新規作成（.env.example から）"
  fi
  echo "▼ キーを入力します（入力は画面に表示されません。空Enterで現状維持）"
  echo "  X（投稿用・OAuth1.0a）"
  prompt_secret X_API_KEY        "X_API_KEY（コンシューマーキー）"
  prompt_secret X_API_SECRET     "X_API_SECRET（コンシューマーシークレット）"
  prompt_secret X_ACCESS_TOKEN   "X_ACCESS_TOKEN（アクセストークン）"
  prompt_secret X_ACCESS_SECRET  "X_ACCESS_SECRET（アクセストークンシークレット）"
  echo "  LINE（承認通知用・Messaging API）"
  prompt_secret LINE_CHANNEL_ACCESS_TOKEN "LINE_CHANNEL_ACCESS_TOKEN（チャネルアクセストークン）"
  prompt_secret LINE_CHANNEL_SECRET       "LINE_CHANNEL_SECRET（チャネルシークレット）"
  echo "  Gemini（任意・文面AI生成。不要なら空Enter）"
  prompt_secret GEMINI_API_KEY   "GEMINI_API_KEY"
  # 承認フローを有効化する既定値を強制セット
  set_kv DRY_RUN 0
  set_kv APPROVAL_MODE 1
  [ -n "$(getval WEBHOOK_PORT)" ] || set_kv WEBHOOK_PORT 8088
  chmod 600 "$ENV_FILE" 2>/dev/null || true
  ok ".env を更新（DRY_RUN=0 / APPROVAL_MODE=1）"
  echo
fi

# --- .env チェック ---
[ -f "$ENV_FILE" ] || { err "$ENV_FILE がありません。先に --init で作成してください"; exit 1; }

MISSING=0
for k in LINE_CHANNEL_ACCESS_TOKEN LINE_CHANNEL_SECRET \
         X_API_KEY X_API_SECRET X_ACCESS_TOKEN X_ACCESS_SECRET; do
  if [ -z "$(getval "$k")" ]; then err "$k が未設定（$ENV_FILE）"; MISSING=1; else ok "$k OK"; fi
done
[ "$MISSING" = 0 ] || { err "未設定の値があります。--init で入力してください"; exit 1; }

[ "$(getval DRY_RUN)" = "0" ] || info "注意: DRY_RUN=0 にしないと承認しても実投稿されません"
APPROVAL_VAL="$(getval APPROVAL_MODE)"
[ "${APPROVAL_VAL:-1}" = "0" ] && info "注意: APPROVAL_MODE=0 だと承認を挟まず即投稿になります" || true

DOMAIN="$(grep -E '^DOMAIN=' "$DOCKER_DIR/.env" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
[ -n "$DOMAIN" ] || { err "docker/.env に DOMAIN がありません"; exit 1; }

# --- 起動 ---
info "sns / caddy をビルド＆起動します..."
"${COMPOSE[@]}" up -d --build sns caddy

# --- 疎通確認 ---
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
echo "    → 返信で届く userId を控える（次の --test で入力できます）"
echo

# --- --cron ---
if [ "$DO_CRON" = 1 ]; then
  C="cd $DOCKER_DIR && docker compose -f docker-compose.prod.yml --env-file .env exec -T sns python"
  # 注意: この一覧を変えたら scripts/deploy/remote_deploy.sh の同じ一覧も揃えること
  # （デプロイ時にも冪等登録される。文字列完全一致で重複判定するため）。
  declare -a LINES=(
    "0 12 * * * $C generate_and_post.py --slot 1 >> /var/log/sns_autopost.log 2>&1"
    "0 21 * * * $C generate_and_post.py --slot 2 >> /var/log/sns_autopost.log 2>&1"
    # 朝枠slot3（2026-08-01 運用者決定で1日3投稿化）
    "0 8 * * * $C generate_and_post.py --slot 3 >> /var/log/sns_autopost.log 2>&1"
    "0 23 * * * $C fetch_metrics.py >> /var/log/sns_metrics.log 2>&1"
    # リード探索(lead_finder)/フォロバ計測(lead_metrics)は運用者指示で停止（2026-07-31。read課金削減）。
    # CRON_MARKER には残す＝再同期で既存行が自動撤去される。再開時は remote_deploy.sh と揃えて2行を戻す:
    #   "0 10 * * * $C lead_finder.py >> /var/log/sns_leads.log 2>&1"
    #   "30 22 * * 0 $C lead_metrics.py >> /var/log/sns_leads.log 2>&1"
    # LP到達ファネルの週次集計（host実行。caddy/backendをexecするためコンテナ内ではなくhost python3で回す）
    "45 22 * * 0 python3 $REPO_ROOT/scripts/ops/access_funnel.py >> /var/log/access_funnel.log 2>&1"
    # 毎朝の定例メトリクス（前日の訪問者/登録/ログインUUをLINE通知。host実行）
    "0 8 * * * python3 $REPO_ROOT/scripts/ops/daily_metrics_line.py >> /var/log/daily_metrics.log 2>&1"
    # KPI日次スプレッドシート記録（docs/84。前日分をGoogle Sheetsにupsert。host実行）
    "10 8 * * * python3 $REPO_ROOT/scripts/ops/kpi_daily_sheet.py >> /var/log/kpi_sheet.log 2>&1"
  )
  # 再同期(reconcile): 追加専用だとコマンド形態変更時（旧 .venv直 → 新 docker compose exec）に
  # 旧行が生きたcrontabに残って同時刻で二重発火する（2026-07 実障害）。管理行をマーカー
  # （jobスクリプト名）で一掃してから正典セットを書き直し、収束させる。remote_deploy.sh と同一方針。
  CRON_MARKER='generate_and_post\.py|fetch_metrics\.py|lead_finder\.py|lead_metrics\.py|access_funnel\.py|daily_metrics_line\.py|kpi_daily_sheet\.py'
  CUR="$(crontab -l 2>/dev/null | grep -vE "$CRON_MARKER" || true)"
  for l in "${LINES[@]}"; do
    CUR="$CUR"$'\n'"$l"; ok "cron 正典: $l"
  done
  printf '%s\n' "$CUR" | sed '/^$/d' | crontab -
  ok "cron 再同期完了（旧形態の重複行があれば除去。確認: crontab -l）"
fi

# --- --test ---
if [ "$DO_TEST" = 1 ]; then
  UIDV="$(getval LINE_OPERATOR_USER_ID)"
  if [ -z "$UIDV" ]; then
    printf '  LINEのuserId（友だち追加でBotが返したUで始まる文字列）を貼ってください: '
    read -r UIDV
    [ -n "$UIDV" ] || { err "userId が空です。中止します"; exit 1; }
    set_kv LINE_OPERATOR_USER_ID "$UIDV"
    ok "LINE_OPERATOR_USER_ID を保存"
    info "反映のため sns を再起動..."
    "${COMPOSE[@]}" up -d sns
    sleep 2
  fi
  info "テスト承認メッセージをLINEに送信..."
  "${COMPOSE[@]}" exec -T sns python - <<'PY'
import approval_queue as q, line_client
d = q.enqueue("tip", 1, "🔧 これはテスト投稿です。承認/却下ボタンの動作確認用。", None, False)
sent, info = line_client.push_approval(d)
print("push:", sent, info, "draft_id:", d["id"])
PY
  ok "送信しました。LINEで [🗑却下] を押して動作確認してください（テスト本文なので却下推奨）"
fi
