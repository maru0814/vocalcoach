#!/usr/bin/env python3
"""投稿前の専門家ゲート（世界水準SNSマーケ）。

.claude/skills/sns-strategist の採点ルーブリックで、生成された投稿（本文＋自己リプ＋画像）を
**項目別に採点**し（合計はコード側で算出＝モデルが中間点に寄せる手抜きを防ぐ）、基準(既定80点)
未満なら改善案を生成して再採点する。最終的に基準を満たした投稿だけを承認(LINE)に通し、満たさ
なければ LINE に出さず保留する。

環境変数:
  GEMINI_API_KEY            … 必須（無ければレビュー未実施＝fail-openで通すが、未レビューと明示）
  SNS_REVIEW_MODEL          … レビュー用の第一モデル（既定 gemini-2.5-flash）
  EXPERT_REVIEW_MIN_SCORE   … 合格ライン（既定 80）
  EXPERT_REVIEW_ROUNDS      … 改善→再採点の最大回数（既定 2）
"""
import json
import os
import re
import sys
import time

# 項目別配点（合計100）。コード側で sum するため、モデルは各項目だけ採点すればよい。
MAXES = {"hook": 25, "target": 15, "algo": 15, "concrete": 15,
         "authority": 10, "image": 10, "cta": 5, "safety": 5}
_LABEL = {"hook": "フック/1行目の停止力", "target": "ターゲット解像度", "algo": "アルゴリズム適合",
          "concrete": "具体性・再現性", "authority": "権威性/トーン", "image": "画像/テキスト停止力",
          "cta": "CTA/導線", "safety": "規約/安全"}

# 採点基準（skill: sns-strategist と一致）。各項目を独立に 0〜上限 で採点させる。
REVIEWER_SYSTEM = """あなたは世界トップクラスのX(Twitter)グロース戦略家です。
個人開発の歌アプリ「ソラ先生」のX投稿を、出稿前に厳密に採点します。

最重要: **各項目を独立に採点**してください。安易に中間点(70前後)に寄せないこと。
良い所は満点近く、弱い所は低く、メリハリをつけて評価します。合計はシステムが計算します。

# 項目別の採点（各項目を 0〜上限 の整数で）
- hook 上限25: 1行目の停止力。平凡な総論=0〜8 / 具体的な悩み提示=12〜18 / 意外性・数字・逆張りで続きが気になる=20〜25。
- target 上限15: 刺さる相手の具体度。誰にでも=0〜6 / 悩みが具体=10〜15。
- algo 上限15: 初速2h・リプ誘発(自己リプに本体)・保存性の設計。無策=0〜6 / 1つ明確=10 / 複数設計=13〜15。
- concrete 上限15: 手順・身体感覚の具体と再現性。抽象論で逃げ=0〜6 / 今日試せる具体手順=12〜15。
- authority 上限10: 専門家トーン。リプ乞い・誇大・媚び=0〜3 / 信頼できる専門家=8〜10。
- image 上限10: 画像があれば停止力(可読性・文字量・ブランド整合)で採点。画像が無い型(tip/contrarian等)はテキスト単体の自己完結性で満点まで可。画像が無いこと自体は減点しない。
- cta 上限5: 本文・自己リプにURLが無いか(あれば0)、誘導はプロフィール固定前提か。
- safety 上限5: 誤情報・断定しすぎ・センシティブが無いか。

# 診断導線(pillar=self_type / voice_type / visual)の追加基準 ★最重要
診断は「したくなるワクワク（好奇心ギャップ）」が命。次を厳しく見る:
- hook: 「【声タイプ図鑑】◯◯」式のラベル陳列・カタログ説明・タイプ定義の提示で始まる本投稿は
  停止力が弱い → hook は上限の半分以下(0〜12)。
  「あなたの声、歌手なら誰に似てる？」のように“自分の正体を知りたくなる問い”で始まる=20〜25。
- **具体的な歌手の実名（例：LiSA・Mrs. GREEN APPLE・宇多田ヒカル等）を本文に出しているか**。
  型名だけで実名ゼロの本投稿は自分ごと化が弱い → concrete/target を減点。実名で「誰系？」を作れている=加点。
  （実名は“声質が近い例”。読者自身の一番近い歌手は診断結果に残す設計＝診断へ誘導、が理想）
- algo/concrete: 自己リプが「リンクだけ」「診断はこちら」だけ=価値ゼロ → algo は 0〜6。
  自己リプに『8タイプ早見（近い歌手の例つき）』など“読む・自分を探す価値”がある = algo 12〜15・concrete加点。
- 80点未満なら revised_text は必ず“似てる歌手フック＋実名”に直し、revised_reply は8タイプ早見を保つ。

# スケール感（合計）
85+=そのまま出して伸びる / 75-84=良いが詰めの余地 / 60-74=弱点あり要改善 / 60未満=作り直し。

# 改善
80点未満になりそうなら、必ず revised_text（必要なら revised_reply）に基準を満たすよう書き直した版を入れる。
ソラ先生のキャラ（明るく面倒見のよい専門家・やわらかい敬体）を保ち、本文・リプにURLは入れない。

# 出力（このJSONだけ。前後に文章を付けない。total は書かなくてよい＝システムが合計する）
{"scores": {"hook": N, "target": N, "algo": N, "concrete": N, "authority": N, "image": N, "cta": N, "safety": N},
 "reasons": ["項目名: なぜその点か", "..."],
 "fixes": ["直すべき点", "..."],
 "verdict": "approve|revise|reject",
 "revised_text": "改善した本投稿（80点未満時は必須）",
 "revised_reply": "改善した自己リプ本体 または null"}
"""


