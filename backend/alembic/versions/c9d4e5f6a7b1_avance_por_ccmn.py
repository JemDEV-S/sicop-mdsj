"""Avance por CCMN (no solo por bolsa) + fechas de aprobacion del seguimiento.

Revision ID: c9d4e5f6a7b1
Revises: a7e5f8c1d2b9
Create Date: 2026-07-31

Motivacion (caso 286/B, sesion 7):

1. `v_bolsa_avance` agrega las fechas sobre TODOS los CCMN candidatos de la
   bolsa. Cuando el puente pedido<->CCMN resuelve (manual/declarado) hacia un
   CCMN detenido, el kanban seguia clasificando el pedido con el avance de
   OTRO candidato (286/B asociado al 2530 sin orden aparecia en "orden
   emitida" por la O/C 618 del 3472). La nueva vista `siga.v_ccmn_avance`
   expone la cadena por CCMN individual; el service la usa para acotar el
   avance de los pedidos resueltos en bolsas compartidas.

2. `SIG_PEDIDOS.FECHA_APROB` viene NULL en el 100% de los pedidos de compra
   2026 (diagnostico_sesion6/08). La fecha real vive en el seguimiento: el VB
   del jefe (estado '1') es el hito de aprobacion de los pedidos '2' (el
   estado '2' del seguimiento nunca se alcanza en compras). `v_pipeline_pedido`
   ahora la completa desde `siga.seguimiento_estados`, solo si la cabecera ya
   dice aprobado/cerrado.

3. `v_bolsa_avance` no exponia la fecha del cuadro consolidado (FECHA_CONS),
   asi que el kanban no podia clasificar un pedido en las etapas 4-5
   (consolidado / estudio de mercado) y lo dejaba en "cuadro de necesidades"
   aunque el detalle mostrara la etapa 5. Nueva columna `fecha_consolid` en
   ambas vistas -> `bolsa_fecha_consolid` en la MV.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c9d4e5f6a7b1"
down_revision: str | None = "a7e5f8c1d2b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_V_CCMN_AVANCE = r"""
CREATE VIEW siga.v_ccmn_avance AS
WITH cadena AS (
    -- Cadena dura de UN cuadro consolidado (mismos laterales que
    -- v_bolsa_avance, sin agregar por bolsa).
    SELECT ec.ano_eje, ec.sec_ejec, ec.tipo_bien, ec.nro_consolid,
           ec.fecha_cons, ec.fecha_cotizacion, ec.fecha_cuadro,
           o.nro_orden, o.fecha_orden,
           cert.fecha_reg AS fecha_certificacion,
           cmp.fecha_interfase AS fecha_compromiso,
           COALESCE(conf.fecha_confor, alm.fecha_ingreso) AS fecha_ejecucion_ccmn,
           pec.fecha_despacho,
           conf.fecha_devengado
    FROM siga.expedientes_ccmn ec
    LEFT JOIN siga.ordenes o
        ON o.ano_eje = ec.ano_eje AND o.sec_ejec = ec.sec_ejec
       AND o.tipo_bien = ec.tipo_bien AND o.nro_consolid = ec.nro_consolid
    LEFT JOIN LATERAL (
        SELECT MAX(c.fecha_reg) AS fecha_reg
        FROM siga.certificaciones c
        WHERE c.ano_eje = ec.ano_eje AND c.sec_ejec = ec.sec_ejec
          AND c.tipo_bien = ec.tipo_bien AND c.nro_consolid = ec.nro_consolid
    ) cert ON TRUE
    LEFT JOIN LATERAL (
        SELECT MIN(d.fecha_interfase) AS fecha_interfase
        FROM siga.compromisos d
        WHERE d.ano_eje = o.ano_eje AND d.sec_ejec = o.sec_ejec
          AND d.exp_siga = o.exp_siga AND d.fecha_interfase IS NOT NULL
    ) cmp ON TRUE
    LEFT JOIN LATERAL (
        SELECT MIN(cf.fecha_movimto) AS fecha_confor,
               MIN(cf.fecha_movimto) FILTER (
                   WHERE cf.estado_deveng IS NOT NULL
                     AND cf.estado_deveng NOT IN ('0', '')
               ) AS fecha_devengado
        FROM siga.conformidades cf
        WHERE cf.ano_orden = o.ano_eje AND cf.sec_ejec = o.sec_ejec
          AND cf.tipo_bien = o.tipo_bien AND cf.nro_orden = o.nro_orden
    ) conf ON TRUE
    LEFT JOIN LATERAL (
        SELECT MIN(ma.fecha_movimto) AS fecha_ingreso
        FROM siga.movimientos_almacen ma
        WHERE ma.ano_eje = o.ano_eje AND ma.sec_ejec = o.sec_ejec
          AND ma.tipo_movimto = 'I' AND ma.nro_orden = o.nro_orden
          AND o.tipo_bien = 'B'
    ) alm ON TRUE
    LEFT JOIN LATERAL (
        SELECT MIN(ma.fecha_movimto) AS fecha_despacho
        FROM siga.pedidos pa
        JOIN siga.pedido_items ia
          ON ia.ano_eje = pa.ano_eje AND ia.sec_ejec = pa.sec_ejec
         AND ia.tipo_bien = pa.tipo_bien AND ia.tipo_pedido = pa.tipo_pedido
         AND ia.nro_pedido = pa.nro_pedido AND ia.nro_pecosa > 0
        JOIN siga.movimientos_almacen ma
          ON ma.ano_eje = pa.ano_eje AND ma.sec_ejec = pa.sec_ejec
         AND ma.tipo_movimto = 'S' AND ma.nro_movimto = ia.nro_pecosa
        WHERE pa.ano_eje = o.ano_eje AND pa.sec_ejec = o.sec_ejec
          AND pa.tipo_bien = 'B' AND pa.tipo_pedido = '1'
          AND o.tipo_bien = 'B'
          AND (substring(pa.motivo FROM 'O/C\s*N[^0-9]{0,4}([0-9]{1,6})'))::int
              = o.nro_orden
    ) pec ON TRUE
)
SELECT
    ano_eje, sec_ejec, tipo_bien, nro_consolid,
    COUNT(DISTINCT nro_orden) FILTER (WHERE nro_orden IS NOT NULL) AS n_ordenes,
    MIN(fecha_cons)                                       AS fecha_consolid,
    MIN(fecha_cotizacion)                                 AS fecha_cotizacion,
    MIN(fecha_cuadro)                                     AS fecha_cuadro,
    MIN(fecha_certificacion)                              AS fecha_certificacion,
    MIN(fecha_orden)                                      AS fecha_orden,
    MIN(fecha_compromiso)                                 AS fecha_compromiso,
    MIN(fecha_ejecucion_ccmn)                             AS fecha_ejecucion,
    MIN(fecha_despacho)                                   AS fecha_despacho,
    MIN(fecha_devengado)                                  AS fecha_devengado,
    STRING_AGG(DISTINCT nro_orden::text, ',' ORDER BY nro_orden::text)
        FILTER (WHERE nro_orden IS NOT NULL)              AS ordenes_csv
