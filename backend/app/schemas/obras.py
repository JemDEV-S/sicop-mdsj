"""Schemas Pydantic para el modulo de obras (HU-01, HU-02, HU-04)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class ObraCardResponse(BaseModel):
    """Tarjeta del listado publico (HU-01)."""

    codigo_unico: str
    nombre_inversion: str | None
    funcion: str | None
    tipologia: str | None
    modalidad: str | None
    estado: str | None
    etapa_f8: str | None
    avance_fisico: float | None
    avance_ejecucion: float | None
    pim_anio_actual: float | None
    dev_anio_actual: float | None
    tiene_avan_fisico: str | None
    latitud: float | None
    longitud: float | None
    semaforo: str = "desconocido"


class ObraListadoResponse(BaseModel):
    items: list[ObraCardResponse]
    total: int
    page: int
    size: int


class MontosObra(BaseModel):
    pia: float = 0
    pim: float = 0
    certificado: float = 0
    comprometido_anual: float = 0
    devengado: float = 0
    girado: float = 0
    porcentaje_devengado: float | None = None


class ObraDetalleResponse(BaseModel):
    codigo_unico: str
    nombre_inversion: str | None
    tipo_inversion: str | None
    marco: str | None
    estado: str | None
    situacion: str | None
    funcion: str | None
    programa: str | None
    tipologia: str | None = Field(alias="des_tipologia", default=None)
    modalidad: str | None = Field(alias="des_modalidad", default=None)
    etapa_f8: str | None
    tiene_f8: str | None
    tiene_f9: str | None
    tiene_f12b: str | None
    expediente_tecnico: str | None
    informe_cierre: str | None

    avance_fisico: float | None
    avance_ejecucion: float | None
    tiene_avan_fisico: str | None

    fec_ini_ejecucion: date | None
    fec_fin_ejecucion: date | None
    fec_ini_ejec_fisica: date | None
    fec_fin_ejec_fisica: date | None
    fecha_viabilidad: date | None
    primer_devengado: date | None
    ultimo_devengado: date | None

    latitud: float | None
    longitud: float | None
    ubigeo: str | None
    departamento: str | None
    provincia: str | None
    distrito: str | None

    nombre_uei: str | None
    nombre_uf: str | None
    nombre_opmi: str | None

    costo_actualizado: float | None
    monto_viable: float | None
    saldo_ejecutar: float | None

    montos_ejecucion: MontosObra
    semaforo: str = "desconocido"

    sincronizado_en: datetime | None = None

    model_config = {"populate_by_name": True}


class ObraMapaItem(BaseModel):
    codigo_unico: str
    nombre_inversion: str | None
    funcion: str | None
    avance_fisico: float | None
    pim_anio_actual: float | None
    latitud: float
    longitud: float
    semaforo: str = "desconocido"


class ObrasMapaResponse(BaseModel):
    items: list[ObraMapaItem]
    sin_coordenadas: list[dict]
    total_con_coords: int
    total_sin_coords: int
