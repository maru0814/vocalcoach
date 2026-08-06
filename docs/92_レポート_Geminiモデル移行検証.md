# 92. レポート — Gemini モデル移行検証（llm_audio_model / llm_analysis_model）

- 作成日: 2026-08-05（2026-08-06 に docs/91 の調査結果を統合）
- 対象: `backend/app/core/config.py` の `llm_audio_model` / `llm_analysis_model`（いずれも `gemini-2.5-flash` 固定）
- 関連: **docs/91（会話エラー修正と課題継続コーチング＝チャット経路側の同根調査）**, docs/43（ゼロベース個人最適FB）, docs/66（会話モードと対話モデル格上げ）, docs/42（FB品質基準・単一ソース）
- 実測環境: `backend/.venv`（google-genai 2.7.0）＋本番と同じ `backend/app/coaching/llm.py` の関数を直接呼び出し。
  §0 の本番検証のみ本番コンテナ内（`docker exec docker-backend-1`）で本番APIキーを使用

---

## 0. 総括 — docs/91 と本レポートの統合結論（2026-08-06）

チャット経路（docs/91・PR #279）と音声/分析経路（本レポート）は、**独立に調査して同一の根本原因に到達した**。

### 共通の根本原因
**`-latest` エイリアスが指す実体が Gemini 3 系へ切り替わり、`thinking_budget=0` が
`400 INVALID_ARGUMENT` で拒否されるようになった。** 両調査とも実測で確認している。

| | docs/91（チャット経路） | 本レポート（音声/分析経路） |
| --- | --- | --- |
| 症状 | テキスト会話が全滅（無言でルールベースに落ちる） | 未発生（既定が 2.5 固定のため潜在） |
| 対処 | `_thinking_off()`＝2.5 系以外には `thinking_config` を送らない | `_safe_thinking_budget()` ＋ `_safe_max_tokens()` |
| 検証方法 | ユニットテスト（モック） | **実APIコール** |

### 統合して分かった2点

**(1) `_thinking_off()` だけでは音声パスは守れない。**
thinking をモデル既定に委ねると思考トークンが `max_output_tokens` を食い、本文が途中で切れる。
実測: `gemini-flash-latest`・`thinking_config` 非送信・`max=600` で `finish=MAX_TOKENS`。
`analyze_pronunciation` は `llm_max_tokens=400` を使っていたため被害が大きい（§2-3）。
→ 音声パスは「最小予算を明示 ＋ 出力枠の下限を確保」の2段構えが要る。判定関数自体は
`_supports_thinking_budget()` に一本化した（真実の источник を1つに保つ）。

**(2) PR #279 の固定先 `gemini-2.5-flash-lite` はすでに 404 で死んでいた。**
docs/91 の検証は `_thinking_off()` の戻り値を確認するユニットテストのみで、
**固定先のモデルが実在するかを実APIで確かめていなかった。** その結果、
`400 INVALID_ARGUMENT` を `404 NOT_FOUND` に置き換えただけで、症状（無言のフォールバック）は
変わらないまま本番へ出た。

### 本番の実測（2026-08-06・本番コンテナ内・本番APIキー）

```
llm_model      = gemini-flash-lite-latest   ← VPSの.envが上書き。コード既定の固定が効いていない
llm_chat_model = gemini-2.5-flash-lite      ← 上書き無し＝コード既定がそのまま＝404 で死亡
```

| モデル | 結果 | 実際の会話形での応答（N=5・履歴4ターン・max=400） |
| --- | --- | --- |
| `gemini-2.5-flash-lite` | **404 NOT_FOUND** | — |
| `gemini-flash-lite-latest` | OK | 1.0s / STOP 5-5 / 思考tok 0 |
| `gemini-3.5-flash-lite` | OK | 1.1s / STOP 5-5 / 思考tok 0 |
| `gemini-3.1-flash-lite` | OK | 1.3s / STOP 5-5 / 思考tok 0 |
| `gemini-2.5-flash` | OK | 1.8s / STOP 5-5 / 思考tok 0 |

`llm_chat_model` は `generate_reply()`（チャット返答）と `generate_coach_comment()`（録音FBの
コーチコメント）が使う。**したがって #279 デプロイ後もチャットは復旧していない。**

### 是正
`llm_model` / `llm_chat_model` を **`gemini-3.5-flash-lite`** に固定する。
現行実効値（エイリアス）との差は **+0.1秒**で体感差なし。docs/91 自身が
「エイリアスは 3.5 系に切り替わった」と結論しており、3.5-flash-lite への固定は
**乗り換えではなく、すでに動いている実体に正しい名前を付ける**操作にあたる。

