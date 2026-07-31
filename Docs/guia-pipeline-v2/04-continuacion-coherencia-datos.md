# 04 — Prompt de continuación: coherencia de datos en las vistas del pipeline

**Propósito:** este documento es el prompt de arranque para la próxima sesión.
Reúne todo lo necesario para **mejorar la coherencia de la información que se
muestra en las vistas** (kanban, detalle, bolsa), verificar los datos
directamente contra SIGA, y mantener el código desacoplado, mantenible y
escalable. Cópialo/refiérelo al iniciar la sesión.

> Contexto previo: la Guía Pipeline v2 (docs 00–03) ya está implementada
> (commits `7344dfc`..`c9aac26`). El kanban lee del snapshot `siga.*` en
> PostgreSQL; el detalle todavía lee SIGA en caliente para UN documento.

---

## 1. El problema a resolver

En varias tarjetas/detalles la información **parece incoherente**: etapas que
no cuadran con las fechas, órdenes atribuidas que no corresponden, montos que
no coinciden entre vistas, o estados que se contradicen entre el kanban y el
detalle. La causa casi siempre es una de estas cuatro:

1. **El puente pedido↔CCMN no está resuelto** y se está mostrando avance de
   otro pedido de la misma bolsa como si fuera propio (ver 02 §1).
2. **El kanban y el detalle leen de fuentes distintas** (snapshot vs SIGA en
   caliente) y una está más fresca o clasifica distinto que la otra.
3. **Un dato de SIGA se está interpretando mal** (columna equivocada, estado
   sin traducir, agregación incorrecta) — hay que verificarlo contra la BD.
4. **Falta un dato en el snapshot** porque el extractor lo colapsó con `MIN()`
   o no lo trae (ver §5, el caso `SIG_ORDEN_PRESUPUESTO`).

**Regla de oro para esta sesión:** *ningún dato en pantalla sin que se pueda
probar contra SIGA o el MEF.* Antes de "arreglar" una vista, ejecuta la query
que confirma cuál es el dato correcto (§4). No inventar; si la llave no cruza,
marcarlo como pendiente y preguntar (CLAUDE.md "Cómo trabajar").

---

## 2. Mapa de archivos relevantes (dónde tocar qué)

### Backend — capa de datos (snapshot SIGA → PostgreSQL)

| Archivo | Qué hace | Cuándo tocarlo |
|---|---|---|
| [backend/app/jobs/siga_extractores.py](../../backend/app/jobs/siga_extractores.py) | Un `Extractor` por tabla `siga.*`: SELECT contra SIGA + mapeo a Postgres | Cuando falte una columna o el mapeo esté mal |
| [backend/app/jobs/sync_siga_pipeline.py](../../backend/app/jobs/sync_siga_pipeline.py) | Motor de sync (watermark/recarga) + `REFRESH` de la vista | Cambios de estrategia de sync |
| [backend/app/jobs/reconciliacion_siga.py](../../backend/app/jobs/reconciliacion_siga.py) | Barrido nocturno: conteos SIGA vs snapshot | Si una tabla se desfasa sistemáticamente |
| [backend/app/jobs/siga_refresh.py](../../backend/app/jobs/siga_refresh.py) | Refresh puntual de UN pedido y su cadena | Ampliar qué tablas refresca el botón del detalle |
| [backend/alembic/versions/d1a2b3c4e5f7_siga_snapshot_schema.py](../../backend/alembic/versions/d1a2b3c4e5f7_siga_snapshot_schema.py) | DDL de `siga.*` (11 tablas) | Añadir columna/tabla al snapshot |
| [backend/alembic/versions/e2b3c4d5f6a8_siga_vistas_pipeline.py](../../backend/alembic/versions/e2b3c4d5f6a8_siga_vistas_pipeline.py) | `v_bolsa_avance` + `v_pipeline_pedido` (materializada) | Cambiar cómo se calcula el avance/etapa en SQL |

### Backend — lógica y API

