# Hallazgos SIGA — Cadena Pedido ↔ Orden ↔ Devengado

> **Propósito.** Consolidar lo aprendido sobre la estructura real de SIGA (Municipalidad Distrital de San Jerónimo, SEC_EJEC=300687) sobre el flujo completo Pedido → Cuadro → Certificación → Orden → Devengado → Conformidad/Pecosa.
>
> **Estado:** sesión 5 (2026-07-15). Se descubrió el puente estructural real para bienes (`NRO_PECOSA`) que sesiones previas habían pasado por alto, y se caracterizó definitivamente la diferencia de flujo entre bienes y servicios.
>
> Este documento **no decide** el fix del pipeline — es referencia técnica. Las decisiones de negocio se toman con el usuario funcional.

---

## 1. TL;DR

**Para bienes (`TIPO_BIEN='B'`), existe puente estructural real:**
```
SIG_DETALLE_PEDIDOS.NRO_PECOSA  =  SIG_MOVIM_ALMACEN.NRO_MOVIMTO  →  NRO_ORDEN
```
Match rate: **98,3% en compras cerradas** (563/573 pedidos TIPO_PEDIDO=1 ESTADO=7).

**Para servicios (`TIPO_BIEN='S'`), no existe puente estructural.** `NRO_PECOSA=0` en el 100% de servicios (el campo está pero no aplica — los servicios no van a almacén). El vínculo se reconstruye por heurístico composite (`SEC_FUNC + CLASIFICADOR + GRUPO+CLASE+FAMILIA+ITEM_BIEN [+VALOR]`) con 89-99% match según incluyamos VALOR.

**Los TIPO_PEDIDO=2 (bienes) son despachos internos de almacén**, no pedidos de compra. Confunden el pipeline si se los cuenta como "solicitados" — hay que separarlos.

**Los estados locales del pedido son mentirosos para servicios**, incluso finalizados. Un servicio ya terminado (con todas sus conformidades pagadas) puede seguir con `ESTADO_PED=1, ESTADO_ATEND=0, ESTADO_CONFOR=0` — SIGA no tiene un mecanismo que marque un servicio como "cerrado". La señal real de finalización hay que reconstruirla contando conformidades en `SIG_MOVIM_CONFOR_SERVICIO`.

**Cadena orden → cuadro → certificación** funciona 100% por FKs reales al 100% en 2026. La ruptura solo está en pedido ↔ orden.

---

## 2. Estructura de PKs de las tablas del ciclo

| Tabla | Primary Key | Rol |
|---|---|---|
| `SIG_PEDIDOS` | `(ANO_EJE, SEC_EJEC, TIPO_BIEN, TIPO_PEDIDO, NRO_PEDIDO)` | Header pedido |
| `SIG_DETALLE_PEDIDOS` | `(…, SECUENCIA)` | Items pedido — tiene `NRO_PECOSA` |
| `SIG_ORDEN_ADQUISICION` | `(ANO_EJE, SEC_EJEC, NRO_ORDEN, TIPO_BIEN, TIPO_PPTO)` | Header orden — tiene `SEC_CUADRO` y `NRO_CERTIFICA` |
| `SIG_ORDEN_ITEM` | `(…, SEC_ORDEN, SEC_ITEM)` | Items orden |
| `SIG_ORDEN_ITEM_PPTO` | `(…, SEC_ITEM_PPTO)` | Distribución presupuestal (aquí vive `VALOR_SOLES`) |
| `SIG_CUADRO_ADQUISICION` | `(ANO_EJE, SEC_EJEC, TIPO_BIEN, SEC_CUADRO)` | Header cuadro — **SEC_CUADRO se reutiliza entre TIPO_BIEN B y S** |
| `SIG_DETALLE_BSERV_CUADRO` | `(…, SECUENCIA)` | Items cuadro — `nro_pedido` a 0% en 2026 |
| `SIG_CERTIFICACION` | `(ANO_EJE, SEC_EJEC, NRO_CERTIFICA)` | Certificación |
| `SIG_CERTIFICACION_FASE` | `(…, SECUENCIA_FASE)` | Fases certif — tiene `NRO_ORDEN`, `NRO_CONSOLID` |
| `SIG_EXP_SIGA` | `(ANO_EJE, SEC_EJEC, TIPO_PPTO, EXP_SIGA)` | Expediente SIGA |
| `SIG_EXP_SIGA_SECU` | `(…, EXP_SIGA_DOC, EXP_SIGA_SECU)` | Secuencias devengado |
| `SIG_MOVIM_ALMACEN` | `(ANO_EJE, SEC_EJEC, TIPO_MOVIMTO, TIPO_TRANSAC, TIPO_PPTO, NRO_MOVIMTO, TIPO_BIEN)` | **Entradas/salidas almacén** — tiene `NRO_ORDEN` |
| `SIG_MOVIM_CONFOR_SERVICIO` | `(…, NRO_MOVIMTO)` | Conformidades de servicio — tiene `NRO_ORDEN`, `ESTADO_DEVENG` |
| `SIG_DETALLE_PECOSA` | `(…, NRO_PECOSA, SECUENCIA)` | Detalle pecosa — tiene `NRO_PEDIDO` |

