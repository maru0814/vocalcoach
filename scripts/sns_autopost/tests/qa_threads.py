"""QA harness: Threads自動投稿（docs/63 AC / docs/64 §10）。
外部API・LINE・Geminiは呼ばない（requests をフェイクに差し替えて走る）。"""
import datetime
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# データ書き込みを一時ディレクトリへ隔離（本物のログ・トークンを汚さない）
_TMP = tempfile.mkdtemp(prefix="qa_threads_")
os.environ["SNS_DATA_DIR"] = _TMP
os.environ.pop("GEMINI_API_KEY", None)
for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET",
          "LINE_CHANNEL_ACCESS_TOKEN", "LINE_CHANNEL_SECRET",
          "THREADS_ENABLED", "THREADS_ACCESS_TOKEN", "THREADS_USER_ID"):
    os.environ.pop(k, None)
os.environ["SNS_PUBLIC_BASE_URL"] = "https://example.test"

import generate_and_post as gp
import threads_client as tc

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")


class FakeResp:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body or {}
        self.text = text or json.dumps(self._body)

    def json(self):
        return self._body


class FakeRequests:
    """threads_client.requests の差し替え。呼び出しを記録し、URLパターンで応答を返す。"""

    def __init__(self, fail_publish=False, fail_container=False):
        self.calls = []            # (method, url, payload)
        self.fail_publish = fail_publish
        self.fail_container = fail_container
        self._seq = 0

    def post(self, url, data=None, timeout=None, **kw):
        self.calls.append(("POST", url, dict(data or {})))
        if url.endswith("/threads_publish"):
            if self.fail_publish:
                return FakeResp(400, {"error": "boom"})
            return FakeResp(200, {"id": f"p{self._seq}"})
        if url.endswith("/threads"):
            if self.fail_container:
                return FakeResp(400, {"error": "boom"})
            self._seq += 1
            return FakeResp(200, {"id": f"c{self._seq}"})
        return FakeResp(404, {})

    def get(self, url, params=None, timeout=None, **kw):
        self.calls.append(("GET", url, dict(params or {})))
        if "refresh_access_token" in url:
            return FakeResp(200, {"access_token": "NEW_TOKEN", "expires_in": 5183944})
        return FakeResp(200, {"status": "FINISHED"})


