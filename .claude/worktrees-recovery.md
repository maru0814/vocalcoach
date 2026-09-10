# worktree 復元マップ（2026-09-10 の棚卸し）

`.claude/worktrees/` にあった作業ツリー9本を削除した。**中身は全部ブランチに残っている。**
未保存だった編集は削除前に `wip(...)` コミットとして各ブランチへ退避済み。

| 旧worktree名 | ブランチ | 先頭コミット | 中身 |
| --- | --- | --- | --- |
| admiring-sinoussi-bfc76f | `claude/kind-grothendieck-a669d7` | 7d24d80 | 会話モードのLLM・config改修＋モデル設定テスト |
| docs106-followup | `worktree-docs106-followup` | 72d2d0d | FB品質ルールの来歴トレーサビリティ＋設計書107/108 |
| eager-greider-fc3edf | `claude/vigorous-matsumoto-9df5a7` | 0a4ef67 | Geminiモデル世代ガード（env差し替えで後継モデルへ） |
| nice-easley-8a5a16 | `rescue/pwa-sw-fix` | fa6be76 | PWAのSWが古い画面を配り続ける欠陥の修正 |
| shindan-copy-talk-not-sing | `worktree-shindan-copy-talk-not-sing` | 9bf82d0 | 診断LPの文言を「歌う」→「話す」基準へ置換 |
| stop-lead-finder-cron | `worktree-stop-lead-finder-cron` | 0641324 | lead-finder cron停止の運用メモ＋デプロイ手順整理 |
| voice-type-page-theming | `worktree-voice-type-page-theming` | c67cb4e | 声タイプ8種のプロフィール文・UI・設計書72/73 |
| vtype-article-bg | `worktree-vtype-article-bg` | 28507ae | 声タイプ記事の背景表示の微調整 |
| welcome-email | `newsletter-optin` | e66d5a7 | メルマガ基盤（オプトイン・配信停止・冪等一斉送信） |
| vocalcoach-tenyen（~/dev直下にあった） | `feat/tenyen-caddy-route` | b53a2a0 | TenYenのLINE承認Webhook向けCaddyルート（**main にマージ済み**） |

## 戻したいとき

```bash
git worktree add .claude/worktrees/<名前> <ブランチ>
```

## 注意

退避した作業は 2026-07-20〜08-14 のもので、当時から main は 7〜91コミット進んでいる。
そのまま main に載せられる保証はない。**保管であってマージではない。**
取り込むときは origin/main に rebase して衝突を解消すること。
