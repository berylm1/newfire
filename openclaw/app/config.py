from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # DB
    db_host: str = "newfire-db"
    db_port: int = 5432
    db_name: str = "newfire"
    db_user: str = "newfire"
    db_password: str = ""
    db_schema: str = "openclaw"

    # CF Access
    cf_team_domain: str = "newwaveclaw.cloudflareaccess.com"
    cf_access_aud: str = ""
    cf_jwks_ttl_seconds: int = 3600

    # Dev bypass: when set, JWT verification is skipped and this email is used.
    # Must be empty in production. Container will refuse to start if both this
    # and cf_access_aud are unset.
    openclaw_dev_email: str = ""

    # LiteLLM endpoint (Stage B classifier). Optional in PR 1.
    litellm_url: str = "http://100.88.112.5:4500"
    litellm_model: str = "nss-tools-light"
    litellm_api_key: str = ""

    # Downstream tools
    opencode_url: str = "https://opencode.newfire.app"
    openhands_url: str = "https://openhands.newfire.app"

    # Service
    service_port: int = 5500
    log_level: str = "info"


settings = Settings()
