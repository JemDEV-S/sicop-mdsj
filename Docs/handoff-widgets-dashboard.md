# Handoff — Corrección de widgets del dashboard interno

**Fecha:** 2026-07-16 (2ª sesión)
**Estado:** 6 fixes aplicados. Widget saldos ahora muestra indicadores duales MEF+SIGA. Pedidos estancados usan umbral por macrofase (1335 → 287). Pendiente commit + testing UI real.

---

## Sesión 2 (2026-07-16 tarde) — Cruce MEF vs SIGA

### Contexto del problema (planteado por el usuario)
- El widget mostraba PIM S/ 163M y "Ejecutado" S/ 92M (56.3%). El **portal MEF muestra PIM S/ 69.5M y devengado S/ 31.1M (44.8%)**.
- Pedidos estancados: 1335. El funcionario esperaba **<8**.
- Existe snapshot MEF en PostgreSQL (`siaf.ejecucion_presupuestal`) para el portal ciudadano.

### Diagnóstico empírico (backend/scripts/diagnostico_cruce_mef_siga.py)

**Hallazgo A — PIM inflado por techo no desagregado (no era bug de código):**
- 264 filas en `SIG_TECHO_PRESUPUESTO` con `SEC_FUNC IS NULL` (PIM S/ 116.6M).
- Son "techo del pliego" cargado en el SIGA (canon, impuestos, FONCOMUN) pero **no asignado a metas ejecutables**.
- Todas con `PPTO_DISP_SIAF = 0` (no participan en la ejecución SIAF).
- Excluyéndolas: PIM SIGA = S/ 46.7M (vs. MEF S/ 69.5M — diferencia real de fuentes sincronizadas SIAF pero no en SIGA aún).

**Hallazgo B — Proxy `PIM - Disp_SIAF` sobreestima brutalmente:**
- Proxy S/ 91.98M vs. devengado real MEF S/ 30.89M.
- La diferencia venía justamente del PIM inflado del techo huérfano.
- `MNTO_ACUM_DEVGDO_SIGA` y `MNTO_ACUM_DEVGDO_SIAF` siguen en 0 en 2026.
- `SIG_DEVENGADO_ITEM_PPTO` también vacío en 2026 (0 devengados).
- **Solución**: reemplazar proxy por `mnto_acum_cert + mnto_acum_coma` (SIGA S/ 28.7M ≈ MEF S/ 31M ✓) y usar snapshot MEF como devengado oficial.

**Hallazgo C — Estancados: 1212/1335 tenían fecha propia, no falso positivo por fecha:**
- El problema real: **umbral de 15 días demasiado agresivo** para servicios/obras plurianuales.
- 782 pedidos en `ejecucion` con edad 31–120 días — legítimos, no estancados.
- Solución: umbrales por macrofase.

### Decisiones tomadas

1. **PIM/Devengado oficial** viene del snapshot MEF (`siaf.ejecucion_presupuestal`).
   Sólo se expone cuando el usuario ve el pliego completo (`centros is None`).
2. **PIM/Cert/Comp interno** viene del SIGA a nivel meta, **excluyendo huérfanas** (SEC_FUNC IS NOT NULL).
3. **Umbrales por macrofase** en `sistema.umbrales_alertas.pedido_estancado`:
   ```json
   {"dias": 15, "dias_por_macrofase": {
     "solicitud": 15, "programacion": 30, "certificacion": 30,
     "contratacion": 45, "ejecucion": 180, "cierre": null
   }}
   ```

### Resultados (verificados con curl al endpoint `/api/v1/interno/saldos/resumen`)

| Métrica | Antes | Después | MEF portal |
|---|---:|---:|---:|
| PIM (widget) | S/ 163.3M ❌ | **S/ 69.5M** (MEF) ✅ | S/ 69.5M |
| Devengado (widget) | S/ 92.0M ❌ | **S/ 30.9M** (MEF) ✅ | S/ 31.1M |
| % Ejecución (widget) | 56.3% ❌ | **44.5%** (MEF) ✅ | 44.8% |
| Estancados totales | 1335 | **287** | — |
| Estancados/macrofase | — | prog 164 · contr 97 · cert 18 · sol 8 | — |

