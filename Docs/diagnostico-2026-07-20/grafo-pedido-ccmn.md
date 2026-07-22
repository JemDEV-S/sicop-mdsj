# Grafo pedido ↔ CCMN — mapa de rutas exploradas

> **Fecha exploración:** 2026-07-20
> **Objetivo:** documentar TODOS los caminos posibles entre `SIG_PEDIDOS` y `SIG_PAAC_CONSOLIDADO` en la BD `SIGA_300687`, para no re-explorar y para elegir la mejor ruta al desambiguar CCMN.
> **Caso testigo:** pedido `232/S` (CC `01.03.07.04`, meta `sec_func=57`, item auxiliar administrativo, `VALOR_TOTAL=0`, `SEC_CUA_MOD_SAL=11553`) → tiene 3 CCMN candidatos (2266, 2281, 3532).

---

## Convenciones

- 🟢 = FK dura + poblada + útil (usable en producción)
- 🟡 = FK dura + poblada pero N:N o ambigua
- 🔴 = FK dura pero **columna clave no poblada** en esta muni (inútil)
- ⚫ = tabla vacía en 2026
- ⚪ = tabla existe pero no aplica al flujo pedido/CCMN

---

## Nodos del grafo (11 tablas centrales)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                        │
│                          [SIG_PEDIDOS]                                 │
│                          (cabecera, PK = ANO+SEC+TIPO_BIEN+NRO)        │
│                                │                                       │
│                                │ FK dura (1:N)                         │
│                                ▼                                       │
│                       [SIG_DETALLE_PEDIDOS]                            │
│                       (items del pedido)                               │
│                        │             │                                 │
│           SEC_CUA_MOD_SAL│  SEC_CUADRO+SEC_ITEM+ANNO_PROG              │
│                (N:1)     │             (1:1) FK dura                   │
│                          ▼             ▼                               │
│         [SIG_CUADRO_MODIFICADO_SALDO] [SIG_CUADRO_MODIFICADO_DET]      │
│         (bolsa presupuestal          (detalle del cuadro necesidad)    │
│          compartida)                                                    │
│                          ▲                                              │
│                          │ (mismo SEC_CUA_MOD_SAL)                     │
│                          │                                              │
│         ┌────────────────┴────────────────┐                            │
│         │  [SIG_CUADRO_MODIFICADO_CMN]    │                            │
│         │  (N filas por SEC_CUA_MOD_SAL —  │                            │
│         │   AQUÍ NACE LA AMBIGÜEDAD)      │                            │
│         └────────────────┬────────────────┘                            │
│                          │ NRO_CONSOLID (FK dura)                      │
│                          ▼                                              │
│                [SIG_PAAC_CONSOLIDADO]                                   │
│                (cabecera del CCMN — el "1 CCMN = 1 proceso")            │
│                          │                                              │
│               ┌──────────┼──────────┬────────────────┐                 │
│               ▼          ▼          ▼                ▼                 │
│         NRO_CERTIFICA  NRO_CONS_PAAC  NRO_ORDEN?  EXP_SIGA/SIAF        │
│         (77% pobl.)    (via cuadro)  (declarado)  (0% pobl.)           │
│               │          │                                              │
│               ▼          ▼                                              │
│      [SIG_CERTIFICACION]  [SIG_CUADRO_ADQUISICION]                     │
│               │              │                                          │
│               │              │ NRO_ORDEN (FK dura, 1:1)                │
│               │              ▼                                          │
│               │       [SIG_ORDEN_ADQUISICION]                          │
│               │              ▲                                          │
│               │ NRO_CERTIFICA (FK dura, 1:N)                            │
│               └──────────────┘                                          │
│                                                                          │
│  🟢 ATAJO CONFIRMADO:                                                    │
│    [SIG_CERTIFICACION_FASE] — puente NRO_CERTIFICA ↔ NRO_CONSOLID ↔     │
│                                NRO_ORDEN en la MISMA fila (2,996 filas   │
│                                pobladas en 2026 — todos los NRO_ORDEN    │
│                                válidos del año caen aquí)                │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Inventario detallado de aristas (todas verificadas contra BD)

### A · De `SIG_PEDIDOS` hacia abajo (única salida) 🟢

