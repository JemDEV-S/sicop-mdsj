# Refactorización del pipeline pedido → CCMN · Decisiones y plan

> **Fecha:** 2026-07-22 · **BD:** `SIGA_300687` (SQL Server 2022) · **SEC_EJEC:** 300687 · **Año:** 2026
>
> **Reemplaza** a `estrategia-match-pedido-ccmn.md`. Ese documento dejaba pistas abiertas.
> Esta sesión las cerró (unas con hallazgo, otras con descarte) y tomó las decisiones de diseño.
>
> **Propósito:** contexto completo para ejecutar la refactorización en otras sesiones.
> Todo número aquí fue medido contra la BD. Lo no medido está marcado ❓.

---

## §0 · Estado: qué está decidido y qué falta

La exploración **terminó**. No quedan pistas estructurales por probar — se agotaron.
Lo que sigue es implementación, con el diseño ya acordado con el usuario.

| | |
|---|---|
| ✅ Decidido | Cascada de confianza, 4 estados de UI, resolución manual N:M, orden por fecha |
| ⏳ Por implementar | Los 9 puntos de §7 |
| ❌ Cerrado | `SIG_SEGUIMIENTO` (§3.2), `SEC_RESUMEN` (§3.1), y todo lo de §2 |

---

## §1 · El hecho que cierra la búsqueda de FK

**Confirmado con un funcionario de logística que ejecuta el proceso (2026-07-21):**

> Toma los datos del pedido, **crea** un CCMN con esos datos, y **no relaciona** ambos en SIGA.

Definitivo. No es captura deficiente: **el paso de vincular no existe en el proceso**.
Ninguna exploración de esquema recupera un dato que nunca se generó.

Verificación exhaustiva que lo respalda:

| Qué se barrió | Resultado |
|---|---|
| Las 937 tablas por columna `NRO_PEDIDO` | 31 la tienen; las no probadas antes están **vacías** |
| Las 588 FK del esquema | Solo **4** apuntan a `SIG_PEDIDOS`/`SIG_DETALLE_PEDIDOS` |
| Los 209 stored procedures | Ruta oficial hallada en `SP_NIVELA_MONTO_RESERVA_PEDIDO` |
| `SIG_DETALLE_PEDIDOS.NRO_CUADRO` (ruta oficial) | **0 de 8,401** pobladas |
| `SIG_PAAC_CONSOLIDADO.SEC_CUADRO_INI` | **2 de 1,988** |
| `SIG_SEGUIMIENTO.NRO_CONSOLID` | **0** en todos los tipos de transacción |

> **No re-explorar nada de lo anterior. Está cerrado.**

---

## §2 · Métodos descartados — con evidencia. NO reintentar

| Método | Medición | Veredicto |
|---|---|---|
| **Ítem (grupo+clase+familia+item)** | **0** de 641 servicios ambiguos resueltos · 0 de 100 bienes | ❌ nunca discrimina |
| **Monto solo** | Bienes **29/671 (4%)** · Servicios 470 únicos pero **403 ambiguos** | ❌ |
| **Ítem + monto** | Resuelve 205/641 (32%) **pero 33 pierden el CCMN correcto** | ❌ peligroso |
| **`CENTRO_COSTO`** | Los 3 candidatos del testigo lo comparten | ❌ |
| **`FECHA_CONS` más cercana** | Acierta en el testigo por 2 días de margen | ❌ frágil |
| **`SEC_RESUMEN` como llave de línea** | 3/3 candidatos del testigo comparten valor (§3.1) | ❌ no discrimina |
| **`SIG_SEGUIMIENTO` tipos 4/8/9** | `NRO_PEDIDO` no contiene pedidos (§3.2) | ❌ campo reutilizado |

### 2.1 La razón de fondo: la ambigüedad vive DENTRO de la bolsa

El CCMN es una **copia** del pedido → comparten ítem, meta, clasificador y centro de costo
**por construcción**. Son justo los campos que los agrupan en la misma bolsa `SEC_CUA_MOD_SAL`.

Testigo 232/S — los 3 candidatos son idénticos salvo el monto:

