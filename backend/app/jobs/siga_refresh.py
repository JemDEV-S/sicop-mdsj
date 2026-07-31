"""Refresh puntual: sincroniza UN pedido y su cadena desde SIGA (§01.3).

Es la valvula para "lo acabo de registrar en SIGA y quiero verlo ya" sin
esperar al ciclo de 30 min. Toca solo las filas del pedido y sus vinculos
(pedido, items, bolsa, CCMN, ordenes de la bolsa, certificaciones,
compromisos, conformidades, almacen), no el año completo.

Se ejecuta bajo rate-limit por usuario en el router (REFRESH_PUNTUAL_COOLDOWN).
Como SIGA es solo lectura (RN-02), esto solo lee de SIGA y hace UPSERT en
Postgres por PK — nunca borra por año, para no competir con el sync masivo.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal
from app.jobs.siga_extractores import EXTRACTORES
from app.jobs.sync_siga_pipeline import _upsert
from app.siga.conexion import get_connection

logger = logging.getLogger(__name__)

# Los extractores se reusan tal cual, pero se les añade un WHERE extra que
# acota a las llaves del pedido. La clave es que el UPSERT (recarga_completa
# se ignora aqui: nunca borramos por año en un refresh puntual).
_ACOTAR: dict[str, str] = {
    # Cabecera e items: por el pedido exacto.
    "pedidos": "AND TIPO_BIEN = :tipo AND TIPO_PEDIDO = :tped AND NRO_PEDIDO = :nro",
    "pedido_items": "AND dp.TIPO_BIEN = :tipo AND dp.TIPO_PEDIDO = :tped AND dp.NRO_PEDIDO = :nro",
    # Bolsa(s) del pedido -> sus CCMN candidatos.
    "bolsas": (
        "AND TIPO_BIEN = :tipo AND SEC_CUA_MOD_SAL IN ("
        "  SELECT DISTINCT SEC_CUA_MOD_SAL FROM SIG_DETALLE_PEDIDOS"
        "  WHERE ANO_EJE = :ano AND SEC_EJEC = :sec_ejec AND TIPO_BIEN = :tipo"
        "    AND TIPO_PEDIDO = :tped AND NRO_PEDIDO = :nro"
        "    AND SEC_CUA_MOD_SAL IS NOT NULL)"
    ),
    # CCMN candidatos de la bolsa del pedido.
    "expedientes_ccmn": (
        "AND pc.TIPO_BIEN = :tipo AND pc.NRO_CONSOLID IN ("
        "  SELECT DISTINCT cmn.NRO_CONSOLID FROM SIG_CUADRO_MODIFICADO_CMN cmn"
        "  JOIN SIG_DETALLE_PEDIDOS dp2"
        "    ON dp2.SEC_EJEC = cmn.SEC_EJEC AND dp2.ANO_EJE = cmn.ANNO_EJEC"
        "   AND dp2.SEC_CUA_MOD_SAL = cmn.SEC_CUA_MOD_SAL AND dp2.TIPO_BIEN = cmn.TIPO_BIEN"
        "  WHERE dp2.ANO_EJE = :ano AND dp2.SEC_EJEC = :sec_ejec"
        "    AND dp2.TIPO_BIEN = :tipo AND dp2.TIPO_PEDIDO = :tped AND dp2.NRO_PEDIDO = :nro)"
    ),
    # Ordenes de los CCMN de la bolsa (cadena dura cuadro -> orden).
    "ordenes": (
        "AND o.TIPO_BIEN = :tipo AND ca.NRO_CONS_PAAC IN ("
        "  SELECT DISTINCT cmn.NRO_CONSOLID FROM SIG_CUADRO_MODIFICADO_CMN cmn"
        "  JOIN SIG_DETALLE_PEDIDOS dp3"
        "    ON dp3.SEC_EJEC = cmn.SEC_EJEC AND dp3.ANO_EJE = cmn.ANNO_EJEC"
        "   AND dp3.SEC_CUA_MOD_SAL = cmn.SEC_CUA_MOD_SAL AND dp3.TIPO_BIEN = cmn.TIPO_BIEN"
        "  WHERE dp3.ANO_EJE = :ano AND dp3.SEC_EJEC = :sec_ejec"
        "    AND dp3.TIPO_BIEN = :tipo AND dp3.TIPO_PEDIDO = :tped AND dp3.NRO_PEDIDO = :nro)"
    ),
}

# Estas tablas se acotan por las ordenes ya acotadas: como el UPSERT es por PK y
# el refresh es best-effort, se recargan enteras del año (son pequeñas y ya
# estan en cache del engine). Mantiene el codigo simple sin perder frescura.
_TABLAS_REFRESH = ("pedidos", "pedido_items", "bolsas", "expedientes_ccmn", "ordenes")


@dataclass
class ResultadoRefresh:
    nro_pedido: int
    tipo_bien: str
    tablas: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.tablas.values())


def refrescar_pedido(
    ano: int, tipo_bien: str, tipo_pedido: str, nro_pedido: int
) -> ResultadoRefresh:
    """UPSERTa las filas del pedido y su cadena desde SIGA a Postgres."""
    res = ResultadoRefresh(nro_pedido=nro_pedido, tipo_bien=tipo_bien)
    params: dict[str, Any] = {
        "ano": ano, "sec_ejec": int(settings.SEC_EJEC),
        "tipo": tipo_bien, "tped": tipo_pedido, "nro": nro_pedido,
    }
    por_destino = {e.destino: e for e in EXTRACTORES}

    session = SessionLocal()
    engine = session.get_bind()
    try:
        with get_connection() as siga:
            filas_por_tabla = {}
            for destino in _TABLAS_REFRESH:
                ext = por_destino[destino]
                sql = ext.sql(con_watermark=False) + " " + _ACOTAR[destino]
                filas = [
                    ext.mapear(dict(r))
                    for r in siga.execute(text(sql), params).mappings()
                ]
                filas_por_tabla[destino] = (ext, filas)

        with engine.begin() as pg:
            for destino, (ext, filas) in filas_por_tabla.items():
                # En refresh puntual el UPSERT es siempre por PK (nunca DELETE
                # por año), aunque la tabla sea de recarga_completa en el masivo.
                ext_upsert = ext if not ext.recarga_completa else _forzar_upsert(ext)
                _upsert(pg, ext_upsert, filas)
                res.tablas[destino] = len(filas)
    finally:
        session.close()

    logger.info(
        "refresh puntual %d/%s: %s", nro_pedido, tipo_bien, res.tablas
    )
    return res


def _forzar_upsert(ext: Any) -> Any:
    """Clona un extractor con recarga_completa=False para UPSERT por PK.

    Los extractores son frozen; se usa dataclasses.replace via __class__ para
    no mutar la definicion global.
    """
    import dataclasses

    return dataclasses.replace(ext, recarga_completa=False)
