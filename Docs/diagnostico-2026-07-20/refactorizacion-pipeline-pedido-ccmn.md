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
| ✅ Implementado | **Los 9 puntos** de §9 (`119f776`, `62d7454`, + §9.3 – §9.8) |
| ⏳ Por implementar | — (plan completo) |
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

> ✅ **VALIDADO (punto 3, 2026-07-22).** La prueba se corrió: donde certificación y orden
> hablan del mismo pedido, **coinciden en 865 de 874 (99.0%)**. La certificación no solo
> *afirma* — queda *corroborada* por una fuente independiente. Es exactamente la evidencia
> que `SEC_RESUMEN` no pudo dar (§3.1). Detalle de las 9 discrepancias en §9.3.

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

✅ **MEDIDO (punto 3, 2026-07-22):** el aporte **neto** de `declarado_cert` es **38 pedidos**
(24 S · 14 B) — no 365. De los 794 ambiguos estructurales, `declarado` (orden) resuelve 614;
la certificación aporta 38 que la orden no cubre; quedan 142 ambiguos. En **403** ambas
fuentes declaran (de ahí el solapamiento). La sospecha del doc era correcta: el neto es
**>0 pero mucho menor** que la cifra bruta. Ver §9.3.

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
| ~~1~~ | ✅ Corregir llave a `TIPO_BIEN+TIPO_PEDIDO+NRO_PEDIDO` | `pipeline_repo.py` | hecho · `119f776` · §9.2 |
| ~~2~~ | ✅ Reemplazar `MAX(CASE...)` por cascada con `confianza` | `schemas/` + `pipeline_service.py` | hecho · `62d7454` · §9.2 |
| ~~3~~ | ✅ Alimentar `declarado` y `declarado_cert` desde el repo | `pipeline_repo.py` | hecho · §9.3 · neto medido = 38 |
| ~~4~~ | ✅ Migración `sistema.resolucion_pedido_ccmn` | Postgres | hecho · §9.4 · `b7c1d2e3f4a5` |
| ~~5~~ | ✅ Endpoints: ver bolsa · asociar · revocar | `routers/pipeline.py` | hecho · §9.5 · + `logs.auditoria` |
| ~~6~~ | ✅ 5 estados con color distinto | `features/pipeline/` | hecho · §9.6 · ámbar ≠ verde |
| ~~7~~ | ✅ Vista de bolsa con orden y monto | `features/pipeline/` | hecho · §9.7 |
| ~~8~~ | ✅ Panel de trazabilidad con cascada automática visible | `features/pipeline/` | hecho · §9.7 |
| ~~9~~ | ✅ Job: detectar resoluciones obsoletas | sync | hecho · §9.8 · `c8d2e3f4a5b6` |

**✅ PLAN COMPLETO.** Los 9 puntos implementados y verificados contra BD.
Los puntos 1 y 2 eran correcciones de bug; el 3 hizo rendir la cascada (ya distingue los
7 niveles, no solo `unico`/`ambiguo`/`sin_ccmn`).

> ✅ **Frontend migrado (punto 6, §9.6).** [`Timeline.tsx`](../../frontend/src/components/Timeline.tsx)
> y [`features/pipeline/types.ts`](../../frontend/src/features/pipeline/types.ts) ya usan los
> 5 `EstadoEtapa`. El `◔ grupo` se pinta en ámbar con etiqueta «avance del grupo» y un aviso
> visible que lista los CCMN candidatos.

### 9.1 Advertencia sobre las métricas — ⚠️ CORREGIDA tras medir

Este documento anticipaba que corregir el `MAX(CASE...)` haría **bajar** los números
visibles de forma notoria. **Medido: no ocurre.** Solo **20 pedidos de 2,358** cambian de
etapa. Ver §9.2 para el porqué. La caída es marginal, no visible en el dashboard.

### 9.2 Lo implementado · sesión 2026-07-22

**Punto 1 — llave de pedido** · commit `119f776`

Corregidos los 11 `GROUP BY`, 1 `PARTITION BY` (en `orden_enriquecida`) y los **9 joins de
`agrup`** — este último era el crítico: sin él la corrección no surtía efecto.
Verificado contra BD: **2,358 filas → 2,358 llaves únicas** (antes 1,912). Las 446
colisiones de §6 quedan resueltas.