### Archivos modificados en sesión 2

**Backend:**
- [backend/app/repositories/saldos_repo.py](../backend/app/repositories/saldos_repo.py) — 4 lugares: excluir SEC_FUNC NULL + reemplazar proxy por cert+comp.
- [backend/app/repositories/ejecucion_mef_repo.py](../backend/app/repositories/ejecucion_mef_repo.py) — **NUEVO**. `resumen_mef()` con PIA/PIM/dev/certif/comp desde snapshot.
- [backend/app/services/saldos_service.py](../backend/app/services/saldos_service.py) — `resumen_saldos()` agrega bloque `mef` cuando `centros is None`; semáforo se aplica al % MEF si existe.
- [backend/app/schemas/saldos.py](../backend/app/schemas/saldos.py) — nuevo schema `EjecucionMef`, campo `mef: EjecucionMef | None` en `SaldosResumenResponse`.
- [backend/app/services/pipeline_service.py](../backend/app/services/pipeline_service.py) — `_cargar_umbrales` reemplaza `_umbral_dias`; `_enriquecer` recibe mapping por macrofase; `null` desactiva la alerta.
- [backend/alembic/versions/0003_seed_auth_umbrales.py](../backend/alembic/versions/0003_seed_auth_umbrales.py) — seed extendido con `dias_por_macrofase`.

**Frontend:**
- [frontend/src/features/dashboard/types.ts](../frontend/src/features/dashboard/types.ts) — nuevo `EjecucionMef`, campo `mef` en `SaldosResumen`.
- [frontend/src/features/dashboard/widgets/WidgetSaldos.tsx](../frontend/src/features/dashboard/widgets/WidgetSaldos.tsx) — reescrito: bloque MEF arriba (número oficial) + bloque SIGA abajo (visión interna). Fallback si el usuario está restringido a un subárbol.

**Scripts nuevos:**
- [backend/scripts/diagnostico_cruce_mef_siga.py](../backend/scripts/diagnostico_cruce_mef_siga.py) — A: PIM inflado, B: devengado, C: estancados por origen de fecha.

### Ajuste colateral

- `saldos_service.py` usaba `metrica='porcentaje_devengado'` pero la BD tiene `metrica='avance_devengado'`. Alineado a la BD (menor blast radius). Efecto: el semáforo del widget ahora resuelve (antes salía siempre "desconocido").

### Pendientes de sesión 2

- ⚠️ Correr `alembic upgrade head` en instalaciones nuevas — el seed ahora incluye `dias_por_macrofase`; en BDs existentes el UPDATE se hizo manualmente y hay que reflejarlo con una migración nueva si se quiere versionar.
- ⚠️ Testing en la UI real del widget rediseñado.
- ⚠️ Considerar añadir una nota en el widget cuando el snapshot MEF esté desfasado (>48h desde `sincronizado_en`).

---

## Sesión 1 (2026-07-16 mañana)

---

## Contexto del problema

Los widgets del dashboard interno (`/interno` → `DashboardWidgets`) mostraban datos incorrectos:

- **`WidgetSaldos`**: mostraba 0% de ejecución y S/ 0 devengado para toda la muni.
- **`WidgetAlertas`**: mostraba 0 metas rezagadas y sobreconteo de pedidos estancados.
- **Único correcto**: `WidgetPipeline` (usa el kanban con inspección directa al SIGA).

El usuario pidió: "vamos a corregir los widgets, primero hacer un diagnóstico".

---

## Referencias de archivos clave

### Frontend

