"""pytest 共通設定とフィクスチャ。

- backend/ を import パスに通し、`app.*` を解決できるようにする（venv実行・CI双方で安定）。
- DB依存のテスト用に、インメモリSQLiteのセッションを毎テスト作り直して提供する
  （MySQL不要・ネットワーク不要・テスト間で状態が漏れない）。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db.base import Base  # noqa: E402
# 全モデルを import して Base.metadata に登録させる（create_all 対象・FK解決のため）。
import app.models  # noqa: E402,F401


@pytest.fixture()
def db():
    """空のインメモリSQLite上に全テーブルを作ったセッションを返す。"""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client():
    """FastAPI TestClient。get_db を共有インメモリSQLiteへ差し替えて返す。

    - StaticPool: リクエストごとに get_db が新セッションを開いても同一の in-memory DB を共有する。
    - lifespan は起動しない（TestClient を with で囲まない）ため、起動時の重い warmup を回避。
    - 重いルーター（coach/recordings/voice_type）の import のため、librosa 等が必要。
    """
    from fastapi.testclient import TestClient
    from sqlalchemy.pool import StaticPool

    from app.db.session import get_db
    from app.main import create_app

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def _override_get_db():
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    test_client = TestClient(app)
    # テスト側から直接DBへシードできるようセッションファクトリを公開する。
    test_client.session_factory = TestingSession
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