```
SIG_PEDIDOS ──[ANO+SEC+TIPO_BIEN+NRO]──▶ SIG_DETALLE_PEDIDOS
```

- **FK:** `FK_PEDIDOS_X_DETALLE_PEDIDOS`
- **Fill rate:** 100% — un pedido tiene N items.
- **Usado hoy:** sí (todo el repo depende de esto).

---

### B · De `SIG_DETALLE_PEDIDOS` a la cadena de programación

#### B1 · Vía `SEC_CUA_MOD_SAL` → `SIG_CUADRO_MODIFICADO_SALDO` 🟡

- **FK:** `FK_SIG_DET_PED_02`
- **Cardinalidad:** N pedidos comparten un mismo `SEC_CUA_MOD_SAL` (la "bolsa presupuestal" por partida).
- **Testigo 232:** `SEC_CUA_MOD_SAL=11553` (compartido con al menos otros 2 pedidos).
- **Utilidad:** solo confirma "hay línea presupuestal", **no** identifica CCMN.

#### B2 · Vía `SEC_CUADRO+SEC_ITEM+ANNO_PROG` → `SIG_CUADRO_MODIFICADO_DET` 🟢🟡

- **FK:** `FK_SIG_DET_PED_01`
- **Cardinalidad:** 1:1 con la línea del cuadro de necesidad.
- **Testigo 232:** `SEC_CUADRO=1, SEC_ITEM=61, ANNO_PROG=2026` → 1 fila con `SEC_FUNC=57, CLASIFICADOR='2.3.2.9.1.1', PRECIO_UNIT=1, MNTO_TOTAL=10785`.
- **Utilidad:** confirma la meta+clasificador del pedido, pero el `SEC_CUA_MOD_SAL` de aquí (`11553`) sigue siendo el mismo compartido.

#### B3 · Vía `NRO_ORDEN` declarado (columna `NRO_ORDEN` en detalle) 🔴

- **Fill rate 232:** `NULL` (el usuario no lo pone).
- **Fill rate global 2026:** bajo (~30% aprox., no verificado exhaustivo).
- **Utilidad:** aleatoria, no confiable.

#### B4 · Vía `NRO_PECOSA` → `SIG_MOVIM_ALMACEN.NRO_MOVIMTO` (solo bienes) 🟢

- **Fill rate 232:** N/A (es servicio, no bien).
- **Utilidad:** llave dura pero solo aplica a bienes con pecosa emitida (etapa muy tardía).

---

### C · De `SIG_CUADRO_MODIFICADO_SALDO` hacia `SIG_CUADRO_MODIFICADO_CMN` 🟡

- **FK:** `FK_SIG_CUA_MOD_CMN_01` (por `SEC_CUA_MOD_SAL`).
- **Cardinalidad:** **1:N** — un SALDO puede tener N CMN. **AQUÍ NACE LA AMBIGÜEDAD.**
- **Testigo 232:** `SEC_CUA_MOD_SAL=11553` → **3 CMN candidatos** (2266, 2281, 3532).

---

### D · De `SIG_CUADRO_MODIFICADO_CMN` hacia `SIG_PAAC_CONSOLIDADO` 🟢

- **FK:** por `NRO_CONSOLID + TIPO_CONSOLID`.
- **Cardinalidad:** 1:1.
- **Utilidad:** una vez que se sabe qué CMN es el correcto, se llega directo al CCMN.

---

### E · De `SIG_CUADRO_MODIFICADO_CMN` hacia `SIG_PAAC_CENTRO_COSTO` 🟢

- **FK:** `FK_SIG_CUA_MOD_CMN_02` (7 columnas).
- **Cardinalidad:** 1:1.
- **Utilidad importante:** `SIG_PAAC_CENTRO_COSTO` **tiene `CENTRO_COSTO` como columna**. Si el CCMN candidato apunta a un CC distinto al del pedido, se descarta. **Este es el filtro composite #3 propuesto en §3.2 del diagnóstico.**
- ⚠️ Fill rate columna `nro_pedido` en esta tabla: **0** (no ayuda como llave dura).

---

### F · De `SIG_PAAC_CONSOLIDADO` hacia adelante (múltiples salidas)

#### F1 · `NRO_CERTIFICA` (columna en la cabecera del CCMN) 🟢