**Observación crítica:** el pedido discrimina por `TIPO_PEDIDO`, la orden por `TIPO_PPTO`. No son la misma dimensión — impide JOIN por igualdad de PK.

---

## 3. FKs y llaves reales que funcionan

### 3.1 Cadena orden → arriba (100% FK real)

```
SIG_ORDEN_ADQUISICION.NRO_CERTIFICA  →  SIG_CERTIFICACION      (FK_SOA_SC_01)
SIG_ORDEN_ADQUISICION.SEC_CUADRO     →  SIG_CUADRO_ADQUISICION (100% fill 2026)
SIG_CERTIFICACION_FASE               →  SIG_CERTIFICACION      (FK_SCF_01)
SIG_DETALLE_BSERV_CUADRO             →  SIG_CUADRO_ADQUISICION (FK real)
SIG_EXP_SIGA_SECU.NRO_ORDEN_SOS      →  SIG_ORDEN_SECUENCIA    (FK_SIG_EXP_SIGA_SECU_01)
SIG_DEVENGADO                        →  SIG_ORDEN_ADQUISICION  (FK_ORD_ADQ_DEVENG, tabla vacía en 2026)
```

### 3.2 Puente real pedido ↔ orden (solo bienes)

**Descubierto en sesión 5.** Este puente fue omitido en sesiones anteriores porque el cruce de columnas buscó `NRO_PEDIDO+NRO_ORDEN` en la misma tabla, pero el puente es indirecto:

```
SIG_DETALLE_PEDIDOS.NRO_PECOSA  =  SIG_MOVIM_ALMACEN.NRO_MOVIMTO
                                                       └── NRO_ORDEN (100% en 2026)
```

**Fill rates 2026 (SEC_EJEC=300687):**

| Universo | Items | Con `NRO_PECOSA>0` |
|---|---:|---:|
| `SIG_DETALLE_PEDIDOS` TIPO_BIEN=B | 7.345 | **3.261 (44%)** |
| `SIG_DETALLE_PEDIDOS` TIPO_BIEN=S | 1.056 | **0 (0%)** — campo poblado con 0 |

Para bienes el 56% restante son items **aún no atendidos** (pedido activo sin entrada al almacén todavía).

### 3.3 Cadena servicio → devengado (sin puente estructural desde pedido)

Para servicios no existe llave dura desde el pedido. La cadena río abajo funciona por FKs internas:

```
SIG_ORDEN_ADQUISICION (TIPO_BIEN='S')  →  SIG_MOVIM_CONFOR_SERVICIO.NRO_ORDEN
                                            └── ESTADO_DEVENG='D' (devengado)
                                            └── SECUENCIA_SIAF, EXPEDIENTE_SIAF
```

Un servicio recurrente (ej: contrato mensual) genera **N filas** en `SIG_MOVIM_CONFOR_SERVICIO`, una por conformidad/pago.

---

## 4. Match rate del puente NRO_PECOSA para bienes

**Datos duros, 2026 SEC_EJEC=300687:**

| Segmento | Pedidos | Match a orden vía pecosa | % |
|---|---:|---:|---:|
| **`TIPO_PEDIDO=1` (compras) ESTADO=7** | 573 | **563** | **98,3%** |
| `TIPO_PEDIDO=2` (despachos internos) | 730 | 0 | 0% (esperado — no son órdenes de compra) |
| Otros huérfanos (TIPO_PEDIDO=1 en estados no-7) | 8 | 0 | investigar caso a caso |

