#!/usr/bin/env python3
"""ツイート投稿前の承認キュー（pending_queue.jsonl）。

generate_and_post.py が生成した下書きをここに積み（status=pending）、
webhook.py が LINE のボタン操作を受けて status を approved/rejected に更新し、
承認されたものだけ X に投稿する。posts_log.jsonl（計測用）とは別物。

各レコード:
  {id, pillar, slot, text, reply, link, post_link, status, tweet_id, info,
   created_at, decided_at}
  reply: 2部構成の本体（自己返信に投稿する中身）。単発型は None。
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
            link: str | None, post_link: bool,
            status: str = "pending", expert_note: str = "") -> dict:
    """下書きを承認待ちとして追加し、作成したレコードを返す。
    reply=自己返信に置く本体（2部構成）。診断導線など単発型は None。
    status: pending=LINE承認待ち / held=専門家ゲート未通過で保留（LINEに出さない）。
    expert_note: 専門家レビューの判定（LINE本文の先頭に表示する）。"""
    rec = {
        "id": uuid.uuid4().hex[:12],
        "pillar": pillar,
        "slot": slot,
        "text": text,
        "reply": reply,
        "link": link,
        "post_link": bool(post_link),
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