- **Fill rate 2026:** 1,536 / 1,988 = **77%**.
- **Cardinalidad:** 1:1 (una certificación por CCMN una vez otorgada).
- **Utilidad:** directa. Los CCMN sin certificación son los que aún no llegaron a la etapa 8.

#### F2 · `EXP_SIGA` / `EXP_SIAF` (columnas en la cabecera del CCMN) 🔴

- **Fill rate 2026:** **0 / 1,988 = 0%** — ¡la muni no las puebla desde el CCMN!
- **Utilidad:** cero. Hay que llegar al expediente por otra vía.

---

### G · 🟢🟢🟢 EL ATAJO NUEVO — `SIG_CERTIFICACION_FASE`

**Descubierto en esta sesión.** Es el eslabón que NO estamos usando y resuelve la trazabilidad hacia adelante desde el CCMN.

- **Columnas clave en la misma fila:** `NRO_CERTIFICA + NRO_CONSOLID + NRO_ORDEN + TIPO_CONTRATO + NRO_CONTRATO`.
- **Fill rate 2026:** **2,996 filas**. Todos los `NRO_ORDEN` válidos del año aparecen aquí.
- **Cardinalidad:** 1:N por certificación (una certificación puede tener varias órdenes o fases), pero por `(NRO_CERTIFICA, NRO_CONSOLID)` es 1:N con las órdenes, filtrable.

**Testigo 232 — cadena confirmada:**

```
NRO_CERTIFICA  NRO_CONSOLID  NRO_ORDEN  VALOR_SOLES  FECHA_REG
     182          2266          132        4800.00   2026-02-16 16:17
     183          2281          155        1485.00   2026-02-18 11:30
    1423          3532          802        4500.00   2026-05-29 14:31
```

**Implicación:** una vez que discriminamos qué CCMN es el "propio" del pedido (por composite fecha+monto+CC), esta tabla nos da la orden 1:1 SIN ambigüedad.

---

### H · De `SIG_CUADRO_ADQUISICION` hacia `SIG_ORDEN_ADQUISICION` 🟢

- **Columna:** `SIG_CUADRO_ADQUISICION.NRO_ORDEN` (1:1).
- **Fill rate 2026:** 1,463 / 1,473 = **99%**.
- **Utilidad:** ruta alternativa a G (cuando la fase certificación no está registrada aún).

---

### I · De `SIG_ORDEN_ADQUISICION` hacia atrás 🟢

- **FK dura:** `FK_SOA_SC_01` → `SIG_CERTIFICACION` por `NRO_CERTIFICA` (1:N).
- **Columna:** `SIG_ORDEN_ADQUISICION.SEC_CUADRO` (apunta al cuadro de adquisición).
- **Utilidad:** validación cruzada — dado un candidato de orden, se puede verificar por qué certificación y qué cuadro pasó.

---

## Puentes teóricos que **NO existen** en esta BD

Verificados y descartados:

| Ruta teórica | En esta BD |
|---|---|
| Puente `SIG_CUADRO_NECESIDAD_DET.NRO_PEDIDO + NRO_CONSOLID` | ❌ 6,318 filas, **0 pobladas** con NRO_PEDIDO/NRO_CONSOLID |
| Puente `SIG_CUADRO_NECESIDAD_DET_PAAC` (16 cols, 100% puente) | ⚫ Existe estructura, **0 filas** en todos los años |
| Puente `SIG_DETALLE_PEDIDO_CUADRO` (100% puente) | ⚫ **Tabla vacía** |
| Puente `SIG_DETALLE_BSERV_CUADRO.nro_pedido` | ❌ 4,405 filas, **0 con nro_pedido** poblado |
| Puente `SIG_PAAC_CENTRO_COSTO.nro_pedido` | ❌ 16,011 filas, **0 pobladas** |
| Puente `SIG_PPR_CUADRO_NECESIDAD_DET` | ❌ 0 pobladas |
| Puente `SIG_TMP_CUADRO_NECESIDAD_DET` (temporal SIGA) | ⚫ Vacía |
| Puente `SIG_DETALLE_CUADRO_ANUAL` | ❌ 0 pobladas con puente |
| Puente `SIG_AUDITORIA.NRO_PEDIDO + NRO_CONSOLID` | ❌ 950 filas con NRO_PEDIDO, 0 con NRO_CONSOLID |
| Puente `SIG_SEGUIMIENTO.NRO_CONSOLID` | ❌ existe columna, todas NULL en 2026 |

