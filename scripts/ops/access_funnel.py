#!/usr/bin/env python3
# LP到達ファネルの週次スナップショット（LLM不使用・VPSホストcronで実行）。
#   Caddyアクセスログ(/data/access.log*) + 本番SQLite(/data/app.db) から
#   ページ閲覧数 / ユニークIP / 診断実行数 / 実会員数 を集計し、
#   /var/log/access_funnel.jsonl に1行追記する（growth-operator が週次レポートで読む）。
#
# 実行: python3 /opt/vocalcoach/scripts/ops/access_funnel.py
#   host から docker exec で caddy / backend コンテナに入るため、host で実行する
#   （sns コンテナ内からは他コンテナを exec できない）。
# cron 登録は scripts/deploy/remote_deploy.sh と scripts/sns_autopost/setup_approval.sh の両方。
import json, re, subprocess, sys, time
from datetime import datetime, timezone

WINDOW_DAYS = 7
JSONL = "/var/log/access_funnel.jsonl"
CADDY = "docker-caddy-1"
BACKEND = "docker-backend-1"

now = time.time()
since = now - WINDOW_DAYS * 86400

# 静的アセット/API/sns を除外し「HTMLページ相当のGET」だけをページ閲覧とみなす
ASSET = re.compile(r"\.(css|js|mjs|png|jpe?g|svg|ico|gif|webp|woff2?|ttf|map|txt|xml|webmanifest)(\?|$)", re.I)
SKIP_PREFIX = ("/api", "/sns", "/healthz", "/_next", "/favicon")


def sh(args):
    return subprocess.run(args, capture_output=True, text=True).stdout


def access_stats():
    """Caddyアクセスログから直近WINDOW日のページ閲覧数とユニークIPを数える。"""
    raw = sh(["docker", "exec", CADDY, "sh", "-c", "cat /data/access.log* 2>/dev/null"])
    views = 0
    ips = set()
    for line in raw.splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("ts", 0) < since:
            continue
        req = d.get("request", {})
        if req.get("method") != "GET":  # HEAD ヘルスチェック等は除外
            continue
        full_uri = req.get("uri") or ""
        path = full_uri.split("?", 1)[0]
        if not path or any(path.startswith(p) for p in SKIP_PREFIX) or ASSET.search(full_uri):
            continue
        views += 1
        ip = req.get("client_ip") or req.get("remote_ip")
        if ip:
            ips.add(ip)
    return views, len(ips)


def db_counts():
    """本番SQLiteから診断数・実会員数（@example.com のテストアカウントを除外）を取る。"""
    py = (
        "import sqlite3,datetime;"
        "c=sqlite3.connect('/data/app.db').cursor();"
        f"cut=(datetime.datetime.utcnow()-datetime.timedelta(days={WINDOW_DAYS})).strftime('%Y-%m-%d %H:%M:%S');"
        "dt=c.execute('SELECT COUNT(*) FROM voice_type_diagnoses').fetchone()[0];"
        "d7=c.execute('SELECT COUNT(*) FROM voice_type_diagnoses WHERE created_at>=?',(cut,)).fetchone()[0];"
        "ut=c.execute(\"SELECT COUNT(*) FROM users WHERE email NOT LIKE '%@example.com'\").fetchone()[0];"
        "u7=c.execute(\"SELECT COUNT(*) FROM users WHERE email NOT LIKE '%@example.com' AND created_at>=?\",(cut,)).fetchone()[0];"
        "print(dt,d7,ut,u7)"
    )
    out = sh(["docker", "exec", BACKEND, "python3", "-c", py]).split()
    if len(out) != 4:
        return None
    return [int(x) for x in out]


def main():
    views, uips = access_stats()
    db = db_counts()
    rec = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": WINDOW_DAYS,
        "page_views": views,
        "unique_ips": uips,
        "diagnoses_total": db[0] if db else None,
        "diagnoses_window": db[1] if db else None,
        "users_real_total": db[2] if db else None,
        "users_real_window": db[3] if db else None,
    }
    try:
        with open(JSONL, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"WARN: jsonl書き込み失敗: {e}", file=sys.stderr)
    print(
        f"[access_funnel {rec['ts']}] 直近{WINDOW_DAYS}日: "
        f"ページ閲覧={views} / ユニークIP={uips} / "
        f"診断(累計{rec['diagnoses_total']}, 期間{rec['diagnoses_window']}) / "
        f"実会員(累計{rec['users_real_total']}, 期間{rec['users_real_window']})"
    )


if __name__ == "__main__":
    main()
