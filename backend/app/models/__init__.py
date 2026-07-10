"""Modelos SQLAlchemy del sistema.

Re-exporta `Base` y todos los modelos para que Alembic los descubra al
importar `app.models`.
"""

from app.database import Base
from app.models import auth, logs, ref, siaf, sistema  # noqa: F401
from app.models.enums import (
    CodigoRol,
    DireccionSemaforo,
    EstadoObservacion,
    EstadoSync,
    EstadoUsuario,
    TipoDocumentoObra,
    TipoEntidadAlerta,
    TipoEntidadAnotacion,
)

__all__ = [
    "Base",
    "CodigoRol",
    "DireccionSemaforo",
    "EstadoObservacion",
    "EstadoSync",
    "EstadoUsuario",
    "TipoDocumentoObra",
    "TipoEntidadAlerta",
    "TipoEntidadAnotacion",
    "auth",
    "logs",
    "ref",
    "siaf",
    "sistema",
]
