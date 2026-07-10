"""ENUMs Python que corresponden 1:1 con los ENUM globales de PostgreSQL.

Los TYPE se crean manualmente en la migración inicial (0001_initial) porque
son referenciados por varias tablas y ENUM.create() genera CREATE TYPE
duplicados si se declara `create_type=True` en cada columna.

En las columnas se usa: `sa.Enum(CodigoRol, name='codigo_rol', create_type=False)`.
"""

from enum import Enum


class EstadoUsuario(str, Enum):
    activo = "activo"
    inactivo = "inactivo"
    bloqueado = "bloqueado"


class EstadoObservacion(str, Enum):
    pendiente = "pendiente"
    leida = "leida"
    respondida = "respondida"
    spam = "spam"


class EstadoSync(str, Enum):
    en_curso = "en_curso"
    exito = "exito"
    error = "error"


class TipoDocumentoObra(str, Enum):
    foto = "foto"
    expediente_tecnico = "expediente_tecnico"
    contrato = "contrato"
    f8 = "f8"
    f9 = "f9"
    otro = "otro"


class TipoEntidadAnotacion(str, Enum):
    pedido = "pedido"
    orden = "orden"
    meta = "meta"
    obra = "obra"
    contrato = "contrato"


class TipoEntidadAlerta(str, Enum):
    pedido = "pedido"
    contrato = "contrato"
    meta = "meta"


class DireccionSemaforo(str, Enum):
    mayor = "mayor"
    menor = "menor"


class CodigoRol(str, Enum):
    ciudadano = "ciudadano"
    operativo = "operativo"
    decisor = "decisor"
    admin = "admin"


ENUM_TYPE_NAMES: dict[type[Enum], str] = {
    EstadoUsuario: "estado_usuario",
    EstadoObservacion: "estado_observacion",
    EstadoSync: "estado_sync",
    TipoDocumentoObra: "tipo_documento_obra",
    TipoEntidadAnotacion: "tipo_entidad_anotacion",
    TipoEntidadAlerta: "tipo_entidad_alerta",
    DireccionSemaforo: "direccion_semaforo",
    CodigoRol: "codigo_rol",
}
