# Hand-off — Bug de coherencia SIGA en el dashboard interno (T-44)

> **Nota de esta versión:** este documento contiene únicamente el **contexto del problema**. Las hipótesis de solución, rutas de exploración y decisiones pendientes ya no viven aquí — están resueltas o en curso en `hallazgos-granularidad-siaf... / hallazgos-siga-cadena-pedido-orden.md` (sesión 5, 2026-07-15), que es la fuente más reciente y autoritativa sobre la estructura real de SIGA. Consultar ese documento para estrategia de fix, no este.

---

## 1. Qué se rompió

Se cerró el rediseño visual del Dashboard de bienvenida (T-44 · Etapa A). Al probarlo, el usuario funcional detectó que **los datos del pipeline y del saldo salen incorrectos**:

- El pipeline (kanban de pedidos) muestra 0 pedidos en etapa "con orden" y 0 en "devengado".
- El saldo disponible del `WidgetSaldos` es inconsistente con lo que muestra el portal público.

**El frontend no es el problema.** Está terminado, funciona, respeta el contexto (año + centro de costo del store) y todos los widgets consumen endpoints reales. El problema está en **las queries SIGA del backend** (`pipeline_repo.pipeline_kanban` y `saldos_repo.resumen_saldos`), que no reflejan correctamente la realidad operativa registrada en SIGA.

---

## 2. Estado del frontend (Etapa A, cerrada — no tocar)

- Rediseño de `DashboardWidgets`, `WidgetAlertas`, `WidgetPipeline`, `WidgetSaldos`, `UltimosPedidos`.
- Hooks (`useKanban`, `useResumenSaldos`, `usePedidosEstancados`, `useContratosPorVencer`, `useMetasRezagadas`) leen año + CC del store `contexto-interno` y disparan refetch al cambiar los chips del topbar.
- Nuevo endpoint backend `GET /interno/saldos/resumen` (agregación en SIGA + top-3 metas críticas + semáforo).
- Query param opcional `centro_costo` agregado a todos los endpoints internos + helper `permisos_service.restringir_a_subrama` que valida contra la subrama ltree del usuario.
- Rutas stub agregadas al router para `/interno/pipeline`, `/interno/pedidos/:nro/:tipo`, `/interno/contratos`, `/interno/cruce`, `/interno/proveedores` (páginas destino son placeholders hasta T-45..T-53).
- Guía `Docs/guia-frontend-interno.md` actualizada.

**Fuera de alcance de este bug:** rediseño frontend, portal público (lee de otra fuente y funciona bien), estructura de archivos/features.

---

## 3. Caso testigo: pedido 232/S

Este es el caso que el usuario funcional usó para validar (y descartar) hipótesis, y que sigue siendo la referencia de verificación.

**Realidad declarada por el usuario:**
- El pedido `232/S` ya fue aprobado.
- Se emitió la orden **132/S** (SERVICIO DE AUXILIAR ADMINISTRATIVO, S/. 4,800, sec_func 57, proveedor 1650).
- Tiene 3 conformidades (entregables mensuales del servicio).
- Debería estar cerrado.

**Cadena real reconstruida por el usuario:**

```
Pedido 232/S (SIG_PEDIDOS, sec_func 57, monto 4800)
    ↓
EM 263 (Cotización) → Cálculos valor referencial 263
    ↓
CCMN 2266 (Solicitud de certificación / cuadro consolidado)
    ↓
Certificación 182 (SIGA) / CCP SIAF 230
    ↓
Expediente SIAF 316 (SIG_EXP_SIGA_SECU, EXP_SIAF=316)
    ↓
Orden 132/S (SIG_ORDEN_ADQUISICION, EXP_SIGA=152)
    ↓
3 conformidades (una por entregable)
```

**Lo que dicen las tablas de pedido de SIGA (no refleja lo anterior):**
- `SIG_PEDIDOS`: ESTADO=1 (activo), FECHA_APROB=NULL, FECHA_ATENC=NULL.
- `SIG_DETALLE_PEDIDOS`: 1 ítem, `NRO_ORDEN=NULL`, `ESTADO_PED=1`, `ESTADO_ATEND=0`, `ESTADO_CONFOR=0`, `FECHA_CONFOR=NULL`.
- `SIG_SEGUIMIENTO`: solo 2 movimientos (creación 2026-02-05 + `TIPO_TRANSACCION=9` con `NRO_TRANSACCION=232` el 2026-03-03). Ese "232" es un `NRO_CONSOLID`, no un `NRO_ORDEN`, aunque coincida numéricamente con el propio pedido.

**Núcleo del problema:** SIGA local **no retro-alimenta las tablas del pedido origen** cuando el flujo avanza aguas abajo. El pedido queda "estancado" en su estado inicial mientras el trabajo real ocurre en tablas de expediente/orden/certificación con IDs nuevos, sin escribir de vuelta al pedido.

