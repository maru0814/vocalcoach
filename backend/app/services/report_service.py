"""詳細添削レポートの生成（docs/31 FR-04, docs/33 §5）。

- 4セクション固定の構造化JSONを生成し evaluations.detailed_report に保存（再生成しない）。
- 反ハルシネーション（docs/12）: 解析に存在する事実（スコア・FB文）だけを根拠にさせ、
  時間帯は解析データに無い限り出力させない。LLM出力はPydanticで検証する。
- GEMINI_API_KEY 未設定・生成失敗時はスコアベースのルール生成にフォールバックする
  （課金機能で「生成できませんでした」を極力出さないため）。
"""
from __future__ import annotations

import logging
from datetime import datetime

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.evaluation import Evaluation

logger = logging.getLogger(__name__)

GENERATING = {"_status": "generating"}
FAILED = {"_status": "failed"}


# --- レポートのスキーマ（4セクション固定） ---

class ReportIssue(BaseModel):
    time: str | None = Field(None, description="例 '0:42-0:48'。解析に無ければ null")
    observation: str = Field(..., max_length=200)
    cause: str = Field(..., max_length=200)


class PracticeDay(BaseModel):
    day: int = Field(..., ge=1, le=7)
    title: str = Field(..., max_length=80)
    steps: str = Field(..., max_length=300)


class DetailedReport(BaseModel):
    issues: list[ReportIssue] = Field(..., max_length=5)
    priority: str = Field(..., max_length=300, description="最優先の改善ポイント1つ")
    practice_menu: list[PracticeDay] = Field(..., min_length=7, max_length=7)
    next_checks: list[str] = Field(..., min_length=1, max_length=3)


def report_status(ev: Evaluation | None) -> str:
    """'none' | 'generating' | 'failed' | 'ready'"""
    if ev is None or ev.detailed_report is None:
        return "none"
    st = ev.detailed_report.get("_status") if isinstance(ev.detailed_report, dict) else None
    if st == "generating":
        return "generating"
    if st == "failed":
        return "failed"
    return "ready"


def _facts(ev: Evaluation, title: str, note: str | None) -> str:
    return (
        f"曲名/タイトル: {title}\n"
        f"本人メモ: {note or '（なし）'}\n"
        f"音程スコア: {ev.pitch_score}/100\n"
        f"リズムスコア: {ev.rhythm_score}/100\n"
        f"表現スコア: {ev.expression_score}/100\n"
        f"総合スコア: {ev.total_score}/100\n"
        f"既存のフィードバック文: {ev.feedback_text}"
    )


def _llm_generate(facts: str) -> DetailedReport | None:
    """Geminiで構造化レポートを生成。失敗・検証NGなら None。"""
    if not settings.llm_enabled:
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception:
        return None
    prompt = (
        "あなたはAIボイストレーナー『ソラ先生』。以下の解析事実だけを根拠に、"
        "有料の詳細添削レポートをJSONで作成してください。\n\n"
        f"# 解析事実（これ以外の事実・数値・秒数を作らない）\n{facts}\n\n"
        "# 厳守事項\n"
        "- 解析事実に時間帯（秒数）の情報は無いので、issues[].time は必ず null にする。\n"
        "- スコアから言える傾向のみ述べ、断定できないことは『〜の可能性があります』と推定で書く。\n"
        "- 誇大表現禁止。やさしく、噛み砕いて、盛らない。\n"
        "- practice_menu は Day1〜7 の7件。1日10分で実行できる具体的な練習名と手順。\n"
        "- issues は弱い順に最大5件。priority は最優先の1点だけに絞る。\n"
        "- next_checks は次回録音時の確認点を3つ以内。\n"
    )
    try:
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(settings.llm_timeout_sec * 1000)),
        )
        resp = client.models.generate_content(
            model=settings.llm_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DetailedReport,
                max_output_tokens=2000,
                temperature=0.3,
            ),
        )
        return DetailedReport.model_validate_json(resp.text or "")
    except (ValidationError, Exception) as e:  # noqa: BLE001
        logger.warning("詳細レポートのLLM生成に失敗: %s", e)
        return None


def _rule_based(ev: Evaluation) -> DetailedReport:
    """LLM不使用時のフォールバック（スコアのみから機械的に構成）。"""
    axes = [
        ("音程", ev.pitch_score,
         "鼻歌で正確に取れるかを先に確認し、取れるなら発声側（支え）を整えましょう。"),
        ("リズム", ev.rhythm_score,
         "原曲を聴きながら手拍子→小声→歌唱の順で段階的に合わせましょう。"),
        ("表現", ev.expression_score,
         "サビ前後で強弱の差をつける箇所を1つ決めて練習しましょう。"),
    ]
    axes.sort(key=lambda a: a[1])
    issues = [
        ReportIssue(time=None,
                    observation=f"{name}スコアが {score}/100 です。",
                    cause="スコアからの推定です。詳細な箇所特定には次回の録音も参考にします。")
        for name, score, _ in axes if score < 80
    ] or [ReportIssue(time=None, observation="全体的に安定しています。", cause="主要3軸が80点以上のためです。")]
    weakest = axes[0]
    menu = [
        PracticeDay(day=1, title="リップロール30秒×3", steps="喉を温めるウォームアップ。歌う前に毎回行いましょう。"),
        PracticeDay(day=2, title=f"{weakest[0]}の集中練習", steps=weakest[2]),
        PracticeDay(day=3, title="ロングトーン10秒×5", steps="お腹に軽く力を残したまま、細く長く吐きます。"),
        PracticeDay(day=4, title=f"{weakest[0]}の集中練習（2回目）", steps=weakest[2]),
        PracticeDay(day=5, title="録音して聴き返す", steps="1コーラスだけ録音し、気になる箇所を3つメモします。"),
        PracticeDay(day=6, title="弱点箇所の部分練習", steps="Day5でメモした箇所だけをテンポを落として反復します。"),
        PracticeDay(day=7, title="通し歌唱＋録音", steps="通しで歌って録音し、ソラ先生の解析でスコアの変化を確認しましょう。"),
    ]
    return DetailedReport(
        issues=issues,
        priority=f"今週は「{weakest[0]}」だけに集中しましょう。{weakest[2]}",
        practice_menu=menu,
        next_checks=[f"{weakest[0]}スコアが {weakest[1]} から上がったか",
                     "歌い出しの音が安定しているか",
                     "息切れせずに歌い切れたか"][:3],
    )


def generate_report(db: Session, evaluation_id: int, title: str, note: str | None) -> None:
    """レポートを生成して保存（BackgroundTasksから呼ぶ。リトライ2回＝計3試行）。"""
    ev = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
    if ev is None or report_status(ev) == "ready":
        return
    facts = _facts(ev, title, note)
    report: DetailedReport | None = None
    for _ in range(3):
        report = _llm_generate(facts)
        if report:
            break
    if report is None:
        report = _rule_based(ev)  # LLM全滅でもルール生成で必ず返す
    ev.detailed_report = report.model_dump()
    ev.report_generated_at = datetime.utcnow()
    db.add(ev)
    db.commit()
