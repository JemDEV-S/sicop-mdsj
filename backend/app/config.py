"""Configuración centralizada (Pydantic Settings).

Todas las vars de entorno se cargan aquí y se acceden mediante `settings`.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ─── App ────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "change-me"
    APP_JWT_ACCESS_MINUTES: int = 15
    APP_JWT_REFRESH_HOURS: int = 8

    # ─── PostgreSQL ─────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "sicop"
    POSTGRES_USER: str = "sicop"
    POSTGRES_PASSWORD: str = "sicop_dev_pw"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ─── Redis ──────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ─── SQL Server (SIGA) ──────────────────────────────────────
    MSSQL_HOST: str = "localhost"
    MSSQL_PORT: int = 1433
    MSSQL_DB: str = "SIGA_300687"
    MSSQL_USER: str = "sa"
    MSSQL_SA_PASSWORD: str = "Sicop_Dev_2026!"
    MSSQL_ODBC_DRIVER: str = "ODBC Driver 18 for SQL Server"
    MSSQL_TRUST_CERT: str = "yes"

    MSSQL_LECTOR_USER: str = "lector_presupuesto"
    MSSQL_LECTOR_PASSWORD: str = "change-me-lector-pw"

    @property
    def mssql_dsn(self) -> str:
        # Conexión de app: usa el usuario lector (solo lectura).
        driver = self.MSSQL_ODBC_DRIVER.replace(" ", "+")
        return (
            f"mssql+pyodbc://{self.MSSQL_LECTOR_USER}:{self.MSSQL_LECTOR_PASSWORD}"
            f"@{self.MSSQL_HOST}:{self.MSSQL_PORT}/{self.MSSQL_DB}"
            f"?driver={driver}&TrustServerCertificate={self.MSSQL_TRUST_CERT}"
        )

    # ─── API MEF ────────────────────────────────────────────────
    MEF_BASE_URL: str = "https://api.datosabiertos.mef.gob.pe/DatosAbiertos/v1"
    MEF_RESOURCE_EJECUCION: str = "615644aa-ef73-4358-b4e0-0c20931632f3"
    MEF_RESOURCE_INVERSIONES: str = "f9cc4ba0-931a-4b70-86c9-eacbd8c68596"

    # ─── Entidad (fijos) ────────────────────────────────────────
    SEC_EJEC: str = "300687"
    UBIGEO: str = "080104"
    ANO_VIGENTE: int = 2026

    # ─── Uploads ────────────────────────────────────────────────
    UPLOAD_PATH: str = "/var/data/uploads"
    UPLOAD_MAX_MB_FOTO: int = 5
    UPLOAD_MAX_MB_DOCUMENTO: int = 20

    # ─── CORS ───────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ─── reCAPTCHA ──────────────────────────────────────────────
    RECAPTCHA_SITE_KEY: str = ""
    RECAPTCHA_SECRET: str = ""

    # ─── Jobs ───────────────────────────────────────────────────
    SYNC_SIAF_HOUR: int = 3
    SYNC_SIAF_MINUTE: int = 0


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