Se agregó `n_candidatos_ccmn` (`COUNT(DISTINCT cmn.NRO_CONSOLID)` por bolsa) al CTE
`programacion`, que es lo que alimenta la cascada.

**Punto 2 — cascada de confianza** · commit `62d7454`

Contrato en [`app/schemas/pipeline.py`](../../backend/app/schemas/pipeline.py) — es lo que
el frontend debe consumir:

```python
NivelConfianza = Literal["unico","declarado","declarado_cert",
                         "resuelto_manual","conflicto","ambiguo","sin_ccmn"]
EstadoEtapa    = Literal["directo","via_ccmn","grupo","manual","sin_dato"]
CONFIANZA_A_ESTADO: dict[str,str]     # nivel -> estado de UI
ESTADOS_ALCANZADOS: frozenset[str]    # {directo, via_ccmn, manual} — `grupo` NO
```

Lógica en [`app/services/pipeline_service.py`](../../backend/app/services/pipeline_service.py):
`confianza_match(fila)` y `estado_etapa_programacion(fila)`. Las etapas 4–7 en
`_etapa_maxima()` ahora requieren `prog_atribuible`.

13 tests en [`tests/services/test_pipeline_confianza.py`](../../backend/tests/services/test_pipeline_confianza.py),
incluido el testigo 232/S. Verde.

**Medición de la cascada (2026, universo 2,358):**

| Nivel | Pedidos |
|---|---|
| `unico` | 1,301 |
| `ambiguo` | 794 |
| `sin_ccmn` | 263 |

`declarado` / `declarado_cert` salen en 0 porque **el repo aún no les pasa los datos**
(punto 3). Los campos que la cascada espera y nadie llena todavía:
`ccmn_declarado_orden`, `ccmn_declarado_cert`, `ccmn_candidatos`, `ccmn_manual`.

**Por qué solo 20 pedidos cambian de etapa** — de los 794 ambiguos, **774 ya están en
etapas 8+**, que se resuelven por vías que **no pasan por el CCMN** (orden vía
pecosa/composite, certificación por su propia tabla). El `MAX(CASE...)` solo hacía daño en
los pedidos detenidos *dentro* de programación. El bug era real; su alcance, más estrecho
de lo que §7 suponía.

**Fallo de test preexistente:** `tests/test_sync_invierte.py::test_leer_todo_consolida_por_codigo`
falla desde antes de esta sesión (verificado con `git stash`). No relacionado. 8 skips en
`test_permisos.py` por falta de CCs en `ref.centros_costo` — ruido de entorno.

### 9.3 Punto 3 · `declarado` y `declarado_cert` · sesión 2026-07-22

**Hallazgo que simplificó la implementación:** la orden llega al CCMN por **ruta estructural**,
no por texto. `SIG_ORDEN_ADQUISICION.SEC_CUADRO → SIG_CUADRO_ADQUISICION.NRO_CONS_PAAC`
está poblado en **las 1,473 órdenes de 2026 (100%)**, y coincide con la ruta alterna vía
`NRO_CERTIFICA → SIG_CERTIFICACION_DOC.NRO_CONSOLID`. El texto solo aporta el **número de
pedido**; el CCMN sale de la cadena dura. Verificado en el testigo: orden 132 → CCMN 2266.

Ambas fuentes emiten `(tipo_bien, ccmn, texto)` y el parseo del pedido se hace en **Python**
(`parsear_nro_pedido`, regex de §3.3), no en T-SQL: es testeable y legible.

**Regla de elección** (`_elegir_declarado`): si varios CCMN declaran el mismo pedido y más de
uno está entre los candidatos, se devuelve `None` — **no desambigua**. Elegir uno sería el
"ganador por parecido" que §2 descarta. Un declarado único fuera de los candidatos **sí** se
devuelve, para que la cascada lo marque `conflicto` en vez de silenciarlo.

**Cascada medida contra BD (2026, universo 2,358):**

| Nivel | Antes (punto 2) | **Ahora** |
|---|---|---|
| `unico` | 1,301 | 1,301 |
| `declarado` | 0 | **590** |
| `declarado_cert` | 0 | **42** |
| `conflicto` | 0 | **4** |
| `ambiguo` | 794 | **158** |
| `sin_ccmn` | 263 | 263 |

