#!/usr/bin/env python3
# 毎朝の定例メトリクスを前日(JST)ぶん集計して運用者にLINEで1通プッシュする。
#   出す数字:
#     1. サービスページ訪問者数(非会員含む) … Caddyアクセスログのユニーク訪問IP（＋ページ閲覧数）
#     2. 新規登録者数                        … 本番SQLite users（@example.com のテストは除外＝実会員）
#     3. ログインUU(＝アクティビティUU)       … その日に認証必須の操作(チャット/録音/FB)をした
#                                              ユニーク実会員。真のログイン記録が無いための代替値。
#     4. メール経由の訪問/同日ログイン        … ウェルカムメールのリンク(src=welcome_mail)を
#                                              踏んだIPと、同日のログインAPI成功IPの突合（推定）。
#
# 設計は scripts/ops/access_funnel.py（週次ファネル）と同じ「VPSホストcron + docker exec」方式で、
# 訪問者数・実会員の定義もそれに揃える（週次と日次で数字がブレないように）。
#   - host から docker exec で caddy(アクセスログ) / backend(SQLite) を読む
#     （sns コンテナ内からは兄弟コンテナを exec できないため host 実行）。
#   - LINE送信は既存の sns コンテナ内 line_client.push_text() を docker exec で叩いて再利用する。
#
# 実行: python3 /opt/vocalcoach/scripts/ops/daily_metrics_line.py
#   DRY_RUN=1 を付けると集計だけ表示しLINE送信しない。
# cron 登録は scripts/deploy/remote_deploy.sh と scripts/sns_autopost/setup_approval.sh の両方
# （毎朝 8:00 JST。サーバTZ=JST）。
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
UTC = timezone.utc
JSONL = "/var/log/daily_metrics.jsonl"
CADDY = "docker-caddy-1"
BACKEND = "docker-backend-1"
SNS = "docker-sns-1"

# access_funnel.py と同じ除外規則（静的アセット/API/sns を除いた「HTMLページ相当のGET」だけ数える）
ASSET = re.compile(r"\.(css|js|mjs|png|jpe?g|svg|ico|gif|webp|woff2?|ttf|map|txt|xml|webmanifest)(\?|$)", re.I)
SKIP_PREFIX = ("/api", "/sns", "/healthz", "/_next", "/favicon")