**Semántica de TIPO_PEDIDO (deducida):**
- **TIPO_PEDIDO=1** = pedido de compra: usuario pide algo → genera orden → llega al almacén (pecosa I=ingreso) → matchea vía `NRO_PECOSA`.
- **TIPO_PEDIDO=2** = despacho interno: usuario pide sacar del almacén algo ya existente → genera pecosa S=salida, pero no hay orden de compra en 2026 (o su orden es de años anteriores).

**Implicación:** los TIPO_PEDIDO=2 **no pertenecen al pipeline pedido→orden→devengado**. El kanban actual los está inflando artificialmente en la etapa "solicitado".

---

## 5. Heurístico composite (necesario para servicios y bienes sin pecosa)

Cuando el puente estructural no aplica (servicios, o bienes en tránsito sin pecosa aún), se reconstruye el vínculo por atributos del ítem:

`(TIPO_BIEN + SEC_FUNC + CLASIFICADOR + GRUPO+CLASE+FAMILIA+ITEM_BIEN)` [+ `VALOR_SOLES` opcional]

**Unión típica:**
```sql
SIG_DETALLE_PEDIDOS dp
JOIN SIG_PEDIDOS p ON (PK compuesta pedido)
JOIN SIG_ORDEN_ITEM oi ON (mismo TIPO_BIEN + GRUPO+CLASE+FAMILIA+ITEM_BIEN)
JOIN SIG_ORDEN_ITEM_PPTO op ON (PK orden_item + SEC_FUNC + CLASIFICADOR = pedido)
```

**Unicidad global 2026 (composite con VALOR):**

| Métrica | Valor |
|---|---:|
| Combinaciones distintas en items de orden 2026 | 4.134 |
| Con match único (n=1) | **4.016 (97,1%)** |
| Con colisión (n>1) | 118 |
| Items afectados por colisión | 393 |

**Match rate global por estado del pedido:**

| Estado pedido | Total | Con match (con VALOR) | Con match (sin VALOR) |
|---|---:|---:|---:|
| 0 (en proceso) | 9 | 7 (77%) | 7 (77%) |
| 1 (activo) | 1.763 | 1.517 (86%) | mayor |
| 7 (cerrado) | 573 | **571 (99,7%)** | 571 (99,7%) |
| **Total pedidos** | **2.345** | 2.095 (89,3%) | 1.530 (65,2%) con VALOR |

**Variante mejorada (§8.2):** matchear vía `SIG_DETALLE_BSERV_CUADRO` aprovechando que `SIG_ORDEN_ADQUISICION.SEC_CUADRO` está al 100%.

---

## 6. Casos testigo validados en sesión 5

### 6.1 Pedido 232/S — servicio finalizado sin señal de cierre en SIGA

**Contexto:** auxiliar administrativo para OTI, contrato de 3 meses, valor 4.800 (total del contrato ejecutado en 3 pagos mensuales).

```
PEDIDO 232/S (05/feb/2026) ESTADO=1 (aunque el servicio ya finalizó)
    ↓ (composite: SEC_FUNC=57 + item 071100431207 + 4800)
CUADRO 131/S (16/feb) — 30 items consolidados de varios pedidos
    ↓ (FK SEC_CUADRO — 100%)
ORDEN 132/S (16/feb) ESTADO_SIAF=2 — proveedor 1650
    ↓ (FK NRO_CERTIFICA)
CERT 182 → CERT_SIAF 230 (ESTADO_CERTIFICA_SIAF=3)
    ↓
EXP_SIGA 152 → EXP_SIAF 316 (TIPO_FASE=D devengado)
    ↓
CONFORMIDADES: 3 pagos en SIG_MOVIM_CONFOR_SERVICIO (mar/abr/may 2026) — ejecución total del contrato
```

**Estados del pedido (mentirosos):** `ESTADO_PED=1, ESTADO_ATEND=0, ESTADO_CONFOR=0` — a pesar de que el servicio **ya terminó** (las 3 conformidades pagadas son la ejecución completa del contrato). **SIGA no tiene un mecanismo que marque la finalización de un servicio como "cerrado"** — el pedido queda en ESTADO=1 indefinidamente. **La señal real de avance/cierre no vive en el pedido; hay que reconstruirla contando conformidades río abajo.**

### 6.2 Pedido 005/B TIPO_PEDIDO=1 — compra cerrada

