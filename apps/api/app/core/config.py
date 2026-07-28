import os


class Settings:
    app_name: str = os.getenv("APP_NAME", "Лари")
    app_env: str = os.getenv("APP_ENV", "development")

    cors_origins: str = os.getenv(
        "CORS_ORIGINS",
        "https://web-production-532a8.up.railway.app,http://localhost:3000,http://127.0.0.1:3000",
    )
    database_url: str | None = os.getenv("DATABASE_URL")
    state_sqlite_path: str = os.getenv("LARY_STATE_SQLITE_PATH", "/tmp/lary-state.sqlite3")
    file_storage_dir: str = os.getenv("FILE_STORAGE_DIR", "/tmp/lary-generated")

    gigachat_credentials: str | None = os.getenv("GIGACHAT_CREDENTIALS")
    gigachat_scope: str = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
    gigachat_model: str = os.getenv("GIGACHAT_MODEL", "GigaChat")
    gigachat_verify_ssl_certs: bool = os.getenv("GIGACHAT_VERIFY_SSL_CERTS", "false").lower() == "true"
    gigachat_timeout: float = float(os.getenv("GIGACHAT_TIMEOUT", "60.0"))
    gigachat_max_retries: int = int(os.getenv("GIGACHAT_MAX_RETRIES", "3"))
    salary_enable_ai_text_composition: bool = os.getenv("SALARY_ENABLE_AI_TEXT_COMPOSITION", "true").lower() == "true"

    salute_speech_authorization_key: str | None = os.getenv("SALUTE_SPEECH_AUTHORIZATION_KEY")
    salute_speech_scope: str = os.getenv("SALUTE_SPEECH_SCOPE", "SALUTE_SPEECH_PERS")
    salute_speech_verify_ssl_certs: bool = os.getenv("SALUTE_SPEECH_VERIFY_SSL_CERTS", "false").lower() == "true"
    speech_provider: str = os.getenv("SPEECH_PROVIDER", "salute").lower()
    vosk_model_path: str | None = os.getenv("VOSK_MODEL_PATH")
    vosk_model_url: str | None = os.getenv("VOSK_MODEL_URL")
    vosk_auto_download: bool = os.getenv("VOSK_AUTO_DOWNLOAD", "false").lower() == "true"
    payment_provider_mode: str = os.getenv("PAYMENT_PROVIDER_MODE", "placeholder")
    payment_webhook_secret: str | None = os.getenv("PAYMENT_WEBHOOK_SECRET")
    product_registry_runtime_enabled: bool = os.getenv("PRODUCT_REGISTRY_RUNTIME_ENABLED", "false").lower() == "true"
    product_config_dir: str | None = os.getenv("PRODUCT_CONFIG_DIR")

    def cors_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
