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
