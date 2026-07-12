# soar_eval — ソラ先生 会話品質 自動検査ハーネス

ソラ先生（`backend/app/coaching/llm.generate_reply`）の会話返答を**本物の Gemini で大量実行**し、
ハルシネーション／過剰拒否／萎え／多ターンの噛み合いなどを検出する。設計は `docs/64`（テスト計画）。

## 構成
| ファイル | 役割 |
| --- | --- |
| `states.py` | 状態バンク（多様な解析JSON）と許可事実の算出 |
| `cases_*.py` | ケース生成: planted(罠) / freeform(敵対) / goodfaith(善意) / multiturn(多ターン) |
| `driver.py` | 会話スクリプトを本物 `generate_reply` で逐次実行（ペーシング・空返答リトライ） |
| `checkers.py` | 決定論チェッカ（秒数/音名/数値/URL/否定ガード 等） |
| `run_case.py` | CLI: ケース実行 → transcript + 決定論所見を JSON 出力 |
| `run.sh` | venv・cwd・PYTHONPATH を隠蔽するラッパ |
| `mech_metrics.py` | 決定論の機械計測（再録音要求/動画オファー/反復/突き放し率）。**ラン間比較で最も信頼できる** |
| `report.py` / `build_*_report.py` | 各種レポート生成（Claude不要） |
| `recheck.py` | Gemini再実行せず既存transcriptにチェッカを再適用 |

## 実行
```bash
# 被検（Gemini）は backend/.env の GEMINI_API_KEY を使う
bash scripts/soar_eval/run.sh --planted-all --out /tmp/out.json          # 罠を全実行
bash scripts/soar_eval/run.sh --batch-file <bank.json> --out /tmp/out.json # 任意バンク

# コーパス生成（バンク作成）
python -m scripts.soar_eval.cases_multiturn > /tmp/bank.json  # backend/ を cwd に

# 機械計測 before/after
python -m scripts.soar_eval.mech_metrics --before A.json B.json --after C.json --out-json m.json
```
LLM審査（回答性・萎え・逃げの意味判定）は Claude サブエージェント／Workflow で実施し、
`reports/judge_out/*.json` に per-case で書き出す（セッション上限で落ちても transcript から回収可能）。

## 重要な運用知見
- **審査は self-critique か敵対的裏取りを必ず通す**（無しだと萎え率が過大に出る。61%→27%の実績）。
- **ラン間のClaude審査ペア比較はノイズが大きい**。行動変化の判定は機械計測（`mech_metrics.py`）を主にする。
- 実行（Gemini）と審査（Claude）は分離する。Gemini実行はセッション上限の外。

## これまでの主な発見と対策
- 過剰拒否（否定して手元事実へ橋渡しせず突き放す）→ `docs/42` 橋渡し義務・再録音要求禁止（機械計測で再録音 -71%）。
- 多ターンの自己発言追従 → `docs/65` 提案済み練習の文脈注入（自己発言違反 5/18→1/18）。
- 動画オファーの同一会話連発 → 履歴からオファー済みを検出し文脈注入。
