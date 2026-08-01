#!/usr/bin/env python3
"""KPI日次集計 → Google スプレッドシート自動記録（docs/84）。

毎朝 cron（08:10 JST）で前日分を集計してシートに upsert する。初回は
--since でリリース日からの全日分をバックフィルする。

  指標: LP遷移UU（リンク別/ページ別）・診断UU・無料会員登録数・ログインUU・
        チャット利用UU・有料会員（新規/在籍）
  除外: オーナー(yumaruyama0814@gmail.com)と @example.com テスト
        （KPI_EXCLUDE_EMAILS で上書き可。IPベース指標はアカウント非紐付けのため除外不能）

実行（VPS host。sns コンテナからは兄弟コンテナを exec できないため host python3）:
  python3 /opt/vocalcoach/scripts/ops/kpi_daily_sheet.py                 # 前日分
  python3 ... --since 2026-06-06 [--until 2026-07-31]                    # バックフィル
  DRY_RUN=1 python3 ...                                                  # シートに書かず表示

シート書き込みは sns コンテナ内の kpi_sheets_push.py に委譲する
（gspread と KPI_SHEET_ID / GOOGLE_SA_JSON_B64 は scripts/sns_autopost/.env 側にある）。
cron 登録は scripts/deploy/remote_deploy.sh と scripts/sns_autopost/setup_approval.sh の両方。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
UTC = timezone.utc
CADDY = "docker-caddy-1"
BACKEND = "docker-backend-1"
SNS = "docker-sns-1"
STATE = "/var/log/kpi_premium_state.json"

RELEASE_DAY = date(2026, 6, 6)   # 本番ドメイン切替・診断機能公開（docs/84 §9）
LOG_START = date(2026, 7, 8)     # Caddyアクセスログ記録開始（docs/60。当日は08:40〜の部分集計）
OUTAGE = {date(2026, 7, 11) + timedelta(days=i) for i in range(4)}  # VPS電源断 7/11〜7/14

DEFAULT_EXCLUDES = "yumaruyama0814@gmail.com"

# KPI_* 設定は環境変数を優先し、無ければ sns の .env（VPS上の運用設定の正）から読む。
# host cron は .env を読まないため、KPI_SHEET_ID 等と同じ場所に置けるようにする。
SNS_ENV_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "sns_autopost", ".env"
)


def kpi_conf(key: str, default: str = "") -> str:
    if os.getenv(key):
        return os.environ[key]
    try:
        with open(SNS_ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1]
    except OSError:
        pass
    return default

# access_funnel.py / daily_metrics_line.py と同じページ判定
ASSET = re.compile(r"\.(css|js|mjs|png|jpe?g|svg|ico|gif|webp|woff2?|ttf|map|txt|xml|webmanifest)(\?|$)", re.I)
SKIP_PREFIX = ("/api", "/sns", "/healthz", "/_next", "/favicon")
# bot/監視の除外（uptime.yml の15分毎 curl、SNSリンクプレビュー等でUUが水増しされるのを防ぐ）
BOT_UA = re.compile(
    r"bot|crawl|spider|slurp|curl|wget|python|httpx|monitor|uptime|headless"
    r"|facebookexternalhit|preview|scan|go-http", re.I)

# ランディングページの分類（シート列と リンク別タブの表示名）
PATH_BUCKETS = [
    ("top", "トップ(/)"),
    ("shindan", "診断LP(/lp/shindan)"),
    ("voitore", "ボイトレLP(/lp/voitore)"),
    ("voicetype", "声タイプ(/voice-type)"),
    ("other", "その他"),
]
BUCKET_LABEL = dict(PATH_BUCKETS)


def path_bucket(path: str) -> str:
    if path == "/":
        return "top"
    if path.startswith("/lp/shindan"):
        return "shindan"
    if path.startswith("/lp/voitore"):
        return "voitore"
    if path.startswith("/voice-type"):
        return "voicetype"
    return "other"


def jst_day_of(ts: float) -> date:
    return datetime.fromtimestamp(ts, JST).date()


def parse_access(days: set[date], exclude_ips: set[str] = frozenset()) -> dict[date, dict]:
    """Caddyアクセスログを1回読み、対象日ごとに LP UU / リンク別UU / 診断UU(IP) を集計する。

    exclude_ips（KPI_EXCLUDE_IPS: オーナーの自宅等の固定IP）は全IPベース指標から除外する。
    """
    raw = subprocess.run(
        ["docker", "exec", CADDY, "sh", "-c", "cat /data/access.log* 2>/dev/null"],
        capture_output=True, text=True,
    ).stdout
    acc: dict[date, dict] = {
        d: {"total": set(), "buckets": {k: set() for k, _ in PATH_BUCKETS},
            "links": {}, "diag_ips": set()}
        for d in days
    }
    for line in raw.splitlines():
        try:
            rec = json.loads(line)
        except Exception:
            continue
        day = jst_day_of(rec.get("ts", 0))
        if day not in acc:
            continue
        req = rec.get("request", {})
        ip = req.get("client_ip") or req.get("remote_ip")
        if not ip or ip in exclude_ips:
            continue
        ua = (req.get("headers", {}).get("User-Agent") or [""])[0]
        if BOT_UA.search(ua):
            continue
        full_uri = req.get("uri") or ""
        path, _, query = full_uri.partition("?")
        a = acc[day]

        # 診断UU(IP推定): 診断解析POSTのユニークIP（計測実装前の期間の代替値）
        if req.get("method") == "POST" and path == "/api/v1/voice-type/analyze":
            a["diag_ips"].add(ip)
            continue
        # ページ閲覧（既存規則: 静的アセット/API等を除いたGET）
        if req.get("method") != "GET":
            continue
        if not path or any(path.startswith(p) for p in SKIP_PREFIX) or ASSET.search(full_uri):
            continue
        a["total"].add(ip)
        bucket = path_bucket(path)
        a["buckets"][bucket].add(ip)
        q = urllib.parse.parse_qs(query)
        link_key = (
            (q.get("utm_source") or ["(utmなし)"])[0],
            (q.get("utm_medium") or [""])[0],
            (q.get("utm_campaign") or [""])[0],
            BUCKET_LABEL[bucket],
        )
        a["links"].setdefault(link_key, set()).add(ip)
    return acc


# backend コンテナ内で走らせるDB集計（全対象日を1回のexecでまとめて処理）。
# 窓・除外メールは環境変数で渡す。login_events / 診断identity列は存在しない版の
# DBでも動くように毎回スキーマを確認する（デプロイ順序に依存しない）。
_DB_SCRIPT = r"""
import sqlite3, json, os, datetime, hashlib
c = sqlite3.connect('/data/app.db').cursor()
windows = json.loads(os.environ["WINDOWS"])
excludes = {e.strip().lower() for e in json.loads(os.environ["EXCLUDES"]) if e.strip()}
# 除外IPの匿名診断も落とす: backend の _visitor_hash と同じ式（sha256("JWT_SECRET:ip")）で
# ハッシュを再現して照合する。JWT_SECRET は backend コンテナ自身の env にある。
_secret = os.environ.get("JWT_SECRET", "")
excl_hashes = {hashlib.sha256(f"{_secret}:{ip}".encode()).hexdigest()
               for ip in json.loads(os.environ.get("EXCLUDE_IPS", "[]")) if _secret}

