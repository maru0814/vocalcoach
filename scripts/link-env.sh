#!/usr/bin/env bash
#
# link-env.sh — 母艦(メイン作業ツリー)の .env を現在の worktree に symlink する。
#
# 背景:
#   .env（Gemini/Stripe 等のキー入り）は .gitignore されているため、
#   origin/main から fresh 分岐する worktree には複製されない。
#   その結果、worktree に入るたびにキーを手で入れ直す手間が発生する。
#   このスクリプトは母艦の .env を「唯一の正」として参照する symlink を張り、その手間を消す。
#
# 使い方:
#   bash scripts/link-env.sh        # 現在の worktree にリンクを張る（冪等）
#   .githooks/post-checkout 経由で git worktree 作成時に自動実行もされる。
#
set -euo pipefail

# 現在地（この worktree のルート）
here="$(git rev-parse --show-toplevel)"
# 母艦(メイン作業ツリー) = git common dir(.git) の親
mother="$(cd "$(git rev-parse --git-common-dir)/.." && pwd)"

if [ "$here" = "$mother" ]; then
  echo "[link-env] ここが母艦なのでリンク不要: $here"
  exit 0
fi

# 母艦にあって .gitignore される秘密ファイル群（存在するものだけリンク）
files=(
  "backend/.env"
  "scripts/sns_autopost/.env"
  "docker/.env"
  "frontend/.env.local"
)

linked=0
for rel in "${files[@]}"; do
  src="$mother/$rel"
  dst="$here/$rel"
  [ -e "$src" ] || continue            # 母艦に無ければスキップ
  if [ -L "$dst" ] || [ -e "$dst" ]; then
    continue                           # 既にある（symlink でも実体でも）→ 触らない
  fi
  mkdir -p "$(dirname "$dst")"
  ln -s "$src" "$dst"
  echo "[link-env] linked  $rel  ->  $src"
  linked=$((linked + 1))
done

if [ "$linked" -eq 0 ]; then
  echo "[link-env] 新規リンクなし（既にリンク済み、または母艦に該当 .env なし）"
else
  echo "[link-env] $linked 件リンクしました"
fi