def _models() -> list[str]:
    """採点に使うモデルの優先順（503フォールバック用）。先頭が第一候補。"""
    primary = os.getenv("SNS_REVIEW_MODEL", "gemini-2.5-flash")
    chain = [primary, "gemini-2.5-flash", "gemini-2.5-pro", "gemini-flash-lite-latest"]
    seen, out = set(), []
    for m in chain:
        if m and m not in seen:
            seen.add(m); out.append(m)
    return out


def _parse_scores(raw: dict) -> dict | None:
    """モデル出力から項目別スコアを取り出し、上限でクランプ。合計はコード側で算出。"""
    sc = raw.get("scores") or {}
    if not isinstance(sc, dict):
        return None
    norm = {}
    for k, mx in MAXES.items():
        try:
            v = int(round(float(sc.get(k, 0))))
        except Exception:
            v = 0
        norm[k] = max(0, min(mx, v))
    return norm


def _call_one(text, reply, pillar, image_path, model):
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
        f"型(pillar): {pillar}\n\n【本投稿】\n{text}\n\n【自己リプ本体】\n{reply or '(なし＝単発型)'}\n\n"
        f"【画像】{'添付あり（上の画像）。停止力も採点する' if has_image else 'なし（テキストのみ）'}\n\n"
        "各項目を独立に採点し、JSONだけを返してください。80点未満になりそうなら改善版も入れてください。"
    )
    parts.append(types.Part.from_text(text=body))
    cfg = types.GenerateContentConfig(
        system_instruction=REVIEWER_SYSTEM, max_output_tokens=1600, temperature=0.2,
        thinking_config=types.ThinkingConfig(thinking_budget=512),
    )
    last = None
    for _ in range(2):  # 503/429 の一過性失敗をリトライ
        try:
            resp = client.models.generate_content(
                model=model, contents=[types.Content(role="user", parts=parts)], config=cfg)
            m = re.search(r"\{.*\}", (resp.text or "").strip(), re.S)
            if not m:
                return None
            s = re.sub(r",(\s*[}\]])", r"\1", m.group(0))  # 末尾カンマを除去して頑健化
            return json.loads(s)
        except Exception as e:
            last = e
            if any(s in str(e) for s in ("503", "UNAVAILABLE", "429")):
                time.sleep(2.5); continue
            raise
    raise last


def _review_once(text, reply, pillar, image_path) -> dict | None:
    """モデル連鎖で1回採点し、{scores,total,...} を返す（どれも失敗なら None）。"""
    for model in _models():
        try:
            raw = _call_one(text, reply, pillar, image_path, model)
        except Exception as e:
            print(f"[warn] レビュー失敗({model}) → 次モデル: {str(e)[:80]}", file=sys.stderr)
            continue
        if not raw:
            continue
        scores = _parse_scores(raw)
        if scores is None:
            continue
        # ハード失格: 本文/リプにURLがあれば即不合格（reach減・$0.20課金・方針違反）。
        # cta は実態に合わせて0にし、合計に反映する。
        hard_fail = ("http" in (text or "")) or ("http" in (reply or ""))
        if hard_fail:
            scores["cta"] = 0
        total = sum(scores.values())
        return {"scores": scores, "total": total, "model": model,
                "verdict": "reject" if hard_fail else (raw.get("verdict") or "revise"),
                "hard_fail": hard_fail,
                "reasons": raw.get("reasons") or [], "fixes": raw.get("fixes") or [],
                "revised_text": (raw.get("revised_text") or "").strip(),
                "revised_reply": raw.get("revised_reply")}
    return None