| | 2266 | 2281 | 3532 |
|---|---|---|---|
| Ítem | 07-11-0043-1207 | idéntico | idéntico |
| `SEC_FUNC` / `FUENTE` / `CLASIFICADOR` | 57 / 09 / 2.3.2.9.1.1 | idéntico | idéntico |
| `CENTRO_COSTO` | 01.03.07.04 | idéntico | idéntico |
| `VALOR` | **4800** | 1485 | 4500 |

**Medido esta sesión — la N:M no está entre CCMN y pedido, está dentro de la bolsa:**

```
CCMN por nº de PEDIDOS distintos      CCMN por nº de LÍNEAS
          1     2-3    4+   peor              1     2-3    4+
Bienes   595     86     5      4    │  B    236    202   321
Servic.  338    240   392     39    │  S    955     28     6
```

Lectura: en **bienes** el CCMN multi-línea es un pedido con muchos ítems (87% un solo pedido) —
la cardinalidad N:1 se sostiene. En **servicios** solo 35% tiene un pedido; **392 CCMN tocan 4+**.

> Ese 35% es exactamente el 35.5% de `unico` de §4.1. **Es el mismo número visto del otro lado.**
> Los 632 CCMN de servicios multi-pedido *son* los que generan los servicios ambiguos.
> No son dos problemas: es uno contado dos veces.

---

## §3 · Pistas cerradas esta sesión

### 3.1 `SEC_RESUMEN` / `SEC_CONSOLID` ❌ descartado

`SIG_CUADRO_MODIFICADO_CMN` tiene una grilla: `SEC_RESUMEN` numera la bolsa dentro del CCMN,
`SEC_CONSOLID` la línea dentro de la bolsa. Parecía una llave de línea.

Medición: el par `(NRO_CONSOLID, SEC_RESUMEN)` apunta a una sola bolsa en 97.1% (S) / 84.8% (B).

**Pero el testigo lo mata:** los 3 candidatos del 232/S tienen `SEC_RESUMEN = 1` los tres,
todos apuntando a la bolsa 11553, que contiene 3 pedidos.

> La pregunta medida ("¿el par apunta a una bolsa?") era la equivocada. La correcta
> ("¿apunta a un pedido?") falla, porque `_CMN` **no baja a nivel de pedido**. Ninguna
> columna de esa tabla puede resolver la ambigüedad intra-bolsa.

### 3.2 `SIG_SEGUIMIENTO` tipos 4/8/9/20 ❌ descartado

Era la pista con más potencial: 3,842 filas, `NRO_PEDIDO` poblado al 100%, podía dar
etapas 4–7 sin pasar por el CCMN.

**`NRO_PEDIDO` está poblado, pero no con pedidos.** En los tipos 8 y 9:

```
TIPO_TRANSACCION=9 → TIPO_PEDIDO=9 · NRO_PEDIDO = NRO_ORIGEN = 1,2,3,5,6...
TIPO_TRANSACCION=8 → TIPO_PEDIDO=8 · NRO_PEDIDO = NRO_ORIGEN = 1,2,3,4,5...
```

Es el correlativo de otro documento. `NRO_ORIGEN` es denso y propio de cada tipo
(tipo 4: 1,795 valores distintos entre 5 y 1835). Cruce contra `SIG_PEDIDOS`: **62 de 779 (B)
y 15 de 1,016 (S)** — coincidencias numéricas espurias.

Los únicos tipos que **sí** referencian pedidos reales:

| Tipo | Filas | Qué es | Medición |
|---|---|---|---|
| 1 | 576 B | registro/aprobación | `d_ped=0`, coincide con `FECHA_APROB` en 565/576 |
| 2 | 734 B / 1048 S | registro del pedido | `d_ped=0` exacto |
| 19 | 573 B | cierre | coincide con `ESTADO='7'` |
| 20 | 574 B | ambiguo — parcial con aprob. (274) y atenc. (256) | ❓ sin identificar |

Todas son etapas **ya resueltas**. La tabla no aporta nada nuevo.

> Corrección al doc anterior: *"tiene `NRO_PEDIDO` poblado al 100%"* es cierto pero **engañoso**.
> Trampa típica de SIGA (§8).

