"""Vistas materializadas de clasificacion del pipeline sobre siga.*.

Revision ID: e2b3c4d5f6a8
Revises: d1a2b3c4e5f7
Create Date: 2026-07-31

Guia Pipeline v2 §01.1 y §02. El kanban lee de aqui (milisegundos, cero carga a
SIGA). La vista precomputa, por pedido, la evidencia dura de cada etapa CON SU
FECHA (principio 7: ninguna etapa sin fecha) y el AVANCE DE LA BOLSA (§02.1: el
avance del expediente es cierto aunque el puente no este resuelto).

Lo que NO va en la vista (queda en el service Python, testeable sin BD):
    - La cascada de confianza del puente (unico/declarado/ambiguo/...): depende
      de fuentes de texto y de las resoluciones manuales de Postgres.
    - Umbrales y alertas: dependen de sistema.umbrales_alertas y de permisos.

La vista expone los insumos que el service necesita: nº de candidatos, CSV de
candidatos, y el avance de la bolsa. La clasificacion final a "etapa maxima" se
hace en Python a partir de estos flags + el nivel del puente.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e2b3c4d5f6a8"
down_revision: str | None = "d1a2b3c4e5f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ─── v_bolsa_avance: avance dura de cada bolsa (SEC_CUA_MOD_SAL) ──────────
# Del CCMN hacia adelante todo es cadena dura (§02.1). Esta vista resume, por
# bolsa, hasta donde llego CUALQUIER CCMN de ella: si hay orden, conformidad,
# compromiso... con su fecha. El pedido `ambiguo` toma de aqui su avance_bolsa.
_V_BOLSA_AVANCE = """
CREATE VIEW siga.v_bolsa_avance AS
WITH ccmn_bolsa AS (
    -- CCMN candidatos por bolsa, con su cadena dura aplanada.
    SELECT b.ano_eje, b.sec_ejec, b.tipo_bien, b.sec_cua_mod_sal,
           b.nro_consolid,
           ec.fecha_cons, ec.fecha_cotizacion, ec.fecha_cuadro,
           o.nro_orden, o.fecha_orden, o.exp_siaf, o.nro_certifica,
           cert.nro_certifica_siaf, cert.fecha_reg AS fecha_certificacion,
           cmp.fecha_interfase AS fecha_compromiso,
           conf.fecha_confor, conf.fecha_devengado
    FROM siga.bolsas b
    LEFT JOIN siga.expedientes_ccmn ec
        ON ec.ano_eje = b.ano_eje AND ec.sec_ejec = b.sec_ejec
       AND ec.tipo_bien = b.tipo_bien AND ec.tipo_consolid = b.tipo_consolid
       AND ec.nro_consolid = b.nro_consolid
    LEFT JOIN siga.ordenes o
        ON o.ano_eje = b.ano_eje AND o.sec_ejec = b.sec_ejec
       AND o.tipo_bien = b.tipo_bien AND o.nro_consolid = b.nro_consolid
    LEFT JOIN LATERAL (
        SELECT MIN(c.nro_certifica_siaf) AS nro_certifica_siaf,
               MAX(c.fecha_reg) AS fecha_reg
        FROM siga.certificaciones c
        WHERE c.ano_eje = b.ano_eje AND c.sec_ejec = b.sec_ejec
          AND c.nro_consolid = b.nro_consolid
    ) cert ON TRUE
    LEFT JOIN LATERAL (
        SELECT MIN(d.fecha_interfase) AS fecha_interfase
        FROM siga.compromisos d
        WHERE d.ano_eje = o.ano_eje AND d.sec_ejec = o.sec_ejec
          AND d.exp_siga = o.exp_siga AND d.fecha_interfase IS NOT NULL
    ) cmp ON TRUE
    LEFT JOIN LATERAL (
        SELECT MIN(cf.fecha_movimto) AS fecha_confor,
               -- Devengado del servicio: primera conformidad con ESTADO_DEVENG
               -- en estado devengado. Reemplaza el tiene_devengado=0 hardcoded
               -- (§02.2, caso 232/S).
               MIN(cf.fecha_movimto) FILTER (
                   WHERE cf.estado_deveng IS NOT NULL
                     AND cf.estado_deveng NOT IN ('0', '')
               ) AS fecha_devengado
        FROM siga.conformidades cf
        WHERE cf.ano_orden = o.ano_eje AND cf.sec_ejec = o.sec_ejec
          AND cf.tipo_bien = o.tipo_bien AND cf.nro_orden = o.nro_orden
    ) conf ON TRUE
)
SELECT
    ano_eje, sec_ejec, tipo_bien, sec_cua_mod_sal,
    COUNT(DISTINCT nro_consolid)                          AS n_candidatos,
    COUNT(DISTINCT nro_orden) FILTER (WHERE nro_orden IS NOT NULL) AS n_ordenes,
    -- Fechas duras: la mas temprana en que la bolsa alcanzo cada etapa.
    MIN(fecha_cotizacion)                                 AS fecha_cotizacion,
    MIN(fecha_cuadro)                                     AS fecha_cuadro,
    MIN(fecha_certificacion)                              AS fecha_certificacion,
    MIN(fecha_orden)                                      AS fecha_orden,
    MIN(fecha_compromiso)                                 AS fecha_compromiso,
    MIN(fecha_confor)                                     AS fecha_ejecucion,
    MIN(fecha_devengado)                                  AS fecha_devengado,
    -- CSV de ordenes de la bolsa (para mostrar "O/S de bolsa: 132, 155, 802").
    STRING_AGG(DISTINCT nro_orden::text, ',' ORDER BY nro_orden::text)
        FILTER (WHERE nro_orden IS NOT NULL)              AS ordenes_csv
