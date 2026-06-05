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

    # --- LLM（ソラ先生の自然言語チャット応答 / Google Gemini）---
    # 重い音声解析・採点はルールベースのまま。テキスト質問への返答だけ Gemini に通す。
    # APIキー未設定時は自動でルールベース応答にフォールバックする。
    gemini_api_key: str | None = None
    # 最安クラス＋無料枠ありの Flash-Lite を既定に。env で上書き可。
    llm_model: str = "gemini-flash-lite-latest"
    # 発音の聞き取り（音声入力）用。Flash-Lite は音声が弱いので Flash を使う。
    llm_audio_model: str = "gemini-2.5-flash"
    llm_max_tokens: int = 400
    llm_timeout_sec: float = 20.0
    # 音声入力は処理が重いのでタイムアウトを長めに
    llm_audio_timeout_sec: float = 60.0
    # 録音FBに添えるコーチコメント用。Gemini はクライアント期限を最低10秒要求するため
    # deadline は 10 秒にしつつ、実際の待ち時間は llm_coach_wait_sec で打ち切る
    # （超過時はルールベースのコメントにフォールバック。会話は止めない）。
    llm_coach_timeout_sec: float = 10.0
    # 録音FBのコーチコメントを待つ最大の実時間（秒）。詳しい発声講評のため少し長めに。
    llm_coach_wait_sec: float = 5.0
    # 録音FBの詳しい講評用の出力トークン上限（CPP/H1-H2等を噛み砕いた解説のため多め）。
    llm_coach_max_tokens: int = 700
    # 直近何件の会話履歴を文脈として渡すか
    llm_history_turns: int = 12

    @property
    def llm_enabled(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.strip())

    # レート制限（音声解析）: ユーザーあたり window 秒で max 回まで
    rate_limit_window_sec: int = 60
    rate_limit_max_audio: int = 8

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

