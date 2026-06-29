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

    # --- ゼロベース個人最適FB（docs/43）。既定OFF。ONにするまで本番挙動は不変 ---
    # 録音FBを「カタログ選択」から「証拠＋生音声を聴いて推論生成」へ切替える経路の有効化。
    enable_zero_base_fb: bool = False
    # 分析ターン専用モデル。雑談は従来の llm_model のまま。
    # コスト優先で既定は flash（マルチモーダル・十分強い）。最高品質が要るなら env で
    # gemini-2.5-pro に上書き可（単価が大きく上がるので注意）。
    llm_analysis_model: str = "gemini-2.5-flash"
    llm_analysis_max_tokens: int = 1200
    # >0 で thinking（推論）有効。コスト抑制のため控えめ（証拠から1点を選ぶには十分）。
    llm_analysis_thinking_budget: int = 1024
    # 生音声＋大きい文脈＋推論で重いのでタイムアウト長め。
    llm_analysis_timeout_sec: float = 90.0

    # --- コスト・ガード（無尽蔵に膨らむのを防ぐ多層の上限。docs/43 §5）---
    # 原曲(お手本)のフル音声は最大のコスト源。既定では送らず、DSPの原曲比較(実測)で代替する。
    # ユーザー音声(短いクリップ)だけ聴かせる＝ハイブリッドは維持しつつコストを大幅圧縮。
    llm_analysis_send_ref_audio: bool = False
    # 1録音あたり送る音声の上限(MB)。超える録音は音声を送らず実測証拠テキストだけで講評（安全側）。
    llm_analysis_max_audio_mb: float = 8.0
    # 1ユーザー1日あたりの分析ターン上限（連投・悪用での膨張を遮断）。超過はルールベースFBへ。
    llm_analysis_max_per_user_per_day: int = 20
    # 月次・全体の分析ターン呼び出し上限（ハードシーリング）。超過はルールベースFBへ。
    llm_analysis_monthly_call_cap: int = 500
    # レポート用の1呼び出し概算コスト(USD)。月次台帳に積算（厳密な課金額ではなく目安）。
    llm_analysis_est_usd_per_call: float = 0.03
    # 月次コスト台帳の保存先（コンテナの永続volume配下を想定）。
    llm_cost_ledger_path: str = "uploads/llm_cost_ledger.json"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.strip())

    # レート制限（音声解析）: ユーザーあたり window 秒で max 回まで
    rate_limit_window_sec: int = 60
    rate_limit_max_audio: int = 8

    # --- 有料プラン（docs/31〜33）---
    # billing_enabled=False の間は全ゲート無効（従来どおり全機能無料）。緊急停止スイッチ兼用。
    billing_enabled: bool = False
    free_analysis_limit: int = 10   # 無料プランの解析回数/暦月（JST）
    free_history_limit: int = 10    # 無料プランの履歴表示件数
    # Stripe（PR-Bで使用。未設定でも起動可）
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_id_premium: str | None = None
    # Checkout/Portal の戻り先（フロント）。本番は同一ドメイン。
    frontend_base_url: str = "http://localhost:3000"

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.stripe_secret_key and self.stripe_price_id_premium)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