| Archivo | Qué hace |
|---|---|
| [backend/app/repositories/pipeline_read_repo.py](../../backend/app/repositories/pipeline_read_repo.py) | **Lectura del kanban** desde la vista materializada + parseo de declaraciones (concepto de orden → CCMN) + cruce MEF por meta |
| [backend/app/repositories/pipeline_repo.py](../../backend/app/repositories/pipeline_repo.py) | **Detalle/bolsa** — lee SIGA en caliente para UN documento (cadena hacia arriba y abajo, `obtener_pedido`, `obtener_bolsa`, `contexto_pedido_bolsa`) |
| [backend/app/services/pipeline_v2.py](../../backend/app/services/pipeline_v2.py) | Clasificación de etapa por fecha, avance de bolsa, identificadores, **alertas v2** — lógica pura, testeable sin BD |
| [backend/app/services/pipeline_service.py](../../backend/app/services/pipeline_service.py) | Orquesta kanban: read repo → cascada de confianza → cards v2. Contiene `confianza_match` (cascada del puente) y `construir_timeline` (detalle) |
| [backend/app/schemas/pipeline.py](../../backend/app/schemas/pipeline.py) | Taxonomía (etapas, macrofases), tipos v2 (`Alerta`, `Puente`, `Identificadores`), y modelos Pydantic de respuesta |
| [backend/app/routers/pipeline.py](../../backend/app/routers/pipeline.py) | Endpoints: `/kanban`, `/pedidos/{n}/{tb}` (detalle), `/bolsa`, `/resoluciones`, `/refrescar` |

### Frontend — vistas

| Archivo | Qué hace |
|---|---|
| [frontend/src/features/dashboard/types.ts](../../frontend/src/features/dashboard/types.ts) | Tipos del kanban: `PedidoCard`, `Alerta`, `Puente`, `AvanceBolsa`, `Identificadores` |
| [frontend/src/features/pipeline/pipeline-ui.tsx](../../frontend/src/features/pipeline/pipeline-ui.tsx) | Primitivas compartidas: `BadgeAlerta`, `CopyChip`, `bordeAlerta` (semántica de color única) |
| [frontend/src/features/pipeline/PedidoCard.tsx](../../frontend/src/features/pipeline/PedidoCard.tsx) | Tarjeta del kanban |
| [frontend/src/features/pipeline/secciones/PipelineKanban.tsx](../../frontend/src/features/pipeline/secciones/PipelineKanban.tsx) | Página del kanban + pie de frescura |
| [frontend/src/features/pipeline/PedidoDetalle.tsx](../../frontend/src/features/pipeline/PedidoDetalle.tsx) | Detalle: cabecera con IDs, bloques, timeline, botón refrescar |
| [frontend/src/features/pipeline/BolsaPedido.tsx](../../frontend/src/features/pipeline/BolsaPedido.tsx) | Vista de bolsa (grafo dos columnas, asociación manual) |
| [frontend/src/features/pipeline/types.ts](../../frontend/src/features/pipeline/types.ts) | Tipos del detalle/bolsa |
| [frontend/src/features/pipeline/api.ts](../../frontend/src/features/pipeline/api.ts) · [frontend/src/features/dashboard/api.ts](../../frontend/src/features/dashboard/api.ts) | Hooks TanStack Query (`useKanban`, `useDetallePedido`, `useBolsaPedido`, `useRefrescarPedido`) |

---

## 3. Datos fijos y arquitectura de datos

| Concepto | Valor |
|---|---|
| Entidad ejecutora | `SEC_EJEC = 300687` (fijar en TODA query, RN-01) |
| Año vigente | `2026` |
| SIGA (SQL Server) | Instancia `.`, BD `SIGA_300687`, Windows Auth, `ODBC Driver 17` |
| PostgreSQL | schemas `auth`, `ref`, `siaf`, `sistema`, `logs`, **`siga`** (snapshot v2) |

**Flujo de datos v2 (respetarlo):**

```
SIGA (SQL Server, SOLO LECTURA)
  │  jobs de sync (siga_extractores.py)
  ▼
siga.* (snapshot en PostgreSQL)  ──►  siga.v_pipeline_pedido (materializada)
                                          │
MEF (API → siaf.ejecucion_presupuestal)   │  pipeline_read_repo (lee)
  │                                        ▼
  └──► devengado por SEC_FUNC  ──►  pipeline_service (cascada + alertas)
                                          │
                                          ▼
                                   API v2 ──► frontend
```

- **Montos presupuestales: SIEMPRE del MEF**, nunca de SIGA (el techo SIGA está
  vacío en 2026). SIGA aporta proceso, fechas, estados y llaves de cruce.
