"""ゼロベースFB（分析ターン）の月次コスト・キャップ（docs/43）。

ねらいはただ1つ: **当月の概算コストが上限(既定¥2000)に達しそうなら、強制的に止める。**
止まった分は呼び出し側がルールベースFBにフォールバックする（会話は止めない）。

厳密な課金額APIは無いため、1呼び出しの概算(JPY)を当月台帳に積み上げて判定する。
単一コンテナ前提。台帳はコンテナの永続volume配下(JSON)に置く。
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()


def _month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load() -> dict:
    """台帳を読む。月が変わっていればリセット(保存はしない)。"""
    try:
        with open(settings.llm_cost_ledger_path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    if d.get("month") != _month():
        d = {"month": _month(), "jpy": 0.0}
    return d


def _save(d: dict) -> None:
    path = settings.llm_cost_ledger_path
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as e:  # 台帳書き込み失敗で会話は止めない
        logger.warning("LLMコスト台帳の保存に失敗: %s", e)


def month_spend_jpy() -> float:
    """当月の概算コスト(JPY)。"""
    with _lock:
        return float(_load().get("jpy", 0.0))


def would_exceed(est_jpy: float) -> bool:
    """この1回(est_jpy)を実行すると当月上限を超えるなら True（＝止める）。

    上限が0以下なら無制限（常に False）。
    """
    cap = settings.llm_monthly_budget_jpy
    if cap is None or cap <= 0:
        return False
    with _lock:
        spend = float(_load().get("jpy", 0.0))
    if spend + est_jpy > cap:
        logger.warning("ゼロベースFB: 当月概算¥%.0f + 今回¥%.0f が上限¥%s を超えるため停止",
                       spend, est_jpy, cap)
        return True
    return False


def zero_base_allowed(is_premium_user: bool, est_jpy: float) -> bool:
    """zero-base FB を呼んでよいか（docs/52 FR-02）。

    有料ユーザーは月次上限の対象外（無料枠が予算を食っても課金者を格下げしない）。
    無料ユーザーは従来どおり上限で停止する。
    """
    if is_premium_user:
        return True
    return not would_exceed(est_jpy)


def month_calls() -> int:
    """当月の zero-base 呼び出し回数（週次の原価・粗利監視用。docs/52 FR-03）。"""
    with _lock:
        return int(_load().get("count", 0))


def record(est_jpy: float) -> None:
    """実際に1回呼んだ後、当月の概算コストに積む。上限に達したら当月1回だけ通知する。"""
    crossed = False
    with _lock:
        d = _load()
        d["jpy"] = round(float(d.get("jpy", 0.0)) + float(est_jpy), 2)
        d["count"] = int(d.get("count", 0)) + 1  # 呼び出し回数（監視用。docs/52 FR-03）
        cap = settings.llm_monthly_budget_jpy
        if cap and cap > 0 and d["jpy"] >= cap and not d.get("notified"):
            d["notified"] = True
            crossed = True
        _save(d)
        spend = d["jpy"]
    logger.info("ゼロベースFB: 当月概算 ¥%.0f / 上限 ¥%s", spend, settings.llm_monthly_budget_jpy)
    if crossed:
        _notify(f"🛑 ゼロベースFBの当月概算コストが上限¥{settings.llm_monthly_budget_jpy}に達しました"
                f"（概算¥{spend:.0f}）。以降は自動でルールベースFBに切り替えています。")


def notify_budget_reached_once() -> None:
    """すでに上限超過の状態で呼ばれた時、当月まだ通知していなければ1回だけ通知する。"""
    with _lock:
        d = _load()
        if d.get("notified"):
            return
        d["notified"] = True
        _save(d)
        spend = float(d.get("jpy", 0.0))
    _notify(f"🛑 ゼロベースFBの当月概算コストが上限¥{settings.llm_monthly_budget_jpy}に達しました"
            f"（概算¥{spend:.0f}）。以降は自動でルールベースFBに切り替えています。")


def _notify(text: str) -> None:
    """通知を送る。ログには必ず出し、Webhookが設定されていればPOSTする（失敗は無視）。"""
    logger.warning("【コスト上限通知】%s", text)
    url = settings.llm_budget_notify_webhook
    if not url:
        return
    try:
        import json as _json
        import urllib.request

        # text / content の両キーを入れて LINE/Slack/Discord どれでも拾えるようにする
        data = _json.dumps({"text": text, "content": text}).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:  # 通知失敗で本処理は止めない
        logger.warning("コスト上限通知の送信に失敗: %s", e)
