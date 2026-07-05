# 57. Claude Code セットアップ監査レポート（実装結果込み・確定版）

> 実施日: 2026-07-02〜03 / 実装PR: #129（`claude/code-setup-audit-fvbxek`）
> read-only 診断 → 承認後に P1〜P8 を実装。本書が監査の正本。

## 0. スキャン範囲の前提

監査セッションはリモートコンテナ上で実行されたため、**監査できたのは vocalcoach リポジトリの Claude Code 構成のみ**。実PC全体（`~/` 階層・`~/.claude/CLAUDE.md`・ユーザースコープ設定・MCP）は観測不能であり、§6 の自己診断コマンドを実PCで実行した結果をもって別途監査する（未実施）。

## 1. 監査時点の現状マップ

| 要素 | 監査時点 | 実装後 |
| --- | --- | --- |
| プロジェクト claude.md | 10.4KB・ディスパッチ規則が3重複 | 単一の対応表に統合 |
| `.claude/settings.json` | SessionStart 長文リマインドのみ | 変更なし（提案を `settings.proposed.json` に同梱・**ユーザー適用待ち**） |
| `.claude/skills/` | 19スキル。vocal-trainer が40KB単一ファイル | vocal-trainer を中核18KB＋`references/` 6分冊に分割 |
| `.claude/agents/` | なし | 教授陣6名を read-only サブエージェント化 |
| `.claude/hooks/` | なし | `protect-main.py`（main直編集・直コミットブロック）新設 |
| `.claude/rules/` / output-styles / MCP | なし | 見送り（移すべき常時ロード内容が現状なく効果薄） |
| permissions | なし（毎回プロンプト） | 提案のみ（`settings.proposed.json`） |
| CI | deploy.yml のみ（品質ゲート不在） | `ci.yml` 新設（backend pytest＋frontend tsc） |
| docs 連番 | 35・44 が各2ファイルで衝突 | 35_本番運用メモ→55、44_レポート→56 に改番。※その後 PR #126（ブランドリニューアル）が独立に 55 を採番したため、本番運用メモは 60 へ再改番（55=ブランドリニューアル仕様が正） |

スキル description（発火トリガー）は総じて高品質（具体的発話例・役割境界明記）で手入れ不要と判定。`scripts/sns_autopost/` の自動化資産・deploy.yml の設計（concurrency 直列化・docs 除外）も良好。

## 2. 問題点マトリクス（影響度×工数）と実施結果

| # | 問題 | 影響 | 工数 | 結果 |
| --- | --- | --- | --- | --- |
| P1 | vocal-trainer 40KB 常時ロード | 高 | 中 | ✅ 分割（欠落ゼロを機械照合） |
| P2 | worktree 規律がフック未強制（混入事故の前歴あり） | 高 | 低 | ✅ フック作成・検証済み。**有効化はユーザー適用待ち** |
| P3 | claude.md 3重複＋SessionStart 4重目 | 中 | 低 | ✅ 統合。SessionStart 短縮は提案に同梱 |
| P4 | CI に品質ゲートなし | 高 | 中 | ✅ ci.yml 新設（初回実行 green 確認済み） |
| P5 | permissions 未設定 | 中 | 低 | △ 提案のみ（自己書換ガードのため） |
| P6 | 教授陣がサブエージェント未活用 | 中 | 中 | ✅ agents 化（skill は残置・段階移行） |
| P7 | skill に model/effort 指定なし | 中 | 低 | △ skills では未サポートのため agents 側のみ `model: inherit` |
| P8 | docs 連番重複（35/44） | 中 | 低 | ✅ 改番＋参照更新 |
| P9 | 整形フックなし | 低 | 低 | 見送り（ruff/prettier がプロジェクト依存に無い） |
| P10 | MCP 未導入 | 低 | 中 | 見送り（必要になった時に判断） |

## 3. 実装の要点

### 3-1. vocal-trainer の progressive disclosure（P1）
`SKILL.md` は中核（役割・ループ概要・出力フォーマット・原則・キャラ・口調）のみ。実務詳細は該当場面で Read する:

| 分冊 | いつ読む |
| --- | --- |
| `references/coaching-loop.md` | セッション開始時（Phase A〜E手順・解析コマンド） |
| `references/taxonomy.md` | Phase B の課題特定時 |
| `references/mix-voice.md` | ミックス・高音・換声点の依頼時 |
| `references/voice-science.md` | 解剖学的説明・練習設計時 |
| `references/analysis-guide.md` | 解析JSON解釈時 |
| `references/cover-analysis.md` | 原曲ありカバーFB時 |