| Cobertura sobre los que tienen bolsa | Medido |
|---|---|
| Bienes | **1,051 / 1,101 (95.5%)** |
| Servicios | **882 / 994 (88.7%)** |

Consistente con lo que §4.1 anticipaba (95.2% / 87.7%) — la diferencia es que ahora los
niveles se emiten de verdad. **Total de filas intacto: 2,358** (los joins nuevos no explotan).

**Las 9 discrepancias certificación × orden — ❓ parcialmente explicadas.** Dos pares están
**intercambiados** entre pedidos adyacentes:

```
ped 848/S: orden=3165 cert=3164   │  ped 901/S: orden=3373 cert=3374
ped 849/S: orden=3164 cert=3165   │  ped 916/S: orden=3374 cert=3373
```

Es transposición al transcribir dos pedidos correlativos, **no un desfase sistemático**
(descarta la teoría que §3.3 dejaba abierta para los 19 conflictos). Las otras 5 son saltos
grandes (`2689` vs `2187`) sin patrón visible con n=5. La cascada las resuelve a favor de
`declarado` por prioridad; solo 4 llegan a `conflicto`.

**Contrato nuevo en `PedidoCard`** — lo que el frontend consumirá en el punto 6:
`n_candidatos_ccmn`, `confianza_ccmn`, `confianza_ccmn_label`, `estado_programacion`,
`ccmn_atribuido`. Los campos de trabajo (`ccmn_candidatos` y los tres declarados) se
consumen en el service y **no salen al API**.

10 tests nuevos en [`tests/repositories/test_declaraciones_ccmn.py`](../../backend/tests/repositories/test_declaraciones_ccmn.py)
(formatos reales de §3.3 + reglas de elección). Los 13 de la cascada siguen verdes,
testigo incluido. Suite: 70 passed, 1 failed (`test_sync_invierte`, preexistente), 8 skips.

### 9.4 Punto 4 · `sistema.resolucion_pedido_ccmn` · sesión 2026-07-22

Migración **`b7c1d2e3f4a5`** (`alembic upgrade head` aplicado y revertido/reaplicado OK).
Schema según §5, con dos añadidos sobre el borrado del doc:

- `CHECK (tipo_bien IN ('B','S'))`.
- `CHECK ((revocado_en IS NULL) = (revocado_por IS NULL))` — revocar exige fecha **y** autor:
  una revocación sin autor no es auditable, y un autor sin fecha deja la fila en limbo.

**Constraints verificadas contra PostgreSQL 16**, no asumidas — 10 casos, todos en
transacciones revertidas (tabla queda en 0 filas):

| Caso | Resultado |
|---|---|
| N:M — mismo pedido, dos CCMN | ✅ permitido |
| N:M — mismo CCMN en dos pedidos (válido §5) | ✅ permitido |
| Llave §6 — mismo `nro_pedido`, distinto `tipo_pedido` | ✅ permitido |
| Duplicado **activo** del mismo par | ❌ rechazado por `uq_par_activo` |
| Un activo + un revocado del mismo par | ✅ permitido |
| Dos revocados del mismo par | ✅ permitido |
| `tipo_bien='X'` · revocación a medias (2 casos) | ❌ rechazados por los CHECK |

> El `NULLS NOT DISTINCT` es lo que hace que dos filas **activas** colisionen. Sin él
> `NULL != NULL` y el `UNIQUE` no impediría duplicados activos — fallaría en silencio.

**Repo:** [`app/repositories/resolucion_ccmn_repo.py`](../../backend/app/repositories/resolucion_ccmn_repo.py)
— `resoluciones_activas` (mapping pedido→CCMN para el pipeline), `resoluciones_de_pedido`
(con autoría e historial, para el panel del punto 8), `crear_resolucion`, `revocar_resolucion`.

`crear_resolucion` es **idempotente** (`ON CONFLICT ON CONSTRAINT uq_par_activo DO NOTHING`
+ relectura): asociar dos veces lo mismo es inocuo, no un error que deba interrumpir al
funcionario. `revocar_resolucion` devuelve `False` si ya estaba revocada — nunca borra.