**Conclusión estructural:** SIGA tiene 6 mecanismos distintos diseñados para persistir la trazabilidad pedido↔CCMN. La muni San Jerónimo **no usa ninguno**. Ninguna magia oculta va a resolver esto por FK dura hacia atrás desde el pedido.

---

## Esquemas paralelos descartados

- **`SI_*`** (SI_PEDIDO, SI_TRANS_PEDIDO, SI_ORDEN…) — interfase de exportación al SIGA-MEF nacional. Todas vacías.
- **`SGE_*`** (SGE_ADQUISICIONES, SGE_PAAC_MENSUAL…) — sistema de gestión externo/reportes. Todas vacías.
- **`TEMP_*` / `TMP_*`** — staging de carga inicial del backup. Todas vacías o con datos residuales sin puente.
- **`SIG_PPAAC_*`** (SIG_PPAAC_CONSOLIDADO, etc.) — "Preliminary PAAC"?. Todas vacías.

---

## Rutas viables con lo que tenemos

### Ruta 1 (actual, débil) 🟡

```
SIG_DETALLE_PEDIDOS.SEC_CUA_MOD_SAL
  → SIG_CUADRO_MODIFICADO_CMN [N candidatos]
    → MAX(...) → sobrestima
```

**Problema:** ambigüedad de N candidatos → sobre-marca etapas.

### Ruta 2 (propuesta §3.2 diagnóstico — composite estricto) 🟢

```
SIG_DETALLE_PEDIDOS
  → SIG_CUADRO_MODIFICADO_CMN [N candidatos]
    → filtrar con SIG_PAAC_CONSOLIDADO por:
       (a) FECHA_CONS >= pedido.FECHA_PEDIDO
       (b) VALOR_PLAN ≈ sum(pedido.VALOR_TOTAL)  [salta si VALOR_TOTAL=0]
    → filtrar con SIG_PAAC_CENTRO_COSTO por:
       (c) CENTRO_COSTO = pedido.CENTRO_COSTO
       (d) SEC_META = pedido.sec_func (via SIG_PAAC_METAS)
  → si queda 1 → confianza='alta'
  → si quedan >1 → fecha más cercana + confianza='baja'
```

### Ruta 3 (nueva, propuesta ahora) 🟢🟢

Una vez discriminado el CCMN con Ruta 2, usar **`SIG_CERTIFICACION_FASE`** para llegar 1:1 a la orden sin heurísticas de composite fuzzy:

```
CCMN elegido (NRO_CONSOLID)
  → SIG_CERTIFICACION_FASE por NRO_CONSOLID
    → NRO_CERTIFICA (certificación real del pedido)
    → NRO_ORDEN (orden real del pedido, si ya se emitió)
```

**Beneficio:** elimina la dependencia del composite `SEC_FUNC + CLASIFICADOR + VALOR_SOLES` que hoy trae falsos positivos cuando el pedido tiene `VALOR_TOTAL=0` (como el 232). La ruta se vuelve determinística.

### Ruta 4 (validación cruzada) 🟢

Para bienes con pecosa emitida, mantener `NRO_PECOSA → SIG_MOVIM_ALMACEN.NRO_MOVIMTO → NRO_ORDEN` como llave dura (ya usada).

---

## Filtros composite candidatos (para discriminar CCMN)

Verificados con testigo 232:

| Filtro | Efectividad esperada | Testigo 232 (candidatos 2266/2281/3532) |
|---|---|---|
| `PAAC.FECHA_CONS >= pedido.FECHA_PEDIDO (2026-02-05)` | Descarta CCMN anteriores | 2266✓ 2281✓ 3532✓ (los 3 pasan) |
| `PAAC.VALOR_PLAN ≈ SUM(pedido.VALOR_TOTAL)` | Ideal — pero falla si pedido=0 | ❌ pedido=0 → no discrimina |
| `PAAC_CENTRO_COSTO.CENTRO_COSTO = pedido.CENTRO_COSTO` | Muy fuerte | por verificar |
| `PAAC_METAS.SEC_META = pedido.sec_func` | Fuerte | por verificar |
| `PAAC.FECHA_CONS mínima (más cercana al pedido)` | Tiebreaker | 2266 (2026-02-11, 6 días después) |

