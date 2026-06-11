# ソラ先生 SNS自動投稿（X / 旧Twitter）

1日2回（昼・夜）、自動でXに投稿する最小ツール。**Geminiが無くてもテンプレで動く**／**キーが無ければ本文表示だけ（安全）**。

## できること / 料金（正直に。詳細 docs/29）
- ✅ **Xへの自動投稿**（従量課金）。**2026年の単価: URLなし投稿 $0.015／URLあり投稿 $0.20／自分の投稿の読取 $0.001**。月額下限なし。
- ✅ **インプレ計測**: `fetch_metrics.py` が投稿のインプレ/エンゲージを取得→型別に集計→**勝ち型に寄せる**。
- ✅ 文面の自動生成（Gemini。無くてもテンプレ）。
- 💴 **月2000円以内の方針**: ①**本文/リプにURLを入れない**（$0.20回避＆reach優先。リンクはプロフィール固定で誘導＝`POST_LINK=0` 既定）②1日2投稿（`MAX_POSTS_PER_DAY=2`）③`MONTHLY_COST_CAP_USD` で上限ガード。これでAPIは月¥450前後（投稿60件＋計測）。
- 🚀 **X Premium（Web版が安い）** に入るとインプレ約6倍。これが最大の費用対効果（docs/29）。
- ⚠️ Instagram/TikTok の完全自動投稿は制限が厳しく非推奨（半自動）。

## セットアップ（5分）
```bash
cd scripts/sns_autopost
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # 値を入れる（.env はGitに入らない）
```

### Xのキー発行
1. https://developer.x.com で開発者登録 → アプリ作成
2. アプリの **User authentication settings** で権限を **Read and write** に
3. **API Key/Secret**（Consumer）と **Access Token/Secret** を発行し `.env` に貼る

## 使い方
```bash
# まずは安全確認（投稿せず本文だけ表示。DRY_RUN=1 が既定）
python generate_and_post.py

# 型を指定して確認（docs/25 の「伸びる型」に対応）
python generate_and_post.py --pillar self_type   # 自己分類フック（診断誘導）
python generate_and_post.py --pillar empathy     # 共感あるある（リンクなし）
python generate_and_post.py --pillar tip         # 番号付きTips
python generate_and_post.py --pillar contrarian  # 逆張り
python generate_and_post.py --pillar question    # 問いかけ（リプ狙い）
python generate_and_post.py --pillar voice_type  # 声タイプ図鑑
python generate_and_post.py --pillar visual      # ビジュアル誘導

# 実投稿（.env で DRY_RUN=0 かつ Xキー設定済み）
DRY_RUN=0 python generate_and_post.py
```

> **本文にもリプにもURLを入れない**のが既定（`POST_LINK=0`）。リンクは**プロフィール固定**で誘導（reach減＆$0.20課金を回避）。
> empathy / question はリンクなしの純粋な会話狙い。**自動は種まき、初速の点火は手動リプで**。

## インプレ計測（改善ループ）
```bash
python fetch_metrics.py            # 直近投稿のインプレ/エンゲージ取得＋型別サマリ
```
- 投稿IDは `posts_log.jsonl`、メトリクスは `metrics_log.jsonl` に記録（Git除外）。
- 出力の「平均imp / eng率」が高い型を `themes.py` の `PILLARS` で増やす。

## 自動化（VPSのcron。夜20–22時が最良）
```bash
# crontab -e（JST）
# 昼12時に1本目（slot1=情報/診断導線）
0 12 * * * cd /opt/vocalcoach/scripts/sns_autopost && ./.venv/bin/python generate_and_post.py --slot 1 >> /var/log/sns_autopost.log 2>&1
# 夜21時に2本目（slot2=会話/リプ型。ゴールデンタイム）
0 21 * * * cd /opt/vocalcoach/scripts/sns_autopost && ./.venv/bin/python generate_and_post.py --slot 2 >> /var/log/sns_autopost.log 2>&1
# 毎日23時にインプレ計測
0 23 * * * cd /opt/vocalcoach/scripts/sns_autopost && ./.venv/bin/python fetch_metrics.py >> /var/log/sns_metrics.log 2>&1
```
- 昼枠(slot1)の型は `themes.py` の `PILLARS`（月=自己分類/火=Tips/水=声タイプ図鑑/木=共感/金=逆張り/土=問いかけ/日=ビジュアル）。
- 夜枠(slot2)は `PILLARS_2ND`（会話・共感型を厚め＝docs/29 §3 リプ至上主義）。同日の昼とは必ず別の型になる。
- 1日2投稿なので `.env` の `MAX_POSTS_PER_DAY=2` を忘れず設定する。

## 安全装置 / 予算ガード
- `DRY_RUN` 既定=1（うっかり投稿しない）。
- `POST_LINK=0`（URL投稿しない＝$0.20回避）／`MAX_POSTS_PER_DAY`／`MONTHLY_COST_CAP_USD` で**月額を物理的に制限**。
- 本文にURLが混入した生成文はテンプレに自動差し替え。
- キーは `.env`（Git除外）。**チャットやコミットに貼らない**。

## 安全装置
- `DRY_RUN` 既定=1（うっかり投稿しない）。実運用で 0 にする。
- Geminiが盛った/URL欠落の文を返したらテンプレに自動差し替え。
- キーは `.env`（Git除外）。**チャットやコミットに貼らない**。