def reset_token(access_token="TOK", days_ago=0):
    ts = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).isoformat(
        timespec="seconds")
    with open(tc.TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump({"access_token": access_token, "refreshed_at": ts}, f)


# ---- TC-01 (AC-01/07): THREADS_ENABLED=0 では Threads API を一切呼ばない -------------
fake = FakeRequests()
tc.requests = fake
gp.post_to_x = lambda *a, **kw: (True, "tw1", "本投稿OK")  # Xは成功をフェイク
ok, tweet_id, threads_id, info = gp.post_all("本文", "リプ", None, False, None)
check("TC-01a 無効時: 全体成功・threads_id空", ok and tweet_id == "tw1" and threads_id == "",
      f"=> {info}")
check("TC-01b 無効時: Threads API呼び出しゼロ", len(fake.calls) == 0)
check("TC-01c 無効時: infoは従来のまま", info == "本投稿OK")

# ---- キー未設定 (FR-03例外): 有効化したがキーが無い → Xのみ・KEYS_MISSING記録 ----------
os.environ["THREADS_ENABLED"] = "1"
ok, tweet_id, threads_id, info = gp.post_all("本文", None, None, False, None)
check("TC-01d 有効+キー無し: X成功のまま", ok and tweet_id == "tw1" and threads_id == "")
check("TC-01e 有効+キー無し: KEYS_MISSINGをinfoに記録", "THREADS_KEYS_MISSING" in info,
      f"=> {info}")

# ---- TC-02 (AC-02/03): 画像+2部構成の3ステップ呼び出しとスレッド構造 -------------------
os.environ["THREADS_USER_ID"] = "me"
reset_token("TOK", days_ago=0)
img = os.path.join(_TMP, "post.png")
with open(img, "wb") as f:
    f.write(b"png")
fake = FakeRequests()
tc.requests = fake
ok, threads_id, info = tc.post("本文フック", "リプ本体", None, False, image_path=img)
posts = [c for c in fake.calls if c[0] == "POST"]
containers = [c for c in posts if c[1].endswith("/me/threads")]
publishes = [c for c in posts if c[1].endswith("/threads_publish")]
check("TC-02a 本投稿+リプで container×2 / publish×2",
      len(containers) == 2 and len(publishes) == 2, f"=> {info}")
check("TC-02b 本投稿はIMAGE+公開URL",
      containers[0][2].get("media_type") == "IMAGE"
      and containers[0][2].get("image_url") == "https://example.test/sns/img/post.png")
check("TC-02c リプはTEXTで本投稿(p1)にreply_to_id",
      containers[1][2].get("media_type") == "TEXT"
      and containers[1][2].get("reply_to_id") == "p1")
check("TC-02d 戻り値は本投稿ID・ok", ok and threads_id == "p1" and "リプ本体" in info,
      f"=> id={threads_id} {info}")

# ---- TC-03 (AC-04): X成功+Threads失敗 → 全体posted扱い・infoに失敗理由 ------------------
fake = FakeRequests(fail_container=True)
tc.requests = fake
ok, tweet_id, threads_id, info = gp.post_all("本文", None, None, False, None)
check("TC-03a Threads失敗でも全体は成功", ok and tweet_id == "tw1" and threads_id == "")
check("TC-03b infoにThreads失敗理由", "Threads失敗" in info and "HTTP 400" in info,
      f"=> {info}")

# ---- TC-04 (AC-05): トークン自動リフレッシュ（45日境界） ------------------------------
reset_token("OLD_TOKEN", days_ago=46)
fake = FakeRequests()
tc.requests = fake
token = tc._maybe_refresh(tc._load_token())
refreshes = [c for c in fake.calls if "refresh_access_token" in c[1]]
saved = json.load(open(tc.TOKEN_PATH, encoding="utf-8"))
check("TC-04a 46日経過でリフレッシュAPIが呼ばれる", len(refreshes) == 1)
check("TC-04b 新トークンが返り・保存される",
      token == "NEW_TOKEN" and saved["access_token"] == "NEW_TOKEN")
check("TC-04c refreshed_atが今日に更新",
      saved["refreshed_at"].startswith(datetime.date.today().isoformat()))
fake = FakeRequests()
tc.requests = fake
token = tc._maybe_refresh(tc._load_token())  # 直後（45日未満）
check("TC-04d 45日未満ではリフレッシュしない",
      token == "NEW_TOKEN" and len(fake.calls) == 0)

# ---- TC-05 (AC-06): 500字切り詰め ----------------------------------------------------
long_text = "あ" * 501
clipped = tc._clip(long_text)
check("TC-05a 501字→500字以内+末尾…", len(clipped) <= 500 and clipped.endswith("…"),
      f"=> len={len(clipped)}")
check("TC-05b 500字ちょうどは無加工", tc._clip("あ" * 500) == "あ" * 500)
fake = FakeRequests()
tc.requests = fake
tc.post(long_text, None, None, False, None)
sent = [c for c in fake.calls if c[1].endswith("/me/threads")][0][2]["text"]
check("TC-05c 実送信ペイロードも500字以内", len(sent) <= 500)

# ---- TC-06: posts_log.jsonl の threads_id 記録と後方互換 ------------------------------
gp._log_post("tw9", "tip", False, True, threads_id="p9")
with open(gp.POSTS_LOG, encoding="utf-8") as f:
    rows = [json.loads(line) for line in f if line.strip()]
check("TC-06a threads_idがログに記録される",
      rows[-1]["threads_id"] == "p9" and rows[-1]["tweet_id"] == "tw9")
old = {"tweet_id": "tw_old", "pillar": "tip", "link": False, "reply": False,
       "ts": "2026-01-01T12:00:00"}  # threads_id無しの旧レコード
check("TC-06b 旧レコード(threads_id無し)も.getで壊れない",
      old.get("threads_id", "") == "")

# ---- 画像フォールバック: SNS_PUBLIC_BASE_URL未設定ならTEXTで投稿 -----------------------
os.environ.pop("SNS_PUBLIC_BASE_URL", None)
fake = FakeRequests()
tc.requests = fake
ok, threads_id, info = tc.post("本文", None, None, False, image_path=img)
sent = [c for c in fake.calls if c[1].endswith("/me/threads")][0][2]
check("TC-07a base未設定: TEXTで投稿（画像なしフォールバック）",
      ok and sent.get("media_type") == "TEXT" and "image_url" not in sent, f"=> {info}")

print("─" * 48)
fails = [r for r in results if not r[1]]
print(f"{len(results) - len(fails)}/{len(results)} PASS"
      + (f" / FAIL: {[r[0] for r in fails]}" if fails else ""))
sys.exit(1 if fails else 0)
