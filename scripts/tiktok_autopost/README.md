# ソラ先生 TikTok自動生成＆投稿（Tips型＋検証型）

歌デモなしで全自動化できる2型に絞った、TikTok用の動画生成→投稿ツール。docs/34 準拠。
**キーが無ければ「絵コンテ＋台本」だけ作って止まる（安全）**／ffmpeg+moviepyがあればMP4まで描画。

## できること
- ✅ 台本の自動生成（曜日で `tip`/`demo` をローテ。Claudeがあれば口語リライト、無くてもテンプレ）。
- ✅ ナレーション（ElevenLabsで声クローン。無ければ無音で尺だけ確保＝字幕動画として成立）。
- ✅ 縦9:16のMP4組立（背景＋テロップ＋検証型は画面録画クリップを合成）。
- ✅ TikTok Content Posting APIへ投稿（未承認/キー無なら生成のみ）。
- ✅ トレンドに寄せる（Research APIで伸びてる尺・音源を取得 → テンプレに反映）。
- ✅ 投稿前チェック通知（LINE/Discordでサムネ付き → `python approve.py` で承認）。
- ✅ 投稿後の指標集計（`fetch_metrics.py`）→ 勝ち型に `themes.PILLARS` を寄せる。
- ✅ 週次パフォーマンスレポート（フック別ランキング＋週次トレンドをLINE/Discordで自動通知）。

## 2つの型（docs/34 §2）
| 型 | 中身 | 素材 |
| --- | --- | --- |
| `tip` | Tips型テキスト動画（フック→本文→CTA）。テロップ＋ナレーション＋字幕 | 生成のみ・素材ゼロ |
| `demo` | 検証型（フック→アプリ画面録画→結果→CTA） | `assets/demo_clips/` の事前収録プールを使い回す |

## 「流行りをパクる」の実装方針（正直に）
`trends.py` が寄せるのは**構造（尺・テロップ密度・トレンド音源ID）**であって、他者の映像・音声そのものではない。
他人の動画を再アップロードしない（IP配慮）。やるのは「今どの構造が伸びてるか」を数値で掴み、
自前テンプレのパラメータに落とすこと。音源は Commercial Sounds Library 等、商用利用が許諾されたものを使う。

## セットアップ
```bash
cd scripts/tiktok_autopost
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# MP4描画する場合はOSにffmpegと日本語フォントも入れる:
#   sudo apt install ffmpeg fonts-noto-cjk
cp .env.example .env      # 値を入れる（.env はGitに入らない）
```

## 使い方
```bash
# まず安全確認（投稿せず生成だけ。DRY_RUN=1 が既定）
python generate_and_render.py                 # 今日の曜日の型で1本
python generate_and_render.py --pillar tip    # 型を指定（tip/demo）
python generate_and_render.py --refresh-trends # Research APIでトレンド更新してから生成

# 生成物は out/ に出る:
#   - moviepy+ffmpeg+フォントあり → YYYY-MM-DD_tip.mp4
#   - 無い環境 → YYYY-MM-DD_tip.storyboard.json と .script.txt（手動編集できる絵コンテ）

# 実投稿（.env で DRY_RUN=0 かつ TIKTOK_ACCESS_TOKEN 設定済み）
DRY_RUN=0 python generate_and_render.py
```

## 一度だけの準備（docs/34）
1. `assets/demo_clips/` にアプリ操作の画面録画を20〜30本（タグ命名は同フォルダREADME）。
2. TikTok Business Account 開設＋ Content Posting API 申請（承認に数日〜2週間）。承認待ちは手動投稿で並行。
3. （任意）ElevenLabsで自分の声をクローン → `ELEVENLABS_VOICE_ID` を `.env` に。

## 自動化（cron。19–23時が良い）
```bash
# crontab -e（JST）。パスは環境に合わせて変更。
VENV=/opt/vocalcoach/scripts/tiktok_autopost/.venv/bin/python
DIR=/opt/vocalcoach/scripts/tiktok_autopost

# 毎日21時: 動画生成＆投稿（NOTIFY_BEFORE_POST=1 なら通知で止まる）
0 21 * * * cd $DIR && $VENV generate_and_render.py >> /var/log/tiktok_autopost.log 2>&1

# 毎日23時: 指標を取得してメトリクスに記録（完了率は手動 --manual 推奨）
0 23 * * * cd $DIR && $VENV fetch_metrics.py >> /var/log/tiktok_metrics.log 2>&1

# 毎週月曜9時: Research APIでトレンド更新（API枠節約のため週1回）
0 9 * * 1 cd $DIR && $VENV trends.py --refresh >> /var/log/tiktok_trends.log 2>&1

# 毎週日曜22時: フック別ランキング＋週次トレンドをLINE/Discordに送信
0 22 * * 0 cd $DIR && $VENV weekly_report.py >> /var/log/tiktok_weekly_report.log 2>&1
```

## 改善ループ
```bash
python fetch_metrics.py            # API取得（要トークン）
python fetch_metrics.py --manual   # アプリのインサイト値を手入力（完了率はこちらが確実）
python analytics.py                # フック別ランキング＋週次トレンドをターミナルに表示
python analytics.py --notify       # 上記をLINE/Discordに送信
python weekly_report.py --dry-run  # 週次レポートのプレビュー（送信しない）
```
- `posts_log.jsonl`（投稿記録）, `metrics_log.jsonl`（指標）はGit除外。
- 平均再生・**視聴完了率**が高い型を `themes.PILLARS` で増やす（docs/34 §3 週次レビュー）。
- 週次レポートには「フック別ランキング」「週次再生トレンド（前週比）」「改善ヒント」が含まれる。

## コスト（docs/34）
| 項目 | 目安 |
| --- | --- |
| ElevenLabs（声クローン） | $11/月 |
| Claude API（台本60本） | ~$5/月 |
| VPS（cron実行） | ¥1,000/月（既存サーバなら0） |
| **合計** | **約¥2,500/月** |

## 安全装置
- `DRY_RUN` 既定=1（うっかり投稿しない）。実運用で 0 に。
- `TIKTOK_PRIVACY=SELF_ONLY` 既定（最初は自分のみ公開で検証）。
- `MAX_POSTS_PER_DAY` で日次上限。MP4が作れなければ投稿しない。
- 効果を誇張する台本は出さない（プロンプトで禁止）。リンクは動画に貼れない前提でCTAは「プロフィールから」。
- キーは `.env`（Git除外）。**チャットやコミットに貼らない**。

## 構成
```
tiktok_autopost/
├── generate_and_render.py  ← オーケストレータ（cronで叩く）
├── themes.py               ← 型・ネタ・絵コンテ生成（Claudeプロンプト）
├── trends.py               ← トレンド検出（Research API / seed）
├── tts_producer.py         ← ナレーション（ElevenLabs / 無音）
├── video_assembler.py      ← MP4組立（moviepy / 絵コンテ縮退）
├── tiktok_poster.py        ← Content Posting API
├── notifier.py             ← LINE/Discord通知（投稿前チェック + 週次レポート）
├── approve.py              ← 投稿承認（NOTIFY_BEFORE_POST=1 時に使用）
├── fetch_metrics.py        ← 指標集計（API / --manual 手入力）
├── analytics.py            ← フック別ランキング＋週次トレンド分析
├── weekly_report.py        ← 週次レポート送信（cron: 毎週日曜22時）
├── trends_seed.json        ← トレンドのフォールバック値（手動更新可）
└── assets/
    ├── demo_clips/         ← 検証型の画面録画プール（要収録・Git管理外）
    └── bgm/                ← ロイヤリティフリーBGM（Git管理外）
```
