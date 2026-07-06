#!/usr/bin/env python3
"""Xリード獲得の探索パイプライン（docs/58/59、フォロー候補版）。

「歌の悩みを実況している人」を集めて選別し、**フォローすべき人だけ**を
LINEに一覧で届ける（返信文は生成しない。2026-07-06 方針転換）。
**フォローの実行は常に運用者がXアプリで自分の指で行う**（write自動化なし）。

自動フォローを実装しない理由: Xの自動化ポリシーはフォロー/アンフォローの
「大量・機械的な実行」自体を禁止行為として明記しており、これは人間が
ボタンを1回押しただけかどうかに関係ない（＝一括フォローAPIをボタン化しても
規約上のリスクは消えない）。LINEの[✅全員フォローした]ボタンは
「Xアプリで手動フォローした」という自己申告を記録するだけで、
X APIへのfollow呼び出しはコードのどこにも存在しない。

候補ソース（優先順・安い順）:
  1. --input ファイル（運用者ペースト方式。oEmbed＝無料・無認証）
  2. 自投稿へのメンション/リプ（owned read ≒$0.001/件。最高熱度）
  3. 従量API検索（post read $0.005/件＋通過分だけ user read $0.010/件＝遅延lookup）

コスト・安全ガード:
  - LEAD_DAILY_READ_BUDGET_USD（既定 0.60）… 当日のread概算がこれを超えたら探索停止
  - MAX_FOLLOWS_PER_DAY（既定 15）… 1日に提案するフォロー候補数の上限
    （公式に「安全な数」は存在しないが、新規/小規模アカウントの経験則として
    フォロー速度のスパイクを避ける目安。docs/60 に根拠と運用ガイドを記載）

使い方:
  python lead_finder.py --dry-run                 # 生成のみ表示（既定の安全側）
  python lead_finder.py --input leads_input.jsonl # ペースト方式（無料）
  python lead_finder.py                           # メンション＋API検索（要Xキー）
  オプション: --no-search / --no-mentions
"""
import argparse
import datetime
import html as html_mod
import json
import os
import re
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.getenv("SNS_DATA_DIR", _DIR)
READS_LOG = os.path.join(_DATA_DIR, "lead_reads_log.jsonl")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_DIR, ".env"))
except Exception:
    pass

import requests

import approval_queue as q
import leads
import line_client

# 従量課金の単価（docs/59 §2.1。概算ガード用。変動したらここを直す）
PRICE = {"post_read": 0.005, "user_read": 0.010, "owned_read": 0.001}


def _truthy(v: str | None) -> bool:
    return (v or "").strip().lower() in ("1", "true", "yes", "on")


