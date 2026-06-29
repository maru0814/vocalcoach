# ソラ先生 TikTok自動生成＆投稿（Tips型＋検証型）

歌デモなしで全自動化できる2型に絞った、TikTok用の動画生成→投稿ツール。docs/34 準拠。
**キーが無ければ「絵コンテ＋台本」だけ作って止まる（安全）**／ffmpeg+moviepyがあればMP4まで描画。

> **⚠️ あなたが手でやる必要があること / 課金まわり → [運用チェックリスト](#運用チェックリストあなたがやること) を必ず読む。**
> コードは全自動だが、**アカウント開設・API申請・課金登録・声クローン**だけは人間（あなた）にしかできない。

## できること
- ✅ 台本の自動生成（曜日で `tip`/`demo` をローテ。Claudeがあれば口語リライト、無くてもテンプレ）。
- ✅ ナレーション（ElevenLabsで声クローン。無ければ無音で尺だけ確保＝字幕動画として成立）。
- ✅ 縦9:16のMP4組立（**実写B-rollをカットごとに切替＋クロスフェード＋CapCut風アニメ字幕＋キーワード黄色＋BGM**。検証型は画面録画を合成）。
  - 🎬 **実写B-roll**（紙芝居脱却の核）：`PEXELS_API_KEY` があればネタに合う縦型の実写素材を自動取得し、本文カットごとに切り替える（`broll.py`）。キー/ffmpegが無ければ背景にフォールバック。
  - 動き（背景のドリフト＋ズーム）は `make_motion_bg.sh` で**一度だけ**焼くので生成は軽いまま。
- ✅ TikTok Content Posting APIへ投稿（未承認/キー無なら生成のみ）。
- ✅ トレンドに寄せる（Research APIで伸びてる尺・音源を取得 → テンプレに反映）。
- ✅ 投稿前チェック通知（LINE/Discordでサムネ付き → `python approve.py` で承認）。
- ✅ 投稿後の指標集計（`fetch_metrics.py`）。
- ✅ 週次パフォーマンスレポート（フック別ランキング＋傾向考察をLINE/Discordで自動通知）。
- ✅ **実績フィードバックの自動チューニング**（`autotune.py`）。伸びたフックパターンのネタを次回から自動で優先。
- ✅ **cron一括登録**（`install_cron.sh`）。生成・指標・トレンド更新・週次レポートを1コマンドで仕込む。

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

# （任意・推奨）動く背景を一度だけ焼く。以後の生成はこの背景を使い回す（描画は軽いまま）:
./make_motion_bg.sh
# BGMを鳴らすなら assets/bgm/ にフリー音源を1つ置く（assets/bgm/README.md 参照）
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

## 自動化（cron。1コマンドで登録）
```bash
# venvのpythonを自動検出して4本のcronを冪等登録（JSTで動かすならサーバTZをAsia/Tokyoに）
./install_cron.sh
# 解除:
./install_cron.sh --remove
```
登録される内容:

| 時刻 | スクリプト | 役割 |
| --- | --- | --- |
| 毎日 21:00 | `generate_and_render.py` | 動画生成→(承認通知 or 投稿) |
| 毎日 23:00 | `fetch_metrics.py` | 指標を取得して記録 |
| 毎週月 09:00 | `trends.py --refresh` | トレンド(尺/音源)を更新 |
| 毎週日 22:00 | `weekly_report.py` | 週次レポートをLINE/Discordへ |

ログは `out/cron_*.log` に出る。手で書くなら `crontab -e` で同じ4行を追加してもよい。

## 改善ループ（自動）
投稿→指標→**自動チューニング**→次の生成、が人手なしで回る:
```
generate_and_render.py で投稿（hookを posts_log に記録）
        ↓
fetch_metrics.py で再生数・完了率を metrics_log に記録
        ↓
autotune.py が「伸びたフックパターン」を学習（次の generate が自動で寄せる）
        ↓
weekly_report.py が日曜にランキング＋傾向考察をLINEへ
```
手動で覗くコマンド:
```bash
python autotune.py                 # 今どのパターンを優先しているか（学習状況）
python analytics.py                # フック別ランキング＋傾向考察をターミナル表示
python analytics.py --notify       # 上記をLINE/Discordに送信
python weekly_report.py --dry-run  # 週次レポートのプレビュー（送信しない）
python fetch_metrics.py --manual   # アプリのインサイト値を手入力（完了率はこれが確実）
```
- `posts_log.jsonl`（投稿記録/hook付き）, `metrics_log.jsonl`（指標）はGit除外。
- 週次レポート内容: フック別ランキング / 週次トレンド(前週比) / **パターン別傾向考察** / 今週のアクション。
- **完了率(視聴完了率)はアルゴリズム最重要シグナル**だが Display API では取れない。`fetch_metrics.py --manual`
  でアプリのインサイト値を入れると、autotune と考察の精度が上がる（無くても再生数だけで動く）。

## 運用チェックリスト（あなたがやること）
コードは全自動だが、以下は**人間にしかできない**（アカウント/契約/課金/本人性）。上から順に。

| # | やること | 必須? | 課金 | 備考 |
| --- | --- | --- | --- | --- |
| 1 | サーバ(VPS等)に clone して `pip install -r requirements.txt`、`./install_cron.sh` | 必須 | VPS ¥0〜1,000/月 | 既存サーバがあれば¥0 |
| 2 | `.env.example` を `.env` にコピーして値を入れる | 必須 | ¥0 | キーはチャット/Gitに貼らない |
| 3 | TikTokアカウント作成 →（投稿API使うなら）Business化＋Content Posting API申請 | 投稿自動化に必須 | ¥0 | 承認に数日〜2週間。待つ間は `NOTIFY_BEFORE_POST=1`＋手動投稿で並行 |
| 4 | LINE Notify or Discord Webhook を発行して `.env` に | 推奨 | ¥0 | 承認通知・週次レポートの受け取り先 |
| 5 | ElevenLabsに登録→自分の声をクローン→`ELEVENLABS_VOICE_ID` を `.env` に | 任意 | **約$11/月** | 無ければ無音(字幕のみ動画)で成立 |
| 6 | AnthropicでAPIキー発行→`ANTHROPIC_API_KEY` を `.env` に | 任意 | **約$5/月** | 無ければテンプレ台本で動く |
| 7 | TikTok Research API申請→`TIKTOK_RESEARCH_TOKEN` を `.env` に | 任意 | ¥0(審査) | 無ければ `trends_seed.json` にフォールバック |
| 8 | （検証型を使うなら）`assets/demo_clips/` に画面録画を20〜30本 | 任意 | ¥0 | 今はTips型のみ運用なら不要 |
| 9 | 初回は `DRY_RUN=1` のまま `python generate_and_render.py` で出力を目視確認 | 必須 | ¥0 | 問題なければ `DRY_RUN=0` に |
| 10 | 毎日: LINE通知が来たら `python approve.py` で承認（NOTIFY_BEFORE_POST=1時） | 運用 | ¥0 | 全自動投稿にしたいなら `NOTIFY_BEFORE_POST=0` |

### 課金まとめ（最小→フル）
- **¥0運用**: ElevenLabs/Claudeなし。無音＋字幕動画＋テンプレ台本。既存サーバ利用。→ **月¥0**
- **推奨運用**: ElevenLabs($11) + Claude($5) + VPS(¥1,000)。声入り＋口語台本。→ **月 約¥2,500**
- いずれもキー未設定の部分は自動で縮退するので、**一部だけ課金**もできる（例: 声だけ入れてClaudeは無し）。

> 💳 **課金が発生するのは ElevenLabs と Claude API の2つだけ**（どちらも任意）。
> TikTok/LINE/Discord/Research API は無料。VPSは既存サーバがあれば¥0。

## 安全装置
- `DRY_RUN` 既定=1（うっかり投稿しない）。実運用で 0 に。
- `TIKTOK_PRIVACY=SELF_ONLY` 既定（最初は自分のみ公開で検証）。
- `MAX_POSTS_PER_DAY` で日次上限。MP4が作れなければ投稿しない。
- 効果を誇張する台本は出さない（プロンプトで禁止）。リンクは動画に貼れない前提でCTAは「プロフィールから」。
- キーは `.env`（Git除外）。**チャットやコミットに貼らない**。

## 構成
```
tiktok_autopost/
├── install_cron.sh         ← cron4本を一括登録（冪等。--remove で解除）
├── make_motion_bg.sh       ← 動く背景を一度だけ焼く（assets/bg/motion.mp4）。以後は使い回し
├── generate_and_render.py  ← オーケストレータ（cronで叩く）
├── broll.py                ← 実写B-roll取得（Pexels API→ffmpegで9:16正規化→キャッシュ）
├── themes.py               ← 型・ネタ・絵コンテ生成 + hook_pattern分類（Claudeプロンプト）
├── autotune.py             ← 実績フィードバック（勝ちパターンのネタを自動優先）
├── trends.py               ← トレンド検出（Research API / seed）
├── tts_producer.py         ← ナレーション（ElevenLabs / 無音）
├── video_assembler.py      ← MP4組立（moviepy / 絵コンテ縮退）
├── tiktok_poster.py        ← Content Posting API
├── notifier.py             ← LINE/Discord通知（投稿前チェック + 週次レポート）
├── approve.py              ← 投稿承認（NOTIFY_BEFORE_POST=1 時に使用）
├── fetch_metrics.py        ← 指標集計（API / --manual 手入力）
├── analytics.py            ← フック別ランキング＋パターン別傾向考察
├── weekly_report.py        ← 週次レポート送信（cron: 毎週日曜22時）
├── trends_seed.json        ← トレンドのフォールバック値（手動更新可）
└── assets/
    ├── demo_clips/         ← 検証型の画面録画プール（要収録・Git管理外）
    └── bgm/                ← ロイヤリティフリーBGM（Git管理外）
```