**Nota crítica:** para el pedido 232, el mejor discriminador termina siendo la combinación **CENTRO_COSTO + fecha más cercana**, porque VALOR_PLAN no ayuda (pedido en 0). La ruta debe ser tolerante a `VALOR_TOTAL=0`.

---

## Métricas del ambiente (contexto)

- Pedidos activos 2026: 1,785 (ESTADO 0/1)
- Pedidos con match CCMN estructural (via SEC_CUA_MOD_SAL): 1,665 (87%)
- Promedio CCMN candidatos por pedido: **3.86** (máx 39)
- CCMN totales 2026: 1,988
- Certificaciones 2026: variable — solo 77% de CCMN tienen NRO_CERTIFICA registrado
- `SIG_CERTIFICACION_FASE` filas 2026: **2,996** (cubre todas las órdenes emitidas)

---

## Próximos pasos concretos

1. **Sesión de código A:** implementar Ruta 2 (composite estricto por CC + fecha) en `pipeline_repo._SQL_KANBAN` CTE `programacion`. Test contra el 232 → debe quedar solo CCMN 2266.

2. **Sesión de código B:** cambiar el match pedido→orden (`match_composite` CTE) para que en lugar de usar `SEC_FUNC+CLASIFICADOR+VALOR_SOLES` (frágil con VALOR_TOTAL=0), use **`SIG_CERTIFICACION_FASE`**: dado el CCMN discriminado en A, JOIN a `SIG_CERTIFICACION_FASE.NRO_CONSOLID` para obtener `NRO_ORDEN` directamente.

3. **Test regresión:** validar que el testigo 010/B (bien con pecosa) siga matcheando por la ruta dura `NRO_PECOSA` (no perder esa vía).

4. **Issue funcional al área de programación SIGA:** activar el módulo de Cuadro de Necesidad → SIG_CUADRO_NECESIDAD_DET_PAAC. Si un día se popula, se puede eliminar el composite entero.

---

## Comandos de reproducción

```bash
# Verificar CCMN candidatos por pedido
sqlcmd -S localhost -E -d SIGA_300687 -W -Q "
SELECT cmn.NRO_CONSOLID, pc.FECHA_CONS, pc.VALOR_PLAN, pc.NRO_CERTIFICA
FROM SIG_CUADRO_MODIFICADO_CMN cmn
INNER JOIN SIG_PAAC_CONSOLIDADO pc
  ON pc.SEC_EJEC=cmn.SEC_EJEC AND pc.ANO_EJE=cmn.ANNO_EJEC
 AND pc.NRO_CONSOLID=cmn.NRO_CONSOLID
WHERE cmn.SEC_CUA_MOD_SAL=11553 AND cmn.ANNO_EJEC=2026"

# Verificar puente CCMN → ORDEN via SIG_CERTIFICACION_FASE
sqlcmd -S localhost -E -d SIGA_300687 -W -Q "
SELECT NRO_CERTIFICA, NRO_CONSOLID, NRO_ORDEN, VALOR_SOLES
FROM SIG_CERTIFICACION_FASE
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND NRO_CONSOLID IN (2266, 2281, 3532)
ORDER BY NRO_CONSOLID"
```

---

## Cambios de aprendizaje sobre el diagnóstico previo

El `pipeline-y-presupuesto-consolidado.md` §3.2 propuso:
> "Aplicar composite estricto: fecha + monto + CC"

Con el mapeo completo del grafo, **agregar**:
> "Y una vez discriminado el CCMN, usar `SIG_CERTIFICACION_FASE` como llave dura hacia la orden (elimina el composite fuzzy pedido↔orden que hoy falla con pedidos VALOR_TOTAL=0)."

Esto es un **refinamiento**, no una contradicción. La Ruta 3 no reemplaza el composite del §3.2 — lo **complementa**: composite para desambiguar CCMN, FK para navegar CCMN→orden.

---

## Pipeline objetivo — las 16 etapas correctas

