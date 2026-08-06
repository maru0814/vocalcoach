#!/usr/bin/env python3
# 設定中の Gemini モデルが「実際に呼べるか」を毎日1回確かめ、死んでいたら LINE で叩き起こす。
#
# なぜ要るか（docs/92 §0）:
#   Google はモデルを公称の終了日より先に「新規ユーザー利用不可」へ切り替えることがあり、
#   その時 404 NOT_FOUND を返す。この事象は公式 deprecation ページに載らず、
#   models.list() にも残ったままなので、外形的な監視では気付けない。
#   実際に 2026-08 に gemini-2.5-flash-lite がこれで死に、ソラ先生のチャット返答が
#   「無言でルールベースに落ちる」状態のまま数日気付かれなかった（例外は握り潰される）。
#   唯一効く検知手段は「本番のキーで実際に1回呼んでみる」こと。それをやるのがこのスクリプト。
#
# 何を見るか:
#   backend コンテナの実効設定（llm_model / llm_chat_model / llm_audio_model /
#   llm_analysis_model）を読み、重複を除いた各モデルへ最小のテキスト生成を1回投げる。
#   1つでも失敗したら LINE 通知。全部OKなら黙る（毎日鳴らさない）。
#
# 実行: python3 /opt/vocalcoach/scripts/ops/gemini_model_healthcheck.py
#   DRY_RUN=1  … 判定だけ表示し LINE 送信しない
#   FORCE_NOTIFY=1 … 全部OKでも通知する（配線の確認用）
# cron 登録は scripts/deploy/remote_deploy.sh（毎朝 8:20 JST。サーバTZ=JST）。
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
UTC = timezone.utc
JSONL = "/var/log/gemini_model_health.jsonl"
BACKEND = "docker-backend-1"
SNS = "docker-sns-1"

# backend コンテナ内で実行する検査本体。設定の実効値をそのまま使うのが肝で、
# ここにモデル名をベタ書きすると「設定を変えたのに検査は旧モデルを見ていた」という
# すれ違いが起きる（今回の障害と同じ構図）。
PROBE = r"""
import json, time
from google import genai
from google.genai import types
from app.core.config import settings

fields = ["llm_model", "llm_chat_model", "llm_audio_model", "llm_analysis_model"]
# 同じモデルIDが複数の用途で使われることが多いので、用途をまとめて1回だけ叩く
used = {}
for f in fields:
    used.setdefault(getattr(settings, f), []).append(f)

out = {"models": [], "api_key": bool(settings.gemini_api_key)}
if settings.gemini_api_key:
    c = genai.Client(api_key=settings.gemini_api_key,
                     http_options=types.HttpOptions(timeout=30000))
    for model, uses in used.items():
        t0 = time.time()
        rec = {"model": model, "uses": uses}
        try:
            c.models.generate_content(
                model=model, contents="ping",
                config=types.GenerateContentConfig(max_output_tokens=16))
            rec.update(ok=True, sec=round(time.time() - t0, 1))
        except Exception as e:
            rec.update(ok=False, sec=round(time.time() - t0, 1),
                       error=f"{type(e).__name__}: {str(e)[:160]}")
        out["models"].append(rec)
print("___RESULT___" + json.dumps(out, ensure_ascii=False))
"""


def probe() -> dict:
    """backend コンテナ内で実効モデルを1つずつ実APIに投げる。"""
    r = subprocess.run(
        ["docker", "exec", "-i", BACKEND, "python", "-"],
        input=PROBE, capture_output=True, text=True,
    )
    for line in (r.stdout or "").splitlines():
        if line.startswith("___RESULT___"):
            return json.loads(line[len("___RESULT___"):])
    return {"error": ((r.stdout or "") + (r.stderr or "")).strip()[:400] or "no output"}


def push_line(msg: str) -> tuple[bool, str]:
    """sns コンテナ内の line_client.push_text() を docker exec で呼ぶ（daily_metrics_line と同方式）。"""
    code = (
        "import os;import line_client;"
        "ok,info=line_client.push_text(os.environ['HEALTH_MSG']);"
        "print('OK' if ok else 'NG', info)"
    )
    r = subprocess.run(
        ["docker", "exec", "-w", "/app", "-e", f"HEALTH_MSG={msg}", SNS, "python", "-c", code],
        capture_output=True, text=True,
    )
    out = (r.stdout + r.stderr).strip()
    return (r.returncode == 0 and out.startswith("OK")), out


USE_JP = {
    "llm_model": "基本",
    "llm_chat_model": "チャット",
    "llm_audio_model": "音声",
    "llm_analysis_model": "分析",
}


def build_message(res: dict, dead: list[dict]) -> str:
    lines = ["🚨 Geminiモデルが応答しません", ""]
    for d in dead:
        uses = "・".join(USE_JP.get(u, u) for u in d["uses"])
        lines.append(f"❌ {d['model']}（{uses}）")
        lines.append(f"   {d.get('error', '')}")
    ok = [m for m in res["models"] if m["ok"]]
    if ok:
        lines.append("")
        lines.append("✅ 生きている: " + "、".join(m["model"] for m in ok))
    lines += [
        "",
        "対処: docker/.env に生きているモデルIDを書いて再起動",
        "  例) LLM_CHAT_MODEL=gemini-3.5-flash-lite",
        "  cd /opt/vocalcoach/docker && docker compose -f docker-compose.prod.yml up -d backend",
        "※ 指定前に必ず実APIで疎通確認（models.listに載っていても死んでいることがある）",
        "詳細: docs/92",
    ]
    return "\n".join(lines)


def main() -> int:
    now = datetime.now(JST)
    res = probe()

    if "error" in res:
        print(f"ERROR: 検査を実行できませんでした: {res['error']}", file=sys.stderr)
        return 1
    if not res.get("api_key"):
        print("GEMINI_API_KEY 未設定のため検査をスキップ（ルールベース運用中）")
        return 0

    for m in res["models"]:
        mark = "OK " if m["ok"] else "NG "
        print(f"{mark}{m['model']:26s} {m['sec']:>4}s  {'/'.join(m['uses'])}"
              + ("" if m["ok"] else f"  {m.get('error', '')}"))

    dead = [m for m in res["models"] if not m["ok"]]

    try:
        with open(JSONL, "a") as f:
            f.write(json.dumps({
                "ts": now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "all_ok": not dead,
                "models": res["models"],
            }, ensure_ascii=False) + "\n")
    except Exception as e:  # noqa: BLE001
        print(f"WARN: jsonl書き込み失敗: {e}", file=sys.stderr)

    force = os.getenv("FORCE_NOTIFY", "").lower() in ("1", "true", "yes")
    if not dead and not force:
        print("全モデル正常。通知はしない。")
        return 0

    msg = build_message(res, dead) if dead else (
        "✅ Geminiモデル疎通OK（FORCE_NOTIFY）\n"
        + "\n".join(f"{m['model']}（{m['sec']}s）" for m in res["models"])
    )
    print(msg)
    if os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes"):
        print("[dry-run] LINE送信はスキップ")
        return 1 if dead else 0
    ok, info = push_line(msg)
    print(f"[LINE] {info}")
    # モデルが死んでいる時は非0で返す（cronログとjsonlの両方から異常を追えるように）
    return 1 if dead or not ok else 0


if __name__ == "__main__":
    sys.exit(main())
