"""Excluir del pipeline los pedidos de atencion de almacen (TIPO_PEDIDO='1').

Revision ID: f3c9d1a2b4e6
Revises: e2b3c4d5f6a8
Create Date: 2026-07-31

Hallazgo (Docs/guia-pipeline-v2/04-continuacion-coherencia-datos.md, sesion de
coherencia de datos): `SIG_PEDIDOS.TIPO_PEDIDO` distingue dos objetos de
negocio distintos que SIGA superpone sobre el mismo NRO_PEDIDO:

  - TIPO_PEDIDO='2': pedido de compra (cuadro de necesidades -> CCMN ->
    cotizacion -> orden). Es el objeto que el pipeline modela.
  - TIPO_PEDIDO='1' (solo bienes): "atencion de pedido a la O/C N°..." -- una
    salida de almacen contra una orden YA emitida. Medido en 2026: 99.5% de
    sus items tiene NRO_PECOSA, 0% tiene SEC_CUA_MOD_SAL (nunca entra a una
    bolsa/CCMN) y 0% declara NRO_ORDEN propio. No es un pedido de compra: no
    tiene bolsa, no tiene CCMN, nunca puede "avanzar" en el pipeline de
    adquisicion, y por eso el kanban lo mostraba como perpetuamente
    estancado en la primera etapa.

Se excluye de `v_pipeline_pedido` (el kanban). El snapshot (`siga.pedidos`,
`siga.pedido_items`) sigue trayendo TIPO_PEDIDO='1' sin filtrar -- no se
descarta el dato, solo se saca de la vista de compras. Queda documentado
como pendiente de un modulo propio de trazabilidad de almacen (no
implementado: fuera del alcance de esta sesion).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f3c9d1a2b4e6"
down_revision: str | None = "e2b3c4d5f6a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS siga.v_pipeline_pedido")
    op.execute(
        """
        CREATE MATERIALIZED VIEW siga.v_pipeline_pedido AS
        WITH ped_bolsa AS (
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
            COALESCE(mi.monto_total, 0)                           AS monto_total,
            COALESCE(mi.items, 0)                                 AS items,
            pb.sec_cua_mod_sal,
            pb.ccmn_candidatos_csv,
            COALESCE(pb.n_candidatos_ccmn, 0)                     AS n_candidatos_ccmn,
            COALESCE(pb.tiene_cuadro_neces, 0)                    AS tiene_cuadro_neces,
            COALESCE(ba.n_ordenes, 0)                             AS bolsa_n_ordenes,
            ba.ordenes_csv                                        AS bolsa_ordenes_csv,
            ba.fecha_cotizacion                                   AS bolsa_fecha_cotizacion,
            ba.fecha_cuadro                                       AS bolsa_fecha_cuadro,
            ba.fecha_certificacion                                AS bolsa_fecha_certificacion,
            ba.fecha_orden                                        AS bolsa_fecha_orden,
            ba.fecha_compromiso                                   AS bolsa_fecha_compromiso,
            ba.fecha_ejecucion                                    AS bolsa_fecha_ejecucion,
            ba.fecha_devengado                                    AS bolsa_fecha_devengado,
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
        -- ESTADO 0/1/7 son los pedidos "vivos" del kanban.
        -- TIPO_PEDIDO='2' es el unico que representa un pedido de compra
        -- (ver docstring): '1' es atencion de almacen contra una O/C ya
        -- emitida y nunca tiene bolsa/CCMN propios.
        WHERE p.estado IN ('0', '1', '7')
          AND p.tipo_pedido = '2'
        """
    )
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
    op.execute(
        """
        CREATE MATERIALIZED VIEW siga.v_pipeline_pedido AS
        WITH ped_bolsa AS (
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
            COALESCE(mi.monto_total, 0)                           AS monto_total,
            COALESCE(mi.items, 0)                                 AS items,
            pb.sec_cua_mod_sal,
            pb.ccmn_candidatos_csv,
            COALESCE(pb.n_candidatos_ccmn, 0)                     AS n_candidatos_ccmn,
            COALESCE(pb.tiene_cuadro_neces, 0)                    AS tiene_cuadro_neces,
            COALESCE(ba.n_ordenes, 0)                             AS bolsa_n_ordenes,
            ba.ordenes_csv                                        AS bolsa_ordenes_csv,
            ba.fecha_cotizacion                                   AS bolsa_fecha_cotizacion,
            ba.fecha_cuadro                                       AS bolsa_fecha_cuadro,
            ba.fecha_certificacion                                AS bolsa_fecha_certificacion,
            ba.fecha_orden                                        AS bolsa_fecha_orden,
            ba.fecha_compromiso                                   AS bolsa_fecha_compromiso,
            ba.fecha_ejecucion                                    AS bolsa_fecha_ejecucion,
            ba.fecha_devengado                                    AS bolsa_fecha_devengado,
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
        WHERE p.estado IN ('0', '1', '7')
        """
    )
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
