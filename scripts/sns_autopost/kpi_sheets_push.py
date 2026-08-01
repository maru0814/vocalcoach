#!/usr/bin/env python3
"""KPI日次データを Google スプレッドシートへ upsert する（docs/84）。

host の scripts/ops/kpi_daily_sheet.py から docker exec で呼ばれる。
stdin で JSON を受け取り、2タブに書き込む:
  {"daily": [[日付, ...15列...], ...],          → タブ「日次KPI」   日付キーで upsert
   "links": [[日付, source, medium, campaign, path, UU], ...]}
                                                → タブ「リンク別LP流入」 対象日を洗い替え

認証は環境変数（scripts/sns_autopost/.env → sns コンテナに注入）:
  KPI_SHEET_ID         … スプレッドシートID（URLの /d/ と /edit の間）
  GOOGLE_SA_JSON_B64   … サービスアカウントJSONの base64
シートはこのスクリプトが全面管理する（手動編集は別タブで行うこと。
自動タブは実行のたびにヘッダ込みで書き直される）。
"""
import base64
import json
import os
import sys

import gspread
from google.oauth2.service_account import Credentials

DAILY_WS = "日次KPI"
LINKS_WS = "リンク別LP流入"

DAILY_HEADER = [
    "日付", "LP遷移UU_合計", "UU_トップ", "UU_診断LP", "UU_ボイトレLP",
    "UU_声タイプ", "UU_その他", "診断UU", "診断実行数", "無料会員登録数",
    "ログインUU", "チャット利用UU", "有料新規", "有料会員数", "備考",
]
LINKS_HEADER = ["日付", "utm_source", "utm_medium", "utm_campaign", "ランディングパス", "UU"]


def _client() -> gspread.Spreadsheet:
    sheet_id = os.environ["KPI_SHEET_ID"]
    info = json.loads(base64.b64decode(os.environ["GOOGLE_SA_JSON_B64"]))
    creds = Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds).open_by_key(sheet_id)


def _worksheet(sh: gspread.Spreadsheet, title: str, cols: int) -> gspread.Worksheet:
    try:
        return sh.worksheet(title)
    except gspread.WorksheetNotFound:
        return sh.add_worksheet(title=title, rows=1000, cols=cols)


def _rewrite(ws: gspread.Worksheet, header: list, rows: list) -> None:
    """ヘッダ＋行で全面書き直し（データ量は高々数百行なのでこれが最も壊れにくい）。"""
    ws.clear()
    ws.update(values=[header] + rows, range_name="A1", value_input_option="USER_ENTERED")


def upsert_daily(sh: gspread.Spreadsheet, incoming: list[list]) -> int:
    ws = _worksheet(sh, DAILY_WS, len(DAILY_HEADER))
    existing = ws.get_all_values()
    merged: dict[str, list] = {}
    for row in existing[1:]:  # 先頭はヘッダ（無ければ空リスト）
        if row and row[0]:
            merged[row[0]] = row
    for row in incoming:
        merged[str(row[0])] = [("" if v is None else v) for v in row]
    rows = [merged[k] for k in sorted(merged)]
    _rewrite(ws, DAILY_HEADER, rows)
    return len(incoming)


def replace_links(sh: gspread.Spreadsheet, incoming: list[list]) -> int:
    if not incoming:
        return 0
    ws = _worksheet(sh, LINKS_WS, len(LINKS_HEADER))
    days = {str(r[0]) for r in incoming}
    existing = ws.get_all_values()
    kept = [r for r in existing[1:] if r and r[0] and r[0] not in days]
    rows = kept + [[("" if v is None else v) for v in r] for r in incoming]
    rows.sort(key=lambda r: (r[0], r[1], r[3], r[4]))
    _rewrite(ws, LINKS_HEADER, rows)
    return len(incoming)


def main() -> int:
    payload = json.load(sys.stdin)
    sh = _client()
    n_daily = upsert_daily(sh, payload.get("daily", []))
    n_links = replace_links(sh, payload.get("links", []))
    print(f"OK daily={n_daily} links={n_links}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