FROM cadena
GROUP BY ano_eje, sec_ejec, tipo_bien, nro_consolid
"""

# v_bolsa_avance: identica a a7e5f8c1d2b9 + fecha_consolid (primera FECHA_CONS
# de los candidatos), para que el kanban pueda clasificar las etapas 4-5.
_V_BOLSA_AVANCE_V2 = r"""
CREATE VIEW siga.v_bolsa_avance AS
WITH ccmn_bolsa AS (
    SELECT b.ano_eje, b.sec_ejec, b.tipo_bien, b.sec_cua_mod_sal,
           b.nro_consolid,
           ec.fecha_cons, ec.fecha_cotizacion, ec.fecha_cuadro,
           o.nro_orden, o.fecha_orden, o.exp_siaf, o.nro_certifica,
           cert.nro_certifica_siaf, cert.fecha_reg AS fecha_certificacion,
           cmp.fecha_interfase AS fecha_compromiso,
           COALESCE(conf.fecha_confor, alm.fecha_ingreso) AS fecha_ejecucion_ccmn,
           pec.fecha_despacho,
           conf.fecha_devengado
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
               MIN(cf.fecha_movimto) FILTER (
                   WHERE cf.estado_deveng IS NOT NULL
                     AND cf.estado_deveng NOT IN ('0', '')
               ) AS fecha_devengado
        FROM siga.conformidades cf
        WHERE cf.ano_orden = o.ano_eje AND cf.sec_ejec = o.sec_ejec
          AND cf.tipo_bien = o.tipo_bien AND cf.nro_orden = o.nro_orden
    ) conf ON TRUE
    LEFT JOIN LATERAL (
        SELECT MIN(ma.fecha_movimto) AS fecha_ingreso
        FROM siga.movimientos_almacen ma
        WHERE ma.ano_eje = o.ano_eje AND ma.sec_ejec = o.sec_ejec
          AND ma.tipo_movimto = 'I' AND ma.nro_orden = o.nro_orden
          AND o.tipo_bien = 'B'
    ) alm ON TRUE
    LEFT JOIN LATERAL (
        SELECT MIN(ma.fecha_movimto) AS fecha_despacho
        FROM siga.pedidos pa
        JOIN siga.pedido_items ia
          ON ia.ano_eje = pa.ano_eje AND ia.sec_ejec = pa.sec_ejec
         AND ia.tipo_bien = pa.tipo_bien AND ia.tipo_pedido = pa.tipo_pedido
         AND ia.nro_pedido = pa.nro_pedido AND ia.nro_pecosa > 0
        JOIN siga.movimientos_almacen ma
          ON ma.ano_eje = pa.ano_eje AND ma.sec_ejec = pa.sec_ejec
         AND ma.tipo_movimto = 'S' AND ma.nro_movimto = ia.nro_pecosa
        WHERE pa.ano_eje = o.ano_eje AND pa.sec_ejec = o.sec_ejec
          AND pa.tipo_bien = 'B' AND pa.tipo_pedido = '1'
          AND o.tipo_bien = 'B'
          AND (substring(pa.motivo FROM 'O/C\s*N[^0-9]{0,4}([0-9]{1,6})'))::int
              = o.nro_orden
    ) pec ON TRUE
)
SELECT
    ano_eje, sec_ejec, tipo_bien, sec_cua_mod_sal,
    COUNT(DISTINCT nro_consolid)                          AS n_candidatos,
    COUNT(DISTINCT nro_orden) FILTER (WHERE nro_orden IS NOT NULL) AS n_ordenes,
    MIN(fecha_cons)                                       AS fecha_consolid,
    MIN(fecha_cotizacion)                                 AS fecha_cotizacion,
    MIN(fecha_cuadro)                                     AS fecha_cuadro,
    MIN(fecha_certificacion)                              AS fecha_certificacion,
    MIN(fecha_orden)                                      AS fecha_orden,
    MIN(fecha_compromiso)                                 AS fecha_compromiso,
    MIN(fecha_ejecucion_ccmn)                             AS fecha_ejecucion,
    MIN(fecha_despacho)                                   AS fecha_despacho,
    MIN(fecha_devengado)                                  AS fecha_devengado,
    STRING_AGG(DISTINCT nro_orden::text, ',' ORDER BY nro_orden::text)
        FILTER (WHERE nro_orden IS NOT NULL)              AS ordenes_csv