なお lite ティアは短い会話プロンプトでは思考トークンを 0 しか使わないため、
`_thinking_off()` が `None` を返して thinking が既定ONになっても
`max_output_tokens=400` は枯渇しない（実測 STOP 5/5・本文最小113字）。チャット側に
`_safe_max_tokens()` 相当は不要。

### 再発防止として効いていないもの / 効くもの
- ❌ 公式 deprecation ページの監視（§1: 「新規ユーザー利用不可」を載せない）
- ❌ `models.list()` の存在確認（`gemini-2.0-flash` は list に載るが実呼び出しは 404）
- ❌ モックのみのユニットテスト（#279 がこれで死んだモデルを通した）
- ✅ **実APIへの疎通確認**（別PRで日次ヘルスチェックcronを追加予定）
- ✅ env 差し替えだけで載せ替えられる構造（本PR）

---

## 1. 発端の前提と、実際に確認できた事実

| 前提（依頼時） | 実際（2026-08-05 実測・公式ページ確認） |
| --- | --- |
| `gemini-2.5-flash` は 2026-10-16 に提供終了 | **誤り**。公式 deprecation ページ（2026-08-03 更新）の該当行は "No shutdown date announced"＝**終了日未定**。後継の指定も無い。10/16 は `gemini-2.5-flash-preview-*` 等の別行と混同した可能性 |
| 後継は `gemini-3.6-flash` | 公式に「`gemini-2.5-flash` の後継」とは書かれていない。ただし `gemini-2.5-flash-preview-05-20` / `-09-25` の Replacement 列は `gemini-3.6-flash`。実在し、当プロジェクトのAPIキーで利用可能 |
| `gemini-2.5-flash-lite` は公称終了日より前に死んでいる | **正しい**。実測で `404 NOT_FOUND … "no longer available to new users"` を再現。**そして公式ページ上ではこのモデルも "No shutdown date announced" のまま** |

### ここが本質的なリスク
公式 deprecation ページは「新規ユーザー利用不可」への切り替わりを**載せない**。
`gemini-2.5-flash-lite` がその実例で、ページ上は「終了日未定」のまま実際には 404 を返す。
**したがって「終了日が未定だから安全」という判断は成り立たない。** 監視源をページだけに置かず、
いつ死んでも env の差し替えだけで復旧できる状態を作っておくことが対策になる。

---

## 2. 実測結果

### 2-1. 依頼された組み合わせ（thinking_budget=512 × max_output_tokens=2048）

**受け付けられる。** 分析ターン（`generate_feedback`）の設定をそのまま `gemini-3.6-flash` に載せ替えて成功。

| モデル | finish_reason | 応答 | thinking トークン | 本文トークン |
| --- | --- | --- | --- | --- |
| `gemini-2.5-flash` | STOP | 5.8s | 509 | 225 |
| `gemini-3.6-flash` | STOP | 7.4s | 673 | 96 |

補足: `gemini-3.6-flash` では thinking トークンが指定予算（512）を**超える**（実測 673）。
予算は上限ではなくヒント。`max_output_tokens` は thinking より十分大きく取る必要があるという
既存コメントの前提は 3 系でも（むしろ強く）成り立つ。

### 2-2. 本当の地雷は `thinking_budget=0`（＝音声パス）

依頼では 512 を懸念していたが、**実際に壊れるのは音声パスの `thinking_budget=0`**。
`classify_register_audio` と `analyze_pronunciation` は両方とも 0 を送っている。

| モデル | tb=0 | tb=128 | tb=512 |
| --- | --- | --- | --- |
| `gemini-2.5-flash` | ✅ | ✅ | ✅ |
| `gemini-3.6-flash` | ❌ **400 INVALID_ARGUMENT** | ✅ | ✅ |
| `gemini-3.5-flash` | ✅ | ✅ | ✅ |
| `gemini-flash-latest`（エイリアス） | ❌ **400** | ✅ | ✅ |
| `gemini-flash-lite-latest`（エイリアス） | ❌ **400** | ✅ | ✅ |

音声パートの有無に関係なく再現する（テキストのみでも 400）。

### 2-3. thinking を切れない世代では出力枠が足りない

`gemini-3.6-flash` は thinking を無効化できないため、思考トークンが `max_output_tokens` を食う。
同一プロンプト・`thinking_budget=128` で N=8 反復:

| max_output_tokens | finish_reason | 本文の最小長 |
| --- | --- | --- |
| 400（＝`llm_max_tokens` の現行値） | **STOP 3 / MAX_TOKENS 5** | 12文字（途中で切れる） |
| 600（＝`classify_register_audio` の現行値） | STOP 8 / 8 | 97文字 |
| 1024 | STOP 8 / 8 | 97文字（thinking 実測最大 670） |

`analyze_pronunciation` は `llm_max_tokens=400` を使っているため、
**モデルIDだけを差し替えると 8回中5回、講評が数十文字で切れる**。600 も thinking 実測 670 に対して余裕が無い。
→ 安全側の下限を **1024** とする。

### 2-4. エイリアスを使わない理由（実証）

`gemini-flash-lite-latest` / `gemini-flash-latest` は、いずれも**すでに Gemini 3 系を指しており**
`thinking_budget=0` を拒否する。エイリアスは「指す実体が予告なく変わり、その時に
呼び出しパラメータの互換性まで壊れる」ことがこれで実証された。
バージョン固定なら、壊れるタイミングをこちら側の都合で選べる。

---

## 3. 実装（このPRの変更）

### 3-1. 設定の追加（`backend/app/core/config.py`）

| 設定 | 既定 | 意味 |
| --- | --- | --- |
| `llm_audio_thinking_budget` | `0` | 音声入力時の thinking 予算。0＝無効（2.5 系のみ可） |
| `llm_audio_max_tokens` | `1024` | 音声入力時の出力枠。従来は 600（声区）/ 400（発音）で分かれていた |

`llm_audio_model` / `llm_analysis_model` のコメントに、バージョン固定の理由・
終了予定日の現況・緊急時の env 差し替え手順を明記した。

### 3-2. モデル世代ガード（`backend/app/coaching/llm.py`）

```python
_THINKING_OFF_SUPPORTED = re.compile(r"^gemini-2\.\d", re.IGNORECASE)
_MIN_THINKING_BUDGET = 128
_MIN_MAX_TOKENS_WITH_THINKING = 1024

def _safe_thinking_budget(model, budget) -> int   # 0 指定を、切れない世代では 128 へ引き上げ
def _safe_max_tokens(model, budget, want) -> int  # 思考が有効なら出力枠の下限を確保
```

**狙いは「緊急時に再デプロイを待たないこと」**。
`LLM_AUDIO_MODEL=gemini-3.6-flash` を env に置いて再起動するだけで載せ替わる。
ガードが無いと、その差し替えは 400 で失敗し、コード修正＋デプロイが必要になる。

既定の `gemini-2.5-flash`（tb=0）では従来どおり thinking 無効・挙動もコストも変わらない。
回帰テスト: `backend/tests/test_llm_model_generation_guard.py`（17件）。

### 3-3. 既定モデルは据え置き

`gemini-2.5-flash` のまま。理由は §4 のとおり、音色の聞き分け品質の before/after 比較が未完のため。
コード側は env だけで載せ替えられる状態になっている。

---

## 4. 品質比較の状況

### 4-1. 分析ターン（`generate_feedback`）— 比較済み・実用差なし

合成音＋実測相当の Evidence Pack で N=6:

| モデル | 失敗 | `**bold**` 混入 | 見出し | 箇条書き | 絵文字 | 文字数中央値 | 応答中央値 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `gemini-2.5-flash` | 0/6 | 2/6 | 0/6 | 0/6 | 2/6 | 407 | 5.7s |
| `gemini-3.6-flash` | 0/6 | 0/6 | 0/6 | 0/6 | 1/6 | 304 | 8.3s |

両モデルとも `llm_analysis_timeout_sec=90` に対して十分速い。3.6 の方がやや短く、やや遅い。

> **別件で見つかった既存バグ**: `**bold**` が **現行の 2.5-flash で 6回中2回** 混入する。
> フロントは `whitespace-pre-wrap` の素テキスト描画（`frontend/src/components/coach/Bubbles.tsx`）なので、
> `**リップロール**` がそのまま画面に出る。`ANALYSIS_SYSTEM_PROMPT` は「Markdown**見出し**は使わない」としか
> 言っておらず、太字を禁じていない。3.6 への移行とは独立した問題。docs/42 の管轄。

### 4-2. 音色の聞き分け（`classify_register_audio`）— 実録音で比較済み

