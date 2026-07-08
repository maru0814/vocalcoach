#!/usr/bin/env python3
"""Threads（Meta公式 Threads API）投稿クライアント。docs/63/64。

X承認フローの配信先を増やすだけのクライアント。post() は post_to_x() と同形の
(ok, threads_id, info) を返し、generate_and_post.post_all() から呼ばれる。

投稿は2ステップ: ①コンテナ作成 POST /{user_id}/threads → ②公開 threads_publish。
画像は公開URL渡しの仕様のため、LINEプレビュー用に既存の GET /sns/img/{name}
（SNS_PUBLIC_BASE_URL 経由）をそのまま使う。base未設定ならテキストのみで投稿。

必要な環境変数（.env.example 参照）:
  THREADS_ENABLED=0        … 1でThreadsにも投稿（既定OFF＝完全に現状維持）
  THREADS_ACCESS_TOKEN=... … 長期トークン（約60日）。初回シード。以後は自動更新
  THREADS_USER_ID=...      … 投稿先ThreadsユーザーID

トークンは {SNS_DATA_DIR}/threads_token.json に保存し、45日経過で投稿時に
自動リフレッシュする（GET /refresh_access_token）。投稿は無料（docs/63）。
"""
import datetime
import json
import os
import sys
import tempfile
import time

import requests

_API = "https://graph.threads.net/v1.0"
_REFRESH_URL = "https://graph.threads.net/refresh_access_token"
_TIMEOUT = 20
TEXT_LIMIT = 500           # Threadsの本文上限
REFRESH_AFTER_DAYS = 45    # 期限(約60日)に対して余裕を持って更新

_DIR = os.path.dirname(os.path.abspath(__file__))
# 実行時データの保存先。本番は永続volume（/data等）を SNS_DATA_DIR で指定する。
_DATA_DIR = os.getenv("SNS_DATA_DIR", _DIR)
TOKEN_PATH = os.path.join(_DATA_DIR, "threads_token.json")


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in ("1", "true", "yes", "on")


def flag_enabled() -> bool:
    """THREADS_ENABLED が立っているか（キーの有無は見ない）。"""
    return _truthy(os.getenv("THREADS_ENABLED", "0"))


def enabled() -> bool:
    """投稿できる状態か（フラグ＋ユーザーID＋トークン）。"""
    return flag_enabled() and bool(os.getenv("THREADS_USER_ID")) and _load_token() is not None


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _write_token(access_token: str) -> dict:
    """トークンを原子的に保存（approval_queue._write_all と同じ tmp→replace 方式）。"""
    rec = {"access_token": access_token, "refreshed_at": _now()}
    d = os.path.dirname(TOKEN_PATH) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".threads_token.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False)
        os.replace(tmp, TOKEN_PATH)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return rec


def _load_token() -> dict | None:
    """threads_token.json を読む。無ければ .env のシードから作る。どちらも無ければ None。"""
    if os.path.exists(TOKEN_PATH):
        try:
            with open(TOKEN_PATH, encoding="utf-8") as f:
                rec = json.load(f)
            if rec.get("access_token"):
                return rec
        except Exception:
            pass
    seed = os.getenv("THREADS_ACCESS_TOKEN")
    if seed:
        return _write_token(seed)
    return None


def _maybe_refresh(rec: dict) -> str:
    """45日経過していたら長期トークンを延命して保存。失敗時は旧トークンで続行。
    注意: レスポンスにトークンが含まれるため、本文はログに出さない。"""
    token = rec.get("access_token", "")
    try:
        ts = datetime.datetime.fromisoformat(rec.get("refreshed_at", ""))
        age_days = (datetime.datetime.now() - ts).days
    except Exception:
        age_days = REFRESH_AFTER_DAYS + 1  # 記録が壊れていれば更新を試みる
    if age_days < REFRESH_AFTER_DAYS:
        return token
    try:
        r = requests.get(_REFRESH_URL,
                         params={"grant_type": "th_refresh_token", "access_token": token},
                         timeout=_TIMEOUT)
        if r.status_code == 200:
            new = str(r.json().get("access_token") or "")
            if new:
                _write_token(new)
                return new
        print(f"[warn] Threadsトークン更新失敗 HTTP {r.status_code}", file=sys.stderr)
    except Exception as e:
        print(f"[warn] Threadsトークン更新例外: {e}", file=sys.stderr)
    return token


def _clip(text: str, limit: int = TEXT_LIMIT) -> str:
    """Threadsの上限(500字)に収める。超過分は末尾を「…」で切り詰め。"""
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