- **El kanban NO toca SIGA** (lee la vista materializada). El detalle SÍ, para
  un documento. Migrar el detalle al snapshot es trabajo pendiente (§7).

---

## 4. Cómo verificar datos directamente contra SIGA

Hay **dos formas**, elige según el contexto:

### 4.1 Query rápida desde el backend (recomendada)

```bash
cd backend
.venv/Scripts/python.exe -c "
from app.siga.conexion import get_connection
from sqlalchemy import text
with get_connection() as c:
    rows = c.execute(text('''
        SELECT NRO_ORDEN, SEC_FUNC, CLASIFICADOR, EXP_SIAF, TOTAL_FACT_SOLES
        FROM SIG_ORDEN_ADQUISICION o
        JOIN SIG_ORDEN_PRESUPUESTO op
          ON op.ANO_EJE=o.ANO_EJE AND op.SEC_EJEC=o.SEC_EJEC
         AND op.TIPO_BIEN=o.TIPO_BIEN AND op.NRO_ORDEN=o.NRO_ORDEN
        WHERE o.ANO_EJE=2026 AND o.SEC_EJEC=300687 AND o.NRO_ORDEN=132
    '''), ).mappings().all()
    for r in rows: print(dict(r))
"
```

- `app/siga/conexion.py` expone `get_connection()`, `fetch_all(sql, params)`,
  `fetch_one(sql, params)` y `health_check()`. **Siempre `SEC_EJEC=300687`.**

### 4.2 Comparar snapshot vs SIGA (para detectar el desfase)

```bash
cd backend
.venv/Scripts/python.exe -c "
from app.database import SessionLocal
from app.siga.conexion import get_connection
from sqlalchemy import text
pg=SessionLocal()
# lo que ve la vista materializada:
print('PG:', dict(pg.execute(text('''
  SELECT nro_pedido, tipo_bien, sec_cua_mod_sal, n_candidatos_ccmn,
         bolsa_ordenes_csv, bolsa_fecha_ejecucion
  FROM siga.v_pipeline_pedido WHERE nro_pedido=232 AND tipo_bien=\'S\'
''')).mappings().first() or {}))
# lo que dice SIGA:
with get_connection() as c:
    print('SIGA bolsa:', [dict(r) for r in c.execute(text('''
      SELECT SEC_CUA_MOD_SAL, NRO_CONSOLID FROM SIG_CUADRO_MODIFICADO_CMN
      WHERE ANNO_EJEC=2026 AND SEC_EJEC=300687 AND SEC_CUA_MOD_SAL=11553
    ''')).mappings().all()])
pg.close()
"
```

### 4.3 Scripts de exploración ya existentes

- `exploracion-siga/` — scripts de la exploración original (`_db.py` tiene un
  helper `connect()` + `q(cur, sql)`; `hallazgos.md` documenta lo medido).
- `backend/scripts/diagnostico_sesion5/*.sql` — queries validadas de la cadena
  del pipeline (testigo 232/S, cadena completa, puentes). Buen punto de partida.
- `backend/scripts/ping_siga.py` — smoke test de conectividad.

### 4.4 Inspeccionar columnas reales de una tabla SIGA

```bash
.venv/Scripts/python.exe -c "
from app.siga.conexion import get_connection
from sqlalchemy import text
with get_connection() as c:
    for n,d in c.execute(text('''SELECT COLUMN_NAME,DATA_TYPE
      FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME=\'SIG_MOVIM_CONFOR_SERVICIO\'
      ORDER BY ORDINAL_POSITION''')).all(): print(n,d)
"
```

---

## 5. Tablas y llaves de SIGA que alimentan el pipeline

Grano y llave de cada tabla (todo con `SEC_EJEC=300687`). Ver el snapshot en
`siga_extractores.py` para el mapeo exacto columna→columna.

