"""Script para reparar mojibake (caracteres corruptos UTF-8 leídos como Latin-1)
en todas las tablas de la base de datos (siaf.inversiones, siaf.ejecucion_presupuestal, etc.).
"""

from __future__ import annotations

import logging
from sqlalchemy import text
from app.database import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("fix_mojibake")


def reparar_texto(texto: str | None) -> str | None:
    if not texto or "Ã" not in texto:
        return texto
    try:
        # Mojibake clásico UTF-8 interpretado como latin-1
        return texto.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Si falla una conversión completa, reemplazar patrones comunes
        reemplazos = {
            "Ã\u0093": "Ó",
            "Ã\u0081": "Á",
            "Ã\u008d": "Í",
            "Ã\u009a": "Ú",
            "Ã\u0091": "Ñ",
            "Ã³": "ó",
            "Ã¡": "á",
            "Ã©": "é",
            "Ã­": "í",
            "Ãº": "ú",
            "Ã±": "ñ",
            "Â·": "·",
            "Â°": "°",
        }
        res = texto
        for k, v in reemplazos.items():
            res = res.replace(k, v)
        return res


def main():
    db = SessionLocal()
    try:
        # 1. siaf.inversiones
        logger.info("Reparando siaf.inversiones...")
        cols_inversiones = [
            "funcion",
            "programa",
            "nombre_inversion",
            "nombre_uei",
            "nombre_uf",
            "nombre_opmi",
            "etapa_f8",
            "situacion",
            "estado",
            "tipo_inversion",
            "des_modalidad",
            "des_tipologia",
            "departamento",
            "provincia",
            "distrito",
        ]

        query = f"SELECT id, codigo_unico, {', '.join(cols_inversiones)} FROM siaf.inversiones"
        rows = db.execute(text(query)).mappings().all()
        actualizados_inversiones = 0

        for r in rows:
            updates = {}
            for col in cols_inversiones:
                val = r[col]
                if val and "Ã" in val:
                    reparado = reparar_texto(val)
                    if reparado != val:
                        updates[col] = reparado

            if updates:
                set_clauses = [f"{col} = :{col}" for col in updates]
                stmt = text(
                    f"UPDATE siaf.inversiones SET {', '.join(set_clauses)} WHERE id = :row_id"
                )
                db.execute(stmt, {**updates, "row_id": r["id"]})
                actualizados_inversiones += 1
                logger.info(
                    "Obra %s corregida: %s",
                    r["codigo_unico"],
                    ", ".join(f"{k}='{v}'" for k, v in updates.items()),
                )

        # 2. siaf.ejecucion_presupuestal
        logger.info("Reparando siaf.ejecucion_presupuestal...")
        cols_ejecucion = [
            "meta_nombre",
            "funcion_nombre",
            "programa_ppto_nombre",
            "producto_proyecto_nombre",
            "rubro_nombre",
            "categoria_gasto_nombre",
            "generica_nombre",
            "subgenerica_nombre",
            "subgenerica_det_nombre",
            "especifica_nombre",
            "especifica_det_nombre",
            "fuente_financiamiento_nombre",
        ]

        query_eje = f"SELECT id, {', '.join(cols_ejecucion)} FROM siaf.ejecucion_presupuestal"
        rows_eje = db.execute(text(query_eje)).mappings().all()
        actualizados_ejecucion = 0

        for r in rows_eje:
            updates = {}
            for col in cols_ejecucion:
                val = r[col]
                if val and "Ã" in val:
                    reparado = reparar_texto(val)
                    if reparado != val:
                        updates[col] = reparado

            if updates:
                set_clauses = [f"{col} = :{col}" for col in updates]
                stmt = text(
                    f"UPDATE siaf.ejecucion_presupuestal SET {', '.join(set_clauses)} WHERE id = :row_id"
                )
                db.execute(stmt, {**updates, "row_id": r["id"]})
                actualizados_ejecucion += 1

        db.commit()
        logger.info(
            "Fin: %d registros en siaf.inversiones y %d en siaf.ejecucion_presupuestal reparados con éxito.",
            actualizados_inversiones,
            actualizados_ejecucion,
        )

    except Exception:
        db.rollback()
        logger.exception("Error reparando mojibake")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