#### 使用サンプル
本番 `uploads/coach` にあった実録音1件（運用者自身のもの・本人確認済み）。
16.62秒 / 22.05kHz / F0中央値 437Hz・95パーセンタイル 864Hz（高音を含む歌唱）。
検証後、ローカルのコピーは削除した。

> 合成音では代用できないことが事前に判明している。
> `gemini-2.5-flash` は合成音に対し「裏声で歌われている」と息の混じり・厚みまで描写して断定した
> （**実在しない声区の作話**）。`gemini-3.6-flash` は「人間の歌声ではなくシンセサイザーによる電子音」と
> 正しく見抜き、判定自体を拒否した。

#### 自己一貫性（同一録音・同一プロンプトで N=8 反復・dsp_hint なし）

| モデル | 粗い判定（地声 / ミックス / 裏声） | 細かい寄り | 失敗 | 応答中央値 |
| --- | --- | --- | --- | --- |
| `gemini-2.5-flash` | **地声 3 / ミックス 5**（ブレる） | 裏声寄り 2・明示なし 3 | 0/8 | 2.9s |
| `gemini-3.6-flash` | **ミックス 8/8**（一致） | 地声寄り 4・裏声寄り 2・明示なし 2 | 0/8 | 9.6s |

**判定は落ちていない。むしろ粗い判定の安定性は明確に改善した。**
ユーザーが実際に聞くのは「これミックス？」という粗いレベルの問い（`coach.py` の声区判定経路）であり、
現行モデルはそこで 8回中3回 別の答えを返す。3.6 は 8/8 で一致した（別途 N=6 でも 6/6 ミックス）。

現行モデルは記述の内部矛盾も出た（同一音声に対し、ある回は「息が多めに混ざっている」、
別の回は「息の混じり方も少なく」）。3.6 は「息漏れが少ない・倍音が豊か・芯がある」で回をまたいで安定していた。

細かい寄り（地声寄り／裏声寄り）は 3.6 でもブレる。ここは元々プロンプトが
「1つに断定しづらければ『ミックス（地声寄り／裏声寄り）』でOK」と許容している範囲。

#### トレードオフ: レイテンシ

`classify_register_audio` は `backend/app/api/v1/endpoints/coach.py:254` で
**リクエスト処理中に同期呼び出しされ、待ち時間の打ち切りが無い**（録音FBのコーチコメントにある
`llm_coach_wait_sec` のような仕組みが無い）。したがって応答時間はそのままユーザーの待ち時間になる。

- `gemini-2.5-flash`: 中央値 2.9s（実測レンジ 2.3〜3.6s）
- `gemini-3.6-flash`: 中央値 9.6s（実測レンジ 4.8〜13.0s、別ランで最大 **33.9s**）

`llm_audio_timeout_sec = 60.0` の範囲には収まるので機能は壊れないが、
**声区を聞くたびに10秒前後、最悪30秒超待たされる**のは体験として無視できない。
既定を 3.6 に切り替えるなら、この経路にローディング表示か待ち時間の打ち切りを入れるべき。

---

## 5. 結論と残タスク

### 結論
`gemini-3.6-flash` への移行は**品質面では問題ない**（判定の安定性はむしろ向上）。
唯一の障害はレイテンシ（声区判定で 2.9s → 9.6s、最悪 33.9s）で、これは UI 側の手当てが要る。
そのため本PRでは**既定を `gemini-2.5-flash` のまま据え置き**、
「いつでも env 1行で載せ替えられる状態」を作るところまでを実装した。

### 残タスク
1. 声区判定経路（`coach.py:254`）のローディング表示／待ち時間の打ち切り → 対応後に既定を 3.6 へ切替
2. チャット経路（`llm_model` / `llm_chat_model` = `gemini-flash-lite-latest`）が
   `thinking_budget=0` を送っており 400 で拒否される件 → **別PRで最優先対応**。
   例外は握り潰されるため、ソラ先生のチャット返答が無言でルールベースに落ちている疑い。
   `gemini-flash-lite-latest` は thinking を有効化すると実測 45.7 秒で `llm_timeout_sec=20` を超えるため、
   モデルIDのバージョン固定込みの判断が要る（docs/66 の決定に触れる）
3. `**bold**` 混入（4-1 の注記）→ docs/42 側で扱う

## 6. 監視について

公式 deprecation ページは「新規ユーザー利用不可」を載せないため、単独の監視源としては不十分。
実質的な早期警戒は「本番から実際に呼んでみて 404/400 が返るか」しかない。
本PRのガードは、その事象が起きた後の**復旧を env 1行＋再起動に縮める**ことを目的としている。
