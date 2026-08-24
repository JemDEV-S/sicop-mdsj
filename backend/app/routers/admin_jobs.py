"""Endpoints admin de trigger manual del sync SIAF/Invierte.

Requieren rol `admin` (Depends require_role). Ver `Docs/actividad-3-arquitectura-tecnica.md`
§6.3 (trigger manual) y §4.5 (endpoints admin).
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.jobs import scheduler as sched
from app.jobs.import_formato_a import importar_formato_a
from app.models.enums import CodigoRol
from app.security.deps import CurrentUser, require_role
from app.services import auditoria_service

router = APIRouter(prefix="/admin/jobs", tags=["admin-jobs"])


class TriggerResponse(BaseModel):
    job_id: str
    nombre: str
    estado: str


class CargaFormatoAResponse(BaseModel):
    """Resultado de subir un Excel SIAF Formato A (carga provisional)."""

    archivo: str
    ano: int
    mes: int | None         # mes de corte (1-12) del PERIODO de la cabecera
    registros: int          # filas cargadas (del ano de corte)
    descartadas: int        # filas ignoradas (sin fase / de otro ano)
    ejecutora: str | None
    periodo: str | None
    resumen_por_fase: dict[str, float]  # monto S/. por fase, estado 'A'


_EXT_PERMITIDAS = (".xlsx", ".xlsm")
_MAX_BYTES = 25 * 1024 * 1024  # 25 MB: el Formato A ronda 1-3 MB.


class RunEstadoResponse(BaseModel):
    job_id: str
    nombre: str
    inicio: datetime
    fin: datetime | None
    estado: str
    resultado: dict | None = None
    error: str | None = None


class JobProgramado(BaseModel):
    """Un job registrado en APScheduler con su próxima corrida."""

    id: str
    nombre: str
    trigger: str
    proxima_ejecucion: datetime | None


class CorridaPersistida(BaseModel):
    """Fila de `logs.sincronizacion` — corrida real (auto o manual)."""

    id: int
    job: str
    inicio: datetime
    fin: datetime | None
    estado: str            # en_curso | exito | error
    registros_procesados: int | None
    error_mensaje: str | None


class SnapshotFuente(BaseModel):
    """Edad del dato más reciente de una fuente sincronizada."""

    fuente: str            # p.ej. "SIAF ejecución", "SIGA pedidos"
    ultimo_sync: datetime | None
    ok: bool               # el conteo se pudo leer sin error


class EstadoSincronizacionResponse(BaseModel):
    """Foto consolidada del subsistema de sincronización (admin-only)."""

    generado_en: datetime
    scheduler_activo: bool
    jobs_programados: list[JobProgramado]
    ultimas_corridas: list[CorridaPersistida]
    snapshots: list[SnapshotFuente]
    corridas_manuales: list[RunEstadoResponse]


# Fuentes cuya "edad de snapshot" se muestra en la vista. Cada tupla es
# (etiqueta legible, columna timestamp, tabla). Se leen con MAX(col) y quedan
# aisladas en try/except para que una tabla ausente no tumbe todo el endpoint.
_SNAPSHOTS: list[tuple[str, str, str]] = [
    ("SIAF ejecución", "sincronizado_en", "siaf.ejecucion_presupuestal"),
    ("SIAF detalle (Formato A)", "cargado_en", "siaf.ejecucion_detalle_siaf"),
    ("Invierte.pe (obras)", "sincronizado_en", "siaf.inversiones"),
    ("SIGA pedidos", "sincronizado_en", "siga.pedidos"),
    ("Catálogos (metas)", "sincronizado_en", "ref.metas"),
    ("Catálogos (centros de costo)", "sincronizado_en", "ref.centros_costo"),
]


@router.post(
    "/sincronizar-siaf",
    response_model=TriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_sync_siaf(
    request: Request,
    ano: int | None = None,
    user: CurrentUser = Depends(require_role(CodigoRol.admin)),
    db: Session = Depends(get_db),
) -> TriggerResponse:
    job_id = sched.trigger_sync_siaf(ano=ano)
    auditoria_service.registrar_desde_request(
        db,
        request,
        accion="trigger_sync_siaf",
        usuario_id=user.id,
        detalle={"job_id": job_id, "ano": ano},
    )
    db.commit()
    return TriggerResponse(job_id=job_id, nombre="sync_siaf", estado="en_curso")


@router.post(
    "/sincronizar-invierte",
    response_model=TriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_sync_invierte(
    request: Request,
    user: CurrentUser = Depends(require_role(CodigoRol.admin)),
    db: Session = Depends(get_db),
) -> TriggerResponse:
    job_id = sched.trigger_sync_invierte()
    auditoria_service.registrar_desde_request(
        db,
        request,
        accion="trigger_sync_invierte",
        usuario_id=user.id,
        detalle={"job_id": job_id},
    )
    db.commit()
    return TriggerResponse(job_id=job_id, nombre="sync_invierte", estado="en_curso")


@router.post(
    "/revisar-resoluciones-ccmn",
    response_model=TriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_revisar_resoluciones(
    request: Request,
    ano: int | None = None,
    user: CurrentUser = Depends(require_role(CodigoRol.admin)),
    db: Session = Depends(get_db),
) -> TriggerResponse:
    """Revisa si alguna resolucion manual pedido<->CCMN quedo obsoleta (§5.1).

    Corre solo cada noche tras el sync; este endpoint es para forzarlo (p.ej.
    despues de una carga masiva de SIGA).
    """
    job_id = sched.trigger_revisar_resoluciones(ano=ano)
    auditoria_service.registrar_desde_request(
        db,
        request,
        accion="trigger_revisar_resoluciones",
        usuario_id=user.id,
        detalle={"job_id": job_id, "ano": ano},
    )
    db.commit()
    return TriggerResponse(
        job_id=job_id, nombre="revisar_resoluciones", estado="en_curso"
    )


@router.post(
    "/cargar-formato-a",
    response_model=CargaFormatoAResponse,
    status_code=status.HTTP_201_CREATED,
)
def cargar_formato_a(
    request: Request,
    archivo: UploadFile = File(...),
    ano: int | None = None,
    mes: int | None = None,
    user: CurrentUser = Depends(require_role(CodigoRol.admin)),
    db: Session = Depends(get_db),
) -> CargaFormatoAResponse:
    """Sube el Excel SIAF "Formato A" y lo carga en siaf.ejecucion_detalle_siaf.

    Carga PROVISIONAL: complementa la ejecucion agregada de la API MEF con el
    detalle por documento (expediente, fase, proveedor, clasificador). Reemplaza
    las filas del (ano, mes) de corte (swap por mes): asi se acumula el rastro
    cargando varios meses y el mes en curso se recarga a diario sin duplicar.
    Requiere rol admin.

    `ano`/`mes` son opcionales: si se omiten, se deducen de la cabecera del
    reporte (PERIODO) y, en su defecto, de las fechas mas frecuentes en las filas.
    """
    nombre = archivo.filename or "formato_a.xlsx"
    if not nombre.lower().endswith(_EXT_PERMITIDAS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato no soportado. Se esperaba {' o '.join(_EXT_PERMITIDAS)}.",
        )

    contenido = archivo.file.read()
    if not contenido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo esta vacio.",
        )
    if len(contenido) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo excede el limite de 25 MB.",
        )

    try:
        resultado = importar_formato_a(BytesIO(contenido), nombre, ano, mes)
    except Exception as exc:  # noqa: BLE001 — se reporta al cliente y se audita.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No se pudo procesar el Excel: {exc}",
        ) from exc

    auditoria_service.registrar_desde_request(
        db,
        request,
        accion="cargar_formato_a",
        usuario_id=user.id,
        detalle={
            "archivo": nombre,
            "ano": resultado.ano,
            "mes": resultado.mes,
            "registros": resultado.registros,
            "descartadas": resultado.descartadas,
        },
    )
    db.commit()

    return CargaFormatoAResponse(
        archivo=nombre,
        ano=resultado.ano,
        mes=resultado.mes,
        registros=resultado.registros,
        descartadas=resultado.descartadas,
        ejecutora=resultado.ejecutora,
        periodo=resultado.periodo,
        resumen_por_fase=resultado.resumen_por_fase,
    )


@router.get("/estado", response_model=EstadoSincronizacionResponse)
def estado_sincronizacion(
    _: CurrentUser = Depends(require_role(CodigoRol.admin)),
    db: Session = Depends(get_db),
) -> EstadoSincronizacionResponse:
    """Foto consolidada del subsistema de sincronización.

    Reúne lo único confiable para saber "¿está corriendo?":
      - si el scheduler embebido está activo y sus próximas corridas;
      - las últimas corridas persistidas en `logs.sincronizacion` (auto +
        manual, sobreviven reinicios);
      - la edad real del dato más reciente por fuente (MAX(sincronizado_en));
      - las corridas manuales en memoria de esta instancia.
    """
    # Últimas corridas persistidas (historial real, incluye las automáticas).
    filas = db.execute(
        text(
            """
            SELECT id, job, inicio, fin, estado::text AS estado,
                   registros_procesados, error_mensaje
              FROM logs.sincronizacion
             ORDER BY inicio DESC
             LIMIT 30
            """
        )
    ).mappings().all()
    ultimas = [CorridaPersistida(**dict(f)) for f in filas]

    # Edad de cada snapshot — cada fuente aislada para no romper el endpoint.
    snapshots: list[SnapshotFuente] = []
    for etiqueta, col, tabla in _SNAPSHOTS:
        try:
            row = db.execute(
                text(f"SELECT MAX({col}) AS ultimo FROM {tabla}")  # noqa: S608
            ).first()
            snapshots.append(
                SnapshotFuente(
                    fuente=etiqueta,
                    ultimo_sync=row.ultimo if row else None,
                    ok=True,
                )
            )
        except Exception:
            db.rollback()
            snapshots.append(
                SnapshotFuente(fuente=etiqueta, ultimo_sync=None, ok=False)
            )

    manuales = [
        RunEstadoResponse(
            job_id=r.job_id,
            nombre=r.nombre,
            inicio=r.inicio,
            fin=r.fin,
            estado=r.estado,
            resultado=r.resultado or None,
            error=r.error,
        )
        for r in sched.listar_runs()
    ]

    return EstadoSincronizacionResponse(
        generado_en=datetime.utcnow(),
        scheduler_activo=sched.esta_corriendo(),
        jobs_programados=[
            JobProgramado(**j) for j in sched.listar_jobs_programados()
        ],
        ultimas_corridas=ultimas,
        snapshots=snapshots,
        corridas_manuales=manuales,
    )


@router.get("/{job_id}", response_model=RunEstadoResponse)
def estado_run(
    job_id: str,
    _: CurrentUser = Depends(require_role(CodigoRol.admin)),
) -> RunEstadoResponse:
    run = sched.obtener_run(job_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="job_id no encontrado"
        )
    return RunEstadoResponse(
        job_id=run.job_id,
        nombre=run.nombre,
        inicio=run.inicio,
        fin=run.fin,
        estado=run.estado,
        resultado=run.resultado or None,
        error=run.error,
    )


@router.get("", response_model=list[RunEstadoResponse])
def listar(
    _: CurrentUser = Depends(require_role(CodigoRol.admin)),
) -> list[RunEstadoResponse]:
    return [
        RunEstadoResponse(
            job_id=r.job_id,
            nombre=r.nombre,
            inicio=r.inicio,
            fin=r.fin,
            estado=r.estado,
            resultado=r.resultado or None,
            error=r.error,
        )
        for r in sched.listar_runs()
    ]
