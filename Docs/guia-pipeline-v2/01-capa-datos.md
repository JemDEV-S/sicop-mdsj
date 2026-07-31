# 01 — Capa de datos: ampliar SIGA sin saturar nada

Objetivo: el pipeline necesita MÁS datos de SIGA (certificación por fase,
conformidades con estado de devengado, seguimiento con historial, presupuesto
por orden) pero el sistema hoy ya se siente lento porque la query del kanban
hace ~12 LEFT JOIN contra SIGA **en cada request**. La solución no es cachear
esa query: es dejar de consultar SIGA en caliente.

## 1. Arquitectura: snapshot incremental en PostgreSQL

Nuevo schema `siga` en la BD intermedia (junto a `ref`, `siaf`, `sistema`):

```
siga.pedidos               ← SIG_PEDIDOS + SIG_DETALLE_PEDIDOS (agregado por pedido)
siga.pedido_items          ← SIG_DETALLE_PEDIDOS (grano item, para la bolsa)
siga.bolsas                ← SIG_CUADRO_MODIFICADO_CMN (SEC_CUA_MOD_SAL ↔ NRO_CONSOLID)
siga.expedientes_ccmn      ← SIG_PAAC_CONSOLIDADO + SIG_SOLICITUD_COTIZACION
                             + SIG_CUADRO_ADQUISICION (una fila por CCMN con
                             sus fechas de cotización/cuadro)
siga.ordenes               ← SIG_ORDEN_ADQUISICION + SIG_ORDEN_PRESUPUESTO
                             (orden + SEC_FUNC + CLASIFICADOR + EXP_SIAF +
                             FECHA_ORDEN) + CCMN vía SIG_CERTIFICACION_FASE
siga.certificaciones       ← SIG_CERTIFICACION_FASE (NRO_CERTIFICA,
                             NRO_CERTIFICA_SIAF, NRO_CONSOLID, NRO_ORDEN, FECHA)
siga.compromisos           ← SIG_EXP_SIGA_DOCU / SIG_EXP_SIGA_SECU
                             (EXP_SIGA, EXP_SIAF, FECHA_INTERFASE, estado)
siga.conformidades         ← SIG_MOVIM_CONFOR_SERVICIO (NRO_ORDEN, FECHA_MOVIMTO,
                             INDI_CONFOR, ESTADO_DEVENG, EXPEDIENTE_SIAF,
                             SECUENCIA_SIAF, glosa)  ← NUEVA, clave para cierre S
siga.movimientos_almacen   ← SIG_MOVIM_ALMACEN (I/R/S, NRO_ORDEN, NRO_PECOSA,
                             fechas) — solo tipos y columnas que usa el pipeline
siga.seguimiento_estados   ← SIG_SEGUIMIENTO + SIG_SEGUIMIENTO_ESTADO
                             (documento, estado, fecha, usuario) — timeline real
siga.catalogo_estados      ← SIG_TRANSACCION_ESTADO (estático, para traducir)
```

Reglas:

- **Una tabla dueña por dato** (sin redundancia). `siga.ordenes` NO guarda
  montos MEF ni nombres de metas: eso vive en `siaf.*` y `ref.*` y se junta
  en vistas.
- **Vistas derivadas, no tablas derivadas**: `siga.v_pipeline_pedido` y
  `siga.v_pipeline_expediente` materializan la clasificación de etapa (ver
  02) con `REFRESH MATERIALIZED VIEW CONCURRENTLY` al final de cada sync.
  El kanban lee la vista materializada: milisegundos, cero carga a SIGA.
- El puente manual pedido↔CCMN ya existe en Postgres (tabla de resoluciones
  T-46); se conserva tal cual.

## 2. Extracción incremental: no releer lo que no cambió

Casi todas las tablas SIGA relevantes tienen `FECHA_REG` (y el seguimiento
además `FECHA_ESTADO`). Estrategia por tabla:

1. **Watermark**: guardar en `sistema.sync_watermarks (tabla, ultima_fecha,
   ultima_corrida, filas)` el máximo `FECHA_REG` visto.
2. Cada corrida trae solo `WHERE FECHA_REG > :watermark` (+ `ANO_EJE = año
   vigente AND SEC_EJEC = 300687`, como siempre) y hace UPSERT por PK.
3. **Barrido de reconciliación** nocturno (1 vez/día): recuenta por tabla
   `COUNT(*)` y `MAX(FECHA_REG)` en SIGA vs Postgres; si difieren, recarga el
   año completo de esa tabla. Cubre updates que no tocan `FECHA_REG` y
   deletes (SIGA a veces borra/renumera).