Se probó y descartó la hipótesis de que `SIG_SEGUIMIENTO.NRO_TRANSACCION` (con `TIPO_TRANSACCION=8/9`) fuera el número de orden: el pedido 232/S señalaba a una "orden 232/S" que sí existe en `SIG_ORDEN_ADQUISICION` pero es un servicio de mantenimiento correctivo de otro proveedor, sin relación con el pedido real. Los namespaces de pedidos y cuadros comparten rango numérico y colisionan — el 100% de match inicial era coincidencia, no relación real.

**Datos del pedido 232 para verificación manual (los tres registros que comparten el número "232" en 2026):**

| Registro | CC | sec_func | Estado | Motivo | Nota |
|---|---|---|---|---|---|
| `2026/232/B/TIPO_PEDIDO=1` | 01.03.11.02 | 29 | 7 (cerrado) | ATENCION DE PEDIDO A LA O/C N°316 | Debe aparecer en "cerrado" |
| `2026/232/B/TIPO_PEDIDO=2` | 01.03.15.02 | 147 | 1 | ADQUISICION DE MATERIAL DE ESCRITORIO | Según usuario, ya tiene orden y conformidad |
| `2026/232/S/TIPO_PEDIDO=2` | 01.03.07.04 | 57 | 1 | SERVICIO DE AUXILIAR ADMINISTRATIVO PARA OTI | **Caso testigo canónico** — cadena completa arriba |

---

## 4. Síntomas observados (reproducción del bug)

### 4.1 Kanban actual (código en producción/dev), admin, año 2026, sin filtro CC

| Etapa | Pedidos | Monto |
|---|---:|---:|
| solicitado | 1,325 | S/ 0.00 |
| conformidad | 438 | S/ 4,388,187.48 |
| cerrado | 573 | S/ 5,564,726.96 |
| **con_orden** | **0** | **0** |
| **devengado** | **0** | **0** |

Los 438 en "conformidad" aparecen solo porque el clasificador detecta `dp.ESTADO_CONFOR='1'` en algún ítem, no por relación real con una orden. Las 8,298 filas de `SIG_ORDEN_ADQUISICION` quedan huérfanas de vínculo con pedido desde el punto de vista de las queries actuales.

### 4.2 Distribución de `SIG_PEDIDOS.ESTADO` en 2026

| ESTADO | Cuántos | Semántica probable |
|---|---:|---|
| 0 | 22 | "En proceso" — FECHA_PEDIDO real, motivos reales, sin FECHA_APROB. No son borradores puros. |
| 1 | 1,763 | Registrados / aprobados |
| 7 | 573 | Cerrados |

El repo actual filtra `ESTADO IN ('1', '7')`, descartando los 22 de ESTADO=0.

### 4.3 Devengado y saldo incoherentes (`SIG_TECHO_PRESUPUESTO`, admin 2026)

| Métrica | Valor |
|---|---:|
| metas activas | 159 |
| filas techo | 1,789 |
| PIA | 65,435,148.00 |
| PIM | 163,255,720.00 |
| certificado | 15,787,701.61 |
| comprometido | 12,880,410.78 |
| **devengado** | **0.00** |
| saldo disponible | 13,862,777.80 |

El devengado en SIGA local para 2026 está en 0, pero el portal público (que lee SIAF vía API MEF) sí muestra devengado real. El saldo de 13.8M sobre un PIM de 163M con solo 15.7M certificado + 12.8M comprometido es incoherente si el devengado real fuera 0 — el saldo debería estar mucho más cerca del PIM.

### 4.4 Formato de `NRO_PEDIDO` inconsistente entre tablas

- `SIG_PEDIDOS.NRO_PEDIDO` y `SIG_DETALLE_PEDIDOS.NRO_PEDIDO`: `varchar(6)` con padding, ej. `'000232'`.
- `SIG_SEGUIMIENTO.NRO_PEDIDO`: `varchar(50)` sin padding, ej. `'232'`.

Cualquier JOIN entre estas tablas necesita normalizar el formato (esto no es la causa raíz del bug, pero afecta cualquier query que las cruce).

`SEC_EJEC` es `numeric` en todas las tablas relevantes, así que no hay problema de tipos/casting ahí.

---

## 5. Herramientas y rastros de la sesión de diagnóstico

- Script inicial: `backend/scripts/diagnostico_dashboard.sql`, corrido contra `SIGA_300687` (dev local, Windows Auth). Resultados en `Resultados.txt` (temporal).
- Exploración directa vía `sqlcmd` sin persistir en archivo — todo el rastro relevante quedó resumido en este documento.
- Conexión SIGA en dev: SQL Server localhost, instancia default, BD `SIGA_300687`, Windows Auth. Ejemplo: `sqlcmd -S localhost -E -d SIGA_300687 -Q "..."`.

---

*Hand-off · contexto del problema · basado en v2, 2026-07-15. Para la estructura real de SIGA, el puente pedido↔orden encontrado, y la estrategia de clasificación, ver el documento de hallazgos de sesión 5.*