Este es el estado final que queremos que muestre el sistema, con la evidencia exacta que se debe cumplir en cada etapa, la tabla del grafo que la resuelve, y el problema conocido de la implementación actual.

Fuente canónica: [backend/app/schemas/pipeline.py](../../backend/app/schemas/pipeline.py) — no inventar etapas nuevas, no renombrar códigos.

### Macrofase 1 · Solicitud

#### [1] `pedido_registrado` 🟢

- **Qué debe cumplir:** existe fila en `SIG_PEDIDOS` con `ESTADO IN ('0','1','7')`.
- **Fecha de la etapa:** `SIG_PEDIDOS.FECHA_PEDIDO`.
- **Estado actual:** correcto.
- **Nota:** cae aquí siempre; es el fallback.

#### [2] `pedido_aprobado` 🟡

- **Qué debe cumplir:** el pedido pasó del estado 0 al 1 (aprobación formal).
- **Evidencia hoy:** `SIG_PEDIDOS.ESTADO='1'` + `FECHA_APROB IS NOT NULL`.
- **Problema:** el 100% de los 1,785 pedidos activos tiene `FECHA_APROB=NULL` (la muni solo la puebla al cerrar).
- **Fix (§3.1 diagnóstico):** usar `SIG_SEGUIMIENTO.FECHA_TRANSACCION` con `TIPO_TRANSACCION=2` como fuente primaria. Confirmado con 232: fila en SIG_SEGUIMIENTO con `TIPO_TRANSACCION=2, FECHA=2026-02-05 10:35:29`.
- **Fecha de la etapa (corregida):** `MAX(SIG_SEGUIMIENTO.FECHA_TRANSACCION WHERE TIPO_TRANSACCION=2)` → fallback `FECHA_APROB` → fallback `FECHA_PEDIDO`.

### Macrofase 2 · Programación

#### [3] `cuadro_necesidad` 🟢

- **Qué debe cumplir:** el item del pedido tiene un `SEC_CUA_MOD_SAL` en `SIG_DETALLE_PEDIDOS` (fue amarrado a una línea del cuadro modificado).
- **Evidencia:** `SIG_DETALLE_PEDIDOS.SEC_CUA_MOD_SAL IS NOT NULL`.
- **Estado actual:** correcto. Testigo 232 → `SEC_CUA_MOD_SAL=11553`. ✓
- **Sin ambigüedad:** cada línea de pedido tiene 1 SEC_CUA_MOD_SAL.

#### [4] `puente_paac` 🟡🔴

- **Qué debe cumplir:** el SEC_CUA_MOD_SAL del pedido tiene al menos un CCMN candidato **que sea el propio del pedido**.
- **Evidencia hoy:** existe cualquier fila en `SIG_CUADRO_MODIFICADO_CMN` con ese SEC_CUA_MOD_SAL.
- **Problema:** un `SEC_CUA_MOD_SAL` puede tener N CCMN candidatos (promedio 3.86, máx 39). Testigo 232 → 3 candidatos, solo uno le corresponde.
- **Fix objetivo:** aplicar composite estricto (Ruta 2 arriba) — solo marcar `tiene_puente_paac=1` si existe **al menos 1 CCMN que pase los filtros de fecha+CC+meta**.

#### [5] `ccmn_em_cvr` 🟡🔴

- **Qué debe cumplir:** existe el CCMN identificado en `SIG_PAAC_CONSOLIDADO` (cabecera del proceso de compra registrado en el PAAC).
- **Evidencia hoy:** JOIN con `SIG_PAAC_CONSOLIDADO.NRO_CONSOLID` — pero con la ambigüedad heredada de [4].
- **Fix objetivo:** una vez discriminado el CCMN correcto, `tiene_ccmn=1` es determinista. Guardar `nro_consolid_muestra` con el CCMN "propio" del pedido (no un `MIN(...)` arbitrario).

#### [6] `cotizacion` 🟡

- **Qué debe cumplir:** para el CCMN discriminado existe al menos una fila en `SIG_SOLICITUD_COTIZACION`.
- **Evidencia hoy:** cualquier `SIG_SOLICITUD_COTIZACION.NRO_CONSOLID` que caiga en algún CCMN candidato.
- **Fix objetivo:** filtrar solo por el CCMN discriminado.
- **Fill rate:** por verificar (algunos servicios omiten cotización si son adjudicación directa < 8 UIT).