class ReadMeter:
    """当日のread課金の概算メーター（LEAD_DAILY_READ_BUDGET_USD ガード）。"""

    def __init__(self):
        self.counts = {k: 0 for k in PRICE}
        self.budget = float(os.getenv("LEAD_DAILY_READ_BUDGET_USD", "0.60"))
        self.spent_today = self._spent_today()

    @staticmethod
    def _spent_today() -> float:
        today = datetime.date.today().isoformat()
        total = 0.0
        if os.path.exists(READS_LOG):
            with open(READS_LOG, encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                        if r.get("date") == today:
                            total += float(r.get("usd", 0))
                    except Exception:
                        pass
        return total

    def add(self, kind: str, n: int = 1) -> None:
        self.counts[kind] += n

    def usd(self) -> float:
        return sum(PRICE[k] * n for k, n in self.counts.items())

    def over(self) -> bool:
        return (self.spent_today + self.usd()) >= self.budget

    def persist(self) -> None:
        if not any(self.counts.values()):
            return
        rec = {"date": datetime.date.today().isoformat(), **self.counts,
               "usd": round(self.usd(), 4),
               "ts": datetime.datetime.now().isoformat(timespec="seconds")}
        with open(READS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _session():
    """X API v2 の OAuth1 セッション（fetch_metrics.py と同じ鍵）。無ければ None。"""
    keys = {k: os.getenv(k) for k in
            ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")}
    if not all(keys.values()):
        return None
    from requests_oauthlib import OAuth1Session
    return OAuth1Session(
        keys["X_API_KEY"], client_secret=keys["X_API_SECRET"],
        resource_owner_key=keys["X_ACCESS_TOKEN"],
        resource_owner_secret=keys["X_ACCESS_SECRET"],
    )


_TAG_RE = re.compile(r"<[^>]+>")


def _fetch_oembed(url: str) -> tuple[str, str] | None:
    """oEmbed（無料・無認証）でツイート本文と著者handleを取る。失敗なら None。"""
    try:
        r = requests.get("https://publish.twitter.com/oembed",
                         params={"url": url, "omit_script": "1"}, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        text = html_mod.unescape(_TAG_RE.sub(" ", data.get("html") or "")).strip()
        text = re.sub(r"\s+", " ", text)
        # 末尾の「— 著者 (@handle) 日付」を落として本文だけに
        text = re.sub(r"[—-]\s*[^—-]*\(@\w+\)[^()]*$", "", text).strip()
        m = re.search(r"(?:twitter|x)\.com/(\w+)", data.get("author_url") or "")
        handle = m.group(1) if m else (data.get("author_name") or "")
        return text, handle
    except Exception:
        return None


def _tweet_url(handle: str, tweet_id: str) -> str:
    return f"https://x.com/{handle.lstrip('@')}/status/{tweet_id}"


# --- 候補ソース ------------------------------------------------------------------

def source_input(path: str) -> list[dict]:
    """運用者ペースト方式: {url, query_id, followers?} を1行1件で読む（無料）。"""
    out = []
    if not os.path.exists(path):
        print(f"[warn] 入力ファイルが見つかりません: {path}", file=sys.stderr)
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                print(f"[warn] JSONとして読めない行をスキップ: {line[:60]}", file=sys.stderr)
                continue
            got = _fetch_oembed(row.get("url", ""))
            if not got:
                print(f"[warn] oEmbed取得失敗をスキップ: {row.get('url', '?')}", file=sys.stderr)
                continue
            text, handle = got
            out.append({"url": row.get("url", ""), "handle": handle, "text": text,
                        "query_id": row.get("query_id", "utattemita"),
                        "source": "input", "followers": row.get("followers"), "bio": ""})
    return out


def source_mentions(oauth, meter: ReadMeter, limit: int = 20) -> list[dict]:
    """自投稿へのメンション/リプ（owned read ≒$0.001）。最高熱度・最安のソース。"""
    out = []
    try:
        me = oauth.get("https://api.twitter.com/2/users/me", timeout=20)
        if me.status_code != 200:
            print(f"[warn] users/me 失敗 HTTP {me.status_code}", file=sys.stderr)
            return out
        meter.add("owned_read", 1)
        my_id = me.json()["data"]["id"]
        r = oauth.get(
            f"https://api.twitter.com/2/users/{my_id}/mentions",
            params={"max_results": limit, "tweet.fields": "author_id,lang",
                    "expansions": "author_id",
                    "user.fields": "public_metrics,description,username"},
            timeout=20)
        if r.status_code != 200:
            print(f"[warn] mentions 失敗 HTTP {r.status_code}: {r.text[:120]}", file=sys.stderr)
            return out
        body = r.json()
        tweets = body.get("data") or []
        meter.add("owned_read", len(tweets))
        users = {u["id"]: u for u in (body.get("includes") or {}).get("users", [])}
        for t in tweets:
            u = users.get(t.get("author_id"), {})
            handle = u.get("username", "")
            out.append({"url": _tweet_url(handle, t["id"]), "handle": handle,
                        "text": t.get("text", ""), "query_id": "mention",
                        "source": "mention",
                        "followers": (u.get("public_metrics") or {}).get("followers_count"),
                        "bio": u.get("description", "")})
    except Exception as e:
        print(f"[warn] メンション取得に失敗: {e}", file=sys.stderr)
    return out


def source_search(oauth, meter: ReadMeter, want: int) -> list[dict]:
    """従量API検索（post read $0.005/件）。クエリは日替わりでローテーション。
    フォロワー数/bio はこの段階では取らない（遅延lookup。docs/59 §2.1改）。"""
    out = []
    qs = leads.search_queries()
    per_run = int(os.getenv("LEAD_QUERIES_PER_RUN", "3"))
    start = datetime.date.today().toordinal() % len(qs)
    rotated = [qs[(start + i) % len(qs)] for i in range(min(per_run, len(qs)))]
    for spec in rotated:
        if meter.over():
            print(f"[info] read予算に到達したため検索を停止（概算 ${meter.usd():.3f}）")
            break
        if len(out) >= want:
            break
        try:
            r = oauth.get(
                "https://api.twitter.com/2/tweets/search/recent",
                params={"query": f"({spec['query']}){leads.SEARCH_SUFFIX}",
                        "max_results": 10, "tweet.fields": "author_id,lang"},
                timeout=20)
            if r.status_code != 200:
                print(f"[warn] 検索失敗({spec['id']}) HTTP {r.status_code}: {r.text[:120]}",
                      file=sys.stderr)
                continue
            tweets = r.json().get("data") or []
            meter.add("post_read", len(tweets))
            for t in tweets:
                out.append({"tweet_id": t["id"], "author_id": t.get("author_id"),
                            "handle": "", "text": t.get("text", ""),
                            "query_id": spec["id"], "source": "search",
                            "followers": None, "bio": "", "url": ""})
        except Exception as e:
            print(f"[warn] 検索に失敗({spec['id']}): {e}", file=sys.stderr)
    return out


def hydrate_users(oauth, meter: ReadMeter, cands: list[dict]) -> None:
    """遅延lookup: 本文フィルタを通過した検索候補だけ user read（$0.010/件）で
    handle/フォロワー数/bio を埋める。in-placeで更新。"""
    ids = sorted({c["author_id"] for c in cands if c.get("author_id") and not c.get("handle")})
    if not ids or oauth is None:
        return
    users: dict[str, dict] = {}
    for i in range(0, len(ids), 100):
        if meter.over():
            print("[info] read予算に到達したため user lookup を停止")
            break
        chunk = ids[i:i + 100]
        try:
            r = oauth.get("https://api.twitter.com/2/users",
                          params={"ids": ",".join(chunk),
                                  "user.fields": "public_metrics,description,username"},
                          timeout=20)
            if r.status_code != 200:
                print(f"[warn] user lookup 失敗 HTTP {r.status_code}", file=sys.stderr)
                continue
            data = r.json().get("data") or []
            meter.add("user_read", len(data))
            users.update({u["id"]: u for u in data})
        except Exception as e:
            print(f"[warn] user lookup に失敗: {e}", file=sys.stderr)
    for c in cands:
        u = users.get(c.get("author_id") or "")
        if u:
            c["handle"] = u.get("username", "")
            c["followers"] = (u.get("public_metrics") or {}).get("followers_count")
            c["bio"] = u.get("description", "")
            c["url"] = _tweet_url(c["handle"], c.get("tweet_id", ""))


# --- メイン -----------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Xフォロー候補の探索（write自動化なし）")
    ap.add_argument("--input", help="運用者ペースト方式の候補ファイル(jsonl)")
    ap.add_argument("--dry-run", action="store_true",
                    help="生成のみ表示（LINE・記録に触れない）")
    ap.add_argument("--no-search", action="store_true", help="従量API検索を使わない")
    ap.add_argument("--no-mentions", action="store_true", help="メンション取得を使わない")
    args = ap.parse_args()

    dry = args.dry_run or _truthy(os.getenv("DRY_RUN", "1"))  # 既定は安全側
    max_per_day = int(os.getenv("MAX_FOLLOWS_PER_DAY", "15"))
    slots = max_per_day - (0 if dry else q.suggested_today())
    if slots <= 0:
        print(f"本日の提示上限（MAX_FOLLOWS_PER_DAY={max_per_day}）に到達済み。終了します。")
        return 0

    meter = ReadMeter()
    if meter.over():
        print(f"本日のread予算（${meter.budget}）を消化済み。探索せず終了します。")
        return 0

    # --- 候補収集（安い順）---
    cands: list[dict] = []
    if args.input:
        cands += source_input(args.input)
    oauth = _session()
    if oauth is None and not args.input:
        print("Xキー未設定です。--input で運用者ペースト方式を使ってください"
              "（.env に X_API_KEY 等を設定すると自動探索が有効になります）。")
        return 0
    if oauth is not None:
        if not args.no_mentions and not meter.over():
            cands += source_mentions(oauth, meter)
        if not args.no_search and not meter.over():
            cands += source_search(oauth, meter, want=slots * 3)

    # --- 選別（本文ベース）→ 遅延lookup → 再選別（フォロワー/bio）---
    engaged = q.engaged_handles()
    dropped: list[tuple[str, str]] = []
    seen_handles: set[str] = set()

    def pre_pass(c: dict) -> bool:
        ok, reason = leads.select(c, engaged)
        if not ok:
            dropped.append((c.get("handle") or c.get("tweet_id") or "?", reason))
        return ok

    survivors = [c for c in cands if pre_pass(c)]
    hydrate_users(oauth, meter, [c for c in survivors if c.get("source") == "search"])

    final: list[dict] = []
    for c in survivors:
        handle = (c.get("handle") or "").lstrip("@").lower()
        if handle and handle in seen_handles:
            dropped.append((handle, "同一実行内の重複"))
            continue
        ok, reason = leads.select(c, engaged)  # lookup後の値で最終判定
        if not ok:
            dropped.append((handle or "?", reason))
            continue
        seen_handles.add(handle)
        c["select_note"] = reason
        final.append(c)
    if len(final) > slots:
        print(f"[info] 上限により {len(final) - slots} 件を切り捨て"
              f"（MAX_FOLLOWS_PER_DAY={max_per_day}）")
        final = final[:slots]

    meter.persist() if not dry else None
    print(f"[info] 候補{len(cands)}件 → 通過{len(final)}件 / 除外{len(dropped)}件 "
          f"/ read概算 ${meter.usd():.3f}（本日累計 ${meter.spent_today + meter.usd():.3f}"
          f" / 予算 ${meter.budget}）")
    for who, why in dropped[:10]:
        print(f"  - 除外 {who}: {why}")

    if not final:
        msg = "🎯 フォロー候補: 本日は該当なしでした。"
        print(msg)
        if not dry:
            line_client.push_text(msg)
        return 0

    digest = [{"handle": c.get("handle", ""), "query_id": c["query_id"],
              "reason": leads.QUERY_BY_ID.get(c["query_id"], {}).get("intent", ""),
              "followers": c.get("followers"), "source_text": c["text"],
              "url": c.get("url", "")} for c in final]

    if dry:
        print("=" * 56)
        for i, c in enumerate(digest, 1):
            print(f"[DRY] {i}. @{c['handle']}（{c['reason']} / followers={c['followers']}）\n"
                  f"     {c['source_text'][:100]}\n     {c['url']}")
        print("DRY_RUN: 生成のみ。LINE・記録はいずれも触れていません。")
        return 0

    batch_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    q.suggest_leads(digest, batch_id)
    ok, info = line_client.push_lead_digest(digest, batch_id)
    if ok:
        print(f"LINEに {len(digest)} 件のフォロー候補を送りました"
              "（実行はXアプリでご自身の指で）。")
    else:
        print(f"[warn] LINE送信失敗（{info}）。候補はengaged_logに記録済み。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
