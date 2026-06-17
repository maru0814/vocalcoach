FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8088

# LINE承認のWebhook常駐サーバ。承認キュー(pending_queue.jsonl)・投稿ログ
# (posts_log.jsonl)は /app に作られるため、本番では volume をマウントして永続化する。
CMD ["sh", "-c", "uvicorn webhook:app --host 0.0.0.0 --port ${WEBHOOK_PORT:-8088}"]
