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
            status: str = "pending", expert_note: str = "",
            ammo_key: str = "") -> dict:
    """下書きを承認待ちとして追加し、作成したレコードを返す。
    reply=自己返信に置く本体（2部構成）。診断導線など単発型は None。
    image=添付画像のローカルパス（無ければ None）。
    status: pending=LINE承認待ち / held=専門家ゲート未通過で保留（LINEに出さない）。
    expert_note: 専門家レビューの判定（LINE本文の先頭に表示する）。
    ammo_key: 使った弾（テンプレ下敷き）の指紋。同じ内容を二度と使わないための記録（dedup.py）。"""
    rec = {
        "id": uuid.uuid4().hex[:12],
        "kind": "post",  # 投稿。リード獲得は engaged_log.jsonl を直接使う（suggest_leads()参照）
        "pillar": pillar,
        "slot": slot,
        "text": text,
        "reply": reply,
        "link": link,
        "post_link": bool(post_link),
        "image": image,
        "status": status,
        "expert_note": expert_note,
        "ammo_key": ammo_key,
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


# ==== リード獲得（docs/58/59）: フォロー候補の提示ログ ==============================
# 返信文は扱わない（2026-07-06 方針転換: 提案返信を廃止し「フォローすべき人」のみ提示）。
# 承認キュー(pending_queue.jsonl)は使わず、engaged_log.jsonl を直接SSOTとする。
# レコード: {lead_id, handle, query_id, followers, source_text, url, batch_id,
#            status(suggested|followed|skipped), suggested_at, followed_back}
ENGAGED_PATH = os.path.join(_DATA_DIR, "engaged_log.jsonl")


def suggest_leads(candidates: list[dict], batch_id: str) -> list[dict]:
    """フォロー候補をバッチとして engaged_log に記録する（status="suggested"）。
    X APIへの書込みはここでは一切行わない（LINEで見せるための記録のみ）。

    candidates の各要素: {handle, query_id, followers, source_text, url}"""
    recs = []
    with _LOCK:
        with open(ENGAGED_PATH, "a", encoding="utf-8") as f:
            for c in candidates:
                rec = {
                    "lead_id": uuid.uuid4().hex[:12],
                    "handle": (c.get("handle") or "").lstrip("@"),
                    "query_id": c.get("query_id", ""),
                    "followers": c.get("followers"),
                    "source_text": c.get("source_text", ""),
                    "url": c.get("url", ""),
                    "batch_id": batch_id,
                    "status": "suggested",
                    "suggested_at": _now(),
                    "followed_back": None,
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                recs.append(rec)
    return recs


def read_engaged() -> list[dict]:
    return _read_all(ENGAGED_PATH)


def engaged_handles() -> set[str]:
    """提示済み（followed/skipped問わず）のhandle集合。重複提示の防止に使う。"""
    return {h for r in read_engaged()
            if (h := (r.get("handle") or "").lstrip("@").lower())}


def suggested_today() -> int:
    """今日すでに提示した候補件数（MAX_FOLLOWS_PER_DAY の判定用）。"""
    today = _now()[:10]
    return sum(1 for r in read_engaged() if (r.get("suggested_at") or "").startswith(today))


def mark_batch_status(batch_id: str, status: str) -> int:
    """指定バッチの status="suggested" な全件を status に更新する。更新件数を返す。"""
    with _LOCK:
        rows = _read_all(ENGAGED_PATH)
        n = 0
        for r in rows:
            if r.get("batch_id") == batch_id and r.get("status") == "suggested":
                r["status"] = status
                r["decided_at"] = _now()
                n += 1
        if n:
            _write_all(rows, ENGAGED_PATH)
        return n


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
