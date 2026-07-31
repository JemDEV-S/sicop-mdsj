"""Auditoria de subfases (paso 4) + diagnostico del puente declarado.

(a) Para pedidos cuya bolsa YA tiene orden: ¿que fechas previas/posteriores
    estan pobladas? Distingue bug de mapeo vs dato inexistente en SIGA.
(b) ¿Por que tan pocos `declarado`? Cobertura del concepto de orden.
"""
from collections import Counter

from sqlalchemy import text

from app.database import SessionLocal
from app.repositories import pipeline_read_repo
from app.repositories.pipeline_read_repo import parsear_nro_pedido
from app.services import pipeline_service

ANO = 2026


def main() -> None:
    db = SessionLocal()
    try:
        # (a) cobertura de fechas de bolsa entre pedidos con orden en bolsa
        row = db.execute(text("""
            SELECT COUNT(*) AS n,
                   COUNT(bolsa_fecha_cotizacion)    AS cotiz,
                   COUNT(bolsa_fecha_cuadro)        AS cuadro,
                   COUNT(bolsa_fecha_certificacion) AS certif,
                   COUNT(bolsa_fecha_compromiso)    AS compromiso,
                   COUNT(bolsa_fecha_ejecucion)     AS ejecucion,
                   COUNT(bolsa_fecha_devengado)     AS devengado
            FROM siga.v_pipeline_pedido
            WHERE ano_eje = :ano AND bolsa_fecha_orden IS NOT NULL
        """), {"ano": ANO}).one()
        print("(a) pedidos con orden en bolsa:", row.n)
        for c in ("cotiz", "cuadro", "certif", "compromiso", "ejecucion", "devengado"):
            v = getattr(row, c)
            print(f"    {c:12s} {v:5d}  ({100*v/row.n:.1f}%)")

        # separpor tipo_bien: ejecucion/devengado vienen de conformidades (solo S?)
        rows = db.execute(text("""
            SELECT tipo_bien, COUNT(*) AS n,
                   COUNT(bolsa_fecha_compromiso) AS compromiso,
                   COUNT(bolsa_fecha_ejecucion)  AS ejecucion,
                   COUNT(bolsa_fecha_devengado)  AS devengado,
                   COUNT(*) FILTER (WHERE tiene_ingreso = 1) AS con_ingreso,
                   COUNT(*) FILTER (WHERE tiene_pecosa = 1)  AS con_pecosa
            FROM siga.v_pipeline_pedido
            WHERE ano_eje = :ano AND bolsa_fecha_orden IS NOT NULL
            GROUP BY tipo_bien
        """), {"ano": ANO}).all()
        for r in rows:
            print(f"    tipo {r.tipo_bien}: n={r.n} compromiso={r.compromiso} "
                  f"ejecucion={r.ejecucion} devengado={r.devengado} "
                  f"ingreso={r.con_ingreso} pecosa={r.con_pecosa}")

        # (b) puente declarado: cobertura del concepto
        ords = db.execute(text("""
            SELECT tipo_bien, nro_orden, nro_consolid, concepto
            FROM siga.ordenes WHERE ano_eje = :ano
        """), {"ano": ANO}).mappings().all()
        c = Counter()
        for o in ords:
            c["ordenes"] += 1
            ped = parsear_nro_pedido(o["concepto"])
            if ped is not None:
                c["concepto_nombra_pedido"] += 1
                if o["nro_consolid"] is not None:
                    c["nombra_y_tiene_ccmn"] += 1
            if o["nro_consolid"] is None:
                c["sin_nro_consolid"] += 1
        print("\n(b) ordenes:", dict(c))

        # (c) los ambiguo: ¿alguna orden de su bolsa los nombra?
        filas = pipeline_read_repo.pipeline_pedidos(db, ANO)
        amb = [f for f in filas
               if pipeline_service.confianza_match(f) == "ambiguo"]
        con_avance = [f for f in amb if (f.get("bolsa_n_ordenes") or 0) > 0]
        print(f"\n(c) ambiguo={len(amb)}, con orden en bolsa={len(con_avance)}")
        declarados_fuera = 0
        for f in amb:
            if f.get("ccmn_declarado_orden") is None and f.get("ccmn_candidatos"):
                pass
        # ¿cuantos pedidos DISTINTOS nombra el total de conceptos?
        nombrados = set()
        for o in ords:
            ped = parsear_nro_pedido(o["concepto"])
            if ped is not None:
                nombrados.add(((o["tipo_bien"] or "").strip(), ped))
        amb_nombrados = sum(
            1 for f in amb
            if ((f["tipo_bien"] or "").strip(), int(f["nro_pedido"])) in nombrados
        )
        print(f"    ambiguo nombrados por algun concepto de orden: {amb_nombrados}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
