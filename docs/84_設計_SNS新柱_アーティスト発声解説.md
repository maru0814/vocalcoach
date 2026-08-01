# 84. 設計 — SNS新柱「アーティスト発声解説」(artist_analysis)

- 作成: 2026-08-01（sns-strategist 戦略決定 → growth-operator 実装）
- 関連: docs/25（X投稿フォーマット研究）/ docs/29（有料自動化・計測）/ docs/12（事実忠実性）
- 対象: `scripts/sns_autopost/`（themes.py / generate_and_post.py / infographic.py / images.py / expert_review.py）

## 1. 背景と決定

- 既存ローテはネタ被りが構造的に発生していた（TIPS弾倉8本に対し tip 枠が週7、逆張りは3本、診断導線はほぼ同一フック）。
- 運用実感として**アーティスト実名入りの投稿はインプレが伸びやすい**（運用者観察）。既存の実名ポリシー（声タイプ系は `themes.artists_for()` の実名を必ず本文に載せる）とも一致する。
- 決定: 新柱 **artist_analysis（アーティスト発声解説）** を追加する。
  「有名アーティストの歌声のヒミツを発声の仕組みから分解 → その声質は8タイプだと【◯◯】→ あなたはどのタイプ？」の流れで**声タイプ診断へ誘導**する。

## 2. 投稿の型（2部構成）

| 部 | 内容 |
| --- | --- |
| 本投稿（hook） | アーティスト実名＋意外な着眼点の問い（例:「LiSAさん、あれだけ叫んで聞こえるのに声が枯れないのはなぜ？」）。答えは書かず「分解はリプに置いた」案内で止める |
| 自己リプ（body） | 発声の仕組みの分解（番号付き①②③・推定の作法）＋ 末尾に診断ブリッジ「この声質はソラの8タイプ診断だと【◯◯】系。あなたの声は15秒でAIが判定（プロフィールから無料）」 |

- URLは本文にもリプにも入れない（`POST_LINK=0` 方針を踏襲）。誘導はプロフィール固定。
- リプ乞い禁止・誇大禁止は既存方針のまま。

## 3. 安全ガード（この型の追加ルール）

1. **推定の作法（事実忠実性 / docs/12 準拠）**: 本人の声帯を測定したわけではないため、断定しない。
   「〜に聞こえます」「音源からの推定です」を必ず含める。
2. **リスペクト一択**: 貶し・他アーティストとの優劣比較は禁止（expert_review で reject）。解説は常に「なぜ凄いか」の分解。
3. **歌手は正本リスト限定**: `themes.ARTISTS_BY_ID`（正本: `backend/app/coaching/voice_coach.py`）に載っている実名のみ使う。でっち上げ・勝手な追加は禁止。8タイプへのマッピングが既に存在するため診断導線が破綻しない。
4. **歌詞の引用禁止**（著作権）。曲名への言及も避け、歌声の特徴だけを扱う。

## 4. 弾倉（ARTIST_ANALYSIS）

運用者指定「ミセス・髭男など、日本の音楽シーンで現役で活躍している人」に基づき、正本リストから現役メジャー10名で初期弾倉を構成:

Mrs. GREEN APPLE / 藤原聡(髭男) / 米津玄師 / 藤井風 / LiSA / あいみょん / Aimer / Superfly / 幾田りら / Uru

- 各エントリは `{"artist", "type"(声タイプid), "hook", "body"}`。
- 着眼点は高音一辺倒にせず分散（換声点処理・脱力レガート・ハスキーの芯・弱声の輪郭・語りの距離感 など）。
- 発声解説の中身は voice-scientist（発声科学）監修を通す。

## 5. ローテ改定（tip枠から2転換）

| 曜日 | 昼(slot1) | 夜(slot2) | 朝(slot3) |
| --- | --- | --- | --- |
| 水 | tip → **artist_analysis** | self_type | contrarian |
| 土 | self_type | tip → **artist_analysis** | contrarian |

- tip は週7→5枠（弾倉8本との被り緩和も兼ねる）。同日3枠は引き続き必ず別型。
- 週2枠×弾倉10本 ≒ 5週で一周（TIPSの毎週一周から大幅改善）。

## 6. 実装ポイント

- `themes.py`: `ARTIST_ANALYSIS` 追加・`PILLARS`/`PILLARS_2ND` 改定・`template_post` / `gemini_twopart_prompt` 対応（実名保持・推定作法・比較禁止をプロンプトで強制）。
- `generate_and_post.py`: `--pillar` choices に追加。2部構成の生成経路（twopart）は既存のまま流用。
- `infographic.py`: `build_data` に artist_analysis 分岐（hook 1行目＝見出し＋ body の①②③を手順図解として描画。診断ブリッジ行は図解から除外）。
- `images.py`: 眉ラベル「歌声のヒミツ」・背景モチーフ追加（図解フォールバック用カード）。
- `expert_review.py`: 採点基準に artist_analysis 節を追加（実名・推定作法・リスペクト・診断ブリッジ）。

## 7. テスト（トレーサビリティ）

`scripts/sns_autopost/tests/qa_artist_analysis.py`（TC-AA01〜）:

- TC-AA01: ローテ — artist_analysis が週2枠・同日3スロットに型の重複なし
- TC-AA02: 弾倉 — 全エントリの artist が正本 `ARTISTS_BY_ID` の実名と一致・type が8タイプに存在
- TC-AA03: 安全 — hook/body に URL なし・貶し/優劣比較の禁止語なし・推定の作法（「推定」表記）あり
- TC-AA04: template_post — 2部構成（text にアーティスト実名・reply に①と診断ブリッジ）
- TC-AA05: 図解 — `build_data("artist_analysis", i)` が手順図解データを返し、診断ブリッジ行が図解に混入しない
- TC-AA06: 通し — `--pillar artist_analysis --dry-run` が rc=0（画像・ネットワーク無効）

## 8. 計測

- `posts_log.jsonl` の pillar=artist_analysis で型別インプレ/エンゲージを従来どおり計測（fetch_metrics.py は型名に依存しないため変更不要）。
- 4週間運用後、勝ち型判定（tip/診断導線との平均imp比較）を週次レポートで実施し、枠数の増減を判断する。
