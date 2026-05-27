# 録音した歌へのフィードバック機能（MVP）

## 実装済み範囲
- Backend: FastAPI + SQLAlchemy + Alembic + JWT(Cookie) 認証
- Frontend: Next.js(App Router) + TypeScript + Tailwind の最小画面
- DB: MySQL（users / recordings / evaluations）
- 録音アップロード -> バックグラウンド評価 -> 一覧/詳細表示

## API
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login` (HTTP Only Cookie発行)
- `POST /api/v1/recordings`
- `GET /api/v1/recordings`
- `GET /api/v1/recordings/{id}`

## ローカル起動（Docker推奨）
1. `cd docker`
2. `docker compose up --build`
3. Frontend: `http://localhost:3000`
4. Backend: `http://localhost:8000` (`/healthz` あり)

## 非Docker起動時の注意
- Frontend は Node.js 18+ 推奨（この環境の Node 16 では依存導入が不安定）
- Backend は `backend/.venv` を使って起動可能
  - `source backend/.venv/bin/activate`
  - `cd backend && alembic upgrade head`
  - `uvicorn app.main:app --reload`
