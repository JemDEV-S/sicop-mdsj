"""Schemas de documentos y fotos de obra (HU-02, HU-03)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentoPublicoItem(BaseModel):
    id: UUID
    codigo_unico_obra: str
    tipo: str
    nombre_original: str
    ruta_relativa: str
    mime_type: str
    tamano_bytes: int
    subido_en: datetime


class DocumentoInternoItem(DocumentoPublicoItem):
    subido_por: UUID
    publicado: bool
