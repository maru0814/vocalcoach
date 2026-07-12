#!/usr/bin/env bash
# ソラ先生 eval ハーネスのラッパ。venv・cwd・PYTHONPATH を隠蔽し、1コマンドで呼べるようにする。
# 例:
#   bash scripts/soar_eval/run.sh --planted-all --out /abs/out.json
#   bash scripts/soar_eval/run.sh --batch-file /abs/scripts.json --out /abs/out.json
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # .../scripts/soar_eval
ROOT="$(cd "$HERE/../.." && pwd)"                       # worktree root
VENV="/Users/maru/dev/vocalcoach/backend/.venv/bin/python"
cd "$ROOT/backend"
PYTHONPATH="$ROOT" "$VENV" -m scripts.soar_eval.run_case "$@"
