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

    # CORS（本番は同一ドメイン[Caddy]想定。別ドメイン時はカンマ区切りで指定）
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # 原曲取得（YouTube）を有効にするか。本番ではデフォルト無効（任意機能）
    enable_youtube_reference: bool = False

    # レート制限（音声解析）: ユーザーあたり window 秒で max 回まで
    rate_limit_window_sec: int = 60
    rate_limit_max_audio: int = 8

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