FROM ccmn_bolsa
GROUP BY ano_eje, sec_ejec, tipo_bien, sec_cua_mod_sal
"""

# v_pipeline_pedido: identica a a7e5f8c1d2b9 + fecha_aprob completada desde el
# seguimiento (VB Jefe) cuando la cabecera dice aprobado pero sin fecha, y
# + bolsa_fecha_consolid.
_V_PIPELINE_PEDIDO_NUEVA = r"""
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
    p.fecha_pedido,
    -- Aprobacion: cabecera si la trae; si no, seguimiento (estado '2'
    -- Aprobado; los pedidos de compra solo alcanzan '1' VB Jefe, que cuenta
    -- como aprobacion solo si la cabecera ya dice aprobado/cerrado).
    COALESCE(
        p.fecha_aprob, seg.fecha_aprob_seg,
        CASE WHEN p.estado IN ('1', '7') THEN seg.fecha_vb_jefe END
    )                                                     AS fecha_aprob,
    p.fecha_atenc,
    p.motivo, p.solicitante, p.fuente_financ,
    COALESCE(mi.monto_total, 0)                           AS monto_total,
    COALESCE(mi.items, 0)                                 AS items,
    pb.sec_cua_mod_sal,
    pb.ccmn_candidatos_csv,
    COALESCE(pb.n_candidatos_ccmn, 0)                     AS n_candidatos_ccmn,
    COALESCE(pb.tiene_cuadro_neces, 0)                    AS tiene_cuadro_neces,
    COALESCE(ba.n_ordenes, 0)                             AS bolsa_n_ordenes,
    ba.ordenes_csv                                        AS bolsa_ordenes_csv,
    ba.fecha_consolid                                     AS bolsa_fecha_consolid,
    ba.fecha_cotizacion                                   AS bolsa_fecha_cotizacion,
    ba.fecha_cuadro                                       AS bolsa_fecha_cuadro,
    ba.fecha_certificacion                                AS bolsa_fecha_certificacion,
    ba.fecha_orden                                        AS bolsa_fecha_orden,
    ba.fecha_compromiso                                   AS bolsa_fecha_compromiso,
    ba.fecha_ejecucion                                    AS bolsa_fecha_ejecucion,
    ba.fecha_despacho                                     AS bolsa_fecha_despacho,
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
LEFT JOIN LATERAL (
    -- Fechas del flujo administrativo (SIG_SEGUIMIENTO). El nro_pedido del
    -- seguimiento es varchar con ceros a la izquierda ('000286').
    SELECT MIN(se.fecha_estado) FILTER (WHERE se.estado_seguimiento = '2')
               AS fecha_aprob_seg,
           MIN(se.fecha_estado) FILTER (WHERE se.estado_seguimiento = '1')
               AS fecha_vb_jefe
    FROM siga.seguimiento_estados se
    WHERE se.ano_eje = p.ano_eje AND se.sec_ejec = p.sec_ejec
      AND se.tipo_bien = p.tipo_bien AND se.tipo_pedido = p.tipo_pedido
      AND NULLIF(regexp_replace(se.nro_pedido, '\D', '', 'g'), '')::bigint
          = p.nro_pedido
) seg ON TRUE
-- ESTADO 0/1/7 son los pedidos "vivos" del kanban. TIPO_PEDIDO='2' es el
-- unico que representa un pedido de compra (f3c9d1a2b4e6).
WHERE p.estado IN ('0', '1', '7')
  AND p.tipo_pedido = '2'