- [frontend/src/features/dashboard/secciones/DashboardWidgets.tsx](../frontend/src/features/dashboard/secciones/DashboardWidgets.tsx) — orquestador; llama a los 5 hooks y renderiza los 3 widgets + `UltimosPedidos`.
- [frontend/src/features/dashboard/widgets/WidgetSaldos.tsx](../frontend/src/features/dashboard/widgets/WidgetSaldos.tsx) — **MODIFICADO** (mapeo semáforo local + label "Ejecutado").
- [frontend/src/features/dashboard/widgets/WidgetAlertas.tsx](../frontend/src/features/dashboard/widgets/WidgetAlertas.tsx) — sin tocar (bug estaba en el backend, no en la UI).
- [frontend/src/features/dashboard/widgets/WidgetPipeline.tsx](../frontend/src/features/dashboard/widgets/WidgetPipeline.tsx) — **NO TOCAR** (funciona correctamente, es la referencia).
- [frontend/src/features/dashboard/api.ts](../frontend/src/features/dashboard/api.ts) — hooks (useKanban, useResumenSaldos, usePedidosEstancados, useContratosPorVencer, useMetasRezagadas).
- [frontend/src/features/dashboard/types.ts](../frontend/src/features/dashboard/types.ts) — SaldosResumen, MetaCritica, MetaRezagada, ContratoPorVencer, PedidoCard, KanbanResponse.
- [frontend/src/features/obras/api.ts](../frontend/src/features/obras/api.ts#L9-L14) — `mapSemaforoApiToEstado` (helper de obras que estaba mal reutilizado en saldos).
- [frontend/src/lib/formatters.ts](../frontend/src/lib/formatters.ts) — `formatearMoneda`, `formatPorcentaje` (correctos).

### Backend — saldos

- [backend/app/routers/saldos.py](../backend/app/routers/saldos.py) — endpoints `/interno/saldos/resumen` y `/interno/saldos/metas-rezagadas`.
- [backend/app/services/saldos_service.py](../backend/app/services/saldos_service.py) — orquesta repo + semaforo_service.
- [backend/app/repositories/saldos_repo.py](../backend/app/repositories/saldos_repo.py) — **MODIFICADO** (3 queries: `listar_saldos`, `resumen_saldos`, `metas_rezagadas`).
- [backend/app/schemas/saldos.py](../backend/app/schemas/saldos.py) — SaldoItem, MetaRezagadaItem, MetaCritica, SaldosResumenResponse.
- [backend/app/services/semaforo_service.py](../backend/app/services/semaforo_service.py) — devuelve `'verde' | 'amarillo' | 'rojo' | 'desconocido'`.

### Backend — pipeline / alertas

- [backend/app/routers/pipeline.py](../backend/app/routers/pipeline.py) — router `pipeline_router` + `alertas_router`. El endpoint `/interno/alertas/pedidos-estancados` está aquí.
- [backend/app/services/pipeline_service.py](../backend/app/services/pipeline_service.py) — **MODIFICADO** (`_fecha_etapa` reescrito).
- [backend/app/repositories/pipeline_repo.py](../backend/app/repositories/pipeline_repo.py) — **MODIFICADO** (5 CTEs ampliados con fechas por etapa).
- [backend/app/schemas/pipeline.py](../backend/app/schemas/pipeline.py) — ETAPA_* constantes, PedidoCard schema.

### Backend — contratos

- [backend/app/repositories/contratos_repo.py](../backend/app/repositories/contratos_repo.py) — **NO TOCADO** (verificación empírica confirmó que ya devuelve los 3 contratos correctos).

### Backend — SIGA

- [backend/app/siga/conexion.py](../backend/app/siga/conexion.py) — `get_connection()` engine SQLAlchemy contra SQL Server local.
- [backend/app/config.py](../backend/app/config.py) — `settings.SEC_EJEC='300687'`, `settings.ANO_VIGENTE=2026`.

### Script de diagnóstico (creado)

- [backend/scripts/diagnostico_alertas_saldos.py](../backend/scripts/diagnostico_alertas_saldos.py) — script que responde 3 preguntas empíricas contra SIGA. Ejecutar:
  ```powershell
  docker exec sicop_backend_dev python -m scripts.diagnostico_alertas_saldos
  ```

### Documentos de referencia usados

- [Docs/exploracion-siga-pipeline-extendido.md](exploracion-siga-pipeline-extendido.md) — mapa canónico §16.6 y §17.6 (**única fuente autoritativa para queries SIGA del pipeline**).
- [CLAUDE.md](../CLAUDE.md) — reglas no negociables (SEC_EJEC=300687, fuentes autoritativas, etc.).

---

## Diagnóstico y hallazgos

### Hallazgo #1 (fix #4) — Semáforo del WidgetSaldos nunca aparecía

**Ubicación bug**: [WidgetSaldos.tsx:14](../frontend/src/features/dashboard/widgets/WidgetSaldos.tsx#L14) importaba `mapSemaforoApiToEstado` de `features/obras/api.ts` — pero:

- Backend de saldos devuelve `'verde' | 'amarillo' | 'rojo' | 'desconocido'` (ver `semaforo_service.color`).
- El helper de obras solo acepta `'ok' | 'alerta' | 'critico'`.
- Resultado: siempre `null` → semáforo nunca renderiza.

**Fix aplicado**: función local `mapSemaforoSaldos` en WidgetSaldos.tsx que traduce el vocabulario del backend correctamente.

### Hallazgo #2 (fix #1) — DESCARTADO: contratos por vencer

**Verificación empírica**: `SIG_CONTRATOS` tiene 127 filas totales (2023-2026), pero el filtro `FECHA_FINAL >= HOY AND FECHA_FINAL <= HOY+30` ya descarta implícitamente los años anteriores. Filtro actual devuelve **3 contratos**, filtro "corregido" con `ANO_EJE=2026` devuelve **3 contratos** (idénticos). **No hay bug real**.

### Hallazgo #3 (fix #3) — El devengado del widget estaba en 0 para toda la muni en 2026

**Causa raíz**: la columna `SIG_TECHO_PRESUPUESTO.MNTO_ACUM_DEVGDO_SIGA` **no está poblada** por el SIGA de la muni en 2026. Verificación en [diagnostico_alertas_saldos.py](../backend/scripts/diagnostico_alertas_saldos.py):

```
MNTO_ACUM_DEVGDO_SIGA (widget actual):  0.00
MNTO_ACUM_DEVGDO_SIAF (columna hermana): 0.00
SIG_DEVENGADO_ITEM_PPTO (autoritativo):  0.00
```

Pero `PPTO_MODIF = 163.25M` y `PPTO_DISP_SIAF = 13.86M` → hay **S/ 149M de diferencia** que representan ejecución real invisible.

**Fix aplicado**: proxy `PPTO_MODIF - PPTO_DISP_SIAF` en las 3 queries del `saldos_repo`. Este proxy incluye certificado + comprometido + devengado. En el widget se relabeleó "Devengado" → "Ejecutado" con tooltip explicativo. Antes de commit definitivo, **hay que hablar con el administrador del SIGA de la muni** para saber si `MNTO_ACUM_DEVGDO_SIGA` debería poblarse (podría ser un trigger deshabilitado o un job pendiente).

### Hallazgo #4 (fix #2) — Pedidos estancados sobrecontados por caída a FECHA_PEDIDO

**Causa raíz**: `pipeline_service._fecha_etapa` solo tenía disponibles 3 fechas cabecera del pedido (`FECHA_PEDIDO`, `FECHA_APROB`, `FECHA_ATENC`). Para un pedido en etapa "ejecucion" sin `FECHA_ATENC`, caía a `FECHA_APROB` o `FECHA_PEDIDO` (hace medio año) → `dias_en_etapa = 160+ días` → **falso estancado**.

Ejemplo: **pedido testigo 232/S** — etapa "ejecucion", `FECHA_PEDIDO=2026-02-05`, no tiene `FECHA_ATENC`. Antes: días_en_etapa=161 (desde FECHA_PEDIDO). Después: días_en_etapa=70 (desde `fecha_ejecucion=2026-05-07`).

**Fix aplicado**: agregadas 9 columnas de fecha por etapa al `agrup` CTE del kanban SQL. `_fecha_etapa` reescrito para usarlas.

---

## Numéricos antes/después

| Métrica | Antes | Después |
|---|---:|---:|
| WidgetSaldos: % Ejecución | 0.00% ❌ | **56.34%** ✅ |
| WidgetSaldos: Devengado/Ejecutado (S/) | 0 | **91,981,282** |
| WidgetSaldos: Metas críticas | 0 | **49** |
| WidgetSaldos: Semáforo visible | nunca | cuando umbrales seedeados |
| WidgetAlertas: Metas rezagadas <50% | 0 | **59** |
| WidgetAlertas: Pedidos estancados | ~1800 (inflados) | **1335** (reales) |
| WidgetAlertas: Contratos por vencer | 3 (ok) | 3 (ok) |

---

## Cambios exactos de código

### Frontend — 1 archivo

**[WidgetSaldos.tsx](../frontend/src/features/dashboard/widgets/WidgetSaldos.tsx)**:

1. Removido import `mapSemaforoApiToEstado from '@/features/obras/api'`.
2. Agregada función local `mapSemaforoSaldos(valor: string)` que mapea `verde → ok`, `amarillo → alerta`, `rojo → critico`.
3. Relabel "Devengado" → "Ejecutado" con tooltip explicando el proxy.
4. "Ejecución" → "% Ejecución" para claridad.

### Backend — 3 archivos

**[saldos_repo.py](../backend/app/repositories/saldos_repo.py)**:

- Docstring del módulo: agregada nota sobre `MNTO_ACUM_DEVGDO_SIGA` = 0 en 2026 y por qué se usa proxy.
- Función `listar_saldos` (query principal): `COALESCE(t.MNTO_ACUM_DEVGDO_SIGA, 0)` → `COALESCE(t.PPTO_MODIF, 0) - COALESCE(t.PPTO_DISP_SIAF, 0)` (2 lugares: SELECT y cálculo del %).
- Función `resumen_saldos` (sql_totales, sql_top, sql_metas_criticas): mismo reemplazo, 5 lugares.
- Función `metas_rezagadas`: mismo reemplazo, 3 lugares.

**[pipeline_repo.py](../backend/app/repositories/pipeline_repo.py)** — agregadas 9 columnas de fecha por etapa:

- CTE `programacion`: `+ MAX(pc.FECHA_CONS) AS fecha_ccmn`
- CTE `cuadro_adq`: `+ MAX(ca.FECHA_CUADRO) AS fecha_cuadro_adq`
- CTE `certificacion`: `+ MAX(c.FECHA) AS fecha_certificacion`
- CTE `orden_enriquecida`: `+ o.FECHA_ORDEN` (a la SELECT del CTE)
- CTE `ejecucion`: `+ MAX(cf.ultima_fecha_confor, ma_i.FECHA_MOVIMTO) AS fecha_ejecucion` y `+ MAX(ma_r.FECHA_MOVIMTO) AS fecha_kardex`. También agregada `MAX(FECHA_MOVIMTO) AS ultima_fecha_confor` al subquery interno de `cf`.
- CTE `pecosa`: `+ MAX(ma.FECHA_MOVIMTO) AS fecha_pecosa`
- CTE `cierre`: `+ MAX(sg.FECHA_TRANSACCION) AS fecha_cierre_seg`
- CTE `agrup` (SELECT final): `+ MAX(...) AS fecha_ccmn/fecha_cuadro_adq/fecha_certificacion/fecha_orden/fecha_compromiso/fecha_ejecucion/fecha_kardex/fecha_pecosa/fecha_cierre_seg` (9 columnas nuevas). No requiere cambios en GROUP BY porque son MAX de columnas no agrupadas.

**[pipeline_service.py](../backend/app/services/pipeline_service.py)**:

- Función `_fecha_etapa` completamente reescrita para usar las nuevas columnas de fecha en lugar de caer a `FECHA_PEDIDO`.
- Docstring nuevo explicando la razón del cambio.

### Script nuevo

**[backend/scripts/diagnostico_alertas_saldos.py](../backend/scripts/diagnostico_alertas_saldos.py)** — script empírico que:
- A: distribución de `SIG_CONTRATOS` por año/estado + comparación filtro actual vs propuesto.
- B: rastrea el pedido testigo 232/S en `SIG_PEDIDOS` → `SIG_DEVENGADO_ITEM_PPTO` → `SIG_TECHO_PRESUPUESTO` para comparar 3 fuentes de devengado.
- C: distribución de pedidos por `(TIPO_PEDIDO, ESTADO)` con edad > 15 días.

---

## Nombres de columnas SIGA verificados (no confiar en el doc, verificado empíricamente)

- `SIG_PEDIDOS.ESTADO` (NO `ESTADO_PEDIDO`)
- `SIG_PEDIDOS.sec_func` (minúsculas — sí está en el cabecero del pedido)
- `SIG_CUADRO_MODIFICADO_SALDO.ANNO_EJEC` (NO `ANO_EJE`; es la única tabla con este nombre)
- `SIG_CUADRO_MODIFICADO_SALDO` **no tiene** `SEC_FUNC` (para llegar al sec_func hay que ir por otra vía)
- `SIG_SEGUIMIENTO.FECHA_TRANSACCION` (NO `FECHA_MOVIMIENTO`)
- `SIG_SEGUIMIENTO.NRO_PEDIDO` es **varchar** — puede contener valores no numéricos como `'01-2026-MDSJ/C'`. Usar `TRY_CAST(sg.NRO_PEDIDO AS INT)` para joins numéricos.
- `SIG_MOVIM_CONFOR_SERVICIO` **no tiene** `MONTO_TOTAL` — hay que ir por `SIG_DETALLE_MOVIM_CONFOR_SERV` con PRECIO_UNIT × CANT.
- `SIG_ORDEN_ADQUISICION` **no tiene** `NRO_PEDIDO` directo (llegar por composite o por `SIG_ORDEN_ITEM_PPTO.SEC_FUNC`).
- `SIG_DEVENGADO_ITEM_PPTO` es el registro autoritativo del devengado por sec_func — pero **está vacío en 2026 en esta muni**.

Ver introspección completa en la sesión anterior (docker exec query a `INFORMATION_SCHEMA.COLUMNS`).

---

## Estado actual y qué falta

### Hecho
- ✅ Fix #4 (semáforo WidgetSaldos)
- ✅ Fix #1 verificado que NO hace falta (contratos_por_vencer ya devuelve el número correcto)
- ✅ Fix #3 (proxy PIM - DISP_SIAF para devengado)
- ✅ Fix #2 (fechas por etapa en pipeline_repo + pipeline_service)
- ✅ Script de diagnóstico creado en `backend/scripts/`
- ✅ Smoke tests pasan a nivel repo (56.34% ejecución, 59 metas rezagadas, 1335 estancados)

### Pendiente
- ❌ **Testing en la UI real** — abrir el frontend y verificar que los widgets se ven bien.
- ❌ **Verificar que TypeScript compila** el fix del WidgetSaldos (no debería romper nada, pero validar).
- ❌ **Commit** — nada está committeado todavía. El usuario dijo "primero haz un diagnóstico" y luego fue avanzando. Preguntar antes de commitear.
- ⚠️ **Hablar con administrador SIGA muni** sobre por qué `MNTO_ACUM_DEVGDO_SIGA` está en 0 en 2026. Podría ser trigger deshabilitado. Si se puebla en el futuro, decidir si cambiar el proxy o mantenerlo como está.
- ⚠️ **Seed de `sistema.umbrales_semaforos`** para `modulo='saldos'`, `metrica='porcentaje_devengado'` — sin esto el widget muestra "desconocido" y el semáforo no aparece (aunque el fix #4 esté aplicado). Verificar `backend/alembic/versions/0003_seed_auth_umbrales.py`.

### Riesgos / cosas a revisar
- La query del kanban ahora trae 9 columnas de fecha más. **Impacto en performance** — no medido. Con 2358 pedidos probablemente marginal pero conviene medir.
- El proxy `PIM - PPTO_DISP_SIAF` **incluye certificado + comprometido**, no solo devengado. El label "Ejecutado" es honesto pero **el usuario funcionario podría no coincidir con lo que ve en el cliente SIGA nativo** (que muestra devengado puro). Habrá que explicárselo o negociar el nombre.
- `formatPorcentaje` en formatters.ts asume input 0-100. El backend devuelve 0-100. Verificado que funciona bien (56.34% se ve como "56.3%").

---


### Cómo re-correr el diagnóstico
```powershell
docker exec sicop_backend_dev python -m scripts.diagnostico_alertas_saldos
```

### Cómo probar el fix del pedido testigo
```powershell
docker exec sicop_backend_dev python -c "
from app.repositories import pipeline_repo
rows = pipeline_repo.pipeline_pedidos_raw(ano=2026, centros=None)
testigo = [r for r in rows if r.get('NRO_PEDIDO','').lstrip('0') == '232' and r.get('TIPO_BIEN')=='S']
print(testigo[0] if testigo else 'no encontrado')
"
