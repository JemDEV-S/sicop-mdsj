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
    # La conexión soporta dos modos:
    #   - MSSQL_AUTH=windows → Trusted_Connection=yes (dev local en Windows)
    #   - MSSQL_AUTH=sql     → usuario/contraseña (recomendado para prod)
    MSSQL_AUTH: str = "windows"  # "windows" | "sql"
    MSSQL_SERVER: str = "."  # instancia: ".", "localhost", "SERVER\\INSTANCE"
    MSSQL_PORT: int = 1433
    MSSQL_DB: str = "SIGA_300687"
    MSSQL_ODBC_DRIVER: str = "ODBC Driver 17 for SQL Server"
    MSSQL_TRUST_CERT: str = "yes"
    MSSQL_ENCRYPT: str = "no"

    # Solo se usan cuando MSSQL_AUTH=sql
    MSSQL_USER: str = ""
    MSSQL_PASSWORD: str = ""

    @property
    def mssql_odbc_connection_string(self) -> str:
        """Connection string ODBC directo para pyodbc.connect().

        Preferido sobre SQLAlchemy DSN para queries crudas (T-05 en adelante).
        """
        parts = [
            f"DRIVER={{{self.MSSQL_ODBC_DRIVER}}}",
            f"SERVER={self.MSSQL_SERVER}",
            f"DATABASE={self.MSSQL_DB}",
            f"TrustServerCertificate={self.MSSQL_TRUST_CERT}",
            f"Encrypt={self.MSSQL_ENCRYPT}",
        ]
        if self.MSSQL_AUTH == "windows":
            parts.append("Trusted_Connection=yes")
        else:
            parts.append(f"UID={self.MSSQL_USER}")
            parts.append(f"PWD={self.MSSQL_PASSWORD}")
        return ";".join(parts) + ";"

    @property
    def mssql_dsn(self) -> str:
        """DSN SQLAlchemy (para engine + pool). Usa la connection string ODBC."""
        from urllib.parse import quote_plus

        return f"mssql+pyodbc:///?odbc_connect={quote_plus(self.mssql_odbc_connection_string)}"

    # ─── API MEF ────────────────────────────────────────────────
    MEF_BASE_URL: str = "https://api.datosabiertos.mef.gob.pe/DatosAbiertos/v1"
    MEF_RESOURCE_EJECUCION: str = "615644aa-ef73-4358-b4e0-0c20931632f3"
    MEF_RESOURCE_INVERSIONES: str = "f9cc4ba0-931a-4b70-86c9-eacbd8c68596"

    # ─── Entidad (fijos) ────────────────────────────────────────
    SEC_EJEC: str = "300687"
    UBIGEO: str = "080104"
    ANO_VIGENTE: int = 2026

    # ─── Uploads ────────────────────────────────────────────────
    # En dev Windows override via `.env` con algo como `./_data/uploads`.
    # En prod Linux Docker usar `/var/data/uploads` (bind-mount al host).
    UPLOAD_PATH: str = "./_data/uploads"
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
