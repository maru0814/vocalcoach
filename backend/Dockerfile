FROM python:3.12-slim

WORKDIR /app

# praat-parselmouth は linux/arm64 向けのpre-builtホイールを配布していないため、
# Apple Silicon等のarm64ホストではソースビルドが走る。ビルドにはcmake/gccが要る。
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
