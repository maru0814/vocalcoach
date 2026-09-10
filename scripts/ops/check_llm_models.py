#!/usr/bin/env python3
"""設定中の Gemini モデルが「今も実際に使えるか」を実呼び出しで確認する（docs/91）。

なぜ必要か:
  models.list() は退役したモデルも返し続ける。gemini-2.5-flash-lite は一覧に載ったまま
  generateContent が 404 "no longer available" を返す状態になり、チャットが黙って
  ルールベースに落ち続けた。一覧では気付けないので、必ず実際に叩いて確かめる。

確認するもの（アプリと同じ設定で呼ぶ）:
  - 応答が返るか（404/400/権限エラーを検出）
  - thinking_config の指定がそのモデルで受け付けられるか
  - max_output_tokens 以内に本文が収まるか（finish=MAX_TOKENS だと本文が空になる）
  - タイムアウト（settings.llm_timeout_sec）に間に合うか

実行:
    cd backend && ./.venv/bin/python ../scripts/ops/check_llm_models.py
  本番:
    docker exec docker-backend-1 python /app/../scripts/ops/check_llm_models.py
    （または docker exec -w /app docker-backend-1 python -c ... で settings を読ませる）

終了コード: 0=全て正常 / 1=1つ以上が使用不能（デプロイ後の確認やcronの失敗検知に使う）
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend"))

from app.coaching.llm import _thinking_off  # noqa: E402
from app.core.config import settings  # noqa: E402

# (設定名, モデル, 出力上限, タイムアウト秒, 用途)
TARGETS = [
    ("llm_chat_model", settings.llm_chat_model, settings.llm_max_tokens,
     settings.llm_timeout_sec, "チャット返答（ソラ先生の会話）"),
    ("llm_model", settings.llm_model, settings.llm_max_tokens,
     settings.llm_timeout_sec, "既定・有料の詳細レポート"),
    ("llm_audio_model", settings.llm_audio_model, settings.llm_max_tokens,
     settings.llm_audio_timeout_sec, "声区の聞き分け・発音解析（音声入力）"),
    ("llm_analysis_model", settings.llm_analysis_model, settings.llm_analysis_max_tokens,
     settings.llm_analysis_timeout_sec, "ゼロベースFB（録音の講評）"),
]

PROMPT = "「準備OK」とだけ短く返してください。"


def check(name, model, max_tokens, timeout, purpose):
    """1モデルを実呼び出しして (ok, 説明) を返す。"""
    from google import genai
    from google.genai import types

    if not model:
        return False, "モデル未設定"
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=int(timeout * 1000)),
    )
    cfg = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=0.3,
        thinking_config=_thinking_off(model),
    )
    t0 = time.time()
    try:
        resp = client.models.generate_content(model=model, contents=PROMPT, config=cfg)
    except Exception as e:  # noqa: BLE001 - 種別を問わず「使えない」として報告する
        return False, f"{time.time() - t0:.1f}s {type(e).__name__}: {str(e)[:120]}"
    el = time.time() - t0
    text = (resp.text or "").strip()
    finish = resp.candidates[0].finish_reason if resp.candidates else None
    if not text:
        # thinking が出力枠を食い潰すとここに落ちる（本文ゼロ＝実質使用不能）
        return False, f"{el:.1f}s 本文が空（finish={finish}）。出力上限{max_tokens}が不足の疑い"
    return True, f"{el:.1f}s 本文{len(text)}字 finish={finish}"


def main():
    if not settings.llm_enabled:
        print("LLM 無効（GEMINI_API_KEY 未設定）。確認をスキップします。")
        return 0
    ng = 0
    for name, model, max_tokens, timeout, purpose in TARGETS:
        ok, detail = check(name, model, max_tokens, timeout, purpose)
        if not ok:
            ng += 1
        print(f"[{'OK ' if ok else 'NG '}] {name}={model}  {detail}")
        if not ok:
            print(f"        ↳ 影響: {purpose} がルールベースにフォールバックします")
    if ng:
        print(f"\n{ng} 件のモデルが使用不能です。env の LLM_* と "
              f"backend/app/core/config.py の既定値を確認してください。")
    else:
        print("\n全モデル正常。")
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
