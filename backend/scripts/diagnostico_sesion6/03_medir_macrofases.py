"""Mide, tras el fix de fecha_cuadro, la distribucion real del kanban.

Reusa el MISMO camino que el endpoint (repo + cascada + service v2) para que
el conteo sea identico a lo que ve la UI.
"""
from collections import Counter
from datetime import date

from sqlalchemy import text

from app.database import SessionLocal
from app.repositories import pipeline_read_repo
from app.services import pipeline_service, pipeline_v2

ANO = 2026


def main() -> None:
    db = SessionLocal()
    try:
        cov = db.execute(text("""
            SELECT COUNT(*) AS filas,
                   COUNT(fecha_cuadro) AS con_fecha_cuadro,
                   COUNT(fecha_cotizacion) AS con_fecha_cotizacion
            FROM siga.expedientes_ccmn WHERE ano_eje = :ano
        """), {"ano": ANO}).one()
        print(f"expedientes_ccmn: {cov.filas} filas, "
              f"fecha_cuadro={cov.con_fecha_cuadro}, "
              f"fecha_cotizacion={cov.con_fecha_cotizacion}")

        filas = pipeline_read_repo.pipeline_pedidos(db, ANO)
        print(f"pedidos en vista: {len(filas)}")

        hoy = date.today()
        macro = Counter()
        etapas = Counter()
        conf_c = Counter()
        combos = Counter()
        for f in filas:
            confianza = pipeline_service.confianza_match(f)
            card = pipeline_v2.construir_card(
                f, confianza, hoy, umbral=None, sincronizado_hasta=None
            )
            macro[card["macrofase"]] += 1
            etapas[card["etapa"]] += 1
            conf_c[confianza] += 1
            combos[(
                int(bool(f.get("tiene_cuadro_neces"))),
                min(int(f.get("n_candidatos_ccmn") or 0), 2),
                int(f.get("bolsa_fecha_cotizacion") is not None),
                int(f.get("bolsa_fecha_cuadro") is not None),
                int(f.get("bolsa_fecha_certificacion") is not None),
                int(f.get("bolsa_fecha_orden") is not None),
            )] += 1

        print("\n-- macrofases --")
        for k, v in macro.most_common():
            print(f"{k:22s} {v}")
        print("\n-- etapas --")
        for k, v in etapas.most_common():
            print(f"{k:26s} {v}")
        print("\n-- confianza puente --")
        for k, v in conf_c.most_common():
            print(f"{k:22s} {v}")
        print("\n-- combos (cuadNec, nCand[0/1/2+], cotiz, cuadAdq, certif, orden) --")
        for k, v in sorted(combos.items(), key=lambda x: -x[1]):
            print(f"{k} {v}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
