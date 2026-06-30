# Debian bookworm を明示（slim 既定の trixie は Playwright 非対応で
# `playwright install --with-deps` が失敗するため）。
FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 日本語フォント(Noto CJK)＋図解レンダラ用 Chromium 本体とOS依存ライブラリ。
# apt のインデックスは playwright の依存導入が終わるまで残す
# （先に消すと --with-deps の apt-get install が対象を見つけられず失敗する）。
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk fonts-noto-color-emoji \
    && python -m playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# Pillow が拾えるよう、CJKフォントのパスを既定で指す（.env で上書き可）。
ENV SNS_FONT_PATH=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc

COPY . .

# Zen Maru Gothic は assets/fonts/ に同梱（infographic.py がローカル@font-faceで参照）。
# 未同梱でもオンライン時はGoogle Fontsにフォールバックする。

EXPOSE 8088

# LINE承認のWebhook常駐サーバ。承認キュー(pending_queue.jsonl)・投稿ログ
# (posts_log.jsonl)は /app に作られるため、本番では volume をマウントして永続化する。
CMD ["sh", "-c", "uvicorn webhook:app --host 0.0.0.0 --port ${WEBHOOK_PORT:-8088}"]