| Tabla SIGA | Grano | Llave / cruce | Notas de trampas |
|---|---|---|---|
| `SIG_PEDIDOS` | pedido | `ANO_EJE+SEC_EJEC+TIPO_BIEN+TIPO_PEDIDO+NRO_PEDIDO` | `ESTADO` 0=proceso,1=aprobado,7=cerrado. `NRO_PEDIDO` solo NO es único |
| `SIG_DETALLE_PEDIDOS` | item | + `SECUENCIA` | `VALOR_TOTAL=0` en 100% servicios → usar `CANT_SOLICITADA*PRECIO_UNIT` |
| `SIG_CUADRO_MODIFICADO_CMN` | puente | `SEC_CUA_MOD_SAL ↔ NRO_CONSOLID` (año=`ANNO_EJEC`) | **sin `FECHA_REG`**; una bolsa tiene N CCMN candidatos → ambigüedad |
| `SIG_PAAC_CONSOLIDADO` | CCMN | `NRO_CONSOLID` | cabecera del cuadro consolidado |
| `SIG_SOLICITUD_COTIZACION` | cotización | `NRO_CONSOLID` | |
| `SIG_CUADRO_ADQUISICION` | cuadro adq. | `NRO_CONS_PAAC → NRO_CONSOLID`, `SEC_CUADRO` | |
| `SIG_ORDEN_ADQUISICION` | orden | `NRO_ORDEN`, `SEC_CUADRO`, `EXP_SIGA`, `EXP_SIAF` | orden→CCMN vía `SEC_CUADRO→NRO_CONS_PAAC` |
| `SIG_ORDEN_PRESUPUESTO` | orden×celda | `NRO_ORDEN` + `SEC_FUNC` + `CLASIFICADOR` | **el extractor colapsa con `MIN()`** — una orden abarca varias metas/clasificadores; el cruce MEF por celda necesita el grano completo (ver §6) |
| `SIG_CERTIFICACION_FASE` | fase | `NRO_CERTIFICA+SECUENCIA_FASE`; `NRO_CONSOLID`, `NRO_ORDEN`, `NRO_CERTIFICA_SIAF` | CCMN↔orden en duro (100% medido) |
| `SIG_EXP_SIGA_DOCU` | doc expediente | `EXP_SIGA+EXP_SIGA_DOC`; `FECHA_INTERFASE` (compromiso), `TIPO_OPERACION` (DV=devengado) | |
| `SIG_MOVIM_CONFOR_SERVICIO` | conformidad | año=`ANO_ORDEN`; `NRO_ORDEN+NRO_MOVIMTO` | `ESTADO_DEVENG`, `EXPEDIENTE_SIAF`; **`glosa` en minúscula**, sin `FECHA_REG` |
| `SIG_MOVIM_ALMACEN` | movimiento | `TIPO_MOVIMTO(I/R/S)+TIPO_TRANSAC+NRO_MOVIMTO` | `TIPO_BIEN` a veces NULL en salidas (S) → se fija 'B' |
| `SIG_SEGUIMIENTO`+`_ESTADO` | timeline | `TIPO_TRANSACCION+NRO_ORIGEN+SEC_ESTADO`; `FECHA_ESTADO` | `NRO_PEDIDO` es varchar; estados negativos (denegado=3, anulado) |
| `SIG_TRANSACCION_ESTADO` | catálogo | `COD_MAESTRO+COD_DETALLE+ESTADO` | traduce códigos de estado a texto (`siga.catalogo_estados`) |

**Testigo de referencia (medido en BD, usar para validar cualquier cambio):**
Pedido `232/S` → bolsa `11553` → 3 CCMN candidatos `(2266, 2281, 3532)` →
órdenes de la bolsa `132, 155, 802`. La O/S `232` (S/ 1,400, EXP SIAF 596) tiene
conformidad el 2026-03-12. Resultado v2 esperado: **sin alerta roja**, etapa
`devengado`, identificadores visibles.

---

## 6. Trabajos de coherencia priorizados (el objetivo de la sesión)

Orden sugerido; cada uno **verifica el dato contra SIGA antes de tocar la vista**.

1. **Auditar la clasificación de etapa vs las fechas mostradas.** Recorrer una
   muestra de pedidos y comprobar que `etapa` y `fechas[etapa]` sean
   consistentes (una etapa alcanzada debe tener fecha; el orden temporal debe
   ser monótono). Lógica en `pipeline_v2.clasificar_etapa` / `fechas_alcanzadas`.

2. **Coherencia kanban ↔ detalle.** Hoy el kanban clasifica desde el snapshot y
   el detalle desde SIGA en caliente con otra lógica (`construir_timeline`). Un
   mismo pedido puede aparecer en etapas distintas. **Decidir:** o migrar el
   detalle a leer del snapshot (recomendado, §7), o alinear las dos lógicas.
   Verificar con el testigo 232/S en ambas vistas.