### 3-2. main 保護フック（P2）
`.claude/hooks/protect-main.py`: main/master 上での「リポジトリ内 Edit/Write」「git commit/merge/rebase/cherry-pick/push」を exit 2 でブロックし worktree へ誘導。リポジトリ外（スクラッチパッド等）は許可。一時クローンで4ケース検証済み。**`.claude/settings.proposed.json` を `.claude/settings.json` に貼るまで発動しない。**

### 3-3. CI（P4）
PR/main push で backend-tests（pytest）＋ frontend-typecheck（tsc --noEmit）。`frontend/package-lock.json` は package.json と不整合で `npm ci` 不能だったため同期済み。

## 4. 発見した既存バグ（要・仕様裁定）

`tests/test_conversational_fb.py::ConversationalFBContract::test_chat_llm_down_honest_not_hedge` が **main 時点で失敗**。LLM停止時は正直フォールバック（「うまく言葉が出せませんでした」）を返す契約（docs/51 系）に対し、実装はルールエンジンが実質回答（ジッター40cents＋練習継続の案内）を返す。

- ci.yml では理由コメント付きで deselect 済み
- **裁定候補**: (a) 契約どおり正直フォールバックに修正（backend-engineer）／(b) ルールベース回答を正としてテスト側を更新（qa-engineer＋docs/51 改定）
- 裁定後、ci.yml の deselect を必ず外す

## 5. 残タスク（ユーザー側アクション）

1. **settings 適用**: `.claude/settings.proposed.json` の内容を確認し `.claude/settings.json` へ貼り付け（permissions.allow＋短縮 SessionStart＋PreToolUse 登録）
2. **§4 の仕様裁定** → pdm/qa へディスパッチ
3. **実PC監査**: §6 のコマンドを実PCで実行し、出力を Claude Code セッションに貼る → PC全体の理想ディレクトリ構成・移動マッピング・ユーザースコープ設定の監査を確定

## 6. 実PC用・自己診断コマンド集（read-only）

```bash
# (1) 開発フォルダの散らかり・階層・命名（中身は開かない）
find ~ -maxdepth 3 -type d \( -name node_modules -o -name .git \) -prune -o -type d -print 2>/dev/null | head -200

# (2) Gitリポジトリの所在（プロジェクト置き場の一貫性）
find ~ -maxdepth 4 -name .git -type d 2>/dev/null | sed 's#/.git##'

# (3) ユーザー全体の Claude Code 設定
ls -la ~/.claude 2>/dev/null
wc -l ~/.claude/CLAUDE.md 2>/dev/null
cat ~/.claude/settings.json 2>/dev/null
cat ~/.claude.json 2>/dev/null | python3 -c 'import sys,json;d=json.load(sys.stdin);print("projects:",list(d.get("projects",{}).keys()));print("mcpServers:",list(d.get("mcpServers",{}).keys()))'

# (4) 全プロジェクトの CLAUDE.md とサイズ（重複・肥大の把握）
find ~ -maxdepth 4 -iname 'claude.md' -not -path '*/node_modules/*' -exec wc -l {} + 2>/dev/null

# (5) 各プロジェクトの .claude 構成の有無
find ~ -maxdepth 4 -type d -name .claude -not -path '*/node_modules/*' 2>/dev/null

# (6) MCP設定の所在
find ~ -maxdepth 4 -name '.mcp.json' -not -path '*/node_modules/*' 2>/dev/null

# (7) Downloads/Desktop の放置量（散らかり指標。件数だけ）
ls ~/Downloads 2>/dev/null | wc -l ; ls ~/Desktop 2>/dev/null | wc -l
```

### 実PC側の理想構成（§6 実行後に突き合わせて確定する雛形）
```
~/
├─ dev/                # 開発ルートを1つに集約（リポジトリは kebab-case・階層2段まで）
│  ├─ vocalcoach/
│  └─ sandbox/         # 実験・使い捨て
├─ .claude/
│  ├─ CLAUDE.md        # 全プロジェクト共通の普遍ルールのみ
│  └─ settings.json    # ユーザースコープ permissions / hooks / model 既定
├─ Documents/          # プロジェクト外の成果物
└─ Downloads/          # 定期的に空にする
```

## 7. 振り分け原則（今後の配置判断の基準）

**常時必要＝claude.md／手続き＝skill（＋references分冊）／強制したい＝hook・permissions／隔離したい＝subagent（agents/）**