FROM ccmn_bolsa
GROUP BY ano_eje, sec_ejec, tipo_bien, sec_cua_mod_sal
"""


# ─── v_pipeline_pedido (MATERIALIZED): una fila por pedido ───────────────
# Evidencia dura + fechas del pedido y su bolsa. La clasificacion a etapa la
# hace el service; aqui estan todos los insumos ya calculados en SQL rapido.
_V_PIPELINE_PEDIDO = """
CREATE MATERIALIZED VIEW siga.v_pipeline_pedido AS
WITH ped_bolsa AS (
    -- Bolsa(s) y candidatos del pedido, via sus items.
    SELECT pi.ano_eje, pi.sec_ejec, pi.tipo_bien, pi.tipo_pedido, pi.nro_pedido,
           MIN(pi.sec_cua_mod_sal)                        AS sec_cua_mod_sal,
           MAX(CASE WHEN pi.sec_cua_mod_sal IS NOT NULL THEN 1 ELSE 0 END)
                                                          AS tiene_cuadro_neces,
           STRING_AGG(DISTINCT b.nro_consolid::text, ','
                      ORDER BY b.nro_consolid::text)      AS ccmn_candidatos_csv,
           COUNT(DISTINCT b.nro_consolid)                 AS n_candidatos_ccmn
    FROM siga.pedido_items pi
    LEFT JOIN siga.bolsas b
        ON b.ano_eje = pi.ano_eje AND b.sec_ejec = pi.sec_ejec
       AND b.tipo_bien = pi.tipo_bien AND b.sec_cua_mod_sal = pi.sec_cua_mod_sal
    GROUP BY pi.ano_eje, pi.sec_ejec, pi.tipo_bien, pi.tipo_pedido, pi.nro_pedido
),
ped_pecosa AS (
    -- Bienes: entrada (I) y despacho (S) de almacen por la pecosa del item.
    SELECT pi.ano_eje, pi.sec_ejec, pi.tipo_bien, pi.tipo_pedido, pi.nro_pedido,
           MAX(CASE WHEN ma.tipo_movimto = 'S' THEN 1 ELSE 0 END) AS tiene_pecosa,
           MAX(CASE WHEN ma.tipo_movimto = 'I' THEN 1 ELSE 0 END) AS tiene_ingreso,
           MAX(CASE WHEN ma.tipo_movimto = 'R' THEN 1 ELSE 0 END) AS tiene_kardex,
           MIN(ma.fecha_movimto) FILTER (WHERE ma.tipo_movimto = 'S') AS fecha_pecosa,
           MIN(ma.fecha_movimto) FILTER (WHERE ma.tipo_movimto = 'I') AS fecha_ingreso
    FROM siga.pedido_items pi
    JOIN siga.movimientos_almacen ma
        ON ma.ano_eje = pi.ano_eje AND ma.sec_ejec = pi.sec_ejec
       AND ma.tipo_bien = pi.tipo_bien AND ma.nro_movimto = pi.nro_pecosa
    WHERE pi.tipo_bien = 'B' AND pi.nro_pecosa > 0
    GROUP BY pi.ano_eje, pi.sec_ejec, pi.tipo_bien, pi.tipo_pedido, pi.nro_pedido
)
SELECT
    p.ano_eje, p.sec_ejec, p.tipo_bien, p.tipo_pedido, p.nro_pedido,
    p.centro_costo, p.sec_func, p.estado, p.act_proy,
    p.fecha_pedido, p.fecha_aprob, p.fecha_atenc,
    p.motivo, p.solicitante, p.fuente_financ,
    -- Monto del pedido (SIGA, informativo). Los montos presupuestales son MEF.
    COALESCE(mi.monto_total, 0)                           AS monto_total,
    COALESCE(mi.items, 0)                                 AS items,
    -- Puente pedido<->CCMN: insumos para la cascada (service).
    pb.sec_cua_mod_sal,
    pb.ccmn_candidatos_csv,
    COALESCE(pb.n_candidatos_ccmn, 0)                     AS n_candidatos_ccmn,
    COALESCE(pb.tiene_cuadro_neces, 0)                    AS tiene_cuadro_neces,
    -- Avance DURO de la bolsa del pedido (cierto aunque el puente no resuelva).
    COALESCE(ba.n_ordenes, 0)                             AS bolsa_n_ordenes,
    ba.ordenes_csv                                        AS bolsa_ordenes_csv,
    ba.fecha_cotizacion                                   AS bolsa_fecha_cotizacion,
    ba.fecha_cuadro                                       AS bolsa_fecha_cuadro,
    ba.fecha_certificacion                                AS bolsa_fecha_certificacion,
    ba.fecha_orden                                        AS bolsa_fecha_orden,
    ba.fecha_compromiso                                   AS bolsa_fecha_compromiso,
    ba.fecha_ejecucion                                    AS bolsa_fecha_ejecucion,
    ba.fecha_devengado                                    AS bolsa_fecha_devengado,
    -- Bienes: pecosa/almacen (etapas propias del pedido, no de la bolsa).
    COALESCE(pp.tiene_pecosa, 0)                          AS tiene_pecosa,
    COALESCE(pp.tiene_ingreso, 0)                         AS tiene_ingreso,
    COALESCE(pp.tiene_kardex, 0)                          AS tiene_kardex,
    pp.fecha_pecosa,
    pp.fecha_ingreso