**Contexto:** útiles de oficina (grupo 20 clase 34), 3 items, valor 5.805.

```
PEDIDO 005/B TIPO_PEDIDO=1 (12/feb/2026) ESTADO=7
    ↓ (composite y también puente NRO_PECOSA=4)
CUADRO 4/B (04/feb) — 3 items exactos, valor 5.805
    ↓ (FK SEC_CUADRO)
ORDEN 003/B (04/feb) ESTADO_SIAF=2 — proveedor 2217
    ↓ (FK NRO_CERTIFICA)
CERT 79 → CERT_SIAF 106
    ↓
EXP_SIGA 59 → EXP_SIAF 179 (TIPO_FASE=D devengado)
    ↓
MOVIM ALMACÉN 4/B (12/feb): entrada I + retiro R, guía EG07-347
    ↓
PECOSA 4 = SIG_DETALLE_PEDIDOS.NRO_PECOSA (3 items del pedido enlazados)
```

**Estados del pedido (fiables aquí):** `ESTADO_PED=8, ESTADO_ATEND=1, ESTADO_CONFOR=1` — a diferencia de servicios, los bienes cerrados sí reflejan avance en sus estados locales.

**Este caso demuestra que el puente `NRO_PECOSA → NRO_MOVIMTO` es una llave estructural real** (no heurístico).

---

## 7. Hallazgos sobre el modelo de datos SIGA

### 7.1 Cuadros multi-ítem consolidados

El cuadro NO es un mapa 1:1 con un pedido. **Un cuadro consolida ítems de varios pedidos.** Ejemplos verificados:
- `SEC_CUADRO=131/S` tiene 30 items (el pedido 232 es solo la última fila).
- `SEC_CUADRO=4/B` tiene 3 items (pedido 005 aporta las 3).

En `SIG_DETALLE_BSERV_CUADRO` la columna `nro_pedido` está a **0% en 2026** — el cuadro no persiste la trazabilidad al pedido origen.

### 7.2 SEC_CUADRO se reutiliza entre TIPO_BIEN

**La PK real es `(SEC_CUADRO, TIPO_BIEN)`, no `SEC_CUADRO` solo.** Ejemplo: `SEC_CUADRO=131` existe como 131/B (bienes, valor 4.681,30, orden 119) y 131/S (servicios, valor 4.800, orden 132) — son dos cuadros distintos.

### 7.3 SIG_DEVENGADO está vacía en 2026

`SIG_DEVENGADO` = **0 filas** para SEC_EJEC=300687 año 2026. El devengado real vive en:
- **Bienes:** `SIG_MOVIM_ALMACEN` (entrada tipo I) — sin `ESTADO_DEVENG` poblado pero enlaza a la orden.
- **Servicios:** `SIG_MOVIM_CONFOR_SERVICIO.ESTADO_DEVENG='D'` — señal fina de cada pago.
- **Consolidado:** `SIG_EXP_SIGA.TIPO_FASE='D'` como bandera de expediente devengado.

**Importante para Fix #2:** el `SIG_TECHO_PRESUPUESTO.MNTO_ACUM_DEVGDO_SIGA=0` es coherente con esto — SIGA no consolida el devengado en su tabla resumen. Hay que ir a SIAF (`siaf.v_ejecucion_normalizada`) o agregar desde las tablas de detalle.

### 7.4 Estados del pedido son heterogéneos por TIPO_BIEN

| Escenario | ESTADO | ESTADO_PED | ESTADO_ATEND | ESTADO_CONFOR |
|---|---|---|---|---|
| Bien cerrado (compra completada) | 7 | 8 | 1 | 1 |
| Servicio finalizado (contrato ejecutado 100%) | **1** | **1** | **0** | **0** |
| Servicio en ejecución (con pagos parciales) | 1 | 1 | 0 | 0 |
| Pedido nuevo sin avance | 1 | 1 | 0 | 0 |

**Los estados del pedido son útiles solo para bienes.** Para servicios los estados del pedido son **indistinguibles entre finalizados y en tránsito** — SIGA no marca la finalización de servicios. Hay que consultar `SIG_MOVIM_CONFOR_SERVICIO` para saber cuántas conformidades tiene, y compararlo con la duración/monto esperado del contrato para deducir si está en ejecución o cerrado.

### 7.5 Ninguna FK apunta desde pedido hacia el ciclo

