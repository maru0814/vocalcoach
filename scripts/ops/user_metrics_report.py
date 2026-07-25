#!/usr/bin/env python3
# 会員登録・声タイプ診断・シェア到達の累計スナップショット（読み取り専用・LLM不使用）。
#   出す数字:
#     1. 実会員数（@example.com のテストアカウント除外。access_funnel.py と同じ定義）
#     2. 声タイプ診断の累計実行数・タイプ別分布（voice_type_diagnoses。PIIなしイベント行）
#     3. シェア到達の代替指標 … Caddyアクセスログの GET /voice-type/share/* ヒット
#        （シェアボタン押下そのものはサーバ側で計測していないため、
#          「シェアされたリンクが開かれた/Xのカード取得が来た」を代替値として数える）
#
# 実行: VPSホスト上で python3 user_metrics_report.py
#   scripts/ops/access_funnel.py と同じ「host から docker exec で caddy/backend を読む」方式。
#   DBへの書き込み・ファイル出力は一切しない（stdout のみ）。
import json
import subprocess
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
CADDY = "docker-caddy-1"
BACKEND = "docker-backend-1"

BOT_UA = ("twitterbot", "facebookexternalhit", "slackbot", "discordbot", "linebot", "bot", "crawler", "spider")


def sh(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout


# backend コンテナ内で走らせるDB集計（読み取りのみ）。
# @example.com のテストアカウントは実会員から除外（access_funnel / daily_metrics と同じ定義）。
_DB_SCRIPT = r"""
import sqlite3, json
c = sqlite3.connect('file:/data/app.db?mode=ro', uri=True).cursor()
def one(q):
    r = c.execute(q).fetchone()
    return r[0] if r else None
out = {}
out['users_real'] = one("SELECT COUNT(*) FROM users WHERE email NOT LIKE '%@example.com'")
out['users_test'] = one("SELECT COUNT(*) FROM users WHERE email LIKE '%@example.com'")
out['users_real_7d'] = one("SELECT COUNT(*) FROM users WHERE email NOT LIKE '%@example.com' "
                           "AND created_at >= datetime('now','-7 day')")
out['user_first_at'] = one("SELECT MIN(created_at) FROM users WHERE email NOT LIKE '%@example.com'")
out['user_last_at'] = one("SELECT MAX(created_at) FROM users WHERE email NOT LIKE '%@example.com'")
out['diag_total'] = one("SELECT COUNT(*) FROM voice_type_diagnoses")
out['diag_7d'] = one("SELECT COUNT(*) FROM voice_type_diagnoses WHERE created_at >= datetime('now','-7 day')")
out['diag_last_at'] = one("SELECT MAX(created_at) FROM voice_type_diagnoses")
out['diag_by_type'] = dict(c.execute(
    "SELECT type_id, COUNT(*) FROM voice_type_diagnoses GROUP BY type_id ORDER BY COUNT(*) DESC"))
print(json.dumps(out, ensure_ascii=False))
"""


def db_snapshot() -> dict:
    raw = sh(["docker", "exec", BACKEND, "python", "-c", _DB_SCRIPT])
    try:
        return json.loads(raw.strip().splitlines()[-1])
    except Exception:
        return {"error": f"DB集計に失敗: {raw[-300:]!r}"}


def share_hits() -> dict:
    """Caddyアクセスログから /voice-type/share/* への到達を数える（シェアの代替指標）。"""
    raw = sh(["docker", "exec", CADDY, "sh", "-c", "cat /data/access.log* 2>/dev/null"])
    total = 0
    human = 0
    bots = 0
    ips: set[str] = set()
    by_day: dict[str, int] = {}
    last_ts = None
    for line in raw.splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        req = d.get("request", {})
        if req.get("method") != "GET":
            continue
        path = (req.get("uri") or "").split("?", 1)[0]
        if not path.startswith("/voice-type/share/"):
            continue
        total += 1
        ts = d.get("ts")
        if ts:
            last_ts = max(last_ts or 0, ts)
            day = datetime.fromtimestamp(ts, JST).strftime("%m/%d")
            by_day[day] = by_day.get(day, 0) + 1
        ua_list = (req.get("headers", {}) or {}).get("User-Agent") or [""]
        ua = (ua_list[0] if ua_list else "").lower()
        if any(b in ua for b in BOT_UA):
            bots += 1
        else:
            human += 1
            ip = req.get("client_ip") or req.get("remote_ip")
            if ip:
                ips.add(ip)
    return {
        "total": total,
        "human": human,
        "bots": bots,
        "unique_ips": len(ips),
        "by_day": by_day,
        "last_at": datetime.fromtimestamp(last_ts, JST).strftime("%Y-%m-%d %H:%M") if last_ts else None,
    }


def main() -> None:
    db = db_snapshot()
    share = share_hits()
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    print(f"📊 ユーザーメトリクス累計スナップショット（{now} JST 時点）")
    print("")
    print("■ 会員登録（実会員 = @example.com のテスト除外）")
    print(f"  累計: {db.get('users_real')} 人（直近7日: +{db.get('users_real_7d')}）")
    print(f"  初回登録: {db.get('user_first_at')} UTC / 最新登録: {db.get('user_last_at')} UTC")
    print(f"  （参考: テストアカウント {db.get('users_test')} 件）")
    print("")
    print("■ 声タイプ診断（voice_type_diagnoses）")
    print(f"  累計実行: {db.get('diag_total')} 件（直近7日: {db.get('diag_7d')} 件）")
    print(f"  最終実行: {db.get('diag_last_at')} UTC")
    print(f"  タイプ別: {json.dumps(db.get('diag_by_type'), ensure_ascii=False)}")
    print("")
    print("■ シェア到達（Caddyログの GET /voice-type/share/*。ボタン押下自体は未計測）")
    print(f"  総ヒット: {share['total']}（人間UA: {share['human']} / bot・カード取得: {share['bots']}）")
    print(f"  人間UAユニークIP: {share['unique_ips']} / 最終到達: {share['last_at']} JST")
    print(f"  日別: {json.dumps(share['by_day'], ensure_ascii=False)}")
    if "error" in db:
        print("")
        print(f"⚠ {db['error']}")


if __name__ == "__main__":
    main()
