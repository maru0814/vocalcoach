"""ゼロベースFB（分析ターン）のコスト・ガード（docs/43 §5）。

強モデル＋生音声は高価なので、コストが無尽蔵に膨らまないよう多層で上限をかける:
  1. 1ユーザー1日あたりの回数（インメモリ・単一コンテナ前提）
  2. 月次・全体の呼び出し回数（永続カウンタ＝ハードシーリング）
いずれか超過なら呼び出しを許可せず、呼び出し側はルールベースFBにフォールバックする。

厳密な課金額APIは無いため、月次USDは概算（calls × est）を台帳に積んで可視化する。
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone

from app.core.config import settings
from app.core.ratelimit import check_rate_limit

logger = logging.getLogger(__name__)

_lock = threading.Lock()


def _month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load() -> dict:
    """台帳を読む。月が変わっていればリセットした dict を返す（保存はしない）。"""
    try:
        with open(settings.llm_cost_ledger_path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    if d.get("month") != _month():
        d = {"month": _month(), "calls": 0, "usd": 0.0}
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


def month_usage() -> dict:
    """当月の {month, calls, usd}（レポート用）。"""
    with _lock:
        return _load()


def allow_analysis_call(user_key: str) -> bool:
    """日次(per-user)・月次(global)の上限内なら True。超過なら False（＝ルールベースFBへ）。"""
    # 月次グローバル上限（読み取りのみ。先に見て、超過なら日次スロットを消費しない）
    if settings.llm_analysis_monthly_call_cap > 0:
        with _lock:
            if _load().get("calls", 0) >= settings.llm_analysis_monthly_call_cap:
                logger.warning("ゼロベースFB: 月次上限(%s)に到達。ルールベースにフォールバック",
                               settings.llm_analysis_monthly_call_cap)
                return False
    # 日次 per-user 上限（インメモリ。True のときスロットを1つ消費する）
    if settings.llm_analysis_max_per_user_per_day > 0:
        if not check_rate_limit(
            f"zbfb:{user_key}", settings.llm_analysis_max_per_user_per_day, 86400
        ):
            return False
    return True


def record_analysis_call(est_usd: float | None = None) -> None:
    """実際に分析ターンを1回呼んだ後に積算する（月次 calls / usd）。"""
    with _lock:
        d = _load()
        d["calls"] = int(d.get("calls", 0)) + 1
        d["usd"] = round(
            float(d.get("usd", 0.0)) + float(
                est_usd if est_usd is not None else settings.llm_analysis_est_usd_per_call
            ),
            4,
        )
        _save(d)
        logger.info("ゼロベースFB: 当月 %s回 / 概算$%.2f", d["calls"], d["usd"])
