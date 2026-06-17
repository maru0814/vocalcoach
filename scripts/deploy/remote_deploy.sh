#!/usr/bin/env bash
# 本番VPSデプロイ（GitHub Actions から SSH 経由で実行される）。
#   main を取得 → 変更されたサービスだけ再ビルドして反映。
# 手元から手動で叩いてもよい:  bash scripts/deploy/remote_deploy.sh
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

# backend / frontend は重いので、該当パスが変わったときだけ再ビルド。
if changed '^backend/';  then "${DC[@]}" up -d --build backend;  fi
if changed '^frontend/'; then "${DC[@]}" up -d --build frontend; fi

# Caddyfile は単一ファイルbind mountのため、変更時は作り直さないと反映されない。
if changed '^docker/Caddyfile'; then "${DC[@]}" up -d --force-recreate caddy; fi

docker image prune -f >/dev/null 2>&1 || true
echo "Deploy done: $NEW"