### 3.3 `SIG_CERTIFICACION_DOC` ✅ **la ganancia de la sesión**

Mejor de lo que el doc anterior suponía: **no hace falta pasar por `SIG_CERTIFICACION_FASE`**.
La tabla trae `NRO_CONSOLID` propio.

| Medición | S | B |
|---|---|---|
| Filas 2026 | 876 | 659 |
| `NRO_CONSOLID` poblado | **876 (100%)** | **659 (100%)** |
| Con texto en `REQUERIMIENTO` | 605 | 442 |
| **Concuerda** con candidatos estructurales | **553 (97.5%)** | **418 (98.8%)** |
| Conflicto | 14 | 5 |
| Pedido sin bolsa | 3 | 8 |
| Sin parsear | 34 | 11 |

**Lo importante — cuánto desambigua de verdad:**

| | Concuerda | **Ambiguo resuelto** | Redundante (ya era único) |
|---|---|---|---|
| Servicios | 553 | **365** | 188 |
| Bienes | 418 | 63 | 355 |

**365 servicios** donde el pedido tenía varios candidatos y la certificación eligió uno.
Coherente con que bienes ya estaba resuelto.

> ⚠️ **Pendiente de validar:** esos 365 son la desambiguación que la certificación *afirma*.
> No está probado que sea *correcta* (misma pregunta que hundió a `SEC_RESUMEN`).
> **Prueba pendiente:** confrontar certificación × orden donde ambas hablen del mismo pedido.

Regex validado (tolera todos los formatos observados):

```python
RE_PED = re.compile(r'PEDIDO\s*(?:DE\s*(?:SERVICIO|COMPRA)\s*)?N?[^0-9A-Z]{0,4}(\d{1,6})', re.I)
RE_CONTRATO = re.compile(r'SEGUN\s+CONTRATO', re.I)   # descartar: no es pedido
```

Formatos reales: `PEDIDO 76` · `PEDIDO 0225` · `PEDIDO DE COMPRA N°000026-2026` ·
`PEDIDO DE SERVICIO N°228-2026 ACTUALIZADO` · `PEDIOD 0041` (typo) ·
`INFORME 275-2026-MDSJ` (no parsea, correcto).

Los 19 conflictos muestran cercanía sospechosa (`ped=458→2688` vs cands `[2817]`;
`ped=459→2187` vs `[2689]`). ❓ **No concluido** — puede ser typo o desfase sistemático.
Revisar caso por caso; con 19 no alcanza para una teoría.

---

## §4 · La cascada de confianza

**Principio:** nunca elegir un ganador por parecido. Resolver en cascada y **declarar el nivel**.
El modelo lleva un campo `confianza` desde el día uno.

| Nivel | Regla | Prioridad |
|---|---|---|
| `unico` | Un solo candidato estructural vía `SEC_CUA_MOD_SAL` | 1 |
| `declarado` | CCMN del texto de la **orden** ∈ candidatos | 2 |
| `declarado_cert` | CCMN de **certificación** ∈ candidatos | 3 ← **nuevo** |
| `resuelto_manual` | Asociado por un funcionario (§5) | 4 |
| `conflicto` | Una fuente declara un CCMN ∉ candidatos | visible |
| `ambiguo` | N candidatos, sin declaración | visible |
| `sin_ccmn` | 0 candidatos — el pedido aún no se programó | correcto |

`declarado` manda sobre `declarado_cert`: la orden es posterior en el proceso y estuvo bajo
más escrutinio. Cuando ambas hablan y difieren → `conflicto`, se registra.

`resuelto_manual` es **su propio nivel**, nunca se fusiona con `declarado`: es juicio humano,
no verificación de dos fuentes. Mezclarlos perdería la auditabilidad del origen.

### 4.1 Cobertura antes de esta sesión

| Nivel | Bienes (671) | Servicios (994) |
|---|---|---|
| `unico` | 571 (85.1%) | 353 (35.5%) |
| `declarado` | 68 (10.1%) | 519 (52.2%) |
| `conflicto` | 2 (0.3%) | 8 (0.8%) |
| `ambiguo` | 30 (4.5%) | 114 (11.5%) |
| **Resuelto confiable** | **639 (95.2%)** | **872 (87.7%)** |