"""

_INDICES = (
    """
    CREATE UNIQUE INDEX ix_v_pipeline_pedido_pk
    ON siga.v_pipeline_pedido
       (ano_eje, sec_ejec, tipo_bien, tipo_pedido, nro_pedido)
    """,
    "CREATE INDEX ix_v_pipeline_pedido_cc "
    "ON siga.v_pipeline_pedido (ano_eje, centro_costo)",
)


def upgrade() -> None:
    op.execute(_V_CCMN_AVANCE)
    op.execute("DROP MATERIALIZED VIEW IF EXISTS siga.v_pipeline_pedido")
    op.execute("DROP VIEW IF EXISTS siga.v_bolsa_avance")
    op.execute(_V_BOLSA_AVANCE_V2)
    op.execute(_V_PIPELINE_PEDIDO_NUEVA)
    for sql in _INDICES:
        op.execute(sql)


# Definicion previa de la MV (a7e5f8c1d2b9): sin el lateral del seguimiento y
# con fecha_aprob directa de la cabecera.
_V_PIPELINE_PEDIDO_PREVIA = (
    _V_PIPELINE_PEDIDO_NUEVA
    .replace(
        """    -- Aprobacion: cabecera si la trae; si no, seguimiento (estado '2'
    -- Aprobado; los pedidos de compra solo alcanzan '1' VB Jefe, que cuenta
    -- como aprobacion solo si la cabecera ya dice aprobado/cerrado).
    COALESCE(
        p.fecha_aprob, seg.fecha_aprob_seg,
        CASE WHEN p.estado IN ('1', '7') THEN seg.fecha_vb_jefe END
    )                                                     AS fecha_aprob,
    p.fecha_atenc,""",
        "    p.fecha_aprob, p.fecha_atenc,",
    )
    .replace(
        """LEFT JOIN LATERAL (
    -- Fechas del flujo administrativo (SIG_SEGUIMIENTO). El nro_pedido del
    -- seguimiento es varchar con ceros a la izquierda ('000286').
    SELECT MIN(se.fecha_estado) FILTER (WHERE se.estado_seguimiento = '2')
               AS fecha_aprob_seg,
           MIN(se.fecha_estado) FILTER (WHERE se.estado_seguimiento = '1')
               AS fecha_vb_jefe
    FROM siga.seguimiento_estados se
    WHERE se.ano_eje = p.ano_eje AND se.sec_ejec = p.sec_ejec
      AND se.tipo_bien = p.tipo_bien AND se.tipo_pedido = p.tipo_pedido
      AND NULLIF(regexp_replace(se.nro_pedido, '\\D', '', 'g'), '')::bigint
          = p.nro_pedido
) seg ON TRUE
-- ESTADO 0/1/7""",
        "-- ESTADO 0/1/7",
    )
    .replace(
        "    ba.fecha_consolid                                     "
        "AS bolsa_fecha_consolid,\n",
        "",
    )
)

_V_BOLSA_AVANCE_PREVIA = _V_BOLSA_AVANCE_V2.replace(
    "    MIN(fecha_cons)                                       "
    "AS fecha_consolid,\n",
    "",
)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS siga.v_ccmn_avance")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS siga.v_pipeline_pedido")
    op.execute("DROP VIEW IF EXISTS siga.v_bolsa_avance")
    op.execute(_V_BOLSA_AVANCE_PREVIA)
    op.execute(_V_PIPELINE_PEDIDO_PREVIA)
    for sql in _INDICES:
        op.execute(sql)