4. Tablas pequeñas (< 5,000 filas/año: certificaciones, órdenes, CCMN,
   conformidades) pueden recargarse completas por año en cada corrida — es
   más barato que la lógica incremental y son las que más cambian de estado.
   Solo `seguimiento_estados` (16k+/año) y `pedido_items` (8k/año) ameritan
   watermark.

## 3. Cadencias (para no saturar SIGA ni el backend)

| Job | Qué sincroniza | Cadencia | Costo estimado en SIGA |
|---|---|---|---|
| `sync_siga_pipeline` | pedidos, items, bolsas, expedientes, órdenes, certificaciones, compromisos, conformidades, almacén | cada **30 min** en horario laboral (07–18h), 1 vez/noche fuera | ~10 SELECT con filtro por año+watermark, < 5 s |
| `sync_siga_seguimiento` | seguimiento_estados | cada **30 min** (mismo ciclo) | 1–2 SELECT incrementales |
| `reconciliacion_siga` | conteos y recargas completas si difieren | 1 vez/día (madrugada) | ~15 COUNT |
| `sync_siaf` (existente) | snapshot MEF | sin cambio | — |

- Los jobs corren con APScheduler (ya existe `jobs/scheduler.py`) y con
  **jitter** y lock (no dos corridas simultáneas).
- Timeout corto (30 s) y `pool_size` bajo hacia SIGA: si SIGA está ocupado,
  el job se salta la corrida y lo reintenta al siguiente ciclo — nunca
  encola presión.
- **Refresh puntual**: en el detalle de un pedido, botón "Actualizar desde
  SIGA" que sincroniza SOLO ese documento y sus vínculos (5–6 SELECT por PK,
  < 200 ms). Rate-limit por usuario (p. ej. 1 refresh/10 s) con el
  `rate_limit` service existente. Es la válvula para "lo acabo de registrar
  en SIGA y quiero verlo ya".

## 4. Capa de lectura del backend

- Los endpoints del pipeline dejan de importar `siga.conexion`; leen SQLAlchemy
  contra Postgres. `pipeline_repo` se parte en:
  - `siga_sync_repo` (escritura del snapshot, usado solo por jobs), y
  - `pipeline_read_repo` (lecturas Postgres para kanban/detalle/bolsa).
- Redis solo para agregados calientes del dashboard (conteos por macrofase,
  TTL 60 s). No cachear el detalle: ya es barato desde Postgres y el usuario
  quiere frescura ahí.
- Todos los responses del pipeline incluyen `sincronizado_hasta`
  (timestamp del último sync OK) para que la UI muestre la frescura
  (ver 03 §Frescura) en lugar de fingir tiempo real.

## 5. Columnas nuevas a extraer (lo que hoy NO se trae y se necesita)

| Fuente SIGA | Columnas | Para qué |
|---|---|---|
| `SIG_CERTIFICACION_FASE` | `NRO_CONSOLID`, `NRO_ORDEN`, `NRO_CERTIFICA_SIAF`, `FECHA_REG`, `VALOR_SOLES`* | CCMN↔orden en duro (100% medido); CCP; fecha de certificación por fase |
| `SIG_MOVIM_CONFOR_SERVICIO` | `INDI_CONFOR`, `ESTADO_DEVENG`, `EXPEDIENTE_SIAF`, `SECUENCIA_SIAF`, `FECHA_MOVIMTO`, `glosa` | Fin real del servicio y su estado de devengado (caso 232/S) |
| `SIG_ORDEN_PRESUPUESTO` | `SEC_FUNC`, `CLASIFICADOR`, `EXP_SIAF`, `MES_CALE` | Llaves de cruce orden→MEF (100% pobladas) |
| `SIG_SEGUIMIENTO` + `_ESTADO` | tipo, número, `ESTADO`, `FECHA_ESTADO`, `CUSER_ID` | Timeline real por documento; estados negativos (denegado/anulado) |
| `SIG_TRANSACCION_ESTADO` | catálogo completo | Traducir estados a texto en la UI |
| `SIG_ORDEN_ADQUISICION` | + `ESTADO` (además de lo actual) | Detectar órdenes anuladas |

\* `VALOR_SOLES` de certificación se guarda como dato del documento (aparece
en el detalle), no como monto presupuestal del dashboard — los agregados de
montos siguen siendo MEF.

## 6. Qué se elimina (anti-redundancia)

- La mega-query `_SQL_KANBAN` (12 CTE contra SIGA por request) desaparece:
  la clasificación se hace sobre el snapshot con la vista materializada.
- El match composite por monto y el escape `valor_soles = 0` desaparecen del
  camino principal: la orden se obtiene por CCMN (duro). El composite queda
  solo como *verificador* opcional del puente (ver 02 §Puente).
- No copiar a Postgres: catálogos que ya están en `ref.*`, montos MEF que ya
  están en `siaf.*`, ni tablas SIGA que ninguna vista usa.
