#!/usr/bin/env python3
"""投稿前の専門家ゲート（世界水準SNSマーケ）。

.claude/skills/sns-strategist の採点ルーブリックで、生成された投稿（本文＋自己リプ＋画像）を
0-100点で採点し、基準(既定80点)未満なら改善案を生成して再採点する。最終的に基準を満たした
投稿だけを承認(LINE)に通し、満たさなければ LINE に出さず保留する。

環境変数:
  GEMINI_API_KEY            … 必須（無ければレビュー未実施＝fail-openで通すが、未レビューと明示）
  SNS_REVIEW_MODEL          … レビュー用モデル（既定 gemini-2.5-flash）
  EXPERT_REVIEW_MIN_SCORE   … 合格ライン（既定 80）
  EXPERT_REVIEW_ROUNDS      … 改善→再採点の最大回数（既定 2）
"""
import json
import os
import re
import sys

# 採点基準（skill: sns-strategist と一致させる。ここがゲートの実体）。
REVIEWER_SYSTEM = """あなたは世界トップクラスのX(Twitter)グロース戦略家です。
個人開発の歌アプリ「ソラ先生」のX投稿を、出稿前に厳しく品質審査します。

# 採点ルーブリック（合計100点）
- フック/1行目の停止力 25: 最初の1行で「自分ごと・続きが気になる」を作れているか。平凡な総論で始まっていないか。
- ターゲット解像度 15: 悩みが具体で刺さる相手が明確か。
- アルゴリズム適合 15: 初速2h・リプ誘発（自己リプに本体を置く）・保存性のどれを狙う設計か。
- 具体性・再現性 15: 手順・身体感覚が具体で、読者が今日試せるか。
- 権威性/トーン 10: リプ乞い・誇大・媚びが無いか。専門家トーンか。
- 画像(サムネ)の停止力 10: 画像があれば親指を止める強さ・1枚目の可読性・文字量・ブランド整合で採点。画像が無い型(tip/contrarian等)はテキスト単体の自己完結性で満点まで評価し、「画像が無いこと自体」を減点理由にしない。
- CTA/導線 5: 本文にURLを入れていないか（reach減・課金回避。誘導はプロフィール固定）。
- 規約/安全 5: 誤情報・断定しすぎ・センシティブが無いか。

# 自動失格(verdict=reject, score<=40)
- 本文または自己リプにURLが入っている
- 「番号でリプして」式のリプ乞い
- 誇大表現・医療的断定・他者攻撃

# 改善の方針
80点未満なら、必ず revised_text（と必要なら revised_reply）に、基準を満たすよう書き直した版を入れる。
ソラ先生のキャラ（明るく面倒見がよい専門家・やわらかい敬体）とトーンは保つ。本文・リプにURLは入れない。

# 出力（このJSONだけを返す。前後に文章を付けない）
{"score": <0-100の整数>, "verdict": "approve"|"revise"|"reject",
 "reasons": ["評価できる点", "..."], "fixes": ["直すべき点", "..."],
 "revised_text": "改善した本投稿（80点未満時は必須）",
 "revised_reply": "改善した自己リプ本体 または null"}
"""


def _model() -> str:
    return os.getenv("SNS_REVIEW_MODEL", "gemini-2.5-flash")