**Inyección en el pipeline:** `_aplicar_resoluciones_manuales` en el service, no en el repo
del pipeline — el pedido vive en SIGA y la asociación en Postgres (regla 2). Si esa consulta
falla, se **loguea y se continúa** con la cascada automática: la resolución manual es
referencial (§5), no puede tumbar el pipeline.

**Verificado end-to-end contra ambas BD** (transacción revertida, 0 filas persistidas):

```
pedido 926/B · 2 candidatos · ambiguo/grupo
  → resolución manual  → resuelto_manual / manual · ccmn_atribuido=99001
  → revocar            → ambiguo   (vuelve al estado previo)
  crear idempotente: mismo id · revocar dos veces: False
```

9 tests nuevos en [`tests/repositories/test_resolucion_ccmn_repo.py`](../../backend/tests/repositories/test_resolucion_ccmn_repo.py),
incluido el de degradación (si Postgres cae, el pipeline sigue con la cascada).
Suite: **79 passed**, 1 failed (`test_sync_invierte`, preexistente), 8 skips.

❓ **Sigue abierto:** quién puede asociar (§13 ítem 6). El repo no impone rol — esa
decisión va en los endpoints del punto 5.

### 9.5 Punto 5 · endpoints de bolsa y resolución manual · sesión 2026-07-22

| Método | Ruta | Quién |
|---|---|---|
| `GET` | `…/pedidos/{nro}/{tipo_bien}/{tipo_pedido}/bolsa` | cualquiera con alcance de CC |
| `GET` | `…/pedidos/{nro}/{tipo_bien}/{tipo_pedido}/resoluciones` | ídem (`?incluir_revocadas`) |
| `POST` | `…/pedidos/{nro}/{tipo_bien}/resoluciones` | Operativo · Decisor · Admin |
| `DELETE` | `…/pedidos/resoluciones/{id}` | ídem |

**✅ §13 ítem 6 CERRADO** (decidido con el usuario 2026-07-22): asocian **Operativo** sobre
sus CC, **Decisor** sobre su jerarquía y **Admin** sin filtro — exactamente el alcance que
RN-04 ya les da para *ver* el pedido. **Revocar sigue la misma regla y NO exige ser el autor:**
una asociación equivocada no debe quedar congelada porque su autor rotó o está de licencia;
la autoría queda en `revocado_por`. Ver ≠ asociar: la lectura no exige rol.

**Validación que evita inventar datos:** el `POST` rechaza con **422** un `nro_consolid` que
no esté entre los candidatos de la bolsa del pedido, y devuelve la lista de candidatos
válidos en el mensaje. Asociar un CCMN de fuera no sería resolver, sería fabricar.

La auditoría guarda `candidatos_al_momento` — es lo que permitirá al job del punto 9
detectar la obsolescencia silenciosa de §5.1 (SIGA agrega un CCMN a la bolsa después de
resolver) comparando contra los candidatos actuales.

#### ⚠️ Trampa de datos encontrada al implementar la vista de bolsa

`SIG_DETALLE_PEDIDOS.VALOR_TOTAL` viene en **0.00 en servicios**. Verificado en los 3 pedidos
de la bolsa 11553:

```
NRO_PEDIDO  CANT_SOLICITADA  PRECIO_UNIT  VALOR_TOTAL
000232          4800.00         1.00         0.00
000278          1485.00         1.00         0.00
001005          4500.00         1.00         0.00
```

El monto real es `CANT_SOLICITADA * PRECIO_UNIT` — coherente con §10, que registra el testigo
como `CANT_SOLICITADA=4800 · PRECIO_UNIT=1`. Usar `VALOR_TOTAL` a secas habría mostrado
**toda la bolsa en S/ 0**: otro fallo silencioso de los de §8. El repo hace fallback y la
bolsa 11553 ya reproduce el mockup de §8.2 (4,500 / 1,485 / 4,800).

> El monto se muestra pero **no ordena** (§8.2). El orden es `FECHA` desc con desempate por
> número desc — cronológico y neutro.

**Verificado contra BD**, bolsa 11553 del testigo:

```
pedidos:    1005 (4,500) · 278 (1,485) · 232 (4,800)   ← más reciente primero
candidatos: 3532 (4,500) → OC 802 · 2281 (1,485) → OC 155 · 2266 (4,800) → OC 132
```