#### [7] `cuadro_adquisicion` 🟢🟡

- **Qué debe cumplir:** existe `SIG_CUADRO_ADQUISICION` con `NRO_CONS_PAAC` = CCMN del pedido.
- **Evidencia:** FK 1:1 desde el CCMN → cuadro adquisición.
- **Fix objetivo:** con CCMN discriminado, esta etapa es determinista.
- **Testigo 232:** CCMN 2266 → CUADRO 131 (S/4800). ✓

### Macrofase 3 · Certificación

#### [8] `certificacion_ccp` 🟢🟡

- **Qué debe cumplir:** existe `SIG_CERTIFICACION` con `NRO_CERTIFICA` = certificación emitida para el CCMN.
- **Evidencia hoy (débil):** `SIG_PAAC_CONSOLIDADO.NRO_CERTIFICA IS NOT NULL` para algún CCMN candidato.
- **Fix objetivo (usar 🟢 Ruta 3):** JOIN a `SIG_CERTIFICACION_FASE` filtrado por `NRO_CONSOLID = CCMN discriminado`. Devuelve `NRO_CERTIFICA` real 1:1.
- **Fecha:** `SIG_CERTIFICACION.FECHA`.
- **Testigo 232:** CCMN 2266 → CERT 182 (2026-02-16). ✓

### Macrofase 4 · Contratación

#### [9] `orden_emitida` 🟢🔴

- **Qué debe cumplir:** existe `SIG_ORDEN_ADQUISICION` con la orden derivada de la certificación del pedido.
- **Evidencia hoy (frágil):** composite `SEC_FUNC + CLASIFICADOR + item + VALOR_SOLES`. Falla si `VALOR_TOTAL=0` (deja pasar todas las órdenes de la partida).
- **Fix objetivo (Ruta 3):** JOIN a `SIG_CERTIFICACION_FASE.NRO_ORDEN` filtrando por el `NRO_CONSOLID` discriminado. Elimina el composite fuzzy.
- **Testigo 232:** hoy matchea 3 órdenes (132, 155, 802) — con la Ruta 3 debe matchear **solo la 132**.
- **Fecha:** `SIG_ORDEN_ADQUISICION.FECHA_ORDEN`.

#### [10] `compromiso_siaf` 🟡

