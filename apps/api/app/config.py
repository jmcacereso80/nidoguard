import base64
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str | None = None
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "nidoguard"
    database_user: str = "postgres"
    database_password: str = ""

    clerk_api_key: str = ""  # clave publicable pk_...
    clerk_secret_key: str = ""
    claude_key: str = ""
    apify_token: str = ""  # busqueda de Google con el actor apify/google-search-scraper
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""

    r2_bucket: str = "nidoguard-private"
    r2_knowledge_bucket: str = "nidoguard-knowledge"
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    app_url: str = "https://app.nidoguard.com"
    cors_origins: str = "http://localhost:3000"

    care_model: str = "claude-haiku-5-5"  # genera los cuidados de cada equipo
    plate_model: str = "claude-haiku-5-5"
    plate_fallback_model: str = "claude-sonnet-5-5"
    plate_min_confidence: float = 0.7

    apify_maps_actor: str = "compass~crawler-google-places"  # el CLI confirma el actor y su costo antes del piloto
    provider_source: str = "apify"  # apify | fake
    provider_ttl_days: int = 90
    voice: str = "fake"  # fake | retell. Con 'fake' nunca se llama a nadie
    calls_enabled: bool = False  # interruptor general de llamadas reales
    calls_allowlist: str = ""  # telefonos E.164 permitidos mientras dure el piloto, separados por coma
    fake_voice_step_seconds: int = 4  # cada cuanto "termina" una llamada falsa
    geocoder: str = "nominatim"  # nominatim | fake
    geocoder_user_agent: str = "NidoGuard/1.0 (contacto@nidoguard.com)"

    claim_max_failures_per_hour: int = 10

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        from urllib.parse import quote_plus
        return (
            f"postgresql+psycopg://{quote_plus(self.database_user)}:{quote_plus(self.database_password)}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def clerk_jwks_url(self) -> str | None:
        """El dominio de Clerk va codificado en la clave publicable."""
        key = self.clerk_api_key
        if not key.startswith(("pk_test_", "pk_live_")):
            return None
        raw = key.split("_", 2)[2]
        raw += "=" * (-len(raw) % 4)
        try:
            domain = base64.b64decode(raw).decode().rstrip("$")
        except Exception:
            return None
        return f"https://{domain}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
