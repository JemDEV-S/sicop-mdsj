"""Servicio de subida y descarga de archivos (fotos + documentos de obra).

Almacenamiento: filesystem local en `UPLOAD_PATH/obras/{codigo_unico}/{tipo}/`.
Metadata: tabla `sistema.documentos_obra`.

Validaciones (HU-03 AC-03.2, AC-03.3):
- Fotos: JPG/PNG, max 5MB, hasta 20 por proyecto.
- Documentos: PDF, max 20MB, hasta 10 por proyecto.
"""

from __future__ import annotations

import hashlib
import mimetypes
import re
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.enums import TipoDocumentoObra


class UploadInvalido(RuntimeError):
    """Falla de validacion del archivo subido."""


_TIPOS_FOTO = {TipoDocumentoObra.foto}
_TIPOS_DOCUMENTO = {
    TipoDocumentoObra.expediente_tecnico,
    TipoDocumentoObra.contrato,
    TipoDocumentoObra.f8,
    TipoDocumentoObra.f9,
    TipoDocumentoObra.otro,
}

_MIME_FOTO = {"image/jpeg", "image/jpg", "image/png"}
_EXT_FOTO = {".jpg", ".jpeg", ".png"}
_MIME_DOC = {"application/pdf"}
_EXT_DOC = {".pdf"}

_MAX_FOTOS = 20
_MAX_DOCUMENTOS = 10


def _sanear_nombre(nombre: str) -> str:
    """Deja solo [a-zA-Z0-9._-] para el nombre en disco."""
    limpio = re.sub(r"[^A-Za-z0-9._-]+", "_", nombre.strip())
    return limpio[:200] or "archivo"


def _carpeta_obra(codigo_unico: str, tipo: TipoDocumentoObra) -> Path:
    base = Path(settings.UPLOAD_PATH) / "obras" / codigo_unico / tipo.value
    base.mkdir(parents=True, exist_ok=True)
    return base


def _contar_por_tipo(
    db: Session, codigo_unico: str, tipo: TipoDocumentoObra
) -> int:
    return int(
        db.execute(
            text(
                """
                SELECT COUNT(*)
                  FROM sistema.documentos_obra
                 WHERE codigo_unico_obra = :codigo
                   AND tipo = CAST(:tipo AS tipo_documento_obra)
                """
            ),
            {"codigo": codigo_unico, "tipo": tipo.value},
        ).scalar_one()
    )


def _validar_extension_y_mime(
    upload: UploadFile, tipo: TipoDocumentoObra
) -> tuple[str, str]:
    """Devuelve (mime, ext) validado o levanta UploadInvalido."""
    nombre = upload.filename or ""
    ext = Path(nombre).suffix.lower()

    mime = (upload.content_type or "").lower()
    if not mime:
        mime = mimetypes.guess_type(nombre)[0] or ""

    if tipo in _TIPOS_FOTO:
        if ext not in _EXT_FOTO or (mime and mime not in _MIME_FOTO):
            raise UploadInvalido(
                f"foto debe ser JPG o PNG (ext={ext}, mime={mime})"
            )
    else:
        if ext not in _EXT_DOC or (mime and mime not in _MIME_DOC):
            raise UploadInvalido(
                f"documento debe ser PDF (ext={ext}, mime={mime})"
            )
    return mime or ("image/jpeg" if tipo in _TIPOS_FOTO else "application/pdf"), ext


def _validar_tamano(
    tamano: int, tipo: TipoDocumentoObra
) -> None:
    if tipo in _TIPOS_FOTO:
        limite = settings.UPLOAD_MAX_MB_FOTO * 1024 * 1024
        etiqueta = f"foto max {settings.UPLOAD_MAX_MB_FOTO} MB"
    else:
        limite = settings.UPLOAD_MAX_MB_DOCUMENTO * 1024 * 1024
        etiqueta = f"documento max {settings.UPLOAD_MAX_MB_DOCUMENTO} MB"
    if tamano > limite:
        raise UploadInvalido(f"{etiqueta} (recibido {tamano // 1024} KB)")


def _validar_cupo(
    db: Session, codigo_unico: str, tipo: TipoDocumentoObra
) -> None:
    if tipo in _TIPOS_FOTO:
        n = _contar_por_tipo(db, codigo_unico, tipo)
        if n >= _MAX_FOTOS:
            raise UploadInvalido(
                f"cupo de fotos agotado ({n}/{_MAX_FOTOS})"
            )
    else:
        n = sum(
            _contar_por_tipo(db, codigo_unico, t) for t in _TIPOS_DOCUMENTO
        )
        if n >= _MAX_DOCUMENTOS:
            raise UploadInvalido(
                f"cupo de documentos agotado ({n}/{_MAX_DOCUMENTOS})"
            )