def has_table(name):
    return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None

def has_column(table, col):
    return any(r[1] == col for r in c.execute(f"PRAGMA table_info({table})"))

# 実会員 = @example.com テスト除外 + 指定メール（オーナー等）除外
id2email = {}
for i, e in c.execute("SELECT id, email FROM users WHERE email NOT LIKE '%@example.com'"):
    if (e or "").lower() not in excludes:
        id2email[i] = e
real_ids = set(id2email)

has_login = has_table('login_events')
has_diag_id = has_column('voice_type_diagnoses', 'user_id')
first_login = c.execute("SELECT MIN(created_at) FROM login_events").fetchone()[0] if has_login else None
first_diag_id = (c.execute(
    "SELECT MIN(created_at) FROM voice_type_diagnoses WHERE user_id IS NOT NULL OR visitor_hash IS NOT NULL"
).fetchone()[0] if has_diag_id else None)

days = {}
for day, us, ue in windows:
    regs = sum(1 for (i,) in c.execute(
        "SELECT id FROM users WHERE created_at>=? AND created_at<?", (us, ue)) if i in real_ids)
    login_uu = None
    if has_login:
        login_uu = sum(1 for (u,) in c.execute(
            "SELECT DISTINCT user_id FROM login_events WHERE created_at>=? AND created_at<?",
            (us, ue)) if u in real_ids)
    act = set()
    for tbl in ("chat_sessions", "recordings"):
        for (u,) in c.execute(
            f"SELECT DISTINCT user_id FROM {tbl} "
            "WHERE (created_at>=? AND created_at<?) OR (updated_at>=? AND updated_at<?)",
            (us, ue, us, ue)):
            act.add(u)
    for (u,) in c.execute(
        "SELECT DISTINCT user_id FROM message_feedback WHERE created_at>=? AND created_at<?",
        (us, ue)):
        act.add(u)
    activity_uu = len(act & real_ids)
    chat_uu = len({u for (u,) in c.execute(
        "SELECT DISTINCT s.user_id FROM chat_messages m JOIN chat_sessions s ON s.id=m.session_id "
        "WHERE m.created_at>=? AND m.created_at<?", (us, ue)) if u in real_ids})
    diag_count = c.execute(
        "SELECT COUNT(*) FROM voice_type_diagnoses WHERE created_at>=? AND created_at<?",
        (us, ue)).fetchone()[0]
    diag_uu = None
    if has_diag_id:
        idents = set()
        for uid, vh in c.execute(
            "SELECT user_id, visitor_hash FROM voice_type_diagnoses "
            "WHERE created_at>=? AND created_at<? AND (user_id IS NOT NULL OR visitor_hash IS NOT NULL)",
            (us, ue)):
            if uid is not None:
                if uid in real_ids:
                    idents.add(f"u:{uid}")
            elif vh and vh not in excl_hashes:
                idents.add(f"v:{vh}")
        diag_uu = len(idents)
    paid_new_created = 0
    if has_table('subscriptions'):
        paid_new_created = sum(1 for (u,) in c.execute(
            "SELECT user_id FROM subscriptions WHERE created_at>=? AND created_at<? "
            "AND status IN ('active','trialing')", (us, ue)) if u in real_ids)
    days[day] = {"regs": regs, "login_uu": login_uu, "activity_uu": activity_uu,
                 "chat_uu": chat_uu, "diag_count": diag_count, "diag_uu": diag_uu,
                 "paid_new_created": paid_new_created}

