"""Endpoints de documentos y fotos de obra (HU-02, HU-03).

Publicos:
- GET  /publico/obras/{codigo}/documentos
- GET  /publico/obras/{codigo}/fotos
- GET  /media/uploads/{ruta}            (descarga directa por ruta relativa)

Internos (requieren JWT):
- POST   /interno/obras/{codigo}/documentos     (upload documento PDF)
- POST   /interno/obras/{codigo}/fotos          (upload foto JPG/PNG)
- DELETE /interno/obras/{codigo}/documentos/{id}
- DELETE /interno/obras/{codigo}/fotos/{id}
- GET    /interno/obras/{codigo}/documentos     (incluye no publicados)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import TipoDocumentoObra
from app.schemas.documentos import DocumentoInternoItem, DocumentoPublicoItem
from app.security.deps import CurrentUser, get_current_user
from app.services import auditoria_service, uploads_service
from app.services.uploads_service import UploadInvalido

publico_router = APIRouter(prefix="/publico/obras", tags=["publico-obras"])
interno_router = APIRouter(prefix="/interno/obras", tags=["interno-obras"])
media_router = APIRouter(prefix="/media/uploads", tags=["media"])


def _obra_existe(db: Session, codigo_unico: str) -> bool:
    return (
        db.execute(
            text("SELECT 1 FROM siaf.inversiones WHERE codigo_unico = :c LIMIT 1"),
            {"c": codigo_unico},
        ).first()
        is not None
    )


# ─── Publicos ────────────────────────────────────────────────────────────

@publico_router.get(
    "/{codigo_unico}/documentos",
    response_model=list[DocumentoPublicoItem],
)
def listar_documentos_publicos(
    codigo_unico: str, db: Session = Depends(get_db)
) -> list[DocumentoPublicoItem]:
    # Excluimos las fotos — las expone otro endpoint.
    todos = uploads_service.listar_publicos(db, codigo_unico=codigo_unico)
    docs = [d for d in todos if d["tipo"] != TipoDocumentoObra.foto.value]
    return [DocumentoPublicoItem.model_validate(d) for d in docs]


@publico_router.get(
    "/{codigo_unico}/fotos",
    response_model=list[DocumentoPublicoItem],
)
def listar_fotos_publicas(
    codigo_unico: str, db: Session = Depends(get_db)
) -> list[DocumentoPublicoItem]:
    fotos = uploads_service.listar_publicos(
        db, codigo_unico=codigo_unico, tipo=TipoDocumentoObra.foto
    )
    return [DocumentoPublicoItem.model_validate(f) for f in fotos]


@media_router.get("/{ruta:path}")
def descargar(ruta: str, db: Session = Depends(get_db)) -> FileResponse:
    """Sirve archivos publicos. En prod, Nginx atiende esta ruta directamente.

    Aqui se conserva para dev / fallback: verifica que exista un registro
    publicado con esa ruta antes de devolver el binario.
    """
    exists = db.execute(
        text(
            """
            SELECT 1 FROM sistema.documentos_obra
             WHERE ruta_relativa = :r AND publicado = true LIMIT 1
            """
        ),
        {"r": ruta},
    ).first()
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no publicado")
    try:
        path_abs = uploads_service.ruta_absoluta(ruta)
    except UploadInvalido:
        raise HTTPException(status_code=400, detail="ruta invalida")
    if not path_abs.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="archivo no encontrado")
    return FileResponse(path_abs)


# ─── Internos ─────────────────────────────────────────────────────────────

def _tipo_desde_str(valor: str) -> TipoDocumentoObra:
    try:
        return TipoDocumentoObra(valor)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"tipo invalido: {valor}. Validos: {[t.value for t in TipoDocumentoObra]}",
        )


@interno_router.get(
    "/{codigo_unico}/documentos",
    response_model=list[DocumentoInternoItem],
)
def listar_documentos_interno(
    codigo_unico: str,
    _: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentoInternoItem]:
    docs = uploads_service.listar_todos(db, codigo_unico=codigo_unico)
    return [DocumentoInternoItem.model_validate(d) for d in docs]


@interno_router.post(
    "/{codigo_unico}/documentos",
    response_model=DocumentoInternoItem,
    status_code=status.HTTP_201_CREATED,
)
def subir_documento(
    codigo_unico: str,
    request: Request,
    archivo: UploadFile = File(...),
    tipo: str = Form("otro", description="expediente_tecnico | contrato | f8 | f9 | otro"),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentoInternoItem:
    if not _obra_existe(db, codigo_unico):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="obra no encontrada")
    tipo_enum = _tipo_desde_str(tipo)
    if tipo_enum == TipoDocumentoObra.foto:
        raise HTTPException(
            status_code=400,
            detail="usa /fotos para tipo=foto",
        )
    try:
        row = uploads_service.guardar_archivo(
            db,
            codigo_unico=codigo_unico,
            tipo=tipo_enum,
            upload=archivo,
            usuario_id=user.id,
        )
    except UploadInvalido as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    auditoria_service.registrar_desde_request(
        db,
        request,
        accion="subida_documento_obra",
        usuario_id=user.id,
        detalle={
            "codigo_unico_obra": codigo_unico,
            "tipo": tipo_enum.value,
            "documento_id": str(row["id"]),
            "tamano_bytes": row["tamano_bytes"],
        },
    )
    db.commit()
    return DocumentoInternoItem.model_validate(row)


@interno_router.post(
    "/{codigo_unico}/fotos",
    response_model=DocumentoInternoItem,
    status_code=status.HTTP_201_CREATED,
)
def subir_foto(
    codigo_unico: str,
    request: Request,
    archivo: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentoInternoItem:
    if not _obra_existe(db, codigo_unico):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="obra no encontrada")
    try:
        row = uploads_service.guardar_archivo(
            db,
            codigo_unico=codigo_unico,
            tipo=TipoDocumentoObra.foto,
            upload=archivo,
            usuario_id=user.id,
        )
    except UploadInvalido as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    auditoria_service.registrar_desde_request(
        db,
        request,
        accion="subida_documento_obra",
        usuario_id=user.id,
        detalle={
            "codigo_unico_obra": codigo_unico,
            "tipo": "foto",
            "documento_id": str(row["id"]),
        },
    )
    db.commit()
    return DocumentoInternoItem.model_validate(row)


@interno_router.delete(
    "/{codigo_unico}/documentos/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_documento(
    codigo_unico: str,
    doc_id: UUID,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    meta = uploads_service.obtener_metadata(db, doc_id)
    if meta is None or meta["codigo_unico_obra"] != codigo_unico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="documento no encontrado")
    borrado, ruta = uploads_service.eliminar(db, doc_id)
    if not borrado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="documento no encontrado")
    auditoria_service.registrar_desde_request(
        db,
        request,
        accion="subida_documento_obra",
        usuario_id=user.id,
        detalle={"eliminado": True, "documento_id": str(doc_id), "ruta": ruta},
    )
    db.commit()


@interno_router.delete(
    "/{codigo_unico}/fotos/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_foto(
    codigo_unico: str,
    doc_id: UUID,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    # Reuso del handler de documentos (misma logica).
    return eliminar_documento(codigo_unico, doc_id, request, user, db)
