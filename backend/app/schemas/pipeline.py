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
# Nombres en lenguaje del funcionario (no jerga SIGA). Fuente unica: la usan
# el kanban, el detalle del pedido y los reportes. Cambiar aqui cambia todo.
ETAPA_A_LABEL: dict[str, str] = {
    ETAPA_PEDIDO_REGISTRADO:  "Pedido registrado",
    ETAPA_PEDIDO_APROBADO:    "Pedido aprobado",
    ETAPA_CUADRO_NECESIDAD:   "Cuadro de necesidades",
    ETAPA_PUENTE_PAAC:        "En programacion anual",
    ETAPA_CCMN:               "Estudio de mercado",
    ETAPA_COTIZACION:         "Cotizacion",
    ETAPA_CUADRO_ADQUISICION: "Cuadro de adquisicion",
    ETAPA_CERTIFICACION:      "Certificacion presupuestal",
    ETAPA_ORDEN_EMITIDA:      "Orden emitida",
    ETAPA_COMPROMISO_SIAF:    "Compromiso (SIAF)",
    ETAPA_EJECUCION:          "Ejecucion",
    ETAPA_RECEPCION_KARDEX:   "Recepcion en almacen",
    ETAPA_PEDIDO_INTERNO:     "Pedido interno",
    ETAPA_DESPACHO_PECOSA:    "Despacho (PECOSA)",
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


# ─── Alertas v2 (Guia Pipeline v2 §02.4) ─────────────────────────────────
#
# Principio: una alerta necesita EVIDENCIA y FECHA. El sistema solo alarma en
# rojo cuando puede probar el problema. Lo inferido (puente sin resolver) es
# ambar/info, nunca rojo.

TipoAlerta = Literal[
    "estancado_real",     # etapa con fecha > umbral Y ninguna posterior (rojo)
    "puente_pendiente",   # bolsa con avance pero puente sin resolver (ambar/info)
    "conflicto_puente",   # fuente declara un CCMN fuera de los candidatos (ambar)
    "cerrado_negativo",   # denegado/anulado con fecha (gris, terminal)
    "sin_consolidar",     # aprobado hace > umbral sin bolsa (ambar)
    "desfase_devengado",  # comprometido hace > umbral y devengado MEF = 0 (ambar)
]

# Severidad -> color de la UI. La semantica de color es unica en todo el modulo
# (§04): rojo solo estancado_real; el resto ambar/gris.
ALERTA_SEVERIDAD: dict[str, str] = {
    "estancado_real":    "rojo",
    "puente_pendiente":  "ambar",
    "conflicto_puente":  "ambar",
    "cerrado_negativo":  "gris",
    "sin_consolidar":    "ambar",
    "desfase_devengado": "ambar",
}


class Alerta(BaseModel):
    """Una advertencia con su evidencia y fecha (§02.4). Sin dato cierto, no hay alerta."""
    tipo: TipoAlerta
    severidad: Literal["rojo", "ambar", "gris"]
    evidencia: str                    # texto para el tooltip / aria-label
    desde: date | None = None         # fecha que sustenta la alerta


class Identificadores(BaseModel):
    """Los 3 IDs principales, visibles en toda vista (§00 principio 2)."""
    pedido: str                       # "232-2026/S"
    orden: str | None = None          # "O/S 232" — null si el puente no resuelve
    exp_siaf: int | None = None
    ccp_siaf: int | None = None


class OrdenBolsa(BaseModel):
    nro_orden: int
    fecha: date | None = None


class AvanceBolsa(BaseModel):
    """Avance DURO de la bolsa (cierto aunque el puente no resuelva, §02.1)."""
    n_ordenes: int = 0
    ordenes: list[OrdenBolsa] = []
    max_etapa: str | None = None      # etapa mas avanzada alcanzada por la bolsa
    max_etapa_label: str | None = None


class Puente(BaseModel):
    """Estado del puente pedido<->CCMN + avance de su bolsa."""
    nivel: NivelConfianza | None = None
    nivel_label: str | None = None
    bolsa: int | None = None
    candidatos: list[int] = []
    ccmn_atribuido: int | None = None
    avance_bolsa: AvanceBolsa = AvanceBolsa()


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

    # ─── v2 ───────────────────────────────────────────────────────────
    # Los 3 identificadores principales, siempre presentes (§00 principio 2).
    identificadores: Identificadores | None = None
    # Fechas de TODAS las etapas alcanzadas (§02.3). La UI muestra "en X desde
    # <fecha>", no solo "N dias".
    fechas: dict[str, date] = {}
    # Estado del puente + avance de la bolsa (cierto aunque el puente no resuelva).
    puente: Puente | None = None
    # Alerta v2: una sola, con evidencia y fecha. null = sin alerta (§02.4).
    alerta: Alerta | None = None
    # Frescura del snapshot (§01.4): ultimo sync OK. La UI lo muestra en el pie.
    sincronizado_hasta: datetime | None = None

    # Cascada de confianza (compatibilidad; el frontend v2 usa `puente`).
    n_candidatos_ccmn: int = 0
    confianza_ccmn: NivelConfianza | None = None
    confianza_ccmn_label: str | None = None
    estado_programacion: EstadoEtapa | None = None
    ccmn_atribuido: int | None = None

    dias_en_etapa: int | None = None
    # `estancado` ahora significa estancado_real (rojo). Los demas casos van en
    # `alerta` con su severidad — un pedido con puente_pendiente NO esta estancado.
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
    # Fecha del VB del jefe (seguimiento SIGA): en los pedidos de compra es el
    # hito real de aprobacion — el estado '2' del seguimiento nunca se alcanza.
    fecha_vb_jefe: date | None = None
    motivo: str | None = None
    solicitante: str | None = None
    fuente_financ: str | None = None
    # Nombre del catalogo FUENTE_FINANC (el codigo va en fuente_financ).
    fuente_financ_nombre: str | None = None

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
    # Obsolescencia (§5.1): sellado por el job cuando la bolsa cambio despues
    # de resolver. NULL = vigente. `candidatos_en_revision` deja ver que cambio.
    revision_pendiente_desde: datetime | None = None
    candidatos_en_revision: list[int] | None = None


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


# ─── Reporte profesional (pivote Meta → Clasificador → Pedido, §9.7) ─────
#
# Vista para economistas. La regla anti-inflado (§7) se refleja en el modelo:
# el monto SIGA es por pedido (informativo, sumable por fila); el dinero MEF va
# por celda/meta (real, sumable 1× por meta); el devengado por pedido es
# ESTIMADO por reparto y se rotula con `atribucion` — no se suma en un total.


class SemaforoCtx(BaseModel):
    color: str
    esperado: float
    real: float | None = None
    rezago: float | None = None
    mes_corte: int


class MefMeta(BaseModel):
    pim: float
    comprometido: float
    devengado: float
    porcentaje_devengado: float | None = None
    semaforo: str
    semaforo_ctx: SemaforoCtx | None = None


class MefCelda(BaseModel):
    pim: float
    comprometido: float
    devengado: float


class PedidoReporte(BaseModel):
    """Fila-pedido del reporte: recorrido + monto SIGA + dinero atribuido."""
    nro_pedido: int
    tipo_bien: str
    tipo_pedido: str | None = None
    centro_costo: str | None = None
    motivo: str | None = None
    identificadores: Identificadores | None = None
    # Mapa etapa → fecha (el rastro histórico para el mini-timeline por fila).
    fechas: dict[str, date] = {}
    etapa: str
    etapa_label: str
    macrofase: Macrofase
    dias_en_etapa: int | None = None
    estancado: bool = False
    alerta: Alerta | None = None
    monto_siga: float = 0
    # Honestidad del puente (§2.2): >1 candidato ⇒ el avance de bolsa es del grupo.
    n_candidatos_ccmn: int = 0
    confianza_ccmn: NivelConfianza | None = None
    tiene_orden: bool = False
    # Capa de dinero por pedido. `atribucion`: "directo" (celda de 1 pedido),
    # "estimado" (reparto), o null (sin orden → sin ejecución atribuible).
    comprometido_pedido: float | None = None
    devengado_estimado: float | None = None
    atribucion: Literal["directo", "estimado"] | None = None


class CeldaClasificador(BaseModel):
    clasificador: str                 # "3.1.10.1.1"
    clasificador_nombre: str | None = None
    n_pedidos: int
    atribucion_directa: bool          # celda de 1 pedido → sin reparto
    monto_siga: float
    mef: MefCelda | None = None       # dinero MEF real de la celda (null si no cruza)
    pedidos: list[PedidoReporte] = []


class OrdenReporte(BaseModel):
    """Orden de compra (O/C, bien) o de servicio (O/S) de una meta.

    Sale del snapshot `siga.ordenes` (misma fuente que el puente pedido↔orden),
    keyed por `sec_func`. `tipo_bien` separa O/C ('B') de O/S ('S').
    """
    nro_orden: int
    tipo_bien: str                    # 'B' → O/C · 'S' → O/S
    clasificador: str | None = None
    estado: str | None = None         # estado SIGA de la orden
    estado_siaf: str | None = None
    exp_siaf: int | None = None
    total_fact_soles: float = 0
    concepto: str | None = None
    proveedor_nombre: str | None = None
    proveedor_ruc: str | None = None
    fecha_orden: date | None = None
    # Recepción de la orden ('1'=pendiente, '2'=parcial, '3'=completa).
    flag_recep: str | None = None


class PecosaReporte(BaseModel):
    """PECOSA (despacho de almacén) de una meta, vía la orden que la origina."""
    nro_pecosa: int
    nro_orden: int | None = None
    tipo_bien: str
    nro_guia: str | None = None
    fecha_movimto: date | None = None
    proveedor_nombre: str | None = None
    total_fact_soles: float = 0


class MetaReporte(BaseModel):
    sec_func: int
    nombre_meta: str | None = None
    # Nº de meta legible (ref.metas.meta, p.ej. "0001") — no la llave interna.
    meta: str | None = None
    # Clasificación SIAF cruda por naturaleza del gasto (4 valores) y su vista
    # binaria: "proyecto" (inversión) vs "producto" (actividad/gasto corriente).
    tipo_meta: str | None = None
    categoria: Literal["producto", "proyecto"] = "producto"
    # Código de la actividad/proyecto (act_proy, 7 díg.) — para verificar en SIAF.
    act_proy: str | None = None
    centros_costo: list[str] = []
    n_pedidos: int
    en_contratacion: int
    en_ejecucion: int
    monto_siga: float
    mef: MefMeta
    n_celdas: int
    n_celdas_directas: int
    celdas: list[CeldaClasificador] = []
    # Trámite operativo SIGA de la meta (pestañas O/C, O/S, PECOSAS del reporte).
    # Salen del snapshot PG keyed por sec_func — no inflan ningún total MEF.
    ordenes: list[OrdenReporte] = []
    pecosas: list[PecosaReporte] = []


class ReporteTotales(BaseModel):
    n_metas: int
    n_pedidos: int
    total_siga_pedidos: float         # suma por pedido (informativo)
    total_mef_devengado: float        # suma 1× por meta (real, anti-inflado)


class CentroCostoInfo(BaseModel):
    """Nombre y sigla de un CC, para el filtro (nombre) y la tabla (sigla)."""
    codigo: str
    nombre: str | None = None
    sigla: str


class ReporteResponse(BaseModel):
    ano: int
    mes_corte: int
    avance_esperado: float
    sincronizado_siga: datetime | None = None
    sincronizado_mef: datetime | None = None
    centros_costo: list[CentroCostoInfo] = []
    metas: list[MetaReporte] = []
    totales: ReporteTotales