17 tests en [`tests/test_resolucion_ccmn_endpoints.py`](../../backend/tests/test_resolucion_ccmn_endpoints.py):
roles autorizados/denegados, alcance de CC, candidato inválido, 404/409, auditoría de alta y
revocación, y el marcado `asociado_manual` en la vista de bolsa.
Suite: **96 passed**, 1 failed (`test_sync_invierte`, preexistente), 8 skips.

### 9.6 Punto 6 · los 5 estados en la UI · sesión 2026-07-22

**Hallazgo al empezar:** el timeline del *detalle* nunca se había migrado. `construir_timeline`
emitía `alcanzada: boolean` calculado aparte de la cascada — el bug de §7 seguía vivo ahí
aunque el kanban ya estuviera corregido. Migrar solo el frontend habría pintado colores sobre
un dato que el backend no emitía.

**Backend primero.** `construir_timeline` ahora marca las etapas 4–7 con `via_ccmn=True` y les
asigna el estado desde la cascada; el resto son `directo` (evidencia propia del pedido).
`obtener_pedido` devuelve los campos de la cascada (`n_candidatos_ccmn`, `ccmn_candidatos`,
declarados) y el router inyecta la resolución manual desde Postgres.

`alcanzada` se mantiene por compatibilidad pero ahora **excluye `grupo`** — así los consumidores
que no migraron (el contador del recorrido, la fecha de etapa actual) heredan la corrección.

**Verificado sobre HTTP** (pedido 926/B, 2 candidatos):

```
confianza: ambiguo · estado_programacion: grupo · candidatos: [2179, 2681]
  [3] Cuadro necesidad      directo   alcanzada=True
  [4] Puente pedido<->PAAC  grupo     alcanzada=False
  [7] Cuadro adquisicion    grupo     alcanzada=False
  [8] Certificacion (CCP)   directo   alcanzada=True    ← tabla propia, no pasa por CCMN
```

Testigo 232/S: `declarado` → etapas 4–7 en `via_ccmn` con fecha marcada «aprox.», no `directo`.
**131 pedidos** tienen avance de programación con nivel `ambiguo`: son los que hasta hoy se
veían con el verde falso.

#### Presentación — el estado nunca se comunica solo por color

El sistema de diseño exige que el color no sea el único portador de estado, y eso coincide con
lo que §8 pedía. Cada estado lleva **ícono propio + etiqueta en palabras**:

| Estado | Ícono | Etiqueta visible | Color |
|---|---|---|---|
| `directo` | `CheckCircle2` relleno | *(sin etiqueta: no hay salvedad)* | verde `secondary` |
| `via_ccmn` | `CircleDot` | «fecha aproximada» + `aprox.` en la fecha | azul `primary` |
| `manual` | `CircleDot` | «asociado manualmente» | azul `primary` |
| `grupo` | `CircleDashed` | **«avance del grupo»** | **ámbar `semaforo-alerta`** |
| `sin_dato` | `Circle` | «pendiente» | gris `muted` |

El ámbar es el amarillo institucional (`--semaforo-alerta`, el token de *aviso*), nunca el verde.
Verificado que las clases se generan en el CSS compilado.

**El aviso va visible, no en un tooltip.** Cuando hay etapas en `grupo`, el recorrido muestra un
bloque ámbar que explica en lenguaje llano por qué, y lista los CCMN candidatos. El sistema de
diseño advierte que el usuario objetivo no descubre tooltips — y §8 avisa que si el ícono no se
distingue con claridad «solo movimos la mentira a un símbolo más bonito».

Se agregó al bloque «Pedido» la fila **Cuadro de necesidades**, que muestra el CCMN atribuido y
su nivel de confianza — siempre lo que dice la cascada automática, también cuando hay resolución
manual (§5).

6 tests nuevos de estados del timeline (`grupo` no cuenta como alcanzada, `directo` en etapas de
evidencia propia, `via_ccmn`/`manual`, y que una etapa sin avance nunca hereda el estado de la
cascada). Suite: **102 passed**, 1 failed (`test_sync_invierte`, preexistente), 8 skips.
`tsc` limpio en los archivos tocados; los errores de `BarraEjecucion.tsx` son **preexistentes**
(verificado con `git stash`).

