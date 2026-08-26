"""一度作ったツイートと同じ内容を、未来永劫出さないための単一モジュール（docs/108）。

2つの指紋で守る:
- **ammo_key**: 弾（themes のテンプレ下敷き）の指紋。下書きを承認キューに積んだ時点で
  レコードに記録し、以後の弾選び（pick_unused_index）で使用済み弾を除外する。
  Geminiリライトで文面が変わっても「同じ下敷き＝同じ内容」とみなして二度と使わない。
- **text_hash**: 実際に投稿された本投稿(text)の指紋。承認→投稿の最終ゲート
  （webhook.py / --post-now）で、過去に投稿済みの本文と一致したら投稿を拒否する。
  「絶対に出ない」の最終保証はここ（生成経路が何であれ、投稿の直前で必ず通る）。

記録の置き場は既存の pending_queue.jsonl / posts_log.jsonl（SNS_DATA_DIR）。
新しい状態ファイルは持たない。過去レコード（ammo_key の無い時代のもの）は、
status=posted の text から text_hash を都度計算して後方互換で取り込む。
"""
import hashlib
import json
import os
import re

_DIR = os.path.dirname(os.path.abspath(__file__))

_WS_RE = re.compile(r"\s+")


def _paths() -> tuple[str, str]:
    """(pending_queue.jsonl, posts_log.jsonl) のパス。テスト容易性のため呼び出し時に解決。"""
    base = os.getenv("SNS_DATA_DIR", _DIR)
    return (os.path.join(base, "pending_queue.jsonl"),
            os.path.join(base, "posts_log.jsonl"))


def _used_ammo_path() -> str:
    """手動焼却の記録（backfill_used_ammo.py が書く）。過去に投稿済みだった弾を
    ammo_key 導入後の世界に持ち込むための追記専用ファイル。"""
    return os.path.join(os.getenv("SNS_DATA_DIR", _DIR), "used_ammo.jsonl")


def record_used(entries: list[dict]) -> int:
    """弾の焼却を追記する。entries: [{ammo_key, pillar, reason}, ...]。書いた件数を返す。"""
    import datetime
    n = 0
    with open(_used_ammo_path(), "a", encoding="utf-8") as f:
        for e in entries:
            if not e.get("ammo_key"):
                continue
            rec = {"ammo_key": e["ammo_key"], "pillar": e.get("pillar", ""),
                   "reason": e.get("reason", ""),
                   "ts": datetime.datetime.now().isoformat(timespec="seconds")}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    return n


def _read_jsonl(path: str) -> list[dict]:
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


def text_hash(text: str) -> str:
    """本投稿本文の指紋。空白・改行の揺れだけを吸収した完全一致（sha1先頭16桁）。"""
    return hashlib.sha1(_WS_RE.sub("", text or "").encode("utf-8")).hexdigest()[:16]


def ammo_key(pillar: str, index: int, app_url: str = "https://x") -> str:
    """弾（テンプレ下敷き）の指紋。pillar と、その弾のテンプレ本文＋リプ本体から作る。
    弾の文言を改稿したら別の弾として扱われる（意図どおり: 新しい内容になったから）。"""
    import themes
    base = themes.template_post(pillar, index, app_url)
    raw = f"{pillar}\x1f{_WS_RE.sub('', base['text'])}\x1f{_WS_RE.sub('', base.get('reply') or '')}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def used_ammo_keys() -> set[str]:
    """これまでに下書き化（承認待ち/保留/却下/投稿済みを問わず）された弾の指紋集合。
    一度キューに載った弾は「作ったツイート」とみなし、二度と選ばない。"""
    qpath, ppath = _paths()
    keys = {r.get("ammo_key") for r in _read_jsonl(qpath)}
    keys |= {r.get("ammo_key") for r in _read_jsonl(ppath)}  # --post-now 直投稿分
    keys |= {r.get("ammo_key") for r in _read_jsonl(_used_ammo_path())}  # 手動焼却分
    keys.discard(None)
    keys.discard("")
    return keys


def posted_text_hashes() -> set[str]:
    """実際に X に投稿された本文の指紋集合（最終ゲート用）。
    キューの status=posted は text から都度計算（ammo_key 導入前の過去分も拾う）。"""
    qpath, ppath = _paths()
    hashes = {text_hash(r.get("text") or "") for r in _read_jsonl(qpath)
              if r.get("status") == "posted"}
    hashes |= {r.get("text_hash") for r in _read_jsonl(ppath)}
    hashes.discard(None)
    hashes.discard("")
    return hashes


def is_posted_duplicate(text: str) -> bool:
    """この本文は過去に投稿済みか（最終ゲート。True なら投稿してはならない）。"""
    return text_hash(text) in posted_text_hashes()


def pick_unused_index(pillar: str, start_index: int, app_url: str) -> int | None:
    """ローテ位置(start_index)から順に、未使用の弾の index を返す。全弾使用済みなら None。
    未使用判定は ammo_key に加え、テンプレ素の文面が投稿済み本文と一致する場合も除外
    （ammo_key 導入前にテンプレ素のまま投稿された過去分への保険）。"""
    import themes
    n = themes.pool_size(pillar)
    used = used_ammo_keys()
    posted = posted_text_hashes()
    for k in range(n):
        i = (start_index + k) % n
        if ammo_key(pillar, i, app_url) in used:
            continue
        if text_hash(themes.template_post(pillar, i, app_url)["text"]) in posted:
            continue
        return i
    return None


def used_first_lines(pillar: str, limit: int = 40) -> list[str]:
    """その型でこれまでに作った下書き本文の1行目一覧（新作生成の除外リスト用）。新しい順。"""
    qpath, _ = _paths()
    rows = [r for r in _read_jsonl(qpath) if r.get("pillar") == pillar]
    lines: list[str] = []
    for r in reversed(rows):
        t = (r.get("text") or "").strip()
        if t:
            first = t.splitlines()[0]
            if first not in lines:
                lines.append(first)
        if len(lines) >= limit:
            break
    return lines


def used_texts(pillar: str, limit: int = 15) -> list[str]:
    """その型でこれまでに作った下書き本文の一覧（診断導線フックの除外リスト用）。新しい順。"""
    qpath, _ = _paths()
    rows = [r for r in _read_jsonl(qpath) if r.get("pillar") == pillar]
    return [r.get("text") or "" for r in reversed(rows) if r.get("text")][:limit]