def guardar_archivo(
    db: Session,
    *,
    codigo_unico: str,
    tipo: TipoDocumentoObra,
    upload: UploadFile,
    usuario_id: UUID,
) -> dict[str, Any]:
    """Guarda el archivo en disco + registra la metadata. Devuelve el dict del row."""
    mime, ext = _validar_extension_y_mime(upload, tipo)
    _validar_cupo(db, codigo_unico, tipo)

    contenido = upload.file.read()
    _validar_tamano(len(contenido), tipo)

    nombre_original = _sanear_nombre(upload.filename or f"archivo{ext}")
    # Nombre en disco: uuid.ext (evita colisiones y traversal).
    nombre_disco = f"{uuid4().hex}{ext}"
    carpeta = _carpeta_obra(codigo_unico, tipo)
    ruta_abs = carpeta / nombre_disco
    ruta_abs.write_bytes(contenido)

    # Ruta relativa para servir por Nginx: obras/{codigo}/{tipo}/{nombre}
    ruta_relativa = f"obras/{codigo_unico}/{tipo.value}/{nombre_disco}"

    row = db.execute(
        text(
            """
            INSERT INTO sistema.documentos_obra (
                codigo_unico_obra, tipo, nombre_original, ruta_relativa,
                mime_type, tamano_bytes, subido_por
            )
            VALUES (
                :codigo, CAST(:tipo AS tipo_documento_obra),
                :nombre, :ruta, :mime, :tamano, :usuario
            )
            RETURNING id, codigo_unico_obra, tipo::text AS tipo,
                      nombre_original, ruta_relativa, mime_type, tamano_bytes,
                      subido_por, subido_en, publicado
            """
        ),
        {
            "codigo": codigo_unico,
            "tipo": tipo.value,
            "nombre": nombre_original,
            "ruta": ruta_relativa,
            "mime": mime,
            "tamano": len(contenido),
            "usuario": str(usuario_id),
        },
    ).mappings().first()

    return dict(row) if row else {}


def obtener_metadata(db: Session, doc_id: UUID) -> dict[str, Any] | None:
    row = db.execute(
        text(
            """
            SELECT id, codigo_unico_obra, tipo::text AS tipo,
                   nombre_original, ruta_relativa, mime_type, tamano_bytes,
                   subido_por, subido_en, publicado
              FROM sistema.documentos_obra
             WHERE id = :id
            """
        ),
        {"id": str(doc_id)},
    ).mappings().first()
    return dict(row) if row else None


def listar_publicos(
    db: Session, *, codigo_unico: str, tipo: TipoDocumentoObra | None = None
) -> list[dict[str, Any]]:
    where = ["codigo_unico_obra = :codigo", "publicado = true"]
    params: dict[str, Any] = {"codigo": codigo_unico}
    if tipo is not None:
        where.append("tipo = CAST(:tipo AS tipo_documento_obra)")
        params["tipo"] = tipo.value
    rows = db.execute(
        text(
            f"""
            SELECT id, codigo_unico_obra, tipo::text AS tipo,
                   nombre_original, ruta_relativa, mime_type, tamano_bytes,
                   subido_en
              FROM sistema.documentos_obra
             WHERE {" AND ".join(where)}
             ORDER BY subido_en DESC
            """
        ),
        params,
    ).mappings().all()
    return [dict(r) for r in rows]


def listar_todos(
    db: Session, *, codigo_unico: str, tipo: TipoDocumentoObra | None = None
) -> list[dict[str, Any]]:
    """Version interna: incluye no publicados."""
    where = ["codigo_unico_obra = :codigo"]
    params: dict[str, Any] = {"codigo": codigo_unico}
    if tipo is not None:
        where.append("tipo = CAST(:tipo AS tipo_documento_obra)")
        params["tipo"] = tipo.value
    rows = db.execute(
        text(
            f"""
            SELECT id, codigo_unico_obra, tipo::text AS tipo,
                   nombre_original, ruta_relativa, mime_type, tamano_bytes,
                   subido_por, subido_en, publicado
              FROM sistema.documentos_obra
             WHERE {" AND ".join(where)}
             ORDER BY subido_en DESC
            """
        ),
        params,
    ).mappings().all()
    return [dict(r) for r in rows]


def eliminar(db: Session, doc_id: UUID) -> tuple[bool, str | None]:
    """Borra registro + archivo en disco. Devuelve (borrado, ruta_relativa).

    Si el archivo en disco ya no existe, el registro se borra igual.
    """
    row = db.execute(
        text(
            """
            DELETE FROM sistema.documentos_obra
             WHERE id = :id
             RETURNING ruta_relativa
            """
        ),
        {"id": str(doc_id)},
    ).first()
    if row is None:
        return False, None
    ruta_relativa = row.ruta_relativa
    ruta_abs = Path(settings.UPLOAD_PATH) / ruta_relativa
    if ruta_abs.is_file():
        try:
            ruta_abs.unlink()
        except OSError:
            pass
    return True, ruta_relativa


def ruta_absoluta(ruta_relativa: str) -> Path:
    """Convierte una ruta_relativa (de la BD) al path absoluto.

    Rechaza rutas con `..` para prevenir traversal.
    """
    if ".." in ruta_relativa.split("/"):
        raise UploadInvalido("ruta invalida")
    return Path(settings.UPLOAD_PATH) / ruta_relativa