### 9.7 Puntos 7 y 8 · rediseño del detalle · sesión 2026-07-22

Vista de bolsa integrada en el detalle del pedido (no página aparte), asociación por
**selección en ambos extremos**, y el recorrido con los identificadores de cada etapa.

**Decisiones tomadas con el usuario:**
- Asociar = seleccionar un pedido y un CCMN, luego confirmar. Se descartó drag-and-drop: sin
  descubrimiento, sin teclado, y choca con el sistema de diseño del proyecto.
- La bolsa vive **dentro** del detalle, plegada bajo el recorrido — es el contexto que explica
  las etapas en ámbar.
- Cada etapa muestra **su documento y número, copiable** (CCP 182, OC 132…). El número se copia
  solo, sin la etiqueta, porque es lo que se pega en el buscador de SIGA.

Cada CCMN candidato muestra además **su propio recorrido** (`flujo`): cuadro → estudio de
mercado → cuadro de adquisición → certificación → orden, con los números de cada paso. Es lo
que permite comparar candidatos entre sí sin que el sistema sugiera un ganador.

#### ⚠️ Bug encontrado al ver la pantalla renderizada

La captura delató que «Orden emitida» mostraba **las 3 órdenes de la bolsa** (132, 155, 802) en
el pedido 232, y que los ítems decían **S/ 0.00**. Ambos síntomas tenían la misma causa:

`SIG_DETALLE_PEDIDOS.VALOR_TOTAL` está en 0 en el **100% de los servicios (1,056/1,056)** y el
**55% de los bienes (4,066/7,345)**. El match composite tiene un escape
`(d.valor_soles = 0 OR ROUND(op.VALOR_SOLES,2) = ROUND(d.valor_soles,2))` que, con el valor en
0, **acepta cualquier monto** — así cada pedido absorbía las órdenes de sus hermanos de bolsa.

Es el mismo fallo silencioso de §7 escondido en otro lugar: no había error, solo un pedido que
parecía tener tres órdenes.

**Corregido** con el fallback `CANT_SOLICITADA * PRECIO_UNIT` en los 4 lugares donde se lee el
monto. Impacto medido en el universo 2026:

| | Antes | Después |
|---|---|---|
| Pedidos con orden matcheada | 2,128 | **1,852** |
| `match_metodo = composite` | 1,122 | **846** |
| Etapa `ejecucion` | 782 | **634** |

**Los 276 matches perdidos eran falsos.** Verificado en la bolsa 11553, donde §10 da la
respuesta correcta:

```
pedido  232/S (S/ 4,800) -> OC 132     ← la respuesta del doc §10
pedido  278/S (S/ 1,485) -> OC 155
pedido 1005/S (S/ 4,500) -> OC 802
```

Antes los tres matcheaban las tres órdenes. Ahora cada uno matchea la suya, y el monto del
pedido, el del ítem, el de la orden y el del CCMN por fin coinciden en pantalla.

> El número de «pedidos con orden» **baja** porque antes estaba inflado. Es la tercera vez que
> una métrica agregada engañaba (§10) — y la primera que se detecta *mirando la pantalla*, no
> los datos.

Test de regresión en `test_declaraciones_ccmn.py` que fija el fallback en el SQL.
Suite: **103 passed**, 1 failed (`test_sync_invierte`, preexistente), 8 skips.
Verificado renderizado con Playwright sobre datos reales (login, detalle y flujo de asociación).

### 9.8 Punto 9 · job de resoluciones obsoletas · sesión 2026-07-24

Cierra el riesgo de §5.1: si SIGA agrega un CCMN a la bolsa **después** de una resolución
manual, la resolución queda obsoleta sin avisar.

**Corrección de una decisión del punto 5.** Ahí la foto de candidatos se guardaba solo en
`logs.auditoria`. Auditoría es append-only y consultarla por cada resolución es frágil, así
que la foto vive ahora en la propia fila (`candidatos_al_crear`), que es donde el job la
necesita. Migración **`c8d2e3f4a5b6`** con esa columna + `revision_pendiente_desde` +
`candidatos_en_revision`, con round-trip verificado.