❓ **No medido:** el aporte **neto** de `declarado_cert` sobre los 114 ambiguos.
Los 365 desambiguados solapan con lo que ya resolvía `declarado` — el neto es **> 0**
pero probablemente mucho menor que 365. **Medir al implementar la cascada.**

---

## §5 · Resolución manual · referencial, no vinculante

Decisión del usuario (2026-07-22): el sistema **funciona solo**. La asociación manual es
**opcional, referencial y modificable** — una preferencia encima de la cascada, no un reemplazo.

Consecuencias de diseño:

- El sistema **nunca pide** asociar. Muestra `◔ avance del grupo` y sigue.
- Si se borran todas las resoluciones manuales, el sistema sigue igual — solo pierde
  precisión en los `ambiguo`.
- La UI **siempre muestra qué dice la cascada automática** junto a la resolución manual.

**Cardinalidad: N:M en ambas direcciones** (confirmado por el usuario):
- Un CCMN puede consolidar varios pedidos (§2.1, medido).
- Un pedido puede consolidar varios CCMN (confirmado por el usuario).
- El mismo CCMN en dos pedidos distintos **es válido** — no se advierte.

```sql
CREATE TABLE sistema.resolucion_pedido_ccmn (
  id                uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  ano_eje           smallint     NOT NULL,
  sec_ejec          integer      NOT NULL DEFAULT 300687,
  tipo_bien         char(1)      NOT NULL,
  tipo_pedido       varchar(2)   NOT NULL,   -- llave real, ver §6
  nro_pedido        integer      NOT NULL,
  nro_consolid      integer      NOT NULL,   -- una fila POR CCMN asociado
  sec_cua_mod_sal   integer      NOT NULL,   -- bolsa, para auditar contexto
  nota              text,
  usuario_id        uuid         NOT NULL REFERENCES auth.usuarios(id),
  creado_en         timestamptz  NOT NULL DEFAULT now(),
  revocado_en       timestamptz,
  revocado_por      uuid         REFERENCES auth.usuarios(id),
  CONSTRAINT uq_par_activo UNIQUE NULLS NOT DISTINCT
    (ano_eje, sec_ejec, tipo_bien, tipo_pedido, nro_pedido, nro_consolid, revocado_en)
);
```

- **Nunca se borra, se revoca.** `revocado_en` preserva historial; el `UNIQUE` con
  `NULLS NOT DISTINCT` deja un solo par activo pero muchos revocados.
- Escribe en **PostgreSQL**, jamás en SIGA (regla 2).
- Va también a `logs.auditoria` (regla 8).

❓ **Pendiente de decidir:** quién puede asociar. Propuesta: Operativo sobre sus CC,
Decisor sobre su jerarquía (regla 6). Sin confirmar.

### 5.1 Riesgo conocido: obsolescencia silenciosa

Si SIGA agrega un CCMN a la bolsa después de una resolución manual, la resolución sigue
ahí sin avisar. **Propuesta:** el job de sync compara los candidatos actuales contra los
del momento de resolver y marca para revisión si cambiaron.

> ⚠️ **Tentación a resistir:** cuando haya cientos de resoluciones manuales, será atractivo
> derivar una regla automática ("si el monto coincide exacto, asociar solo"). Eso reintroduce
> el fallo silencioso de §2 — el monto **pierde el CCMN correcto en 33 casos**. Si se intenta,
> que sea con nivel de confianza propio y midiendo cuántas veces contradice a un humano.

---

## §6 · Hallazgo colateral · la llave real de `SIG_PEDIDOS`

**Medido:** `SIG_PEDIDOS` tiene 2,358 filas en 2026.

| Llave | Valores distintos | ¿Única? |
|---|---|---|
| `NRO_PEDIDO` | 1,176 | ❌ |
| `TIPO_BIEN + NRO_PEDIDO` | 1,912 | ❌ **446 colisiones** |
| **`TIPO_BIEN + TIPO_PEDIDO + NRO_PEDIDO`** | **2,358** | ✅ |