FKs reales del pedido (todas apuntan a catálogos, no al ciclo):

```
SIG_DETALLE_PEDIDOS  →  SIG_PEDIDOS                (FK_PEDIDOS_X_DETALLE_PEDIDOS)
SIG_DETALLE_PEDIDOS  →  CATALOGO_BIEN_SERV         (FK_CATALOGO_X_DETALLE_PEDIDOS)
SIG_DETALLE_PEDIDOS  →  SIG_CUADRO_MODIFICADO_DET  (degradada en 2026)
SIG_PEDIDOS          →  SIG_CENTRO_COSTO, SIG_PERSONAL, FUENTE_FINANC_EJEC, etc.
```

Confirmado en sesiones previas: **ningún SP, vista o trigger** de la BD une pedido con orden/certificación/expediente. El vínculo en 2026 vive parcialmente en `NRO_PECOSA` (bienes) y para el resto en la lógica de la aplicación cliente SIGA.

---

## 8. Estrategia recomendada para el pipeline

### 8.1 Regla de clasificación por segmento

```
SI TIPO_BIEN='B' Y TIPO_PEDIDO=1:
    SI NRO_PECOSA>0:
        → matchear vía SIG_MOVIM_ALMACEN (llave dura, 98,3%)
    SI NRO_PECOSA=0:
        → matchear vía composite heurístico
        → clasificar como "solicitado/con_orden" según resultado

SI TIPO_BIEN='B' Y TIPO_PEDIDO=2:
    → despacho interno: NO cuenta en pipeline pedido→orden
    → mostrar en vista separada de "consumo de almacén" o filtrar

SI TIPO_BIEN='S':
    → matchear vía composite heurístico (SEC_FUNC + item + valor)
    → clasificar por presencia de conformidades en SIG_MOVIM_CONFOR_SERVICIO:
        · 0 conformidades → "solicitado/con_orden"
        · >=1 conformidad → "en_ejecución" (SIGA no marca cierre — ver §10.4)
    → cierre real solo detectable con Fix #2: SUM(siaf.devengado)>=orden.TOTAL_FACT_SOLES
    → NO confiar en ESTADO_PED/ATEND/CONFOR del pedido
```

### 8.2 Variante mejorada del composite

Aprovechando que `SIG_ORDEN_ADQUISICION.SEC_CUADRO` está al 100%: matchear **item de cuadro ↔ item de pedido** en lugar de item de orden ↔ item de pedido. El cuadro preserva las cantidades originales del pedido origen (la orden las puede partir/consolidar), así que el match por `GRUPO+CLASE+FAMILIA+ITEM+VALOR_SOLES` en `SIG_DETALLE_BSERV_CUADRO` podría ser más limpio.

**Prueba pendiente en sesión 6.**

### 8.3 Limitaciones honestas

1. **~14% de pedidos activos no matchean por composite** (246 pedidos). Causas: precio unitario modificado entre pedido y orden, item bien recodificado, o pedido aún sin orden emitida.
2. **118 combinaciones con colisión** en composite (2,9%). Necesitan desempate por proximidad temporal, CC del pedido ↔ CC del cuadro, o "N candidatos → primero".
3. **NRO_PECOSA=0 no siempre significa "sin atender"**. En servicios siempre es 0, aunque haya conformidades pagadas.
4. **NRO_PECOSA como PK del pedido no es único cross-año**. Filtrar siempre por `ANO_EJE`.

---

## 9. Distribución de datos 2026 (contexto para dashboards)

### 9.1 SIG_PEDIDOS por estado

| ESTADO | Cuántos | Semántica |
|---:|---:|---|
| 0 | 22 | En proceso (creado, no aprobado) |
| 1 | 1.763 | Activo / aprobado |
| 7 | 573 | Cerrado |
| **Total** | **2.358** | |

### 9.2 SIG_DETALLE_PEDIDOS 2026

| TIPO_BIEN | Total items | Con NRO_PECOSA>0 | Con FECHA_CONFOR |
|---|---:|---:|---:|
| B | 7.345 | **3.261 (44%)** | 3.261 |
| S | 1.056 | 0 (todos con valor 0) | 0 |
| **Total** | **8.401** | **3.261** | **3.261** |

### 9.3 SIG_ORDEN_ADQUISICION por año