def _image_url(image_path: str | None) -> str | None:
    """公開画像URL（Threadsはバイト添付不可＝公開URL必須）。base未設定なら None。"""
    base = (os.getenv("SNS_PUBLIC_BASE_URL") or "").rstrip("/")
    if not image_path or not base:
        return None
    return f"{base}/sns/img/{os.path.basename(image_path)}"


def _create_container(user_id: str, token: str, text: str,
                      image_url: str | None = None,
                      reply_to: str | None = None) -> tuple[str | None, str]:
    """メディアコンテナ作成。returns (container_id, info)。"""
    data = {"access_token": token, "text": _clip(text)}
    if image_url:
        data["media_type"] = "IMAGE"
        data["image_url"] = image_url
    else:
        data["media_type"] = "TEXT"
    if reply_to:
        data["reply_to_id"] = reply_to
    r = requests.post(f"{_API}/{user_id}/threads", data=data, timeout=_TIMEOUT)
    if r.status_code in (200, 201):
        cid = str(r.json().get("id", ""))
        if cid:
            return cid, "ok"
    return None, f"HTTP {r.status_code}: {r.text[:200]}"


def _wait_ready(container_id: str, token: str) -> None:
    """コンテナの処理完了を待つ（2秒間隔・最大5回）。画像は通常数秒で FINISHED。
    確認に失敗しても最終的に publish を1回は試すため、ここでは例外にしない。"""
    for i in range(5):
        try:
            r = requests.get(f"{_API}/{container_id}",
                             params={"fields": "status,error_message", "access_token": token},
                             timeout=_TIMEOUT)
            if r.status_code == 200:
                status = r.json().get("status")
                if status in ("FINISHED", "ERROR", "EXPIRED"):
                    return
        except Exception:
            pass
        if i < 4:
            time.sleep(2)


def _publish(user_id: str, token: str, container_id: str) -> tuple[str | None, str]:
    """コンテナを公開して投稿IDを得る。returns (threads_id, info)。"""
    r = requests.post(f"{_API}/{user_id}/threads_publish",
                      data={"access_token": token, "creation_id": container_id},
                      timeout=_TIMEOUT)
    if r.status_code in (200, 201):
        pid = str(r.json().get("id", ""))
        if pid:
            return pid, "ok"
    return None, f"HTTP {r.status_code}: {r.text[:200]}"


def _post_one(user_id: str, token: str, text: str,
              image_url: str | None = None,
              reply_to: str | None = None) -> tuple[str | None, str]:
    """1件投稿（コンテナ作成→処理待ち→公開）。returns (threads_id, info)。"""
    cid, info = _create_container(user_id, token, text, image_url=image_url, reply_to=reply_to)
    if not cid:
        return None, f"コンテナ作成失敗 {info}"
    _wait_ready(cid, token)
    pid, info = _publish(user_id, token, cid)
    if not pid:
        return None, f"公開失敗 {info}"
    return pid, "ok"


def post(text: str, reply: str | None, link: str | None,
         post_link: bool, image_path: str | None = None) -> tuple[bool, str, str]:
    """本投稿(text)→リプ本体(reply)→(任意)URL の順にスレッド投稿する（post_to_x と同構造）。
    returns (ok, threads_id, info)。threads_id は本投稿のID。"""
    user_id = os.getenv("THREADS_USER_ID")
    rec = _load_token()
    if not user_id or not rec:
        return False, "", "THREADS_KEYS_MISSING"
    token = _maybe_refresh(rec)
    try:
        img = _image_url(image_path if image_path and os.path.exists(image_path) else None)
        pid, info = _post_one(user_id, token, text, image_url=img)
        if not pid:
            return False, "", info
        img_info = "+画像" if img else ""
        result, last_id = "本投稿OK" + img_info, pid
        if reply:                                   # 大事な中身を自己リプに（Xと同じ設計）
            rid, rinfo = _post_one(user_id, token, reply, reply_to=last_id)
            if rid:
                result, last_id = "本投稿+リプ本体" + img_info, rid
            else:
                result += f"/リプ本体失敗({rinfo})"
        if post_link and link and last_id:          # Xと同方針: 既定OFF
            lid, linfo = _post_one(user_id, token,
                                   f"▼ ここから無料で診断できます🎤\n{link}", reply_to=last_id)
            result += " +link" if lid else f" +link失敗({linfo})"
        return True, pid, result
    except Exception as e:
        return False, "", f"EXC: {e}"