Los duplicados son todos tipo B con n=2: mismo número, distinto `TIPO_PEDIDO`.

**Impacto en el código actual:** `pipeline_repo.py` arrastra `TIPO_PEDIDO` en los CTE
(líneas 58, 75) y lo expone al frontend, **pero los 11 `GROUP BY` no lo incluyen**:

```
líneas 119, 137, 157, 184, 198, 229, 300, 315, 334, 350, 366
GROUP BY d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN   ← falta TIPO_PEDIDO
```

**El dato ya está en el query.** El fix es agregar la columna a los `GROUP BY` y a los
joins de agregación — no reescribir el pipeline.

---

## §7 · El bug a corregir · `MAX(CASE...)`

[`backend/app/repositories/pipeline_repo.py:97-119`](../../backend/app/repositories/pipeline_repo.py#L97-L119)

```sql
LEFT JOIN SIG_CUADRO_MODIFICADO_CMN cmn
    ON cmn.SEC_CUA_MOD_SAL = d.SEC_CUA_MOD_SAL   -- trae N filas
...
MAX(CASE WHEN pc.NRO_CONSOLID IS NOT NULL THEN 1 ELSE 0 END) AS tiene_ccmn
GROUP BY d.ANO_EJE, d.SEC_EJEC, d.NRO_PEDIDO, d.TIPO_BIEN
```

El `MAX(CASE...)` responde *"¿alguno de los N candidatos llegó a esta etapa?"*.
Los otros candidatos son de **otros pedidos** → el pedido 232 se muestra "certificado"
porque el CCMN 2281 (del pedido 278) se certificó.

**Falla en silencio.** Muestra un verde creíble. Es el patrón repetido en todos los CTE de etapa.

> `MIN(pc.NRO_CONSOLID) AS nro_consolid_muestra` — el nombre es honesto: es una muestra,
> no la respuesta. No usarlo como si lo fuera.

### 7.1 La otra ruta, que sí es confiable

`pipeline_repo.py` tiene una segunda ruta que **no pasa por el CCMN** (etapas 9–14):

| Vía | Llave | Cobertura |
|---|---|---|
| Pecosa (bienes) | `NRO_PECOSA = NRO_MOVIMTO` — dura | **573/862 bienes (66%)** |
| Composite | ítem + `SEC_FUNC` + clasificador + monto | resto · **0 servicios por pecosa** |

⚠️ Ninguna es FK declarada — son joins del código. Si SIGA cambia cómo llena
`NRO_PECOSA`, se rompe sin error.

---

## §8 · Diseño de UI · 4 estados, 16 etapas siempre visibles

**Requisito del usuario:** mantener las 16 etapas y 6 macrofases visibles siempre.
Lo que cambia entre flujos es el **estado** de cada etapa, nunca su presencia.

| | Estado | Significado |
|---|---|---|
| ✅ | `directo` | Alcanzada por **este** pedido. Dato duro. |
| ◐ | `via_ccmn` | Vía CCMN identificado por fuente declarativa. Fecha aproximada (`~`). |
| ◔ | `grupo` | **Avance del grupo.** Alguno de los candidatos llegó; no se sabe si por este pedido. |
| ◑ | `manual` | Vía CCMN asociado manualmente. Muestra quién y cuándo. |
| ⬜ | `sin_dato` | No alcanzada o sin dato. |

> ⚠️ **El `◔` es donde se juega la honestidad del sistema.** Hoy esos casos se ven ✅ y son
> falsos. Si el ícono no se distingue con claridad, no arreglamos nada — solo movemos la
> mentira a un símbolo más bonito. **Color distinto (ámbar, no verde)** + panel de advertencia
> imposible de no ver.

### 8.1 Cobertura por etapa tras la refactorización

| # | Etapa | Macrofase | Resolución |
|---|---|---|---|
| 1 | `pedido_registrado` | 1 Solicitud | ✅ FK dura |
| 2 | `pedido_aprobado` | 1 Solicitud | ✅ `SIG_SEGUIMIENTO` t=2 |
| 3 | `cuadro_necesidad` | 2 Programación | ✅ FK dura |
| 4 | `puente_paac` | 2 Programación | ✅◐◔◑ según nivel |
| 5 | `ccmn_em_cvr` | 2 Programación | ✅◐◔◑ según nivel |
| 6 | `cotizacion` | 2 Programación | ✅◐◔◑ según nivel |
| 7 | `cuadro_adquisicion` | 2 Programación | ✅◐◔◑ según nivel |
| 8 | `certificacion_ccp` | 3 Certificación | ✅ **`SIG_CERTIFICACION_DOC`** (§3.3) |
| 9 | `orden_emitida` | 4 Contratación | ✅ `declarado` |
| 10 | `compromiso_siaf` | 4 Contratación | ✅ vía orden |
| 11 | `ejecucion` | 5 Ejecución | ✅ vía orden |
| 12 | `recepcion_kardex` | 5 Ejecución | ✅ vía orden |
| 13 | `pedido_interno` | 5 Ejecución | ❓ heurística |
| 14 | `despacho_pecosa` | 5 Ejecución | ✅ FK dura |
| 15 | `devengado` | 5 Ejecución | ❌ SIAF/Postgres |
| 16 | `cierre` | 6 Cierre | ✅ FK dura |

**Etapas 4–7 con múltiples CCMN asociados:** se calculan sobre el conjunto — alcanzada si
**cualquiera** lo alcanzó, fecha = la **más temprana**.

### 8.2 Vista de bolsa

Orden **de más reciente a más antiguo** en ambas listas (pedidos por `FECHA_PEDIDO`,
CCMN por `FECHA_CONS`). Empates → desempatar por `NRO_CONSOLID` desc, para que el orden
sea **estable entre recargas**.

```
┌─ Bolsa 11553 · 3 pedidos · 3 CCMN candidatos ──────────────────┐
│ Ítem 07-11-0043-1207 · Meta 57 · CC 01.03.07.04                │
│                                                                │
│ PEDIDOS EN ESTA BOLSA              ⌄ más reciente primero      │
│  ▸ 1005/S  4,500   12/02/2026                       ambiguo    │
│  ▸  278/S  1,485   07/02/2026                       declarado  │
│  ▸  232/S  4,800   05/02/2026   ← estás aquí        ambiguo    │
│                                                                │
│ CCMN CANDIDATOS                    ⌄ más reciente primero      │
│  ▸ 3532   4,500   cons. 20/02/2026   sin certificar            │
│  ▸ 2281   1,485   cons. 18/02/2026   CCP 190 · OC 145          │
│  ▸ 2266   4,800 ⓘ cons. 18/02/2026   CCP 182 · OC 132          │
│              └─ monto coincide con lo solicitado por 232/S     │
│                                                                │
│ ⓘ SIGA no registra la correspondencia. Si la conoces,          │
│   puedes declararla (opcional).   [ Asociar CCMN a 232/S ]     │
└────────────────────────────────────────────────────────────────┘
```

> ⚠️ **El monto se muestra, NO se ordena ni se sugiere por él.** Marcar coincidencia exacta
> es ayuda visual; ordenar por proximidad de monto o fecha sería una recomendación disfrazada,
> y ambos métodos están descartados en §2 por perder el CCMN correcto.
> **El orden es cronológico y neutro.**

En el **timeline del pipeline** el orden se mantiene **ascendente** (etapa 1 arriba,
16 abajo): ahí el orden es el proceso, no la novedad.

---

## §9 · Plan de implementación

| # | Qué | Dónde | Notas |
|---|---|---|---|
| 1 | Corregir llave a `TIPO_BIEN+TIPO_PEDIDO+NRO_PEDIDO` | `pipeline_repo.py` 11 `GROUP BY` | §6 · el dato ya está en el query |
| 2 | Reemplazar `MAX(CASE...)` por cascada con `confianza` | `pipeline_repo.py:97-119` + CTE de etapa | §7 · patrón repetido |
| 3 | Integrar `declarado_cert` a la cascada | `pipeline_service.py` | §3.3 · **medir aporte neto** |
| 4 | Migración `sistema.resolucion_pedido_ccmn` | Postgres | §5 · N:M |
| 5 | Endpoints: ver bolsa · asociar · revocar | `routers/pipeline.py` | + `logs.auditoria` |
| 6 | 4 estados con color distinto | `features/pipeline/` | §8 · ámbar ≠ verde |
| 7 | Vista de bolsa con orden y monto | `features/pipeline/` | §8.2 |
| 8 | Panel de trazabilidad con cascada automática visible | `features/pipeline/` | §5 |
| 9 | Job: detectar resoluciones obsoletas | sync | §5.1 |

**Orden sugerido:** 1 → 2 → 3 → 4 → 5 → 6/7/8 → 9.
Los puntos 1 y 2 son correcciones de bug: sin ellos, lo demás se construye sobre datos falsos.

### 9.1 Advertencia sobre las métricas

**Corregir el `MAX(CASE...)` va a hacer BAJAR los números visibles.** Hoy el pipeline reporta
cobertura que no tiene. Es una corrección, no una regresión — pero el dashboard se verá peor
antes de que `declarado_cert` lo levante. **Avisar antes de desplegar.**

---

## §10 · Caso testigo · pedido 232/S

Único caso recorrido de punta a punta. **Test de regresión obligatorio.**

```
SIG_PEDIDOS          NRO_PEDIDO=000232 · TIPO_BIEN=S · ESTADO=1
                     CENTRO_COSTO=01.03.07.04 · SEC_FUNC=57 · FECHA=2026-02-05
SIG_DETALLE_PEDIDOS  SEC_ITEM=61 · SEC_CUA_MOD_SAL=11553 · NRO_CUADRO=0
                     CANT_SOLICITADA=4800 · PRECIO_UNIT=1 · ítem 07-11-0043-1207
  → 3 candidatos: 2266 · 2281 · 3532   (los 3 con SEC_RESUMEN=1)
  → bolsa 11553 compartida con pedidos 278 y 1005
  → respuesta correcta: CCMN 2266 → CERT 182 → ORDEN 132
```

Confirmado por dos fuentes independientes: el texto de la orden 132
(`PEDIDO DE SERVICIO N° 00232`) y `VALOR_PLAN=4800` = `CANT_SOLICITADA=4800`.

> ⚠️ El testigo **no aparece** en `SIG_CERTIFICACION_DOC`. Con la cascada eso no es
> bloqueante: es una fuente más en el orden de prioridad, no la única.

**Validar 20–30 pedidos caso por caso** antes de dar por buena la refactorización.
Las métricas agregadas ya demostraron ser engañosas al menos dos veces
(el "3.86 candidatos" inflado, y el 97.1% de `SEC_RESUMEN` que medía la pregunta equivocada).

---

## §11 · Conexión y trampas de sqlcmd

```bash
sqlcmd -S localhost -E -d SIGA_300687 -W -h -1 -s"|" -Q "SET NOCOUNT ON; <QUERY>"
```
`-E` Windows Auth (obligatorio) · `-W` recorta espacios · `-h -1` sin cabeceras · `-s"|"` separador

| Síntoma | Solución |
|---|---|
| `data type text is invalid for argument 1 of left function` | `CAST(col AS varchar(2000))` |
| Tildes como `?` | Cosmético; usar `LIKE '%PEDIDO%'` sin tildes |
| **`-E` y `-y 0` son mutuamente excluyentes** | Redirigir con `> archivo.txt` del shell, no `-o` |
| `Cannot perform an aggregate on ... a subquery` | Mover la subconsulta a un CTE |
| `Conversion failed ... '01-2026-MDSJ/C' to int` | `TRY_CAST`, no `CAST` — `SIG_SEGUIMIENTO` mezcla formatos |

**Nunca asumir nombres de columna** — SIGA es inconsistente:
`NRO_CONSOLID`/`NRO_CONS_PAAC` · `NRO_PEDIDO`/`nro_pedido` · `ANO_EJE`/`ANNO_EJEC`/`ANNO_PROG`

> ⚠️ `SIG_CUADRO_MODIFICADO_CMN` usa **`ANNO_EJEC`**, no `ANO_EJE`. Falla ruidosamente — pero
> `SIG_DETALLE_PEDIDOS` y `SIG_CUADRO_MODIFICADO_DET` tienen **dos** columnas de año con
> conteos distintos (5,122 vs 8,401): ahí la elección equivocada **falla en silencio**.

```sql
SELECT c.name, ty.name FROM sys.columns c
JOIN sys.types ty ON ty.user_type_id=c.user_type_id
WHERE c.object_id=OBJECT_ID('<TABLA>') ORDER BY c.column_id;
```

---

## §12 · Universo 2026

| Métrica | Valor |
|---|---|
| Pedidos `ESTADO IN ('0','1','7')` | 2,358 (1,048 S · 1,310 B) |
| Pedidos con detalle y bolsa | 1,771 (730 B · 1,041 S) |
| CCMN distintos | 1,748 (6,431 filas en `_CMN`) |
| Órdenes de adquisición | 1,473 |
| Órdenes con texto parseado | 1,402 (96%) |
| `SIG_CERTIFICACION_DOC` | 1,535 (876 S · 659 B) · 1,047 con texto |
| `SIG_CERTIFICACION_FASE` | 2,996 |
| `SIG_SEGUIMIENTO` | 6,828 |

---

## §13 · Lo que queda abierto

| # | Qué | Estado |
|---|---|---|
| 1 | Confrontar certificación × orden — validar los 365 (§3.3) | ❓ prueba diseñada, no corrida |
| 2 | Aporte **neto** de `declarado_cert` sobre los 114 ambiguos (§4.1) | ❓ medir al implementar |
| 3 | Los 19 conflictos: ¿typo o desfase sistemático? (§3.3) | ❓ revisar caso por caso |
| 4 | `SIG_SEGUIMIENTO` tipo 20 — qué evento es (§3.2) | ❓ menor |
| 5 | Patrón `CCMN = 2000 + CVR` (§13.1) | ❓ **nunca verificado** |
| 6 | Quién puede asociar manualmente (§5) | ❓ decisión de producto |

### 13.1 La única pista estructural sin probar

Observado en textos de órdenes, **nunca verificado**:

```
CVR 0002 → CCMN 02003      CVR 00061 → CCMN 02061
CVR 00013 → CCMN 02013     CVR 00042 → CCMN 02042
```

Si el CVR es alcanzable estructuralmente desde el pedido, daría un puente para etapas 4–7
sin depender de texto. **Primer paso:** encontrar dónde vive el CVR
(`SIG_PAAC_CONSOLIDADO.NRO_EST_MDO`?) y verificar en población completa.

> ⚠️ Son **4 observaciones**. Un offset numérico es exactamente lo que se sostiene en muestra
> y se rompe en silencio a escala (cambio de año, reinicio de serie, segundo bloque de CVR).
> **Si no verifica cerca del 100%, entra con nivel de confianza propio o no entra.**

---

## §14 · Reglas del proyecto aplicables

1. `SEC_EJEC = 300687` en **toda** query SIGA/SIAF.
2. **Solo lectura** sobre SIGA. Toda escritura va a PostgreSQL.
3. Devengado → **de SIAF/Postgres**, no de SIGA (`SIG_DEVENGADO`: 0 filas en 2026;
   `MNTO_ACUM_DEVGDO_SIGA` en 0).
4. Llave cruce SIAF↔SIGA: `ANO_EJE + SEC_EJEC + SEC_FUNC` (+ `EXP_SIAF` secundaria).
5. Maestros SIGA → leer de `ref.*`, no consultar SIGA en cada request.
6. Umbrales en `sistema.umbrales_*` — no hardcodear.
7. Auditoría en `logs.auditoria` para la resolución manual (§5).

---

**Regla que no se negocia:** subir cobertura **nunca** a costa de métodos que fallan en
silencio. Preferible 87.7% honesto que 97% inventado. Todo match lleva su nivel de confianza,
y `ambiguo` se muestra como tal en la UI.
