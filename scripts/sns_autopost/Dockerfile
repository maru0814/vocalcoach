FROM python:3.12-slim

WORKDIR /app

# 日本語フォント: Pillowカード用に Noto CJK、図解(HTML)用に丸ゴシック(Zen Maru Gothic)。
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# Pillow が拾えるよう、CJKフォントのパスを既定で指す（.env で上書き可）。
ENV SNS_FONT_PATH=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 図解レンダラ用に Chromium 本体とOS依存ライブラリを導入。
RUN python -m playwright install --with-deps chromium

COPY . .

# Zen Maru Gothic は assets/fonts/ に同梱（infographic.py がローカル@font-faceで参照）。
# 未同梱でもオンライン時はGoogle Fontsにフォールバックする。

EXPOSE 8088

# LINE承認のWebhook常駐サーバ。承認キュー(pending_queue.jsonl)・投稿ログ
# (posts_log.jsonl)は /app に作られるため、本番では volume をマウントして永続化する。
CMD ["sh", "-c", "uvicorn webhook:app --host 0.0.0.0 --port ${WEBHOOK_PORT:-8088}"]
