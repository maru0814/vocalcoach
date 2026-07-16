"""QA harness: --text/--reply 完成稿の手動投入（automatable cases）。
各TCをassertしPASS/FAILを出す。ネットワーク（Gemini/X/LINE）は呼ばない。"""
import io
import os
import sys
import importlib
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# 画像生成のネットワークを無効化（安全・高速）。
os.environ["SNS_IMAGE"] = "0"

import generate_and_post as gp
import approval_queue as q
import line_client

# expert_review はキー無しでskip＝approved にする。
# .env がある環境（本番 sns コンテナ等）では generate_and_post の import 時に
# load_dotenv が GEMINI_API_KEY を復活させるため、pop は import 後に行う。
# （load_dotenv を行うのは generate_and_post のみ。import 後に pop すれば復活しない）
os.environ.pop("GEMINI_API_KEY", None)

results = []


def check(tc, cond, detail=""):
    results.append((tc, bool(cond), detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {tc} {detail}")


def run_main(argv, env=None):
    """main() を argv/env を差し替えて実行し、(rc, stdout) を返す。"""
    old_argv, old_env = sys.argv, dict(os.environ)
    if env:
        os.environ.update(env)
    sys.argv = ["generate_and_post.py"] + argv
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            rc = gp.main()
    finally:
        sys.argv = old_argv
        os.environ.clear()
        os.environ.update(old_env)
    return rc, buf.getvalue()


CUSTOM_TEXT = ("厳しいことを言います。\n\nカラオケで100回歌っても、音痴はほぼ直りません。\n\n"
               "必要なのは練習量じゃなく、ズレの可視化。")
CUSTOM_REPLY = "15秒歌うと、AIのソラ先生があなたのピッチと声タイプをその場で可視化します。"


# TC-01: --text 指定時は generate_post（themes/Gemini）を呼ばず、指定文言をそのまま使う
_orig_generate_post = gp.generate_post


def _boom(*a, **k):
    raise AssertionError("generate_post must NOT be called on --text path")


gp.generate_post = _boom
try:
    rc, out = run_main(["--text", CUSTOM_TEXT, "--reply", CUSTOM_REPLY,
                        "--pillar", "contrarian", "--dry-run"])
    check("TC-01 generate_post未呼び出し", rc == 0)
    check("TC-01 本文がそのまま出る", "カラオケで100回歌っても、音痴はほぼ直りません。" in out,
          f"=> text_in_output={CUSTOM_TEXT.splitlines()[2] in out}")
    check("TC-01 自己リプがそのまま出る", CUSTOM_REPLY in out)
    check("TC-01 DRY_RUNで投稿しない", "承認キュー・LINE・投稿はいずれもしていません" in out)
finally:
    gp.generate_post = _orig_generate_post

# TC-02: --reply 省略 → 単発（リプ本体を出さない）
gp.generate_post = _boom
try:
    rc, out = run_main(["--text", CUSTOM_TEXT, "--pillar", "contrarian", "--dry-run"])
    check("TC-02 単発（リプ見出しなし）", "【リプ（自己返信）＝大事な中身】" not in out)
finally:
    gp.generate_post = _orig_generate_post

# TC-03: --pillar 未指定 → contrarian にフォールバック（noticeを出す）
gp.generate_post = _boom
try:
    rc, out = run_main(["--text", CUSTOM_TEXT, "--dry-run"])
    check("TC-03 pillar未指定→contrarian", "'contrarian' として扱います" in out
          and "pillar=contrarian" in out)
finally:
    gp.generate_post = _orig_generate_post

# TC-04: DRY_RUN=0 で承認キュー投入まで到達し、キューに“指定文言そのまま”が載る（LINEはモック）
captured = {}
_orig_enqueue, _orig_push = q.enqueue, line_client.push_approval


def _fake_enqueue(pillar, slot, text, reply, link, post_link, image=None,
                  status="pending", expert_note=""):
    rec = {"id": "test123", "pillar": pillar, "slot": slot, "text": text,
           "reply": reply, "link": link, "post_link": post_link,
           "image": image, "status": status, "expert_note": expert_note}
    captured["rec"] = rec
    return rec


def _fake_push(draft):
    captured["pushed"] = draft
    return True, "ok"


gp.generate_post = _boom
q.enqueue = _fake_enqueue
line_client.push_approval = _fake_push
try:
    rc, out = run_main(["--text", CUSTOM_TEXT, "--reply", CUSTOM_REPLY,
                        "--pillar", "contrarian"],
                       env={"DRY_RUN": "0", "APPROVAL_MODE": "1", "POST_LINK": "0"})
    rec = captured.get("rec", {})
    check("TC-04 キューに到達", "rec" in captured and rc == 0)
    check("TC-04 本文が一言一句そのまま", rec.get("text") == CUSTOM_TEXT,
          f"=> {rec.get('text', '')[:24]!r}...")
    check("TC-04 リプがそのまま", rec.get("reply") == CUSTOM_REPLY)
    check("TC-04 link無し（URL混入なし）", rec.get("link") is None and rec.get("post_link") is False)
    check("TC-04 status=pending（ゲート通過）", rec.get("status") == "pending")
    check("TC-04 LINE承認へpush", captured.get("pushed", {}).get("id") == "test123")
finally:
    gp.generate_post = _orig_generate_post
    q.enqueue, line_client.push_approval = _orig_enqueue, _orig_push


# ---- 図解の A(自動) / B(構造化) 描画データ（renderは呼ばず build_data で検証） ----
import infographic

# TC-05: A(auto) contrarian = 本文/リプを自動構造化。見出しは本文1行目、鍵はリプ由来。
a = infographic.build_data("contrarian", 0,
                           {"mode": "auto", "text": CUSTOM_TEXT, "reply": CUSTOM_REPLY})
check("TC-05 A: type=contrarian", a.get("type") == "contrarian")
check("TC-05 A: 見出し=本文1行目", a.get("title") == "厳しいことを言います。", f"=> {a.get('title')!r}")
check("TC-05 A: 鍵は2枚", len(a.get("reasons", [])) == 2)

# TC-06: B(spec) contrarian = 運用者の構造をそのまま。誤解/鍵を制御でき、highlightは自動補完。
SPEC = {"title": "音痴は、カラオケで歌い込めば直る", "verdict": "半分ウソ",
        "reasons": [{"title": "耳", "body": "原因は喉ではなく耳。"},
                    {"title": "可視化", "body": "ズレを見てから直す。"}],
        "summary": "必要なのは練習量より、ズレの可視化。"}
b = infographic.build_data("contrarian", 0, {"mode": "spec", "data": SPEC})
check("TC-06 B: 見出し=指定の誤解", b.get("title") == SPEC["title"])
check("TC-06 B: 判定=指定", b.get("verdict") == "半分ウソ")
check("TC-06 B: 鍵1=耳 / 鍵2=可視化",
      [r["title"] for r in b.get("reasons", [])] == ["耳", "可視化"])
check("TC-06 B: highlight自動補完", bool(b.get("highlight")))

# TC-07: A と B は明確に異なる出力（見出し・鍵ラベルが別物）
check("TC-07 A≠B: 見出しが違う", a.get("title") != b.get("title"))
check("TC-07 A≠B: 鍵ラベルが違う",
      [r["title"] for r in a.get("reasons", [])] != [r["title"] for r in b.get("reasons", [])])

# TC-08: --image-spec 不正JSON → rc=2（安全に停止）
gp.generate_post = _boom
try:
    rc, out = run_main(["--text", CUSTOM_TEXT, "--pillar", "contrarian",
                        "--image-spec", "{not json", "--dry-run"])
    check("TC-08 不正spec→rc=2", rc == 2)
finally:
    gp.generate_post = _orig_generate_post


# ---- 完成稿(mode=card)の画像分岐: 診断導線は図鑑図解を優先、tip/contrarianはカード ----
import themes


def _run_build_image(pillar, override, ig_result):
    """build_image を実レンダリング無しで実行し、(戻り値, 図解呼び出し?, カード呼び出しheadline) を返す。"""
    calls = {"ig": None, "card": None}
    _orig_ig, _orig_img = gp.infographic.generate, gp.images.generate_image

    def _fake_ig(pillar, day_index, app_url, out, override=None):
        calls["ig"] = {"pillar": pillar, "override": override}
        return ig_result

    def _fake_card(pillar, headline, out):
        calls["card"] = headline
        return "/tmp/card.png"

    gp.infographic.generate = _fake_ig
    gp.images.generate_image = _fake_card
    os.environ["SNS_IMAGE"] = "1"
    try:
        path = gp.build_image(pillar, 1, 0, "https://x.test", override=override)
    finally:
        gp.infographic.generate, gp.images.generate_image = _orig_ig, _orig_img
        os.environ["SNS_IMAGE"] = "0"
    return path, calls


CARD_OVERRIDE = {"mode": "card", "text": CUSTOM_TEXT, "reply": CUSTOM_REPLY}

# TC-09: 診断導線 × mode=card → themes 図鑑図解を先に試す（override=None で呼ぶ）。カードは焼かない
for pl in themes.DIAGNOSIS_PILLARS:
    path, calls = _run_build_image(pl, dict(CARD_OVERRIDE), ig_result="/tmp/ig.png")
    check(f"TC-09 {pl}: 図解を先に試す", calls["ig"] is not None
          and calls["ig"]["override"] is None, f"=> ig_called={calls['ig']}")
    check(f"TC-09 {pl}: 図解成功ならカード無し", path == "/tmp/ig.png" and calls["card"] is None)

# TC-10: 診断導線 × mode=card × 図解失敗 → 完成稿の文言からカードにフォールバック
path, calls = _run_build_image("voice_type", dict(CARD_OVERRIDE), ig_result=None)
check("TC-10 図解失敗→カードにフォールバック", path == "/tmp/card.png" and calls["card"] is not None)
check("TC-10 カード見出しは完成稿由来",
      calls["card"] == gp.images.build_headline("voice_type", CUSTOM_TEXT, CUSTOM_REPLY),
      f"=> {calls['card']!r}")

# TC-11: tip/contrarian × mode=card → 従来どおり図解を試さず即カード（広告化回避の規律を維持）
for pl in ("tip", "contrarian"):
    path, calls = _run_build_image(pl, dict(CARD_OVERRIDE), ig_result="/tmp/ig.png")
    check(f"TC-11 {pl}: 図解を呼ばず即カード", calls["ig"] is None and path == "/tmp/card.png")


failed = [tc for tc, ok, _ in results if not ok]
print("\n" + "─" * 40)
print(f"{len(results) - len(failed)}/{len(results)} PASS")
if failed:
    print("FAILED:", ", ".join(failed))
    sys.exit(1)
