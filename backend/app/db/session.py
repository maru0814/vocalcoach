from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def get_database_url() -> str:
    if settings.database_url:
        return settings.database_url

    return (
        f"mysql+pymysql://{settings.db_user}:{settings.db_password}@{settings.db_host}:"
        f"{settings.db_port}/{settings.db_name}?charset=utf8mb4"
    )


database_url = get_database_url()
engine_kwargs = {"pool_pre_ping": True}
if database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    database_url,
    **engine_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