**Qué hace el job** (`revisar_resoluciones_obsoletas`, en el sync nocturno tras los catálogos):
por cada resolución activa compara los candidatos guardados al crear contra los actuales de la
bolsa en SIGA. Si cambiaron, sella `revision_pendiente_desde` y guarda los nuevos candidatos.

**Lo que NO hace: nunca revoca.** Quitar el juicio de un humano sin avisar sería el fallo
silencioso que toda la refactorización evita (§2, §7). Solo marca; el funcionario decide. La
tentación de §5.1 —derivar una regla automática— se resiste por diseño.

**Verificado end-to-end contra BD** (transacción revertida, 0 filas persistidas), los 5
comportamientos:

```
1. sin cambios en la bolsa        -> no marca
2. aparece el CCMN 9999           -> marca · detalle dice aparecieron=[9999]
3. re-correr con el cambio        -> idempotente, no re-marca
4. la bolsa vuelve a coincidir    -> DESMARCA (el aviso no queda pegado)
5. en todos los casos            -> revocado_en = NULL (nunca revoca)
```

Endpoint admin `/admin/jobs/revisar-resoluciones-ccmn` para forzarlo (p.ej. tras una carga
masiva). La UI muestra el aviso en ámbar dentro de la asociación afectada, con cuántos
candidatos hay ahora — no la deshace.

7 tests del job + el E2E. Suite: **110 passed**, 1 failed (`test_sync_invierte`, preexistente),
8 skips. `tsc` limpio en lo tocado.

---

## §9.9 · Resumen de la refactorización completa

| # | Qué se logró | Verificación |
|---|---|---|
| 1 | Llave de pedido `TIPO_BIEN+TIPO_PEDIDO+NRO_PEDIDO` | 2,358 filas → 2,358 únicas |
| 2 | Cascada de confianza reemplaza `MAX(CASE...)` | 13 tests + testigo |
| 3 | `declarado` + `declarado_cert` alimentados | B 95.5% · S 88.7% · cert corrobora 99.0% |
| 4 | Tabla `resolucion_pedido_ccmn` N:M | 10 constraints contra PG16 |
| 5 | Endpoints ver/asociar/revocar + auditoría | 17 tests · 422 si no es candidato |
| 6 | 5 estados en la UI, ámbar ≠ verde | 131 pedidos dejan de verse verde falso |
| 7-8 | Detalle rediseñado: bolsa, flujo, docs copiables | render verificado con Playwright |
| 9 | Job de obsolescencia (nunca revoca) | 5 comportamientos contra BD |

**Bugs de datos encontrados en el camino** (todos silenciosos, ninguno daba error):
1. El `MAX(CASE...)` pintaba avance ajeno como propio (§7 · punto 2).
2. `VALOR_TOTAL=0` en el 100% de servicios inflaba el match composite: cada pedido absorbía
   las órdenes de su bolsa (§9.7 · encontrado *mirando la pantalla*).

La búsqueda de una FK pedido↔CCMN se agotó (§1): no existe en SIGA. La solución no es
encontrarla sino **declarar el nivel de confianza** de cada match y dejar que un humano resuelva
lo que la estructura no puede. Preferible 88.7% honesto que 97% inventado.

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
| 1 | ~~Confrontar certificación × orden~~ | ✅ **cerrado** · 865/874 (99.0%) coinciden · §9.3 |
| 2 | ~~Aporte **neto** de `declarado_cert`~~ | ✅ **cerrado** · **38 pedidos** (24 S · 14 B) · §9.3 |
| 3 | Los conflictos: ¿typo o desfase sistemático? (§3.3) | ◐ **parcial** · 2 pares son transposición; 5 sin patrón (§9.3). Descartado el desfase sistemático |
| 4 | `SIG_SEGUIMIENTO` tipo 20 — qué evento es (§3.2) | ❓ menor |
| 5 | Patrón `CCMN = 2000 + CVR` (§13.1) | ❓ **nunca verificado** |
| 6 | ~~Quién puede asociar manualmente~~ | ✅ **cerrado** · Operativo/Decisor/Admin por CC; revocar igual, sin exigir autoría · §9.5 |
| 7 | Ruta del frontend `pedidos/:nroPedido/:tipoBien` no lleva `tipoPedido` | ❓ colisiona con §6 · 446 pedidos comparten URL |

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