def _call_reviewer(text: str, reply: str | None, pillar: str,
                   image_path: str | None) -> dict | None:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    parts: list = []
    has_image = bool(image_path and os.path.exists(image_path))
    if has_image:
        mime = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
        with open(image_path, "rb") as f:
            parts.append(types.Part.from_bytes(data=f.read(), mime_type=mime))
    body = (
        f"型(pillar): {pillar}\n\n"
        f"【本投稿】\n{text}\n\n"
        f"【自己リプ本体】\n{reply or '(なし＝単発型)'}\n\n"
        f"【画像】{'添付あり（上の画像）。サムネ停止力も採点する' if has_image else 'なし（テキストのみ）'}\n\n"
        "この投稿を採点基準で審査し、JSONだけを返してください。"
        "80点未満なら revised_text（必要なら revised_reply）に改善版を必ず入れてください。"
    )
    parts.append(types.Part.from_text(text=body))
    cfg = types.GenerateContentConfig(
        system_instruction=REVIEWER_SYSTEM,
        max_output_tokens=1400,
        temperature=0.3,
        thinking_config=types.ThinkingConfig(thinking_budget=512),
    )
    import time
    last_err = None
    for attempt in range(3):  # 503(高需要)など一過性失敗をリトライ
        try:
            resp = client.models.generate_content(
                model=_model(), contents=[types.Content(role="user", parts=parts)], config=cfg)
            m = re.search(r"\{.*\}", (resp.text or "").strip(), re.S)
            if not m:
                return None
            return json.loads(m.group(0))
        except Exception as e:
            last_err = e
            if "503" in str(e) or "UNAVAILABLE" in str(e) or "429" in str(e):
                time.sleep(2.5)
                continue
            raise
    raise last_err


def review_and_gate(text: str, reply: str | None, pillar: str,
                    image_path: str | None = None) -> dict:
    """投稿を採点・改善し、ゲート結果を返す。

    戻り値: {approved, skipped, score, text, reply, report}
      approved=True のときだけ呼び出し側は LINE 承認に回す。
      text/reply は（改善された場合）差し替え済みの最終版。
    """
    min_score = int(os.getenv("EXPERT_REVIEW_MIN_SCORE", "80"))
    rounds = int(os.getenv("EXPERT_REVIEW_ROUNDS", "2"))

    if not os.getenv("GEMINI_API_KEY"):
        return {"approved": True, "skipped": True, "score": None,
                "text": text, "reply": reply,
                "report": "⚠️ 専門家レビュー未実施（GEMINI_API_KEY 未設定）"}

    cur_text, cur_reply = text, reply
    last: dict | None = None
    try:
        for _ in range(rounds + 1):
            r = _call_reviewer(cur_text, cur_reply, pillar, image_path)
            if not r:
                break
            last = r
            score = int(r.get("score") or 0)
            if r.get("verdict") == "approve" or score >= min_score:
                report = f"✅ 専門家レビュー合格 {score}/{min_score}点"
                good = r.get("reasons") or []
                if good:
                    report += "\n良い点: " + " / ".join(str(x) for x in good[:2])
                return {"approved": True, "skipped": False, "score": score,
                        "text": cur_text, "reply": cur_reply, "report": report}
            # 改善案で差し替えて次ラウンドで再採点（URLが混じった改善は採用しない）
            rt = (r.get("revised_text") or "").strip()
            if rt and "http" not in rt:
                cur_text = rt
            if "revised_reply" in r:
                rr = r.get("revised_reply")
                rr = (rr or "").strip() or None if rr is not None else None
                if not (rr and "http" in rr):
                    cur_reply = rr
        # 基準未達（または採点不能）
        score = int((last or {}).get("score") or 0)
        fixes = (last or {}).get("fixes") or (last or {}).get("reasons") or []
        report = f"⛔ 専門家レビュー不合格 {score}/{min_score}点 → LINE未送信・保留"
        if fixes:
            report += "\n改善要求: " + " / ".join(str(x) for x in fixes[:3])
        return {"approved": False, "skipped": False, "score": score,
                "text": cur_text, "reply": cur_reply, "report": report}
    except Exception as e:
        # 技術的失敗で運用全体を止めないため fail-open。ただし未レビューと明示する。
        print(f"[warn] 専門家レビュー実行に失敗 → 未レビューで通します: {e}", file=sys.stderr)
        return {"approved": True, "skipped": True, "score": None,
                "text": text, "reply": reply,
                "report": f"⚠️ 専門家レビュー未実施（エラー: {e}）"}
