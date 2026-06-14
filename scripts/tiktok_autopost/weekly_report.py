#!/usr/bin/env python3
"""週次パフォーマンスレポートを送信する（毎週日曜 22:00 に cron 実行）。

cron 設定例（tiktok_autopostディレクトリで実行）:
  0 22 * * 0 cd /path/to/scripts/tiktok_autopost && python weekly_report.py >> out/weekly_report.log 2>&1

使い方:
  python weekly_report.py           # 直近2週のレポートをLINE/Discordに送信
  python weekly_report.py --weeks 4 # 直近4週
  python weekly_report.py --dry-run # 送信せずターミナルに表示
"""
import argparse
import datetime
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

import analytics
import notifier


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true", help="送信せず表示のみ")
    args = ap.parse_args()

    print(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] 週次レポート生成中...")
    report = analytics.build_report(weeks=args.weeks)

    print(report)
    if args.dry_run:
        print("\n[dry-run] 送信しません。")
        return 0

    sent = notifier.send_report(report)
    if sent:
        print("週次レポートを送信しました。")
    else:
        print("通知キー未設定のためターミナルに出力しました（LINE/Discord設定で自動送信）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
