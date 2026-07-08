"""QA harness: --text/--reply 完成稿の手動投入（automatable cases）。
各TCをassertしPASS/FAILを出す。ネットワーク（Gemini/X/LINE）は呼ばない。"""
import io
import os
import sys
import importlib
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# 画像生成とゲートのネットワークを無効化（安全・高速）。
os.environ["SNS_IMAGE"] = "0"
os.environ.pop("GEMINI_API_KEY", None)  # expert_review はキー無しでskip＝approved

import generate_and_post as gp
import approval_queue as q
import line_client

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


failed = [tc for tc, ok, _ in results if not ok]
print("\n" + "─" * 40)
print(f"{len(results) - len(failed)}/{len(results)} PASS")
if failed:
    print("FAILED:", ", ".join(failed))
    sys.exit(1)
