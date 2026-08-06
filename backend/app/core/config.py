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
    # ⚠️ "-latest" エイリアスは使わない（docs/91 原因1）: Google 側で新世代（Gemini 3 系）に
    #    切り替わった際、thinking_budget=0 が INVALID_ARGUMENT になりテキスト会話が全滅した。
    #    バージョンは明示的に固定する。
    llm_model: str = "gemini-2.5-flash-lite"
    # 対話ターン（会話返答・コーチコメント）専用モデル（docs/66）。
    # 既定は llm_model（flash-lite）と同じ。格上げ（gemini-2.5-flash）は before/after 測定の結果、
    # カジュアル/感情は改善したが「多ターンの噛み合い」が悪化＋コスト3倍のため既定では採らない
    # （丸山CEO判断 2026-07-12: 会話モードのプロンプト側だけ採用）。必要なら env で 2.5-flash に格上げ可。
    llm_chat_model: str = "gemini-2.5-flash-lite"
    # 発音の聞き取り（音声入力）用。Flash-Lite は音声が弱いので Flash を使う。
    # ⚠️ モデルIDは意図的に「バージョン固定」。`gemini-flash-latest` 等のエイリアスは使わない。
    #    理由: エイリアスは予告なく指す実体が変わり、その時に呼び出しパラメータの互換性まで壊れる。
    #    実測 2026-08-05: `gemini-flash-lite-latest` / `gemini-flash-latest` は既に Gemini 3 系を
    #    指しており、`thinking_budget=0` を 400 INVALID_ARGUMENT で拒否する（2.5 系は受け付ける）。
    #    固定IDなら「いつ壊れるか」をこちらの都合で選べる。実測記録は docs/92。
    # 次の終了予定日: 公式 deprecation ページ（2026-08-03 更新時点）では gemini-2.5-flash は
    #    "No shutdown date announced"＝**未定**。ただし終了日より先に「新規ユーザー利用不可」で
    #    404 になる前例あり（同世代の gemini-2.5-flash-lite が実際にこれで死亡・実測確認済み）。
    #    公式ページはこの事象を載せないので、ページだけを監視源にしないこと。
    # 緊急時: env に LLM_AUDIO_MODEL=gemini-3.6-flash を置いて再起動すれば載せ替わる（再デプロイ不要）。
    #    Gemini 3 系は thinking を切れないため、下の 2 設定がコード側で自動的に安全値へ寄る。
    llm_audio_model: str = "gemini-2.5-flash"
    # 音声入力時の thinking 予算。0＝無効（2.5 系のみ可）。Gemini 3 系に載せ替えると
    # コード側（llm._safe_thinking_budget）が自動で最小値まで引き上げる。
    llm_audio_thinking_budget: int = 0
    # 音声入力時の出力トークン上限。thinking が有効な世代では思考トークンが同じ枠を食うため、
    # 実測で 400 だと 8回中5回 finish=MAX_TOKENS（本文12文字で途切れ）。1024 なら 8/8 STOP。
    # 2.5 系（thinking=0）では 600 で足りるが、載せ替え時に事故らない値を既定にしておく。
    llm_audio_max_tokens: int = 1024
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

    # --- 生徒カルテと主観問診（docs/53/54）。falseで全フック無効＝現行動作（即ロールバック） ---
    enable_student_karte: bool = True

    # --- ソラ先生ツール化（docs/44）。ONでチャット返答を function calling 経由にし、
    # 動画リンク等の"事実"はカタログの実データだけをツールで供給する（捏造防止＋自然会話）。
    coach_tools_enabled: bool = True
    # ツール往復の最大回数（暴走・レイテンシ防止）
    coach_tool_loop_max: int = 2

    # --- ゼロベース個人最適FB（docs/43, docs/52）。CEO決定によりON（既定有効）。 ---
    # 録音FBを「カタログ選択」から「証拠＋生音声を聴いて推論生成」へ切替える経路の有効化。
    # 緊急ロールバックは env に ENABLE_ZERO_BASE_FB=false を置いて再起動（再デプロイ不要）。
    enable_zero_base_fb: bool = True
    # 分析ターン専用モデル（推論＋音色判断）。雑談は従来の llm_model のまま。
    # 既定 flash: 安定供給＋安価で完全な講評を返す（実測 pro は 503 多発）。最高品質が
    # 要る時だけ env で gemini-2.5-pro に上書き可。
    # ⚠️ ここも意図的にバージョン固定（理由・終了予定日は llm_audio_model のコメント参照）。
    # 後継検証済み: gemini-3.6-flash は下の thinking_budget=512 / max_tokens=2048 の組み合わせを
    #   そのまま受け付け finish=STOP（実測 2026-08-05・応答 7.4秒）。載せ替えは env だけで可。
    llm_analysis_model: str = "gemini-2.5-flash"
    # ⚠️ Gemini 2.5 では thinking トークンも出力枠を消費する。max は thinking より十分大きく
    #    すること（thinking=512+本文 で実測 finish=STOP。max<thinking だと本文が途中で切れる）。
    llm_analysis_max_tokens: int = 2048
    # >0 で thinking（推論）有効。診断に十分な範囲で控えめに（出力切れ＆コスト回避）。
    llm_analysis_thinking_budget: int = 512
    # 生音声＋大きい文脈＋推論で重いのでタイムアウト長め。
    llm_analysis_timeout_sec: float = 90.0
    # --- 月次コスト上限（これだけ）。当月の概算コストが上限に達しそうなら強制停止し、
    #     ルールベースFBにフォールバックする。0以下で無制限。docs/43。
    llm_monthly_budget_jpy: int = 2000
    # 分析ターン1回の概算コスト(JPY)。flash 実測 ≒¥0.5/回（音声込み総~3.3kトークン）に対し
    # 安全側に ¥1.5 を既定とする。pro に上げる時はこの値も上げること（env）。
    llm_analysis_est_jpy_per_call: float = 1.5
    # 月次コスト台帳の保存先（コンテナの永続volume配下を想定）。
    llm_cost_ledger_path: str = "uploads/llm_cost_ledger.json"
    # 上限に達したら通知するWebhook URL（任意）。LINE/Slack/Discord等の受け口を指定。
    # 未設定でもログには必ず出る。通知は当月1回だけ（毎回は鳴らさない）。
    llm_budget_notify_webhook: str | None = None

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

    # --- Web Push（練習リマインド通知 / PWA。docs/73〜75）---
    # VAPID鍵ペア（公開鍵はフロントにも NEXT_PUBLIC_VAPID_PUBLIC_KEY として渡す）。
    # 秘密鍵はサーバー/バッチ専用。未設定なら購読は保存できるが配信はスキップされる。
    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    vapid_subject: str = "mailto:admin@example.com"  # 本番は実連絡先(mailto:)を .env で設定
    # 最後の録音から何日練習がないユーザーにリマインドを送るか（docs/73 FR-05）。
    reminder_idle_days: int = 3

    @property
    def push_enabled(self) -> bool:
        return bool(self.vapid_public_key and self.vapid_private_key and self.vapid_subject)

    # --- ウェルカムメール（docs/84/85）。キー未設定なら送信スキップ＝現行動作 ---
    # Brevo(REST API)。送信者アドレスは Brevo 側で認証済みであること（docs/86 手順）。
    mail_api_key: str | None = None
    mail_from_address: str | None = None
    mail_from_name: str = "ソラ先生（Vocal Coach）"
    mail_timeout_sec: float = 10.0

    @property
    def mail_enabled(self) -> bool:
        return bool(self.mail_api_key and self.mail_from_address)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