3. **Cruce MEF por celda (hoy simplificado a meta).** `pipeline_read_repo`
   agrega devengado por `SEC_FUNC` porque el clasificador SIGA
   (`'2.3. 2  9. 1  1'`) no cruza 1:1 con el desglose SIAF, y el extractor de
   `ordenes` colapsó `SIG_ORDEN_PRESUPUESTO` con `MIN()`. Para el cruce fino
   (02 §6): (a) crear tabla `siga.orden_presupuesto` con grano
   orden×celda completo, (b) normalizar el clasificador SIGA↔SIAF o cruzar por
   `EXP_SIAF`, (c) mostrar cobertura por celda en el detalle. **Verificar** con
   la query de §4.1 sobre la orden 132.

4. **Estados de seguimiento en texto.** `siga.seguimiento_estados` +
   `siga.catalogo_estados` (159 filas, `COD_MAESTRO='TIPO_MODULO'`) permiten
   mostrar "VB Jefe", "Aprobado", "Denegado" con fecha y usuario en el timeline
   del detalle (03 §2, sub-hitos administrativos). Hoy NO se están usando.
   Estado real: 0=Pendiente,1=VB Jefe,2=Aprobado,3=Denegado,7=Pecosa...

5. **Estados negativos → `cerrado_negativo`.** Detectar órdenes anuladas
   (`SIG_ORDEN_ADQUISICION.ESTADO`) y denegados del seguimiento; sacarlos del
   flujo activo y del cálculo de alertas (02 §2, §4). Ya existe el tipo de
   alerta `cerrado_negativo` en el schema; falta poblarlo.

6. **Devengado de servicios (caso 232/S).** `v_bolsa_avance` ya calcula
   `fecha_devengado` con la primera conformidad cuyo `ESTADO_DEVENG` no es
   0/vacío. **Verificar** contra `SIG_MOVIM_CONFOR_SERVICIO` que el estado de
   devengado se está leyendo bien (query §4.4 para ver los valores reales de
   `ESTADO_DEVENG`).

Para cada arreglo: si toca la vista materializada, recuerda
`REFRESH MATERIALIZED VIEW CONCURRENTLY siga.v_pipeline_pedido` (o corre
`python -m app.jobs.sync_siga_pipeline --ano 2026`, que refresca al final).

---

## 7. Deuda técnica conocida (candidatos a desacoplar)

- **Detalle lee SIGA en caliente.** `pipeline_repo.obtener_pedido` hace varias
  queries a SIGA por request. Migrarlo a leer de `siga.*` (como el kanban)
  unifica la lógica y elimina la incoherencia kanban↔detalle. Es el trabajo
  más grande y el que más coherencia aporta.
- **`SIG_ORDEN_PRESUPUESTO` colapsado con `MIN()`** en el extractor de `ordenes`
  → pierde el grano orden×celda (bloquea el cruce MEF fino, §6.3).
- **`construir_timeline` (detalle) y `pipeline_v2` (kanban) son dos modelos de
  clasificación** que deben converger.

---

## 8. Patrón de diseño y arquitectura (mantenible y escalable)

### 8.1 Backend — capas y responsabilidades

Respetar la separación que ya existe; **no mezclar responsabilidades**:

```
router (pipeline.py)        → HTTP, permisos (RN-04), validación, DTO
  └─ service (pipeline_*.py) → lógica de negocio PURA (testeable sin BD)
       └─ repo (read/repo)    → acceso a datos (SQL), sin lógica de negocio
            └─ snapshot siga.* / vista materializada / SIGA (solo detalle)
```

Principios (Guía v2 §00, ampliados):

1. **Una tabla dueña por dato** (sin redundancia). Las vistas derivan por JOIN.
   No copiar a Postgres lo que ya vive en `ref.*` (catálogos) o `siaf.*` (MEF).
2. **La lógica de negocio va en el service, no en SQL ni en el router.** La
   clasificación de etapa, la cascada de confianza y las alertas son Python
   puro que recibe dicts y devuelve dicts → se testea sin BD
   (ver `tests/services/test_pipeline_v2.py`, 15 tests de referencia).
3. **Extractores declarativos.** Añadir una tabla al snapshot = añadir un
   `Extractor` (destino, PK, SELECT, `mapear`). El motor de sync no cambia.
   Este es el patrón a replicar para escalar la capa de datos.
