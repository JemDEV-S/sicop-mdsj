"""Cliente HTTP para la API de Datos Abiertos del MEF (datastore_search_sql).

Limitaciones documentadas (`Docs/actividad-1-exploracion-mef.md` §4):
- Maximo ~8 columnas por request.
- LIMIT 100 recomendado, con OFFSET para paginacion.
- Sin tildes en filtros.
- Reintentos con backoff exponencial ante fallos transitorios.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)

TIMEOUT_S = 30.0
PAGE_LIMIT = 100


class MefApiError(RuntimeError):
    """Error no recuperable al consultar la API MEF."""


class MefApiTransientError(RuntimeError):
    """Error potencialmente recuperable (5xx, timeout)."""


class MefClient:
    """Cliente sincrono para `datastore_search_sql`.

    Uso:
        with MefClient() as c:
            for pagina in c.paginar_sql(sql_base, columnas, filtros_where):
                ...
    """

    def __init__(self, base_url: str | None = None, timeout: float = TIMEOUT_S):
        self.base_url = (base_url or settings.MEF_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._client: httpx.Client | None = None

    def __enter__(self) -> MefClient:
        self._client = httpx.Client(timeout=self.timeout)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    @retry(
        retry=retry_if_exception_type(MefApiTransientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, min=10, max=90),
        reraise=True,
    )
    def datastore_search(
        self, resource_id: str, filters: dict[str, str], limit: int, offset: int
    ) -> list[dict[str, Any]]:
        """Ejecuta una consulta JSON contra la API MEF usando datastore_search."""
        assert self._client is not None, "MefClient debe usarse como context manager"
        url = f"{self.base_url}/datastore_search"
        
        # filters debe mandarse como un string JSON en el query parameter
        import json
        params = {
            "resource_id": resource_id,
            "filters": json.dumps(filters),
            "limit": limit,
            "offset": offset
        }
        
        try:
            resp = self._client.get(url, params=params)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise MefApiTransientError(f"Timeout/red: {exc}") from exc

        if resp.status_code >= 500:
            raise MefApiTransientError(
                f"HTTP {resp.status_code} desde MEF: {resp.text[:200]}"
            )
        if resp.status_code >= 400:
            raise MefApiError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        payload = resp.json()
        
        # La API MEF a veces devuelve "sucess" en vez de "success"
        is_success = payload.get("success") or payload.get("sucess")
        if not is_success and str(is_success).lower() != "true":
            raise MefApiError(f"success=false: {payload.get('error')}")
        
        records = payload.get("records")
        if records is None:
            records = payload.get("result", {}).get("records", [])
        return records  # type: ignore[no-any-return]

    def paginar_json(
        self,
        resource_id: str,
        filters: dict[str, str],
        page_size: int = PAGE_LIMIT,
        delay_seconds: float = 0.15,
    ):
        """Generador que hace paginado con datastore_search (JSON).
        
        Aplica un pequeño delay defensivo (150ms por defecto) entre peticiones 
        para prevenir rate-limiting (HTTP 429) cuando iteramos masivamente.
        """
        import time
        offset = 0
        while True:
            filas = self.datastore_search(
                resource_id=resource_id, 
                filters=filters, 
                limit=page_size, 
                offset=offset
            )
            
            if not filas:
                return
                
            yield filas
            
            # Condicion de corte rigurosa: 
            # Si nos devolvió menos registros que el límite que pedimos, 
            # entonces obligatoriamente ya no hay más registros en las siguientes páginas.
            # No dependemos de `include_total` que a veces es solo una estimación.
            if len(filas) < page_size:
                return
                
            offset += page_size
            
            # Rate limiting defensivo entre peticiones exitosas para proteger la API
            time.sleep(delay_seconds)

    # ─── METODOS SQL DEPRECADOS ──────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type(MefApiTransientError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=10, min=10, max=90),
        reraise=True,
    )
    def datastore_search_sql(self, sql: str) -> list[dict[str, Any]]:
        """Ejecuta un SQL contra la API MEF y devuelve los registros.

        Los 409/500 con SQL invalido son errores permanentes (no reintenta).
        Los 5xx generales y timeouts se consideran transitorios.
        """
        assert self._client is not None, "MefClient debe usarse como context manager"
        url = f"{self.base_url}/datastore_search_sql"
        try:
            resp = self._client.get(url, params={"sql": sql})
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise MefApiTransientError(f"Timeout/red: {exc}") from exc

        if resp.status_code >= 500:
            raise MefApiTransientError(
                f"HTTP {resp.status_code} desde MEF: {resp.text[:200]}"
            )
        if resp.status_code == 409:
            # SQL invalido segun la API (mas de N columnas, etc.) — no reintentar.
            raise MefApiError(f"HTTP 409 (SQL rechazado): {resp.text[:200]}")
        if resp.status_code >= 400:
            raise MefApiError(f"HTTP {resp.status_code}: {resp.text[:200]}")

        payload = resp.json()
        if not payload.get("success"):
            raise MefApiError(f"success=false: {payload.get('error')}")
        records = payload.get("result", {}).get("records", [])
        return records  # type: ignore[no-any-return]

    def paginar_sql(
        self,
        sql_template: str,
        page_size: int = PAGE_LIMIT,
    ):
        """Generador que hace paginado con LIMIT/OFFSET.

        `sql_template` debe contener los placeholders `{limit}` y `{offset}`.
        Termina cuando una pagina devuelve menos de `page_size` filas.
        """
        offset = 0
        while True:
            sql = sql_template.format(limit=page_size, offset=offset)
            filas = self.datastore_search_sql(sql)
            if not filas:
                return
            yield filas
            if len(filas) < page_size:
                return
            offset += page_size


# ─── Helpers para construir SQL contra los resources del MEF ─────────────

def sql_ejecucion_por_mes(resource_id: str, ano: int, mes: int) -> str:
    """SQL para un mes de ejecucion presupuestal (max 8 columnas monto).

    La API admite hasta ~8 columnas — dividimos entre "identificacion + montos".
    Ver `Docs/actividad-1-exploracion-mef.md` §10.
    """
    return f'''
        SELECT "SEC_FUNC", "MES_EJE", "MONTO_PIA", "MONTO_PIM",
               "MONTO_CERTIFICADO", "MONTO_COMPROMETIDO_ANUAL",
               "MONTO_DEVENGADO", "MONTO_GIRADO"
        FROM "{resource_id}"
        WHERE "SEC_EJEC" = '{settings.SEC_EJEC}'
          AND "ANO_EJE" = '{ano}'
          AND "MES_EJE" = '{mes}'
        LIMIT {{limit}} OFFSET {{offset}}
    '''


def sql_ejecucion_identificacion(resource_id: str, ano: int) -> str:
    """SQL para poblar los campos maestros de cada meta (MES_EJE=0)."""
    return f'''
        SELECT "SEC_FUNC", "PRODUCTO_PROYECTO", "PRODUCTO_PROYECTO_NOMBRE",
               "TIPO_ACT_PROY", "META", "META_NOMBRE",
               "FUNCION", "FUNCION_NOMBRE"
        FROM "{resource_id}"
        WHERE "SEC_EJEC" = '{settings.SEC_EJEC}'
          AND "ANO_EJE" = '{ano}'
          AND "MES_EJE" = '0'
        LIMIT {{limit}} OFFSET {{offset}}
    '''


def sql_ejecucion_clasificadores(resource_id: str, ano: int) -> str:
    """SQL para clasificadores de gasto y fuente por meta (MES_EJE=0)."""
    return f'''
        SELECT "SEC_FUNC", "PROGRAMA_PPTO", "PROGRAMA_PPTO_NOMBRE",
               "GENERICA", "GENERICA_NOMBRE",
               "FUENTE_FINANCIAMIENTO", "FUENTE_FINANCIAMIENTO_NOMBRE",
               "RUBRO"
        FROM "{resource_id}"
        WHERE "SEC_EJEC" = '{settings.SEC_EJEC}'
          AND "ANO_EJE" = '{ano}'
          AND "MES_EJE" = '0'
        LIMIT {{limit}} OFFSET {{offset}}
    '''


def sql_inversiones(resource_id: str) -> str:
    """SQL para el dataset Invierte.pe filtrando por la ejecutora."""
    return f'''
        SELECT "CODIGO_UNICO", "NOMBRE_INVERSION", "TIPO_INVERSION", "MARCO",
               "ESTADO", "SITUACION", "ANIO_PROCESO", "SEC_EJEC"
        FROM "{resource_id}"
        WHERE "SEC_EJEC" = '{settings.SEC_EJEC}'
        LIMIT {{limit}} OFFSET {{offset}}
    '''


def sql_inversiones_avance(resource_id: str) -> str:
    """Complemento con montos y avance fisico."""
    return f'''
        SELECT "CODIGO_UNICO", "AVANCE_FISICO", "AVANCE_EJECUCION",
               "TIENE_AVAN_FISICO", "PIM_ANIO_ACTUAL", "DEV_ANIO_ACTUAL",
               "DEVEN_ACUMUL_ANIO_ANT", "COMPROM_ANUAL_ANIO_ACTUAL"
        FROM "{resource_id}"
        WHERE "SEC_EJEC" = '{settings.SEC_EJEC}'
        LIMIT {{limit}} OFFSET {{offset}}
    '''


def sql_inversiones_costo(resource_id: str) -> str:
    return f'''
        SELECT "CODIGO_UNICO", "CERTIF_ANIO_ACTUAL", "COSTO_ACTUALIZADO",
               "MONTO_VIABLE", "SALDO_EJECUTAR", "TIENE_F8", "ETAPA_F8",
               "TIENE_F9"
        FROM "{resource_id}"
        WHERE "SEC_EJEC" = '{settings.SEC_EJEC}'
        LIMIT {{limit}} OFFSET {{offset}}
    '''


def sql_inversiones_etapa(resource_id: str) -> str:
    return f'''
        SELECT "CODIGO_UNICO", "TIENE_F12B", "INFORME_CIERRE",
               "EXPEDIENTE_TECNICO", "DES_MODALIDAD", "DES_TIPOLOGIA",
               "FUNCION", "PROGRAMA"
        FROM "{resource_id}"
        WHERE "SEC_EJEC" = '{settings.SEC_EJEC}'
        LIMIT {{limit}} OFFSET {{offset}}
    '''


def sql_inversiones_cronograma(resource_id: str) -> str:
    return f'''
        SELECT "CODIGO_UNICO", "FEC_INI_EJECUCION", "FEC_FIN_EJECUCION",
               "FEC_INI_EJEC_FISICA", "FEC_FIN_EJEC_FISICA",
               "FECHA_VIABILIDAD", "PRIMER_DEVENGADO", "ULTIMO_DEVENGADO"
        FROM "{resource_id}"
        WHERE "SEC_EJEC" = '{settings.SEC_EJEC}'
        LIMIT {{limit}} OFFSET {{offset}}
    '''


def sql_inversiones_geo(resource_id: str) -> str:
    return f'''
        SELECT "CODIGO_UNICO", "LATITUD", "LONGITUD", "UBIGEO",
               "DEPARTAMENTO", "PROVINCIA", "DISTRITO", "NOMBRE_UEI"
        FROM "{resource_id}"
        WHERE "SEC_EJEC" = '{settings.SEC_EJEC}'
        LIMIT {{limit}} OFFSET {{offset}}
    '''


def sql_inversiones_unidades(resource_id: str) -> str:
    return f'''
        SELECT "CODIGO_UNICO", "NOMBRE_UF", "NOMBRE_OPMI"
        FROM "{resource_id}"
        WHERE "SEC_EJEC" = '{settings.SEC_EJEC}'
        LIMIT {{limit}} OFFSET {{offset}}
    '''
