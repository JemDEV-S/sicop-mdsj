"""Cadena de MONTOS SIAF dentro de SIGA: ¿de dónde sacar los números correctos?

Fuentes candidatas (todas dentro de SIGA_300687, sin llamar a la API MEF):

  1. SIG_EXP_SIGA / _SECU / _PPTO: expediente SIGA con CICLO/FASE
     (C=compromiso, D=devengado, G=girado) y monto por meta+clasificador.
  2. SIG_ORDEN_PRESUPUESTO: monto por orden+meta+clasificador con EXP_SIAF.
  3. SIG_TECHO_PRESUPUESTO: acumulados (cert, com, devengado SIGA y SIAF,
     disponible, EJEC_01..12). Medimos qué campos están poblados en 2026.
  4. INTF_CAB + INTF_DET: la interfase real SIGA→SIAF con MEF_ESTADO.

Salida: resultados/05-cadena-montos-siaf.md
"""

from __future__ import annotations

from _db import ANO, SEC_EJEC, Reporte, connect, q, salida_utf8

W = f"ANO_EJE = {ANO} AND SEC_EJEC = {SEC_EJEC}"


def main() -> None:
    salida_utf8()
    rep = Reporte("05-cadena-montos-siaf", "Cadena de montos SIAF dentro de SIGA")
    cn = connect()
    cur = cn.cursor()

    # 1. Fases del expediente SIGA.
    rep.h("1. SIG_EXP_SIGA_SECU: fases y estados (2026)")
    rep.tabla(q(cur, f"""
        SELECT CICLO, FASE, ESTADO_FASE, ESTADO_EXP,
               COUNT(*) AS secuencias,
               COUNT(DISTINCT EXP_SIGA) AS expedientes,
               SUM(CASE WHEN EXP_SIAF IS NOT NULL AND EXP_SIAF > 0
                        THEN 1 ELSE 0 END) AS con_exp_siaf
        FROM SIG_EXP_SIGA_SECU
        WHERE {W}
        GROUP BY CICLO, FASE, ESTADO_FASE, ESTADO_EXP
        ORDER BY CICLO, FASE, ESTADO_FASE
    """))

    rep.h("Montos por fase (SECU × PPTO)", 3)
    rep.tabla(q(cur, f"""
        SELECT s.CICLO, s.FASE, s.ESTADO_FASE,
               COUNT(DISTINCT s.EXP_SIGA)     AS expedientes,
               SUM(p.MNTO_SOLES)              AS monto_soles
        FROM SIG_EXP_SIGA_SECU s
        JOIN SIG_EXP_SIGA_PPTO p
            ON p.ANO_EJE = s.ANO_EJE AND p.SEC_EJEC = s.SEC_EJEC
           AND p.TIPO_PPTO = s.TIPO_PPTO AND p.EXP_SIGA = s.EXP_SIGA
           AND p.EXP_SIGA_DOC = s.EXP_SIGA_DOC AND p.EXP_SIGA_SECU = s.EXP_SIGA_SECU
        WHERE s.ANO_EJE = {ANO} AND s.SEC_EJEC = {SEC_EJEC}
        GROUP BY s.CICLO, s.FASE, s.ESTADO_FASE
        ORDER BY s.CICLO, s.FASE, s.ESTADO_FASE
    """))

    # ¿El expediente conoce su orden? (NRO_ORDEN_SOS)
    rep.h("Vínculo expediente → orden (NRO_ORDEN_SOS)", 3)
    rep.tabla(q(cur, f"""
        SELECT TIPO_BIEN_SOS,
               COUNT(*) AS secuencias,
               SUM(CASE WHEN NRO_ORDEN_SOS IS NOT NULL AND NRO_ORDEN_SOS > 0
                        THEN 1 ELSE 0 END) AS con_orden
        FROM SIG_EXP_SIGA_SECU
        WHERE {W}
        GROUP BY TIPO_BIEN_SOS
    """))

    # 2. SIG_ORDEN_PRESUPUESTO: EXP_SIAF por orden.
    rep.h("2. SIG_ORDEN_PRESUPUESTO: cobertura EXP_SIAF y fase")
    rep.tabla(q(cur, f"""
        SELECT TIPO_BIEN, FASE, ESTADO_EXP,
               COUNT(DISTINCT NRO_ORDEN) AS ordenes,
               SUM(CASE WHEN EXP_SIAF IS NOT NULL AND EXP_SIAF > 0
                        THEN 1 ELSE 0 END) AS filas_con_exp_siaf,
               SUM(MNTO_SOLES) AS monto_soles
        FROM SIG_ORDEN_PRESUPUESTO
        WHERE {W}
        GROUP BY TIPO_BIEN, FASE, ESTADO_EXP
        ORDER BY TIPO_BIEN, FASE
    """))

    # 3. SIG_TECHO_PRESUPUESTO: qué acumulados están poblados en 2026.
    rep.h("3. SIG_TECHO_PRESUPUESTO 2026: totales por campo")
    rep.tabla(q(cur, f"""
        SELECT
            COUNT(*)                            AS filas,
            SUM(PPTO_PIA)                       AS pia,
            SUM(PPTO_MODIF)                     AS pim,
            SUM(mnto_acum_cert)                 AS acum_cert,
            SUM(MNTO_ACUM_CERT_SIAF)            AS acum_cert_siaf,
            SUM(MNTO_ACUM_COMA_SIAF)            AS acum_com_anual_siaf,
            SUM(MNTO_ACUM_COMM_SIAF)            AS acum_com_mensual_siaf,
            SUM(MNTO_ACUM_DEVGDO_SIGA)          AS acum_dev_siga,
            SUM(MNTO_ACUM_DEVGDO_SIAF)          AS acum_dev_siaf,
            SUM(PPTO_DISP_SIAF)                 AS disponible_siaf,
            SUM(MNTO_RESERVA_PEDIDO)            AS reserva_pedido
        FROM SIG_TECHO_PRESUPUESTO
        WHERE {W}
    """))

    rep.h("EJEC_01..12 (¿ejecución mensual poblada?)", 3)
    rep.tabla(q(cur, f"""
        SELECT SUM(EJEC_01) AS e01, SUM(EJEC_02) AS e02, SUM(EJEC_03) AS e03,
               SUM(EJEC_04) AS e04, SUM(EJEC_05) AS e05, SUM(EJEC_06) AS e06,
               SUM(EJEC_07) AS e07, SUM(EJEC_08) AS e08
        FROM SIG_TECHO_PRESUPUESTO WHERE {W}
    """))

    rep.h("FECHA_SIAF del techo: ¿cuándo se sincronizó por última vez?", 3)
    rep.tabla(q(cur, f"""
        SELECT MIN(FECHA_SIAF) AS min_fecha, MAX(FECHA_SIAF) AS max_fecha,
               COUNT(CASE WHEN FECHA_SIAF IS NOT NULL THEN 1 END) AS filas_con_fecha
        FROM SIG_TECHO_PRESUPUESTO WHERE {W}
    """))

    # 4. INTF_CAB / INTF_DET: interfase real con SIAF.
    rep.h("4. INTF_CAB: operaciones por ciclo/fase/estado MEF (2026)")
    rep.tabla(q(cur, f"""
        SELECT CICLO, FASE, ESTADO, MEF_ESTADO,
               COUNT(*) AS operaciones,
               SUM(CASE WHEN SIAF_EXP IS NOT NULL AND SIAF_EXP <> ''
                        THEN 1 ELSE 0 END) AS con_exp_siaf
        FROM INTF_CAB
        WHERE {W}
        GROUP BY CICLO, FASE, ESTADO, MEF_ESTADO
        ORDER BY CICLO, FASE, MEF_ESTADO
    """))

    rep.h("Montos de la interfase (INTF_CAB × INTF_DET) por fase", 3)
    rep.tabla(q(cur, f"""
        SELECT c.CICLO, c.FASE, c.MEF_ESTADO,
               COUNT(DISTINCT c.SECUENCIAL) AS operaciones,
               SUM(d.MONTO_MN)              AS monto_mn
        FROM INTF_CAB c
        JOIN INTF_DET d ON d.SECUENCIAL = c.SECUENCIAL
        WHERE c.ANO_EJE = {ANO} AND c.SEC_EJEC = {SEC_EJEC}
        GROUP BY c.CICLO, c.FASE, c.MEF_ESTADO
        ORDER BY c.CICLO, c.FASE, c.MEF_ESTADO
    """))

    # 5. Devengado por orden: ruta EXP_SIGA_DOCU (actual) vs SECU fase D.
    rep.h("5. Órdenes con devengado según SECU fase D")
    rep.tabla(q(cur, f"""
        SELECT s.TIPO_BIEN_SOS AS tipo_bien,
               COUNT(DISTINCT s.NRO_ORDEN_SOS) AS ordenes_con_devengado,
               SUM(p.MNTO_SOLES)               AS monto_devengado
        FROM SIG_EXP_SIGA_SECU s
        JOIN SIG_EXP_SIGA_PPTO p
            ON p.ANO_EJE = s.ANO_EJE AND p.SEC_EJEC = s.SEC_EJEC
           AND p.TIPO_PPTO = s.TIPO_PPTO AND p.EXP_SIGA = s.EXP_SIGA
           AND p.EXP_SIGA_DOC = s.EXP_SIGA_DOC AND p.EXP_SIGA_SECU = s.EXP_SIGA_SECU
        WHERE s.ANO_EJE = {ANO} AND s.SEC_EJEC = {SEC_EJEC}
          AND s.FASE = 'D' AND s.NRO_ORDEN_SOS > 0
        GROUP BY s.TIPO_BIEN_SOS
    """))

    # Devengado por meta (sec_func) — la base del dashboard de saldos.
    rep.h("Devengado 2026 por meta vía expedientes (top 15)", 3)
    rep.tabla(q(cur, f"""
        SELECT TOP 15 p.SEC_FUNC,
               SUM(p.MNTO_SOLES) AS devengado
        FROM SIG_EXP_SIGA_SECU s
        JOIN SIG_EXP_SIGA_PPTO p
            ON p.ANO_EJE = s.ANO_EJE AND p.SEC_EJEC = s.SEC_EJEC
           AND p.TIPO_PPTO = s.TIPO_PPTO AND p.EXP_SIGA = s.EXP_SIGA
           AND p.EXP_SIGA_DOC = s.EXP_SIGA_DOC AND p.EXP_SIGA_SECU = s.EXP_SIGA_SECU
        WHERE s.ANO_EJE = {ANO} AND s.SEC_EJEC = {SEC_EJEC} AND s.FASE = 'D'
        GROUP BY p.SEC_FUNC
        ORDER BY SUM(p.MNTO_SOLES) DESC
    """), max_rows=15)

    rep.guardar()
    cn.close()


if __name__ == "__main__":
    main()
