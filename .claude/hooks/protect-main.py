#!/usr/bin/env python3
"""PreToolUse ガード: main/master ブランチ上でのリポジトリ編集・コミットをブロックする。

背景: 複数の Claude Code セッションが同一 checkout を共有した際、
ブランチ混入事故（教授陣コミットが課金ブランチに混入）が実際に発生した。
claude.md の「並行作業（worktree・必須）」規律を仕組みとして強制する。
リポジトリ外のファイル（スクラッチパッド等）への書き込みは許可する。
"""
import json
import re
import subprocess
import sys


def git(args, cwd):
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=cwd
    ).stdout.strip()


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    cwd = data.get("cwd") or None
    tool = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    try:
        branch = git(["branch", "--show-current"], cwd)
        repo_root = git(["rev-parse", "--show-toplevel"], cwd)
    except Exception:
        return 0
    if branch not in ("main", "master") or not repo_root:
        return 0

    blocked = False
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        blocked = path.startswith(repo_root + "/") or path == repo_root
    elif tool == "Bash":
        cmd = tool_input.get("command", "")
        blocked = bool(
            re.search(r"\bgit\b[^\n;|&]*\b(commit|merge|rebase|cherry-pick)\b", cmd)
            or re.search(r"\bgit\s+push\b", cmd)
        )

    if blocked:
        print(
            f"ブロック: 現在 {branch} ブランチ上です。claude.md の規律により "
            "main 直編集・直コミットは禁止です。EnterWorktree でセッション専用 "
            "worktree に入るか、作業ブランチへ切り替えてから再実行してください。",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