FROM siga.pedidos p
LEFT JOIN ped_bolsa pb
    ON pb.ano_eje = p.ano_eje AND pb.sec_ejec = p.sec_ejec
   AND pb.tipo_bien = p.tipo_bien AND pb.tipo_pedido = p.tipo_pedido
   AND pb.nro_pedido = p.nro_pedido
LEFT JOIN siga.v_bolsa_avance ba
    ON ba.ano_eje = p.ano_eje AND ba.sec_ejec = p.sec_ejec
   AND ba.tipo_bien = p.tipo_bien AND ba.sec_cua_mod_sal = pb.sec_cua_mod_sal
LEFT JOIN ped_pecosa pp
    ON pp.ano_eje = p.ano_eje AND pp.sec_ejec = p.sec_ejec
   AND pp.tipo_bien = p.tipo_bien AND pp.tipo_pedido = p.tipo_pedido
   AND pp.nro_pedido = p.nro_pedido
LEFT JOIN LATERAL (
    SELECT SUM(valor_soles) AS monto_total, COUNT(*) AS items
    FROM siga.pedido_items x
    WHERE x.ano_eje = p.ano_eje AND x.sec_ejec = p.sec_ejec
      AND x.tipo_bien = p.tipo_bien AND x.tipo_pedido = p.tipo_pedido
      AND x.nro_pedido = p.nro_pedido
) mi ON TRUE
-- ESTADO 0/1/7 son los pedidos "vivos" del kanban (mismo criterio que el
-- _SQL_KANBAN que esta vista reemplaza).
WHERE p.estado IN ('0', '1', '7')
"""


def upgrade() -> None:
    op.execute(_V_BOLSA_AVANCE)
    op.execute(_V_PIPELINE_PEDIDO)
    # Indice unico -> permite REFRESH MATERIALIZED VIEW CONCURRENTLY.
    op.execute(
        """
        CREATE UNIQUE INDEX ix_v_pipeline_pedido_pk
        ON siga.v_pipeline_pedido
           (ano_eje, sec_ejec, tipo_bien, tipo_pedido, nro_pedido)
        """
    )
    op.execute(
        "CREATE INDEX ix_v_pipeline_pedido_cc "
        "ON siga.v_pipeline_pedido (ano_eje, centro_costo)"
    )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS siga.v_pipeline_pedido")
    op.execute("DROP VIEW IF EXISTS siga.v_bolsa_avance")