- **Qué debe cumplir:** la orden fue interfaseada al SIAF (fase Compromiso).
- **Evidencia:** `SIG_EXP_SIGA_DOCU.FECHA_INTERFASE IS NOT NULL` para el `EXP_SIGA` de la orden.
- **Ruta:** una vez identificada la orden (etapa 9), esta etapa es determinista.
- **Bug secundario en timeline:** hoy el `alcanzada` de esta etapa no cuadra con la fecha que se pinta (ver [pipeline_service.py:495](../../backend/app/services/pipeline_service.py#L495)). Revisar.

### Macrofase 5 · Ejecución

#### [11] `ejecucion` 🟢🟡

- **Qué debe cumplir:**
  - **Servicios (S):** existe al menos una conformidad en `SIG_MOVIM_CONFOR_SERVICIO` para la orden del pedido.
  - **Bienes (B):** existe una entrada al almacén (`SIG_MOVIM_ALMACEN` con `TIPO_MOVIMTO='I'`, `TIPO_TRANSAC=1`) por la orden del pedido.
- **Ruta:** determinista una vez que la orden está bien identificada (etapa 9).
- **Nota:** una conformidad marca "hay ejecución en curso", no necesariamente el cierre 100%.

#### [12] `recepcion_kardex` 🟢 (solo B)

- **Qué debe cumplir:** existe `SIG_MOVIM_ALMACEN` con `TIPO_MOVIMTO='R', TIPO_TRANSAC=1` para la orden.
- **Ruta:** determinista una vez identificada la orden.

#### [13] `pedido_interno` 🟡 (solo B)

- **Qué debe cumplir:** existe otro pedido `TIPO_PEDIDO=1` posterior con misma meta+CC que consume el bien.
- **Evidencia hoy:** composite meta+CC+fecha posterior.
- **Ruta:** aceptable por ahora, es una etapa opcional de bienes.

#### [14] `despacho_pecosa` 🟢 (solo B)

- **Qué debe cumplir:** existe `SIG_MOVIM_ALMACEN` con `TIPO_MOVIMTO='S', TIPO_TRANSAC=1` + `NRO_PECOSA > 0` en `SIG_DETALLE_PEDIDOS`.
- **Ruta:** FK dura vía `NRO_PECOSA → NRO_MOVIMTO`. Correcta hoy.

#### [15] `devengado` 🔴

- **Qué debe cumplir:**
  - **Servicios:** la sumatoria de conformidades cubre el 100% del `TOTAL_FACT_SOLES` de la orden (ver §3.3 diagnóstico — "cierre operativo").
  - **Bienes:** existe expediente SIAF con `TIPO_OPERACION='DV'`.
- **Problema:** hoy `MNTO_ACUM_DEVGDO_SIGA=0` para todo 2026 (columna no poblada). Para servicios no se calcula el cierre operativo. Para bienes se usa el proxy EXP fase DV.
- **Fix pendiente (§3.3 + §3.4):** cruzar con `siaf.ejecucion_presupuestal` (Postgres) usando `sec_func + clasificador + exp_siaf` para obtener el devengado real por orden.

### Macrofase 6 · Cierre

#### [16] `cierre` 🟢

- **Qué debe cumplir:** el pedido fue cerrado en SIGA.
- **Evidencia:** `SIG_PEDIDOS.ESTADO='7'` **o** existe `SIG_SEGUIMIENTO` con `TIPO_TRANSACCION=19`.
- **Fecha:** `SIG_PEDIDOS.FECHA_ATENC` o `SIG_SEGUIMIENTO.FECHA_TRANSACCION` (t=19).
- **Nota:** solo 573 pedidos de 2026 están en ESTADO=7 — el resto que "parece cerrado operativamente" cae bajo [15] devengado con flag `cierre_operativo` (nuevo, §3.3).

---

## Resumen de fixes necesarios por etapa

| Etapa | Estado | Fuente correcta | Prioridad |
|---|---|---|---|
| [1] pedido_registrado | 🟢 OK | `SIG_PEDIDOS.FECHA_PEDIDO` | — |
| [2] pedido_aprobado | 🟡 fecha mal | `SIG_SEGUIMIENTO t=2` (§3.1) | **A1** |
| [3] cuadro_necesidad | 🟢 OK | `SIG_DETALLE_PEDIDOS.SEC_CUA_MOD_SAL` | — |
| [4] puente_paac | 🔴 ambiguo | composite CCMN estricto (§3.2) | **A2** |
| [5] ccmn_em_cvr | 🔴 ambiguo | composite CCMN estricto (§3.2) | **A2** |
| [6] cotizacion | 🟡 ambiguo | filtrar por CCMN discriminado | **A2** |
| [7] cuadro_adquisicion | 🟡 ambiguo | filtrar por CCMN discriminado | **A2** |
| [8] certificacion_ccp | 🟡 ambiguo | `SIG_CERTIFICACION_FASE` (Ruta 3) | **A3** |
| [9] orden_emitida | 🔴 falsos+ | `SIG_CERTIFICACION_FASE.NRO_ORDEN` (Ruta 3) | **A3** |
| [10] compromiso_siaf | 🟡 timeline bug | JOIN determinista + fix flag | **A3** |
| [11] ejecucion | 🟢 OK si orden es correcta | — | (depende de A3) |
| [12] recepcion_kardex | 🟢 OK | — | — |
| [13] pedido_interno | 🟡 heurística | aceptable | — |
| [14] despacho_pecosa | 🟢 OK | — | — |
| [15] devengado | 🔴 no calculado | SIAF via Postgres (§3.4) | **B** |
| [16] cierre | 🟢 OK | — | — |

**Iteración A del diagnóstico se descompone en 3 sub-tareas:**
- **A1:** fix fechas (etapa [2]).
- **A2:** composite estricto CCMN (etapas [4]–[7]).
- **A3:** Ruta 3 con `SIG_CERTIFICACION_FASE` (etapas [8]–[10]).

Con A1+A2+A3 el pipeline de servicios queda 100% correcto. B es una tarea aparte para el devengado real.
