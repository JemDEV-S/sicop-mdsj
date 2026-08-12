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
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import Row

from app.config import settings

# Engine SQLAlchemy compartido — pool moderado, sin autocommit (solo lectura).
_engine: Engine | None = None


def _forzar_varchar(dbapi_conn: pyodbc.Connection, _record: Any) -> None:
    """Envía los strings como VARCHAR (no NVARCHAR) — crítico para el rendimiento.

    Por defecto pyodbc manda los parámetros str como Unicode (NVARCHAR). Las
    columnas de SIGA son VARCHAR (no-Unicode, code page latin-1), así que
    comparar `columna_VARCHAR = :param_NVARCHAR` obliga a SQL Server a una
    conversión implícita que INVALIDA los índices → scans completos. Contra
    producción, la ficha de pedido (JOINs por GRUPO/CLASE/FAMILIA/ITEM_BIEN)
    pasaba de <1s a >30s (timeout). Forzando VARCHAR/latin-1 vuelve a <1s.

    latin-1 es el code page real de esta BD (mismo encoding que devuelve la
    API MEF: la 'Ñ' = byte 0xd1). Ver `app/services/mef_client.py`.
    """
    dbapi_conn.setdecoding(pyodbc.SQL_CHAR, encoding="latin-1")
    dbapi_conn.setdecoding(pyodbc.SQL_WCHAR, encoding="latin-1")
    dbapi_conn.setencoding(encoding="latin-1")


def _lecturas_sucias(dbapi_conn: pyodbc.Connection, _record: Any) -> None:
    """Fija READ UNCOMMITTED en cada conexión — evita esperar locks de producción.

    SIGA es una BD OLTP VIVA: el sistema municipal escribe sobre ella todo el
    día. Bajo el nivel de aislamiento por defecto (READ COMMITTED), un SELECT
    nuestro que toque una fila/página con una transacción abierta se BLOQUEA
    hasta que esa transacción cierre — o hasta el timeout. Medido contra
    producción: leer `SIG_PAAC_CONSOLIDADO` filtrando ano+sec_ejec y proyectando
    una columna del clustered index (p.ej. NRO_EST_MDO) colgaba >30s por lock
    wait; con `WITH (NOLOCK)` la misma query devolvía en 0.01s. Esto colgaba el
    sync del pipeline en el extractor `expedientes_ccmn`. En el backup local no
    pasaba porque nadie más escribe en el backup (sin transacciones concurrentes).

    Somos una réplica de solo-lectura para reporting: leer datos ya escritos con
    lecturas sucias (dirty reads) es el patrón correcto para NO bloquear ni ser
    bloqueados por el SIGA operativo. RN-02: solo lectura, nunca escribimos.
    """
    cur = dbapi_conn.cursor()
    try:
        cur.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    finally:
        cur.close()


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
        # Cada conexión nueva del pool manda strings como VARCHAR (ver arriba)
        # y lee en READ UNCOMMITTED para no bloquearse con locks de producción.
        event.listen(_engine, "connect", _forzar_varchar)
        event.listen(_engine, "connect", _lecturas_sucias)
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
    conn = pyodbc.connect(settings.mssql_odbc_connection_string, timeout=10)
    _forzar_varchar(conn, None)   # mismo fix VARCHAR/latin-1 que el engine
    _lecturas_sucias(conn, None)  # READ UNCOMMITTED: no bloquearse con producción
    return conn


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
