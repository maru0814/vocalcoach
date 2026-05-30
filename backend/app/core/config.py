from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database (MySQL)
    database_url: str | None = None
    db_host: str = "db"
    db_port: int = 3306
    db_name: str = "claude_md"
    db_user: str = "app"
    db_password: str = "app_password"

    # Auth (JWT + HTTPOnly cookie)
    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    access_token_exp_minutes: int = 60 * 24  # 24 hours
    cookie_name: str = "access_token"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"  # "lax" | "strict" | "none"

    # Upload / storage
    uploads_dir: str = "uploads"
    coach_audio_dir: str = "uploads/coach"
    reference_cache_dir: str = "uploads/reference"
    max_audio_mb: int = 20


settings = Settings()

