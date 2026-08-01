#!/usr/bin/env python3
"""一度だけ実行するログインセッション保存ツール。

Playwright でブラウザを開き、手動でログインしてもらったあとセッションを
assets/auth_state.json に保存する。clip_recorder.py がこれを使い回す。

使い方:
  python setup_auth.py
  → ブラウザが開くので手動でログイン → Enter を押す → セッション保存

条件:
  pip install playwright && playwright install chromium
"""
import os
import sys

_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_STATE = os.path.join(_DIR, "assets", "auth_state.json")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_DIR, ".env"))
except Exception:
    pass

APP_URL = os.getenv("APP_URL", "https://sora-vocal-ai.duckdns.org").rstrip("/")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright未導入。pip install playwright && playwright install chromium")
        return 1

    os.makedirs(os.path.join(_DIR, "assets"), exist_ok=True)
    print(f"ブラウザを開きます: {APP_URL}/login")
    print("手動でログインしたら、このターミナルで Enter を押してください。")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, locale="ja-JP")
        page = ctx.new_page()
        page.goto(f"{APP_URL}/login")
        input("ログイン完了後に Enter ▶")
        ctx.storage_state(path=AUTH_STATE)
        ctx.close()
        browser.close()

    print(f"✅ セッション保存: {AUTH_STATE}")
    print("次回から clip_recorder.py がこのセッションを使います。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