| ANO_EJE | Órdenes | ESTADO_SIAF='2' |
|---:|---:|---:|
| 2023 | 396 | 390 |
| 2024 | 3.269 | 3.211 |
| 2025 | 3.160 | 3.148 |
| 2026 | 1.473 | 1.469 |

### 9.4 SIG_TECHO_PRESUPUESTO 2026 admin

| Métrica | Valor |
|---|---:|
| Metas activas | 159 |
| Filas techo | 1.789 |
| PIA | 65.435.148,00 |
| PIM | 163.255.720,00 |
| Certificado | 15.787.701,61 |
| Comprometido | 12.880.410,78 |
| **Devengado SIGA** | **0,00** (bug — no sincronizado con SIAF) |
| Saldo disponible | 13.862.777,80 |

### 9.5 Kanban actual (código bugueado) vs proyectado

| Etapa | Actual | Con estrategia §8.1 (estimado) |
|---|---:|---:|
| solicitado | 1.325 | ~250 (los TIPO_PEDIDO=1 sin match) |
| despacho_interno (nuevo) | — | ~730 (los TIPO_PEDIDO=2) |
| con_orden | 0 | los TIPO_PEDIDO=1 con match parcial |
| conformidad | 438 | recalcular con señal cruzada |
| **devengado** | **0** | **~2.087** (1.516 activos matched + 571 cerrados) |
| cerrado | 573 | 573 |

---

## 10. Hallazgos independientes del bug del pipeline

### 10.1 Fix #2 — Devengado del WidgetSaldos

`SIG_TECHO_PRESUPUESTO.MNTO_ACUM_DEVGDO_SIGA = 0` para 2026, pero SIAF sí tiene devengado real (portal público lo muestra).

**Opciones:**
- **A:** mantener SIGA + banner "sin sync"
- **B (recomendada):** JOIN con `siaf.v_ejecucion_normalizada` (PostgreSQL) para el devengado, mantener SIGA para PIM/PIA/saldo
- **C:** banner temporal + investigar sync después

**Blocker pendiente:** localizar PostgreSQL en el entorno dev (`psql` no en PATH).

**Nota:** este fix es prerequisito para la detección de finalización de servicios (§10.4).

### 10.2 Fix #3 — Semántica ESTADO=0 en SIG_PEDIDOS

22 pedidos con `ESTADO=0` en 2026. Todos con `FECHA_PEDIDO` real, motivos reales, algunos con ítems, sin `FECHA_APROB`. Mover filtro de `ESTADO IN ('1','7')` a `ESTADO IN ('0','1','7')` y clasificarlos como "solicitado".

### 10.3 FECHA_APROB no se usa en esta muni

Todos los pedidos verificados (activos y cerrados) tienen `FECHA_APROB=NULL`. La aprobación real vive en `ESTADO=1`. No usar `FECHA_APROB` como criterio.

### 10.4 Detección de finalización de servicios

**Contexto operativo confirmado con usuario (2026-07-15):** el cumplimiento del servicio depende de los entregables acordados, y **todos los contratos normalmente se ejecutan al 100% del monto**.

**Señales disponibles y descartadas:**

| Campo | Fill rate 2026 | Utilidad |
|---|---:|---|
| `SIG_ORDEN_ADQUISICION.PLAZO_ENTREGA` | 0/841 servicios | Descartado |
| `SIG_ORDEN_ADQUISICION.FECHA_CANCEL` | 0/841 servicios | Descartado |
| `SIG_ORDEN_ADQUISICION.NRO_CONTRATO` | 0/841 servicios | Descartado |
| `SIG_ORDEN_ADQUISICION.TOTAL_FACT_SOLES` | 100% (841/841) | **Fiable — monto total del contrato** |
| `SIG_MOVIM_CONFOR_SERVICIO` | count por orden | Solo cuenta conformidades, no tiene monto |
| SIAF `devengado` vía `EXP_SIAF` | pendiente Fix #2 | **Fuente autoritativa del monto ejecutado** |

**Regla de clasificación adoptada:**

```
servicio_cerrado ⇔ SUM(siaf.devengado WHERE exp_siaf = orden.exp_siaf)
                   >= orden.TOTAL_FACT_SOLES
```

