"""Engine y sesión de PostgreSQL (base intermedia del sistema).

La conexión a SQL Server (SIGA) vive en `app/siga/conexion.py` — este módulo
se enfoca únicamente en PostgreSQL, donde vive el modelo del sistema.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# Engine PostgreSQL — pool moderado para producción, echo=False.
engine = create_engine(
    settings.postgres_dsn,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.APP_ENV == "development" and False,  # activar manual si se depura SQL
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos SQLAlchemy del sistema."""


def get_db() -> Generator[Session, None, None]:
    """Dependency de FastAPI que provee una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