premium_emails = []
if has_table('subscriptions'):
    nowstr = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    for (u,) in c.execute(
        "SELECT user_id FROM subscriptions WHERE status IN ('active','trialing') "
        "AND current_period_end > ?", (nowstr,)):
        if u in real_ids:
            premium_emails.append(id2email[u])
print(json.dumps({"days": days, "first_login": first_login,
                  "first_diag_identity": first_diag_id,
                  "premium_emails": sorted(premium_emails)}))
"""


def db_stats(days: list[date], excludes: list[str],
             exclude_ips: list[str] | None = None) -> dict | None:
    windows = []
    for d in days:
        start = datetime(d.year, d.month, d.day, tzinfo=JST)
        windows.append([
            d.isoformat(),
            start.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            (start + timedelta(days=1)).astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S"),
        ])
    r = subprocess.run(
        ["docker", "exec", "-i",
         "-e", f"WINDOWS={json.dumps(windows)}",
         "-e", f"EXCLUDES={json.dumps(excludes)}",
         "-e", f"EXCLUDE_IPS={json.dumps(exclude_ips or [])}",
         BACKEND, "python3", "-"],
        input=_DB_SCRIPT, capture_output=True, text=True,
    )
    try:
        return json.loads(r.stdout.strip())
    except Exception:
        print(f"ERROR: DB集計に失敗: {r.stderr.strip()[:500]}", file=sys.stderr)
        return None


def _utc_str_to_jst_day(s: str | None) -> date | None:
    """DBのUTCナイーブ 'YYYY-MM-DD HH:MM:SS' をJSTの暦日に変換する。"""
    if not s:
        return None
    try:
        dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    except ValueError:
        return None
    return dt.astimezone(JST).date()


def load_state() -> dict:
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(premium_emails: list[str], as_of: date) -> None:
    try:
        with open(STATE, "w") as f:
            json.dump({"as_of": as_of.isoformat(), "premium_emails": premium_emails}, f)
    except Exception as e:  # noqa: BLE001
        print(f"WARN: 状態ファイル書き込み失敗: {e}", file=sys.stderr)


def build_rows(days: list[date], acc: dict[date, dict], db: dict | None,
               is_backfill: bool) -> tuple[list[list], list[list]]:
    first_login_day = _utc_str_to_jst_day((db or {}).get("first_login"))
    first_diag_day = _utc_str_to_jst_day((db or {}).get("first_diag_identity"))
    premium_now = (db or {}).get("premium_emails", [])
    state = load_state()
    prev_premium = set(state.get("premium_emails", []))

    daily_rows: list[list] = []
    link_rows: list[list] = []
    last_day = max(days)
    for d in days:
        notes = []
        a = acc.get(d)
        has_log = d >= LOG_START
        if not has_log:
            notes.append("ログ欠測(7/8開始)")
        elif d == LOG_START:
            notes.append("ログ開始日(08:40〜部分)")
        if d in OUTAGE:
            notes.append("VPS停止期間")

        if has_log and a:
            lp = [len(a["total"])] + [len(a["buckets"][k]) for k, _ in PATH_BUCKETS]
            for (src, med, camp, path_label), ips in sorted(a["links"].items()):
                link_rows.append([d.isoformat(), src, med, camp, path_label, len(ips)])
        else:
            lp = [""] * (1 + len(PATH_BUCKETS))

        day_db = (db or {}).get("days", {}).get(d.isoformat())
        if day_db is None:
            regs = login_uu = chat_uu = paid_new = diag_count = ""
            diag_uu = ""
            notes.append("DB集計失敗")
        else:
            regs = day_db["regs"]
            chat_uu = day_db["chat_uu"]
            diag_count = day_db["diag_count"]
            # ログインUU: login_events の初回記録日以降は真値、それ以前は代替値
            if first_login_day is not None and d >= first_login_day and day_db["login_uu"] is not None:
                login_uu = day_db["login_uu"]
            else:
                login_uu = day_db["activity_uu"]
                notes.append("ログインUUは代替値(アクティビティUU)")
            # 診断UU: identity記録日以降は真値 → ログがあればIP推定 → それ以前は欠測
            if first_diag_day is not None and d >= first_diag_day:
                diag_uu = day_db["diag_uu"]
            elif has_log and a:
                diag_uu = len(a["diag_ips"])
                notes.append("診断UUはIP推定")
            else:
                diag_uu = ""
            # 有料新規: 日次はスナップショット差分、バックフィルは created_at 近似
            if not is_backfill and d == last_day and prev_premium:
                paid_new = len(set(premium_now) - prev_premium)
            else:
                paid_new = day_db["paid_new_created"]
                if is_backfill and paid_new:
                    notes.append("有料新規はcreated_at近似")
        premium_total = len(premium_now) if d == last_day else ""
        daily_rows.append(
            [d.isoformat(), *lp, diag_uu, diag_count, regs, login_uu, chat_uu,
             paid_new, premium_total, " / ".join(notes)]
        )

    if db is not None:
        save_state(premium_now, last_day)
    return daily_rows, link_rows


def push_to_sheet(payload: dict) -> tuple[bool, str]:
    r = subprocess.run(
        ["docker", "exec", "-i", "-w", "/app", SNS, "python", "kpi_sheets_push.py"],
        input=json.dumps(payload, ensure_ascii=False), capture_output=True, text=True,
    )
    out = (r.stdout + r.stderr).strip()
    return (r.returncode == 0 and "OK" in r.stdout), out


def main() -> int:
    ap = argparse.ArgumentParser(description="KPI日次集計→スプレッドシート記録（docs/84）")
    ap.add_argument("--since", help="バックフィル開始日 YYYY-MM-DD（例: 2026-06-06）")
    ap.add_argument("--until", help="バックフィル終了日（省略時は前日）")
    args = ap.parse_args()

    yesterday = (datetime.now(JST) - timedelta(days=1)).date()
    if args.since:
        start = date.fromisoformat(args.since)
        end = date.fromisoformat(args.until) if args.until else yesterday
        is_backfill = True
    else:
        start = end = yesterday
        is_backfill = False
    if end > yesterday:
        end = yesterday  # 当日分は未確定なので書かない
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    if not days:
        print("対象日がありません")
        return 1

    excludes = [e.strip() for e in
                kpi_conf("KPI_EXCLUDE_EMAILS", DEFAULT_EXCLUDES).split(",") if e.strip()]
    exclude_ips = {i.strip() for i in kpi_conf("KPI_EXCLUDE_IPS").split(",") if i.strip()}
    if exclude_ips:
        print(f"[kpi_daily_sheet] 除外IP {len(exclude_ips)}件を適用")
    acc = parse_access({d for d in days if d >= LOG_START}, exclude_ips)
    db = db_stats(days, excludes, sorted(exclude_ips))
    daily_rows, link_rows = build_rows(days, acc, db, is_backfill)
    payload = {"daily": daily_rows, "links": link_rows}

    print(f"[kpi_daily_sheet] {days[0]}〜{days[-1]} {len(daily_rows)}日分 / リンク行{len(link_rows)}")
    if os.getenv("DRY_RUN", "").lower() in ("1", "true", "yes"):
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        print("[dry-run] シート書き込みはスキップ")
        return 0
    ok, info = push_to_sheet(payload)
    print(f"[sheets] {info}")
    if not ok and db is None:
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