def _breakdown(scores: dict) -> str:
    return " ".join(f"{_LABEL[k]}{scores[k]}/{MAXES[k]}" for k in MAXES)


def review_and_gate(text: str, reply: str | None, pillar: str,
                    image_path: str | None = None) -> dict:
    """投稿を項目別採点・改善し、ゲート結果を返す。

    戻り値: {approved, skipped, score, scores, text, reply, report}
      approved=True のときだけ呼び出し側は LINE 承認に回す。
    """
    min_score = int(os.getenv("EXPERT_REVIEW_MIN_SCORE", "80"))
    # 受かるまで「改善→再採点」を繰り返す。暴走防止の安全上限＋“頭打ち”検出付き。
    max_attempts = int(os.getenv("EXPERT_REVIEW_MAX_ATTEMPTS",
                                 os.getenv("EXPERT_REVIEW_ROUNDS", "6")))

    if not os.getenv("GEMINI_API_KEY"):
        return {"approved": True, "skipped": True, "score": None, "scores": None,
                "text": text, "reply": reply,
                "report": "⚠️ 専門家レビュー未実施（GEMINI_API_KEY 未設定）"}

    cur_text, cur_reply = text, reply
    best = None          # (total, text, reply, result)
    prev_total = -1
    stagnant = 0         # スコアが上がらない連続回数
    seen = set()         # 同じ改善案のループを検出
    try:
        for attempt in range(1, max_attempts + 1):
            r = _review_once(cur_text, cur_reply, pillar, image_path)
            if not r:
                break
            total = r["total"]
            if best is None or total > best[0]:
                best = (total, cur_text, cur_reply, r)
            # 合格 → このバージョンで承認（何回目で受かったかも表示）
            if not r["hard_fail"] and total >= min_score:
                report = (f"✅ 専門家レビュー合格 {total}/{min_score}点"
                          f"（{attempt}回目で通過 / {r['model']}）\n内訳: {_breakdown(r['scores'])}")
                return {"approved": True, "skipped": False, "score": total,
                        "scores": r["scores"], "text": cur_text, "reply": cur_reply,
                        "report": report}
            # まだ受かっていない → 改善案を取り込んで再提出
            rt = r["revised_text"]
            new_text = rt if (rt and "http" not in rt) else cur_text
            new_reply = cur_reply
            if r["revised_reply"] is not None:
                rr = (r["revised_reply"] or "").strip() or None
                if not (rr and "http" in rr):
                    new_reply = rr
            # 頭打ち検出: 改善案が前と同じ／スコアが2回連続で上がらない → これ以上は無理
            sig = (new_text, new_reply or "")
            stagnant = stagnant + 1 if total <= prev_total else 0
            prev_total = total
            if (new_text == cur_text and new_reply == cur_reply) or sig in seen or stagnant >= 2:
                break
            seen.add(sig)
            cur_text, cur_reply = new_text, new_reply

        # ここに来たら未達（安全上限到達 or 頭打ち or 採点不能）。
        if best is None:
            raise RuntimeError("全モデルで採点不能")
        btotal, btext, breply, br = best
        if br["hard_fail"]:
            # URLが残る版は方針違反（reach減・$0.20課金）。これだけは送らず保留する。
            report = (f"⛔ 専門家レビュー失格（本文/リプにURL）最高{btotal}/{min_score}点 "
                      f"→ LINE未送信・保留\n内訳: {_breakdown(br['scores'])}")
            return {"approved": False, "skipped": False, "score": btotal,
                    "scores": br["scores"], "text": btext, "reply": breply, "report": report}
        # 基準未達でも、何回も改善した中での“いちばん良かった版”をLINEに送る（人間が最終判断）。
        report = (f"⚠️ 専門家ライン未達（{max_attempts}回改善の最高 {btotal}/{min_score}点）"
                  f"→ 最良版を確認用に送付（{br['model']}）\n内訳: {_breakdown(br['scores'])}")
        if br["fixes"]:
            report += "\n残る改善点: " + " / ".join(str(x) for x in br["fixes"][:3])
        return {"approved": True, "skipped": False, "score": btotal,
                "scores": br["scores"], "text": btext, "reply": breply,
                "report": report}
    except Exception as e:
        print(f"[warn] 専門家レビュー実行に失敗 → 未レビューで通します: {e}", file=sys.stderr)
        return {"approved": True, "skipped": True, "score": None, "scores": None,
                "text": text, "reply": reply,
                "report": f"⚠️ 専門家レビュー未実施（エラー: {e}）"}