**Estados en el kanban (mientras Fix #2 esté pendiente):**

- **`en_ejecución`**: servicio con al menos 1 conformidad en `SIG_MOVIM_CONFOR_SERVICIO`. Etiqueta honesta "SIGA no reporta cierre".
- **`solicitado/con_orden`**: servicio sin conformidades aún.
- **`cerrado`**: no se puede clasificar hasta que tengamos SIAF operativo. **No usar umbrales de tiempo** — sin conocimiento operativo del funcional, cualquier umbral introduce falsos positivos (contratos con pausas administrativas se marcarían como cerrados incorrectamente).

**Fallback futuro opcional (si el usuario lo pide):** tabla en PostgreSQL (`sistema.servicios_cerrados_manual`) para override manual por el funcionario, útil solo para casos de rescisión parcial (que según el usuario son excepcionales).

---

## 11. Estructura del backend (para el fix)

**Archivos a modificar:**
- `backend/app/repositories/pipeline_repo.py` — `pipeline_kanban` (query principal del bug)
- `backend/app/repositories/saldos_repo.py` — `resumen_saldos`, `listar_saldos`, `metas_rezagadas` (para Fix #2)
- `backend/app/services/saldos_service.py` — orquestación
- `backend/app/schemas/saldos.py` — si cambia el shape del devengado
- `backend/app/routers/pipeline.py` — si cambian query strings del kanban

**No tocar:**
- Frontend del dashboard (T-44 etapa A cerrada)
- Endpoint `/interno/saldos/resumen` (funciona, solo devengado mal)
- Filtros por CC / año / semáforos / permisos

---

## 12. Entorno de exploración

**Comando base (PowerShell):**
```powershell
sqlcmd -S localhost -E -d SIGA_300687 -W -s "|" -Q "SELECT ..."
```

- `-E`: Windows Auth. En git-bash usar rutas Windows + PowerShell.
- `-h -1` incompatible con `-y 0`. `-W` incompatible con `-y`.
- Para SPs / triggers grandes: volcar con `-o archivo.sql` (sin `-W`).
- Volcados de sesiones anteriores en `backend/scripts/diagnostico_sesion3/` y `backend/scripts/diagnostico_sesion4/`.

**PostgreSQL:** aún no localizado. Buscar en `C:\Program Files\PostgreSQL\*\bin\psql.exe` o servicio Windows `postgresql*`.

---

## 13. Próximos pasos (sesión 6)

**Prioridad 1 — Implementar híbrido pecosa+composite en pipeline_repo.py:**
- Bienes TIPO_PEDIDO=1 con pecosa → JOIN con SIG_MOVIM_ALMACEN (llave dura).
- Bienes TIPO_PEDIDO=1 sin pecosa → composite.
- Bienes TIPO_PEDIDO=2 → separar en vista "despachos internos" o filtrar.
- Servicios → composite + conteo de SIG_MOVIM_CONFOR_SERVICIO.

**Prioridad 2 — Validar variante mejorada del composite (§8.2):**
- Matchear vía `SIG_DETALLE_BSERV_CUADRO` usando `SIG_ORDEN_ADQUISICION.SEC_CUADRO` (100%).
- Comparar match rate y unicidad contra la variante directa item-orden ↔ item-pedido.

**Prioridad 3 — Decisión con el usuario:**
- ¿Aceptar híbrido (llave dura para bienes + heurístico para servicios) con limitaciones conocidas?
- Manejo de los ~14% sin match: "solicitado" o cubo nuevo "en proceso/cotización".
- Manejo de las 118 colisiones: desempate automático o marcar "múltiples candidatos".
- ¿Separar TIPO_PEDIDO=2 (despachos) del pipeline principal?

**Prioridad 4 — Localizar PostgreSQL** para aplicar Fix #2 y habilitar la detección de servicios finalizados (§10.4). Bloquea la clasificación "cerrado" en servicios.

**Prioridad 5 — Preguntar al funcional:**
- Confirmar semántica de TIPO_PEDIDO (1=compra, 2=despacho).
- Qué pantalla del cliente SIGA usa para ver "en qué va" un pedido.
- Si se puede activar SQL profiler mientras usa el cliente → obtenemos las queries exactas del cliente.

---

*Documento reescrito en sesión 5 (2026-07-15) tras hallazgo del puente estructural `NRO_PECOSA` que sesiones 1-4 habían omitido. Reemplaza toda la información previa. Los volcados históricos siguen disponibles en `backend/scripts/diagnostico_sesion3/` y `backend/scripts/diagnostico_sesion4/`.*
