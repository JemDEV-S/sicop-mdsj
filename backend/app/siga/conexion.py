"""Conexión a SIGA (SQL Server) — factory y helpers.

Estrategia:
- Un engine SQLAlchemy con pool de conexiones (reutilizable entre requests).
- Preferencia por consultas SQL crudas ejecutadas con `text()` y parámetros bind.
- Windows Auth en dev, SQL Auth en prod (controlado por MSSQL_AUTH en .env).

Referencias:
- Docs/actividad-3-arquitectura-tecnica.md §5 (adaptador SIGA)
- Docs/diccionario-datos-unificado.md §17 (llaves cruce)
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pyodbc
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import Row

from app.config import settings

# Engine SQLAlchemy compartido — pool moderado, sin autocommit (solo lectura).
_engine: Engine | None = None


def get_engine() -> Engine:
    """Obtiene (creando si hace falta) el engine SQLAlchemy contra SIGA."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.mssql_dsn,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=1800,  # 30 min
            echo=False,
        )
    return _engine


@contextmanager
def get_connection() -> Iterator[Any]:
    """Context manager con conexión SQLAlchemy (usar `.execute(text(...))`)."""
    engine = get_engine()
    with engine.connect() as conn:
        yield conn


def get_pyodbc_connection() -> pyodbc.Connection:
    """Conexión pyodbc directa — útil para scripts CLI y jobs.

    Preferir `get_connection()` (SQLAlchemy) en el código de la aplicación.
    """
    return pyodbc.connect(settings.mssql_odbc_connection_string, timeout=10)


def fetch_all(sql: str, params: dict[str, Any] | None = None) -> list[Row]:
    """Helper: ejecuta un SELECT y devuelve todas las filas como Rows SQLAlchemy."""
    with get_connection() as conn:
        result = conn.execute(text(sql), params or {})
        return result.fetchall()


def fetch_one(sql: str, params: dict[str, Any] | None = None) -> Row | None:
    """Helper: ejecuta un SELECT y devuelve una fila (o None)."""
    with get_connection() as conn:
        result = conn.execute(text(sql), params or {})
        return result.fetchone()


def health_check() -> dict[str, Any]:
    """Verificación rápida de conectividad SIGA.

    Devuelve: server, database, user, driver, versión, timestamp.
    Levanta excepción si no hay conectividad.
    """
    sql = """
        SELECT
            @@SERVERNAME AS server_name,
            DB_NAME() AS database_name,
            SUSER_NAME() AS login_name,
            @@VERSION AS version_str,
            GETDATE() AS server_time
    """
    row = fetch_one(sql)
    if row is None:
        raise RuntimeError("SIGA health_check devolvió NULL")
    return {
        "server_name": row.server_name,
        "database_name": row.database_name,
        "login_name": row.login_name,
        "version": row.version_str.split("\n")[0].strip(),
        "server_time": str(row.server_time),
    }