4. **SIGA es solo lectura (RN-02).** Toda escritura va a PostgreSQL. Jamás un
   `INSERT/UPDATE` contra SIGA.
5. **Idempotencia en el sync:** UPSERT por PK (o `DO NOTHING` si toda la fila es
   PK). La reconciliación nocturna corrige deletes/renumeraciones.
6. **Frescura explícita:** cada respuesta lleva `sincronizado_hasta`. Nunca
   fingir tiempo real.

### 8.2 Frontend — componentes y estado

- **Primitivas compartidas en `pipeline-ui.tsx`.** Los badges de alerta, chips
  de copiar y bordes por color viven ahí; las vistas los consumen. Si una vista
  "necesita" un color/estado nuevo, se agrega a la primitiva, no ad-hoc.
- **Tipos en un solo lugar** (`dashboard/types.ts` para kanban,
  `pipeline/types.ts` para detalle). El backend es la fuente; el frontend
  refleja el schema Pydantic.
- **Datos vía hooks TanStack Query** (`api.ts`), nunca `fetch` suelto en el
  componente. Los hooks encapsulan la queryKey y la invalidación.
- **Estado de UI local o Zustand** (filtros del kanban), nunca en el servidor.

### 8.3 Sistema de diseño institucional (OBLIGATORIO en toda vista)

Fuente de verdad: skill `frontend-design-system`
(`.claude/skills/frontend-design-system/SKILL.md`) y
`frontend/src/styles/globals.css`. Reglas duras:

- **4 colores institucionales** + rojo funcional (única excepción):
  blanco (`--background`), azul (`--primary`, dominante), verde/turquesa
  (`--secondary`, positivo), amarillo (`--accent`, aviso). Rojo
  (`--destructive`) solo error/crítico. **No introducir un 5º color.**
- **Semántica de color única del pipeline (03 §4):** verde=hecho con fecha ·
  azul=en curso normal · ámbar=requiere acción del usuario · rojo=estancado
  real probado · gris=terminal/negativo. Ya implementada en `pipeline-ui.tsx`.
- **Estado = color + TEXTO**, nunca color solo (accesibilidad).
- **Gubernamental, sobrio:** sin gradientes, glass, neón, sombras exageradas ni
  animaciones decorativas. Radio `0.5rem`. Jerarquía por tamaño/peso/color.
- **Cero emojis.** Íconos solo como apoyo funcional y con texto al lado; ante la
  duda entre ícono y palabra, la palabra.
- **Lenguaje llano** para funcionarios sin experiencia en apps: "Actualizar
  desde SIGA", no "Refresh"; mensajes de error dicen qué pasó y qué hacer.

### 8.4 Cómo verificar antes de cerrar

```bash
# Backend
cd backend && .venv/Scripts/python.exe -m pytest tests/services/test_pipeline_v2.py \
  tests/services/test_pipeline_confianza.py tests/repositories/test_declaraciones_ccmn.py -q
# Frontend
cd frontend && npx tsc --noEmit && npx vite build
```

Smoke test de aceptación (el caso guía): kanban del 232/S **sin alerta roja**,
etapa real con fecha, O/S y EXP SIAF visibles y copiables.

---

## 9. Prompt sugerido para arrancar la sesión

> Lee `Docs/guia-pipeline-v2/04-continuacion-coherencia-datos.md` y los docs
> 00–03 de esa carpeta. La Guía Pipeline v2 ya está implementada (kanban desde
> snapshot `siga.*`, alertas v2). Quiero **mejorar la coherencia de la
> información en las vistas** (kanban, detalle, bolsa): hay pedidos donde la
> etapa, las fechas, las órdenes atribuidas o los montos no cuadran.
>
> Antes de tocar cualquier vista, **verifica el dato contra SIGA** con las
> queries de §4 (usa `app/siga/conexion.py`, siempre `SEC_EJEC=300687`).
> Empieza por el trabajo 1 de §6 (auditar etapa vs fechas) usando el testigo
> 232/S, y avanza en orden. Mantén la separación de capas (§8.1), la lógica de
> negocio en el service (testeable sin BD), y el sistema de diseño institucional
> (§8.3). No inventes: si una llave no cruza, márcalo y pregúntame.
