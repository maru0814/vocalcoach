#!/usr/bin/env python3
"""ツイート投稿前の承認キュー（pending_queue.jsonl）。

generate_and_post.py が生成した下書きをここに積み（status=pending）、
webhook.py が LINE のボタン操作を受けて status を approved/rejected に更新し、
承認されたものだけ X に投稿する。posts_log.jsonl（計測用）とは別物。

各レコード:
  {id, pillar, slot, text, reply, link, post_link, image, status, tweet_id, info,
   created_at, decided_at}
  reply: 2部構成の本体（自己返信に投稿する中身）。単発型は None。
  image: 添付画像のローカルパス or None（生成できなかった場合）。
  status: pending | posted | rejected | failed
"""
import datetime
import json
import os
import tempfile
import uuid

_DIR = os.path.dirname(os.path.abspath(__file__))
# 実行時データの保存先。本番は永続volume（/data等）を SNS_DATA_DIR で指定する。
_DATA_DIR = os.getenv("SNS_DATA_DIR", _DIR)
os.makedirs(_DATA_DIR, exist_ok=True)
QUEUE_PATH = os.path.join(_DATA_DIR, "pending_queue.jsonl")

# 同一プロセス（uvicorn）内での読み書き競合を避ける軽量ロック。
# webhook は単一ワーカー想定。複数ワーカーにする場合は外部ロックに置き換える。
try:
    import threading
    _LOCK = threading.Lock()
except Exception:  # pragma: no cover
    class _Noop:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    _LOCK = _Noop()


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _read_all(path: str = QUEUE_PATH) -> list[dict]:
    rows: list[dict] = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
    return rows


def _write_all(rows: list[dict], path: str = QUEUE_PATH) -> None:
    # 一時ファイルに書いてから置換（書き込み途中の破損を防ぐ）。
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".queue.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def enqueue(pillar: str, slot: int, text: str, reply: str | None,
            link: str | None, post_link: bool, image: str | None = None,
            status: str = "pending", expert_note: str = "") -> dict:
    """下書きを承認待ちとして追加し、作成したレコードを返す。
    reply=自己返信に置く本体（2部構成）。診断導線など単発型は None。
    image=添付画像のローカルパス（無ければ None）。
    status: pending=LINE承認待ち / held=専門家ゲート未通過で保留（LINEに出さない）。
    expert_note: 専門家レビューの判定（LINE本文の先頭に表示する）。"""
    rec = {
        "id": uuid.uuid4().hex[:12],
        "kind": "post",  # 投稿。リード承認は enqueue_lead()（kind="lead"）
        "pillar": pillar,
        "slot": slot,
        "text": text,
        "reply": reply,
        "link": link,
        "post_link": bool(post_link),
        "image": image,
        "status": status,
        "expert_note": expert_note,
        "tweet_id": "",
        "info": "",
        "created_at": _now(),
        "decided_at": "",
    }
    with _LOCK:
        with open(QUEUE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def get(draft_id: str) -> dict | None:
    for r in _read_all():
        if r.get("id") == draft_id:
            return r
    return None


def update(draft_id: str, **fields) -> dict | None:
    """指定IDのレコードを部分更新する。見つからなければ None。"""
    with _LOCK:
        rows = _read_all()
        updated = None
        for r in rows:
            if r.get("id") == draft_id:
                r.update(fields)
                updated = r
                break
        if updated is not None:
            _write_all(rows)
        return updated


def mark_decided(draft_id: str, status: str, tweet_id: str = "",
                 info: str = "") -> dict | None:
    """承認処理の結果（posted / rejected / failed）を確定させる。"""
    return update(draft_id, status=status, tweet_id=tweet_id, info=info,
                  decided_at=_now())


def pending(limit: int = 50) -> list[dict]:
    return [r for r in _read_all() if r.get("status") == "pending"][-limit:]


# ==== リード獲得（docs/58/59）: 承認キュー相乗り＋engaged_log ========================
# 既存レコードに kind が無いものは "post" として扱う（後方互換。docs/59 §11）。
ENGAGED_PATH = os.path.join(_DATA_DIR, "engaged_log.jsonl")


def enqueue_lead(lead: dict, expert_note: str = "", status: str = "pending") -> dict:
    """リード承認カードをキューに積む（kind="lead"）。

    lead: {url, handle, query_id, source, source_text, followers, reply_text}
    承認しても X には投稿しない（実行は運用者の手動。webhook.py 参照）。"""
    rec = {
        "id": uuid.uuid4().hex[:12],
        "kind": "lead",
        "pillar": "lead",           # 既存表示コードとの互換用
        "slot": 0,
        "text": lead.get("reply_text", ""),
        "reply": None, "link": None, "post_link": False, "image": None,
        "status": status,
        "expert_note": expert_note,
        "lead": dict(lead),
        "tweet_id": "",
        "info": "",
        "created_at": _now(),
        "decided_at": "",
    }
    with _LOCK:
        with open(QUEUE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def leads_today() -> int:
    """今日キューに積んだリード件数（MAX_LEADS_PER_DAY の判定用）。"""
    today = _now()[:10]
    return sum(1 for r in _read_all()
               if r.get("kind") == "lead" and (r.get("created_at") or "").startswith(today))


def append_engaged(rec: dict) -> dict:
    """engaged_log.jsonl に1件追記する（計測のSSOT。docs/59 §4.2）。"""
    rec = dict(rec)
    rec.setdefault("approved_at", _now())
    rec.setdefault("followed_back", None)
    with _LOCK:
        with open(ENGAGED_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def read_engaged() -> list[dict]:
    return _read_all(ENGAGED_PATH)


def engaged_handles() -> set[str]:
    """対応済み（承認/スキップ問わず）のhandle集合。重複提示の防止に使う。"""
    out = set()
    for r in read_engaged():
        h = (r.get("handle") or "").lstrip("@").lower()
        if h:
            out.add(h)
    # キューでpending中のリードも重複提示しない
    for r in _read_all():
        if r.get("kind") == "lead":
            h = ((r.get("lead") or {}).get("handle") or "").lstrip("@").lower()
            if h:
                out.add(h)
    return out


def recent_lead_reply_texts(limit: int = 30) -> list[str]:
    """直近のリード返信文（同文連投の検出用）。engaged_log＋キューの両方から集める。"""
    texts = [r.get("reply_text", "") for r in read_engaged()]
    texts += [(r.get("lead") or {}).get("reply_text", "")
              for r in _read_all() if r.get("kind") == "lead"]
    return [t for t in texts if t][-limit:]


def update_engaged(lead_id: str, **fields) -> dict | None:
    """engaged_log の1件を部分更新する（followed_back の記入など）。"""
    with _LOCK:
        rows = _read_all(ENGAGED_PATH)
        updated = None
        for r in rows:
            if r.get("lead_id") == lead_id:
                r.update(fields)
                updated = r
                break
        if updated is not None:
            _write_all(rows, ENGAGED_PATH)
        return updated
