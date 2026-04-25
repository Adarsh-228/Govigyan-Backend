from pydantic_settings import BaseSettings, SettingsConfigDict

# Comma-separated default allowlist: localhost and 127.0.0.1 are different browser origins.
_DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:5173,http://127.0.0.1:5173"
)


class Settings(BaseSettings):
    APP_NAME: str = "Govigyan Backend"
    APP_ENV: str = "development"
    APP_PORT: int = 4000
    API_PREFIX: str = "/api/v1"

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    DATABASE_URL: str | None = None

    CORS_ORIGINS: str = _DEFAULT_CORS_ORIGINS
    # Optional: e.g. https://.*\.vercel\.app$ to allow any Vercel preview URL
    CORS_ORIGIN_REGEX: str | None = None
    AUTH_COOKIE_NAME: str = "access_token"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    @property
    def cors_origins_list(self) -> list[str]:
        raw = (self.CORS_ORIGINS or "").strip()
        parts = [o.strip() for o in raw.split(",") if o.strip()]
        if not parts:
            return [o.strip() for o in _DEFAULT_CORS_ORIGINS.split(",") if o.strip()]
        return parts

    @property
    def cors_origin_regex(self) -> str | None:
        r = (self.CORS_ORIGIN_REGEX or "").strip()
        return r or None


settings = Settings()
