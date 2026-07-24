"""Schemas del pipeline (HU-09, HU-10, HU-11).

Modelo jerarquico en dos niveles (ver Docs/exploracion-siga-pipeline-extendido.md §17.6):

    Macrofases (6): solicitud, programacion, certificacion, contratacion,
                    ejecucion, cierre.
    Etapas detalladas: 13 para servicios, 16 para bienes.

Un pedido cae en la etapa mas avanzada cuya evidencia existe en SIGA.
El widget del dashboard consume por macrofase; el pipeline detallado
consume por etapa. La macrofase se deriva de la etapa (mapping fijo).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

# ─── Taxonomia canonica ───────────────────────────────────────────────────

MACROFASES = ("solicitud", "programacion", "certificacion",
              "contratacion", "ejecucion", "cierre")

Macrofase = Literal[
    "solicitud", "programacion", "certificacion",
    "contratacion", "ejecucion", "cierre",
]

# Etapas detalladas (codigo estable). Servicios usan 1-11 + 15-16.
# Bienes usan las 16.
ETAPA_PEDIDO_REGISTRADO      = "pedido_registrado"        # [1]
ETAPA_PEDIDO_APROBADO        = "pedido_aprobado"          # [2]
ETAPA_CUADRO_NECESIDAD       = "cuadro_necesidad"         # [3]
ETAPA_PUENTE_PAAC            = "puente_paac"              # [4]
ETAPA_CCMN                   = "ccmn_em_cvr"              # [5]
ETAPA_COTIZACION             = "cotizacion"               # [6]
ETAPA_CUADRO_ADQUISICION     = "cuadro_adquisicion"       # [7]
ETAPA_CERTIFICACION          = "certificacion_ccp"        # [8]
ETAPA_ORDEN_EMITIDA          = "orden_emitida"            # [9]
ETAPA_COMPROMISO_SIAF        = "compromiso_siaf"          # [10]
ETAPA_EJECUCION              = "ejecucion"                # [11]
ETAPA_RECEPCION_KARDEX       = "recepcion_kardex"         # [12] solo B
ETAPA_PEDIDO_INTERNO         = "pedido_interno"           # [13] solo B
ETAPA_DESPACHO_PECOSA        = "despacho_pecosa"          # [14] solo B
ETAPA_DEVENGADO              = "devengado"                # [15]
ETAPA_CIERRE                 = "cierre"                   # [16]

ETAPAS_ORDEN: tuple[str, ...] = (
    ETAPA_PEDIDO_REGISTRADO,
    ETAPA_PEDIDO_APROBADO,
    ETAPA_CUADRO_NECESIDAD,
    ETAPA_PUENTE_PAAC,
    ETAPA_CCMN,
    ETAPA_COTIZACION,
    ETAPA_CUADRO_ADQUISICION,
    ETAPA_CERTIFICACION,
    ETAPA_ORDEN_EMITIDA,
    ETAPA_COMPROMISO_SIAF,
    ETAPA_EJECUCION,
    ETAPA_RECEPCION_KARDEX,
    ETAPA_PEDIDO_INTERNO,
    ETAPA_DESPACHO_PECOSA,
    ETAPA_DEVENGADO,
    ETAPA_CIERRE,
)

ETAPA_A_MACROFASE: dict[str, Macrofase] = {
    ETAPA_PEDIDO_REGISTRADO:  "solicitud",
    ETAPA_PEDIDO_APROBADO:    "solicitud",
    ETAPA_CUADRO_NECESIDAD:   "programacion",
    ETAPA_PUENTE_PAAC:        "programacion",
    ETAPA_CCMN:               "programacion",
    ETAPA_COTIZACION:         "programacion",
    ETAPA_CUADRO_ADQUISICION: "programacion",
    ETAPA_CERTIFICACION:      "certificacion",
    ETAPA_ORDEN_EMITIDA:      "contratacion",
    ETAPA_COMPROMISO_SIAF:    "contratacion",
    ETAPA_EJECUCION:          "ejecucion",
    ETAPA_RECEPCION_KARDEX:   "ejecucion",
    ETAPA_PEDIDO_INTERNO:     "ejecucion",
    ETAPA_DESPACHO_PECOSA:    "ejecucion",
    ETAPA_DEVENGADO:          "ejecucion",
    ETAPA_CIERRE:             "cierre",
}

# Numero visible en UI (1..16).
ETAPA_A_NUMERO: dict[str, int] = {
    e: i + 1 for i, e in enumerate(ETAPAS_ORDEN)
}

# Etiquetas humanas para el UI (evita duplicar strings en el front).
ETAPA_A_LABEL: dict[str, str] = {
    ETAPA_PEDIDO_REGISTRADO:  "Pedido registrado",
    ETAPA_PEDIDO_APROBADO:    "Aprobacion pedido",
    ETAPA_CUADRO_NECESIDAD:   "Cuadro necesidad",
    ETAPA_PUENTE_PAAC:        "Puente pedido<->PAAC",
    ETAPA_CCMN:               "CCMN / EM (CVR)",
    ETAPA_COTIZACION:         "Cotizacion",
    ETAPA_CUADRO_ADQUISICION: "Cuadro adquisicion",
    ETAPA_CERTIFICACION:      "Certificacion (CCP)",
    ETAPA_ORDEN_EMITIDA:      "Orden emitida",
    ETAPA_COMPROMISO_SIAF:    "Compromiso / envio SIAF",
    ETAPA_EJECUCION:          "Ejecucion",
    ETAPA_RECEPCION_KARDEX:   "Recepcion kardex",
    ETAPA_PEDIDO_INTERNO:     "Pedido interno",
    ETAPA_DESPACHO_PECOSA:    "Despacho / pecosa",
    ETAPA_DEVENGADO:          "Devengado",
    ETAPA_CIERRE:             "Cierre",
}

MACROFASE_A_LABEL: dict[Macrofase, str] = {
    "solicitud":     "Solicitud",
    "programacion":  "Programacion",
    "certificacion": "Certificacion",
    "contratacion":  "Contratacion",
    "ejecucion":     "Ejecucion",
    "cierre":        "Cierre",
}


# ─── Confianza del match pedido <-> CCMN ─────────────────────────────────
#
# SIGA no registra que CCMN corresponde a que pedido: logistica copia los datos
# del pedido a un CCMN nuevo y no los vincula. Cuando la bolsa (SEC_CUA_MOD_SAL)
# agrupa varios pedidos, hay N candidatos y ninguno es "el" del pedido.
# En vez de elegir por parecido (metodos medidos que pierden el CCMN correcto,
# ver §2 del doc), se resuelve en cascada y se declara el nivel.
#
# Ref: Docs/diagnostico-2026-07-20/refactorizacion-pipeline-pedido-ccmn.md §4

NivelConfianza = Literal[
    "unico",            # 1 solo candidato estructural en la bolsa
    "declarado",        # CCMN del texto de la orden ∈ candidatos
    "declarado_cert",   # CCMN de SIG_CERTIFICACION_DOC ∈ candidatos
    "resuelto_manual",  # asociado por un funcionario (referencial, opcional)
    "conflicto",        # una fuente declara un CCMN ∉ candidatos
    "ambiguo",          # N candidatos, ninguna fuente resuelve
    "sin_ccmn",         # 0 candidatos: el pedido aun no se programo
]

# Orden de prioridad de la cascada. `declarado` manda sobre `declarado_cert`
# porque la orden es posterior en el proceso y estuvo bajo mas escrutinio.
CONFIANZA_PRIORIDAD: tuple[str, ...] = (
    "unico",
    "declarado",
    "declarado_cert",
    "resuelto_manual",
)

# Niveles en los que el CCMN identificado es de ESTE pedido.
CONFIANZA_RESUELTA: frozenset[str] = frozenset(CONFIANZA_PRIORIDAD)

CONFIANZA_A_LABEL: dict[str, str] = {
    "unico":           "Candidato unico",
    "declarado":       "Declarado en la orden",
    "declarado_cert":  "Declarado en la certificacion",
    "resuelto_manual": "Asociado manualmente",
    "conflicto":       "Conflicto entre fuentes",
    "ambiguo":         "Ambiguo: varios candidatos",
    "sin_ccmn":        "Sin CCMN todavia",
}


# ─── Estado de cada etapa en el timeline ─────────────────────────────────
#
# Reemplaza el booleano `alcanzada`. La distincion critica es directo vs grupo:
# hoy el MAX(CASE...) del repo responde "¿algun candidato llego a esta etapa?",
# y los otros candidatos son de OTROS pedidos -> pinta verdes ajenos.

EstadoEtapa = Literal[
    "directo",    # alcanzada por ESTE pedido — dato duro
    "via_ccmn",   # via CCMN identificado por fuente declarativa — fecha aprox.
    "grupo",      # algun candidato de la bolsa llego; no se sabe si por este
    "manual",     # via CCMN asociado manualmente
    "sin_dato",   # no alcanzada, o sin evidencia
]

# Estados que cuentan como "alcanzada" para clasificar la etapa maxima.
# `grupo` NO cuenta: es justamente el caso que hoy falla en silencio.
ESTADOS_ALCANZADOS: frozenset[str] = frozenset(
    {"directo", "via_ccmn", "manual"}
)

CONFIANZA_A_ESTADO: dict[str, str] = {
    "unico":           "directo",
    "declarado":       "via_ccmn",
    "declarado_cert":  "via_ccmn",
    "resuelto_manual": "manual",
    "conflicto":       "grupo",
    "ambiguo":         "grupo",
    "sin_ccmn":        "sin_dato",
}


# ─── Tarjeta del pedido (kanban) ──────────────────────────────────────────

class PedidoCard(BaseModel):
    ano_eje: int
    sec_ejec: str
    nro_pedido: int
    tipo_bien: str
    tipo_pedido: str | None = None
    centro_costo: str | None = None
    sec_func: int | None = None
    estado_pedido: str | None = None
    fecha_pedido: date | None = None
    fecha_aprob: date | None = None
    fecha_atenc: date | None = None
    motivo: str | None = None
    solicitante: str | None = None
    fuente_financ: str | None = None
    monto_total: float = 0
    items: int = 0

    # Etapa detallada + macrofase derivada + numero (1..16) para UI.
    etapa: str
    etapa_numero: int
    etapa_label: str
    macrofase: Macrofase
    macrofase_label: str

    # Flags de evidencia — utiles para debug y para pintar el timeline en detalle.
    tiene_cuadro_neces: int = 0
    tiene_puente_paac: int = 0
    tiene_ccmn: int = 0
    tiene_cotizacion: int = 0
    tiene_cuadro_adq: int = 0
    tiene_certificacion: int = 0
    tiene_orden: int = 0
    tiene_compromiso: int = 0
    tiene_ejecucion: int = 0
    tiene_kardex: int = 0
    tiene_pedido_interno: int = 0
    tiene_pecosa: int = 0
    tiene_devengado: int = 0
    tiene_cierre: int = 0

    # Muestras: primer ID encontrado en cada tabla (para drill-down / tooltips).
    nro_consolid_muestra: int | None = None      # CCMN
    nro_est_mdo_muestra: int | None = None       # EM/CVR
    nro_orden_muestra: int | None = None
    exp_siaf_muestra: int | None = None
    exp_siga_muestra: int | None = None
    sec_cuadro_muestra: int | None = None
    nro_certifica_muestra: int | None = None
    nro_certifica_siaf_muestra: int | None = None
    match_metodo: str | None = None

    # Cascada de confianza del match pedido <-> CCMN (§4 del doc). El frontend
    # debe pintar `estado_programacion` con color propio: `grupo` es avance de
    # OTROS pedidos de la bolsa y hoy se ve como un verde falso.
    n_candidatos_ccmn: int = 0
    confianza_ccmn: NivelConfianza | None = None
    confianza_ccmn_label: str | None = None
    estado_programacion: EstadoEtapa | None = None
    ccmn_atribuido: int | None = None

    dias_en_etapa: int | None = None
    estancado: bool = False

    model_config = {"populate_by_name": True}


# ─── Conteo agregado por macrofase (widget dashboard) ─────────────────────

class EtapaConteo(BaseModel):
    etapa: str
    etapa_numero: int
    etapa_label: str
    conteo: int = 0
    monto: float = 0.0


class MacrofaseConteo(BaseModel):
    macrofase: Macrofase
    macrofase_label: str
    conteo: int = 0
    monto: float = 0.0
    etapas: list[EtapaConteo] = []


class KanbanResponse(BaseModel):
    """Vista del kanban agrupada por macrofase.

    `pedidos_por_etapa` permite drill-down: mapping etapa->PedidoCard[].
    `macrofases` da los agregados listos para el widget.
    """
    ano: int
    macrofases: list[MacrofaseConteo]
    pedidos_por_etapa: dict[str, list[PedidoCard]]


# ─── Detalle de un pedido (cadena completa) ───────────────────────────────

class ItemPedido(BaseModel):
    secuencia: int
    grupo_bien: str | None = None
    clase_bien: str | None = None
    familia_bien: str | None = None
    item_bien: str | None = None
    cant_solicitada: float | None = None
    cant_aprobada: float | None = None
    cant_atendida: float | None = None
    valor_total: float | None = None
    clasificador: str | None = None
    nro_orden_declarado: int | None = None
    nro_pecosa: int | None = None
    estado_ped: str | None = None
    estado_atend: str | None = None
    estado_confor: str | None = None
    estado_compra: str | None = None
    fecha_confor: date | None = None


class OrdenAsociada(BaseModel):
    nro_orden: int
    tipo_bien: str
    exp_siaf: int | None = None
    exp_siga: int | None = None
    sec_cuadro: int | None = None
    nro_certifica: int | None = None
    estado: str | None = None
    estado_siaf: str | None = None
    total_fact_soles: float | None = None
    concepto: str | None = None
    fecha_orden: date | None = None
    proveedor_nombre: str | None = None
    proveedor_ruc: str | None = None
    match_metodos: str | None = None


class Cuadro(BaseModel):
    sec_cuadro: int
    tipo_bien: str
    estado: str | None = None
    fecha_cuadro: date | None = None
    fecha_autoriz: date | None = None
    fecha_compra: date | None = None
    valor_total: float | None = None


class Certificacion(BaseModel):
    nro_certifica: int
    nro_certifica_siaf: int | None = None
    estado_certifica_siaf: str | None = None
    fecha: date | None = None


class Expediente(BaseModel):
    exp_siga: int
    tipo_ppto: int | None = None
    tipo_fase: str | None = None
    exp_siaf: int | None = None
    estado_siaf: str | None = None
    fecha_exp_siga: date | None = None
    fecha_documento: date | None = None
    fecha_siaf: date | None = None


class Conformidad(BaseModel):
    nro_orden: int | None = None
    ano_orden: int | None = None
    tipo_bien: str | None = None
    fecha_movimto: date | None = None
    indi_confor: str | None = None
    proveedor: str | None = None
    estado_deveng: str | None = None
    exp_siaf: str | None = None
    responsable: str | None = None
    observacion: str | None = None


class MovimientoAlmacen(BaseModel):
    nro_movimto: int
    nro_orden: int | None = None
    tipo_movimto: str | None = None
    tipo_transac: int | None = None
    tipo_ppto: int | None = None
    fecha_movimto: date | None = None
    nro_guia: str | None = None


class DocumentoEtapa(BaseModel):
    """Identificador con el que se encuentra el documento en SIGA.

    Sin esto el recorrido dice "llego a certificacion" pero no *cual*, que es
    justo el dato que el funcionario necesita para verificarlo.
    """
    etiqueta: str
    valor: str


class TimelineEvento(BaseModel):
    """Un evento verificable del timeline del pedido (13/16 hitos posibles)."""
    etapa: str
    etapa_numero: int
    etapa_label: str
    macrofase: Macrofase
    fecha: datetime | None = None
    detalle: str | None = None
    documentos: list[DocumentoEtapa] = []
    # Estado real de la etapa (§8). `grupo` es el caso critico: avance de
    # OTROS pedidos de la bolsa, que antes se pintaba como un verde creible.
    estado: EstadoEtapa = "sin_dato"
    # Compatibilidad: excluye `grupo` — un avance ajeno no es de este pedido.
    alcanzada: bool = False


class PedidoDetalleResponse(BaseModel):
    ano_eje: int
    sec_ejec: str
    nro_pedido: int
    tipo_bien: str
    tipo_pedido: str | None = None
    centro_costo: str | None = None
    centro_costo_nombre: str | None = None
    sec_func: int | None = None
    act_proy: str | None = None
    nombre_meta: str | None = None
    estado_pedido: str | None = None
    fecha_pedido: date | None = None
    fecha_aprob: date | None = None
    fecha_atenc: date | None = None
    motivo: str | None = None
    solicitante: str | None = None
    fuente_financ: str | None = None

    etapa_actual: str
    etapa_actual_numero: int
    etapa_actual_label: str
    macrofase_actual: Macrofase
    macrofase_actual_label: str

    # Cascada de confianza (§4). La UI muestra SIEMPRE lo que dice la cascada
    # automatica, tambien cuando hay resolucion manual (§5).
    confianza_ccmn: NivelConfianza | None = None
    confianza_ccmn_label: str | None = None
    estado_programacion: EstadoEtapa | None = None
    ccmn_atribuido: int | None = None
    ccmn_candidatos: list[int] = []
    sec_cua_mod_sal: int | None = None

    items: list[ItemPedido]
    ordenes: list[OrdenAsociada]
    cuadros: list[Cuadro] = []
    certificaciones: list[Certificacion] = []
    expedientes: list[Expediente] = []
    conformidades: list[Conformidad]
    movimientos_almacen: list[MovimientoAlmacen] = []
    timeline: list[TimelineEvento] = []


# ─── Vista de bolsa y resolucion manual (§5, §8.2) ───────────────────────

class PedidoEnBolsa(BaseModel):
    """Un pedido que comparte la bolsa `SEC_CUA_MOD_SAL`."""
    nro_pedido: int
    tipo_bien: str
    tipo_pedido: str | None = None
    centro_costo: str | None = None
    sec_func: int | None = None
    estado_pedido: str | None = None
    fecha_pedido: date | None = None
    motivo: str | None = None
    solicitante: str | None = None
    valor_soles: float | None = None
    item: str | None = None
    # Nivel que la cascada automatica le asigna. La UI lo muestra SIEMPRE,
    # junto a la resolucion manual si la hay (§5).
    confianza_ccmn: NivelConfianza | None = None


class HitoCCMN(BaseModel):
    """Un paso del recorrido propio de un CCMN, para la vista de bolsa."""
    codigo: str          # 'ccmn' | 'cotizacion' | 'cuadro' | 'ccp' | 'orden'
    label: str
    numero: str | None = None   # el identificador, si existe
    alcanzado: bool = False


class CandidatoCCMN(BaseModel):
    """Un CCMN candidato de la bolsa, con su avance propio."""
    nro_consolid: int
    tipo_consolid: str | None = None
    fecha_cons: date | None = None
    valor_plan: float | None = None
    nro_est_mdo: int | None = None
    nro_certifica: int | None = None
    nro_certifica_siaf: int | None = None
    sec_cuadro: int | None = None
    nro_orden: int | None = None
    fecha_orden: date | None = None
    # True si este CCMN esta asociado manualmente al pedido consultado.
    asociado_manual: bool = False
    # Recorrido propio del CCMN: hasta donde llego ESTE cuadro, con sus
    # numeros. Es lo que permite comparar candidatos entre si.
    flujo: list[HitoCCMN] = []


class BolsaResponse(BaseModel):
    """Vista de bolsa: donde vive la ambiguedad (§2.1).

    Ambas listas van de mas reciente a mas antiguo, con desempate por numero
    descendente para que el orden sea estable entre recargas. El monto se
    muestra pero NO ordena: ordenar por proximidad de monto seria una
    recomendacion disfrazada, y ese metodo pierde el CCMN correcto (§2).
    """
    ano_eje: int
    sec_cua_mod_sal: int
    tipo_bien: str
    pedidos: list[PedidoEnBolsa] = []
    candidatos: list[CandidatoCCMN] = []


class ResolucionCreate(BaseModel):
    """Alta de una asociacion manual pedido -> CCMN."""
    tipo_pedido: str
    nro_consolid: int
    nota: str | None = None
    ano_eje: int | None = None


class ResolucionResponse(BaseModel):
    id: UUID
    nro_consolid: int
    sec_cua_mod_sal: int | None = None
    nota: str | None = None
    usuario_id: UUID | None = None
    usuario_nombre: str | None = None
    creado_en: datetime
    revocado_en: datetime | None = None
    revocado_por: UUID | None = None
    revocado_por_nombre: str | None = None


# ─── Anotaciones (sin cambios) ────────────────────────────────────────────

class AnotacionCreate(BaseModel):
    texto: str


class AnotacionResponse(BaseModel):
    id: int
    entidad_tipo: str
    entidad_id: str
    usuario_id: str
    texto: str
    creado_en: datetime
