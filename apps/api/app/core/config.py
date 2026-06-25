import os


class Settings:
    app_name: str = os.getenv("APP_NAME", "Lary 2 MVP 0.1")
    app_env: str = os.getenv("APP_ENV", "development")

    cors_origins: str = os.getenv("CORS_ORIGINS", "*")
    database_url: str | None = os.getenv("DATABASE_URL")
    file_storage_dir: str = os.getenv("FILE_STORAGE_DIR", "/tmp/lary-generated")

    gigachat_credentials: str | None = os.getenv("GIGACHAT_CREDENTIALS")
    gigachat_scope: str = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
    gigachat_model: str = os.getenv("GIGACHAT_MODEL", "GigaChat")
    gigachat_verify_ssl_certs: bool = os.getenv("GIGACHAT_VERIFY_SSL_CERTS", "false").lower() == "true"
    gigachat_timeout: float = float(os.getenv("GIGACHAT_TIMEOUT", "60.0"))
    gigachat_max_retries: int = int(os.getenv("GIGACHAT_MAX_RETRIES", "3"))

    salute_speech_authorization_key: str | None = os.getenv("SALUTE_SPEECH_AUTHORIZATION_KEY")
    salute_speech_scope: str = os.getenv("SALUTE_SPEECH_SCOPE", "SALUTE_SPEECH_PERS")
    salute_speech_verify_ssl_certs: bool = os.getenv("SALUTE_SPEECH_VERIFY_SSL_CERTS", "false").lower() == "true"
    payment_provider_mode: str = os.getenv("PAYMENT_PROVIDER_MODE", "placeholder")

    def cors_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