def sh(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout


def yesterday_window(now: datetime) -> tuple[datetime, datetime]:
    y = (now.astimezone(JST) - timedelta(days=1)).date()
    start = datetime(y.year, y.month, y.day, tzinfo=JST)
    return start, start + timedelta(days=1)


def access_stats(start: datetime, end: datetime) -> dict:
    """Caddyアクセスログから前日(JST)のページ閲覧数・ユニーク訪問IPに加え、
    メール経由の流入を数える。

    メール経由の定義（docs/86。ウェルカムメールのリンクは src=welcome_mail 付き）:
      - mail_visits    … src=welcome_mail 付きURIを踏んだユニークIP数
      - mail_logins_est … そのIPのうち、同日中に POST /api/v1/auth/login が 200 を
                          返したIP数（IP突合の推定値。真のクリック→ログイン紐付けでは
                          ない。モバイル回線のIP変動で取りこぼす可能性あり）
    """
    s, e = start.timestamp(), end.timestamp()
    raw = sh(["docker", "exec", CADDY, "sh", "-c", "cat /data/access.log* 2>/dev/null"])
    views = 0
    ips: set[str] = set()
    mail_ips: set[str] = set()
    login_ips: set[str] = set()
    for line in raw.splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        ts = d.get("ts", 0)
        if not (s <= ts < e):
            continue
        req = d.get("request", {})
        full_uri = req.get("uri") or ""
        path = full_uri.split("?", 1)[0]
        ip = req.get("client_ip") or req.get("remote_ip")
        # メール経由の突合はページ閲覧の除外規則より前に見る（/api も対象のため）
        if ip and "src=welcome_mail" in full_uri:
            mail_ips.add(ip)
        if (
            ip
            and req.get("method") == "POST"
            and path == "/api/v1/auth/login"
            and d.get("status") == 200
        ):
            login_ips.add(ip)
        if req.get("method") != "GET":
            continue
        if not path or any(path.startswith(p) for p in SKIP_PREFIX) or ASSET.search(full_uri):
            continue
        views += 1
        if ip:
            ips.add(ip)
    return {
        "page_views": views,
        "visitors": len(ips),
        "mail_visits": len(mail_ips),
        "mail_logins_est": len(mail_ips & login_ips),
    }


# backend コンテナ内で走らせるDB集計。窓の境界は US/UE 環境変数で渡す（文字列クォート事故を避ける）。
# @example.com のテストアカウントは登録数・UU・メール一覧の全てから除外（access_funnel の実会員定義）。
_DB_SCRIPT = r"""
import sqlite3, json, os
c = sqlite3.connect('/data/app.db').cursor()
us, ue = os.environ["US"], os.environ["UE"]
# 実会員(@example.com のテスト除外)の id->email
id2email = dict(c.execute("SELECT id, email FROM users WHERE email NOT LIKE '%@example.com'"))
# 新規登録（実会員）の email 一覧（登録順）
reg_emails = [e for (_i, e) in c.execute(
    "SELECT id, email FROM users WHERE email NOT LIKE '%@example.com' "
    "AND created_at>=? AND created_at<? ORDER BY created_at", (us, ue))]
# アクティビティUU: その日に作成 or 更新された chat_sessions / recordings ＋ その日のFB
uu = set()
for r in c.execute("SELECT DISTINCT user_id FROM chat_sessions "
                   "WHERE (created_at>=? AND created_at<?) OR (updated_at>=? AND updated_at<?)",
                   (us, ue, us, ue)):
    uu.add(r[0])
for r in c.execute("SELECT DISTINCT user_id FROM recordings "
                   "WHERE (created_at>=? AND created_at<?) OR (updated_at>=? AND updated_at<?)",
                   (us, ue, us, ue)):
    uu.add(r[0])
for r in c.execute("SELECT DISTINCT user_id FROM message_feedback "
                   "WHERE created_at>=? AND created_at<?", (us, ue)):
    uu.add(r[0])
# 実会員だけに絞ってメール化（None・テストアカウントは id2email に無いので自然に落ちる）
uu_emails = sorted(id2email[i] for i in uu if i in id2email)
print(json.dumps({"registrations": len(reg_emails), "reg_emails": reg_emails,
                  "active_uu": len(uu_emails), "uu_emails": uu_emails}))
"""


def db_counts(start: datetime, end: datetime) -> dict | None:
    """本番SQLiteから前日(JST)の新規登録・アクティビティUUの件数と、それぞれのメール一覧を取る。"""
    us = start.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")
    ue = end.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")
    out = subprocess.run(
        ["docker", "exec", "-i", "-e", f"US={us}", "-e", f"UE={ue}", BACKEND, "python3", "-"],
        input=_DB_SCRIPT, capture_output=True, text=True,
    ).stdout.strip()
    try:
        return json.loads(out)
    except Exception:
        return None


def _with_emails(header: str, emails: list[str]) -> str:
    """見出し行の下に、該当メールを1行ずつぶら下げる。0人なら見出しだけ。"""
    if not emails:
        return header
    return header + "\n" + "\n".join(f"　・{e}" for e in emails)


def build_message(day: datetime, acc: dict, db: dict | None) -> str:
    if db is None:
        reg_line = "🆕 新規登録: 取得失敗"
        uu_line = "🔑 ログインUU(認証操作したユニーク): 取得失敗"
    else:
        reg_line = _with_emails(f"🆕 新規登録: {db['registrations']}人", db.get("reg_emails", []))
        uu_line = _with_emails(
            f"🔑 ログインUU(認証操作したユニーク): {db['active_uu']}人", db.get("uu_emails", [])
        )
    return (
        f"📊 前日のサービス指標（{day:%Y-%m-%d} JST）\n"
        f"{'─' * 16}\n"
        f"👥 訪問者(非会員含む): {acc['visitors']}人 / PV {acc['page_views']}\n"
        f"{reg_line}\n"
        f"{uu_line}\n"
        f"📩 メール経由: 訪問 {acc.get('mail_visits', 0)}人 / "
        f"同日ログイン {acc.get('mail_logins_est', 0)}人(IP突合の推定)"
    )


def push_line(msg: str) -> tuple[bool, str]:
    """sns コンテナ内の line_client.push_text() を docker exec で呼ぶ。

    本文は -e で環境変数に渡す（引数のシェルクォートを避け、改行もそのまま通す）。
    """
    code = (
        "import os;import line_client;"
        "ok,info=line_client.push_text(os.environ['DAILY_MSG']);"
        "print('OK' if ok else 'NG', info)"
    )
    r = subprocess.run(
        ["docker", "exec", "-w", "/app", "-e", f"DAILY_MSG={msg}", SNS, "python", "-c", code],
        capture_output=True, text=True,
    )
    out = (r.stdout + r.stderr).strip()
    return (r.returncode == 0 and out.startswith("OK")), out


def main() -> int:
    now = datetime.now(JST)
    start, end = yesterday_window(now)
    acc = access_stats(start, end)
    db = db_counts(start, end)
    msg = build_message(start, acc, db)
    print(msg)

    # 履歴も残す（後から推移を追えるように access_funnel と同じ jsonl 方式）
    rec = {
        "ts": now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "day_jst": f"{start:%Y-%m-%d}",
        "visitors": acc["visitors"],
        "page_views": acc["page_views"],
        "registrations": db["registrations"] if db else None,
        "active_uu": db["active_uu"] if db else None,
        "mail_visits": acc["mail_visits"],
        "mail_logins_est": acc["mail_logins_est"],
    }
    try:
        with open(JSONL, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:  # noqa: BLE001
        print(f"WARN: jsonl書き込み失敗: {e}", file=sys.stderr)

    if os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes"):
        print("[dry-run] LINE送信はスキップ")
        return 0
    ok, info = push_line(msg)
    print(f"[LINE] {info}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
