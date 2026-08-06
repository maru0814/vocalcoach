#!/usr/bin/env bash
# 本番VPSデプロイ（GitHub Actions から SSH 経由で実行される）。
#   main を取得 → 変更されたサービスだけ再ビルドして反映。
# 手元から手動で叩いてもよい:  bash scripts/deploy/remote_deploy.sh
# Last triggered: 2026-06-29
set -euo pipefail

REPO="/opt/vocalcoach"
cd "$REPO"

OLD="$(git rev-parse HEAD 2>/dev/null || echo "")"
git fetch origin main
git checkout main
git pull --ff-only origin main
NEW="$(git rev-parse HEAD)"
echo "Deploy: ${OLD:-（初回）} -> $NEW"

# 変更ファイル一覧（初回や不明時は ALL 扱い＝必要分を素直に再ビルド）
if [ -n "$OLD" ] && git cat-file -e "$OLD" 2>/dev/null; then
  CHANGED="$(git diff --name-only "$OLD" "$NEW")"
else
  CHANGED="ALL"
fi
echo "Changed files:"; printf '%s\n' "$CHANGED"
changed() { [ "$CHANGED" = "ALL" ] || printf '%s\n' "$CHANGED" | grep -q "$1"; }

cd "$REPO/docker"
DC=(docker compose -f docker-compose.prod.yml --env-file .env)

# sns（SNS文面のWebhook/生成）は軽いので毎回最新化。これが主な更新対象。
"${DC[@]}" up -d --build sns

# sns のスモークテスト（リード系QA。外部キー不要・一時dirで完結）。FAILならデプロイを止める。
"${DC[@]}" exec -T sns python tests/qa_leads.py > /tmp/qa_leads.out 2>&1 \
  || { echo "sns smoke test FAILED:"; tail -20 /tmp/qa_leads.out; exit 1; }
echo "sns smoke test: $(tail -1 /tmp/qa_leads.out)"

# backend / frontend は重いので、該当パスが変わったときだけ再ビルド。
if changed '^backend/';  then "${DC[@]}" up -d --build backend;  fi
if changed '^frontend/'; then "${DC[@]}" up -d --build frontend; fi

# Caddyfile は単一ファイルbind mountのため、変更時は作り直さないと反映されない。
if changed '^docker/Caddyfile'; then "${DC[@]}" up -d --force-recreate caddy; fi

# SNS運用cronの冪等登録（setup_approval.sh --cron と同じ一覧・同じ重複判定。
# 一覧を変えるときは両ファイルを揃えること）。deployユーザーのcrontabに入る。
C="cd $REPO/docker && docker compose -f docker-compose.prod.yml --env-file .env exec -T sns python"
CRON_LINES=(
  "0 12 * * * $C generate_and_post.py --slot 1 >> /var/log/sns_autopost.log 2>&1"
  "0 21 * * * $C generate_and_post.py --slot 2 >> /var/log/sns_autopost.log 2>&1"
  # 朝枠slot3（2026-08-01 運用者決定で1日3投稿化。MAX_POSTS_PER_DAY=3 は compose の environment で上書き）
  "0 8 * * * $C generate_and_post.py --slot 3 >> /var/log/sns_autopost.log 2>&1"
  "0 23 * * * $C fetch_metrics.py >> /var/log/sns_metrics.log 2>&1"
  # リード探索(lead_finder)/フォロバ計測(lead_metrics)は運用者指示で停止（2026-07-31。read課金削減）。
  # 行を消しても CRON_MARKER に残しているため、次回デプロイの再同期でVPSの既存行は自動撤去される。
  # 再開時はこの2行を戻す（setup_approval.sh の一覧も揃えること）:
  #   "0 10 * * * $C lead_finder.py >> /var/log/sns_leads.log 2>&1"
  #   "30 22 * * 0 $C lead_metrics.py >> /var/log/sns_leads.log 2>&1"
  # LP到達ファネルの週次集計（host実行。caddy/backendをexecするためコンテナ内ではなくhost python3で回す）
  "45 22 * * 0 python3 $REPO/scripts/ops/access_funnel.py >> /var/log/access_funnel.log 2>&1"
  # 毎朝の定例メトリクス（前日の訪問者/登録/ログインUUをLINE通知。host実行）
  "0 8 * * * python3 $REPO/scripts/ops/daily_metrics_line.py >> /var/log/daily_metrics.log 2>&1"
  # KPI日次スプレッドシート記録（docs/84。前日分をGoogle Sheetsにupsert。host実行）
  "10 8 * * * python3 $REPO/scripts/ops/kpi_daily_sheet.py >> /var/log/kpi_sheet.log 2>&1"
  # Geminiモデルの生存確認（docs/92。設定中のモデルを実APIで1回叩き、死んでいたらLINE通知。
  # 公式deprecationページにもmodels.listにも出ない「新規ユーザー利用不可＝404」を捕まえる唯一の手段。
  # 全部OKなら黙る。host実行）
  "20 8 * * * python3 $REPO/scripts/ops/gemini_model_healthcheck.py >> /var/log/gemini_health.log 2>&1"
)
# 再同期(reconcile): VocalCoach管理のcron行を「マーカー(=実行するjobスクリプト名)」で
# いったん全除去してから正典セットを書き直す。append専用だと、コマンド形態を変えた時
# （旧: .venv直 → 新: docker compose exec）に旧行が生きたcrontabに取り残され、文字列
# 完全一致の重複判定をすり抜けて同時刻に二重発火する（2026-07 実障害）。マーカー除去なら
# 過去のどの形態も一掃して収束するため、二重投稿・二重課金の再発を根から断てる。
CRON_MARKER='generate_and_post\.py|fetch_metrics\.py|lead_finder\.py|lead_metrics\.py|access_funnel\.py|daily_metrics_line\.py|kpi_daily_sheet\.py|gemini_model_healthcheck\.py'
CUR="$(crontab -l 2>/dev/null | grep -vE "$CRON_MARKER" || true)"
for l in "${CRON_LINES[@]}"; do
  CUR="$CUR"$'\n'"$l"
done
printf '%s\n' "$CUR" | sed '/^$/d' | crontab -
echo "cron 再同期: VocalCoach管理 ${#CRON_LINES[@]}件を正典化（旧形態の重複行があれば除去。確認: crontab -l）"

docker image prune -f >/dev/null 2>&1 || true
echo "Deploy done: $NEW"
