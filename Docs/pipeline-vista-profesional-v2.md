# Vista Profesional del Pipeline (v2) — Hallazgos, cálculos y alternativas

> Documento de análisis previo a implementar. Objetivo: una segunda vista del
> pipeline (alternable con el Kanban) con enfoque de **tabla/reporte
> profesional tipo hoja Excel**: columnas por macrofase, **comprometido y
> devengado**, totales por etapa, y filtros clave por **centro de costo** y
> **meta**. Este doc fija qué es realmente calculable, dónde está la trampa de
> consistencia, y las alternativas de diseño con su costo.

Fecha de análisis: 2026-08-07 · Datos: snapshot dev (backup SIGA + MEF), año 2026.

---

## 0. TL;DR (lo que hay que entender antes de diseñar)

1. **Los filtros que pediste (CC y meta) y el "rastro histórico" ya existen en
   los datos** que hoy sirve `/interno/pipeline/kanban`. Cada `PedidoCard` trae
   `centro_costo`, `sec_func` (meta) y un mapa `fechas` con la fecha de cada
   etapa alcanzada. No hace falta backend nuevo para la tabla base ni para el
   rastro por fila.

2. **Comprometido y devengado NO existen por pedido.** Viven en SIAF/MEF a nivel
   **meta (`SEC_FUNC`)**. El clasificador presupuestal de SIGA no cruza 1:1 con
   el desglose SIAF (está escrito en el propio código, `pipeline_read_repo.py`
   §232-239). La única llave 100% fiable entre ambos lados es `SEC_FUNC`.

3. **Esto es la trampa de consistencia.** Si se pone el comprometido/devengado
   de la meta en cada fila-pedido y se suma la columna, el total se **infla
   ×34.9** (medido: S/ 26,499,495 reales → S/ 924,150,585 falsos). Hay en
   promedio **~15 pedidos por meta** (una meta llega a 151). Cualquier tabla que
   mezcle "una fila = un pedido" con "montos MEF por meta" y ofrezca un total al
   pie miente, salvo que se maneje la agregación con cuidado explícito.

4. **Salida limpia:** separar dos rejillas conceptuales — una **por pedido**
   (recorrido físico + monto SIGA del pedido) y una **por meta** (dinero MEF:
   PIM, comprometido, devengado). Se ofrecen como dos modos de la misma vista, o
   se combinan con agrupación por meta donde los montos MEF viven en la fila de
   grupo (una vez), no en cada pedido.

---

## 1. Qué datos tenemos, de dónde, y a qué grano

### 1.1 Por pedido — `siga.v_pipeline_pedido` (vista materializada)

Grano: **una fila por pedido vivo** (`ano_eje, sec_ejec, tipo_bien,
tipo_pedido, nro_pedido`). Ya la consume el Kanban. Trae:

| Dato | Columna | Uso en la tabla |
|---|---|---|
| Centro de costo | `centro_costo` | **filtro/agrupación clave** |
| Meta | `sec_func` | **filtro/agrupación clave** |
| Monto del pedido (SIGA) | `monto_total` | columna sumable *del pedido* |
| Ítems | `items` | columna |
| Fechas por etapa (propias) | `fecha_pedido`, `fecha_aprob`, `fecha_atenc`, `fecha_ingreso`, `fecha_pecosa` | **rastro histórico** |
| Fechas por etapa (bolsa) | `bolsa_fecha_cotizacion`, `_cuadro`, `_certificacion`, `_orden`, `_compromiso`, `_ejecucion`, `_devengado` | **rastro histórico** |
| Avance duro de bolsa | `bolsa_n_ordenes`, `bolsa_ordenes_csv` | badges de órdenes |
| Ambigüedad del puente | `n_candidatos_ccmn` | **honestidad del rastro** |

El servicio (`pipeline_service.clasificar_pedidos` → `pipeline_v2.construir_card`)
convierte esto en la `PedidoCard` con `macrofase`, `etapa`, `fechas` (mapa
`EtapaCodigo → fecha`), `alerta`, `estancado`, `dias_en_etapa`. **Todo eso ya
llega al frontend hoy.**

### 1.2 Por meta — `siaf.v_ejecucion_meta_anual` (vista)

Grano: **una fila por meta** (`ano_eje, sec_ejec, sec_func`). Es la fuente
única de dinero MEF en todo el backend (saldos, cruce y pipeline la comparten).
Aplica la regla de granularidad SIAF (definición verificada en la BD):

```sql
pia          = SUM(monto_pia)          FILTER (mes_eje = 0)
pim          = SUM(monto_pim)          FILTER (mes_eje = 0)
certificado  = SUM(monto_certificado) FILTER (mes_eje > 0)
comprometido = SUM(monto_comprometido_anual) FILTER (mes_eje > 0)
devengado    = SUM(monto_devengado)   FILTER (mes_eje > 0)
girado       = SUM(monto_girado)      FILTER (mes_eje > 0)
```

Ya hay repo listo: `ejecucion_mef_repo.ejecucion_por_meta(db, ano, sec_funcs)`
devuelve `{sec_func: {pia, pim, certificado, comprometido, devengado, girado,
saldo_disponible, porcentaje_devengado}}`. **Comprometido y devengado ya están
disponibles por meta, sin desarrollo nuevo.**

### 1.3 Lo que NO existe (y por qué)

- **Devengado por pedido**: no existe. SIGA no vincula el pedido con su línea de
  ejecución SIAF de forma dura. El backend solo confirma "hay devengado en la
  meta de este pedido" (`devengado_mef_por_sec_func`), no un monto por pedido.
- **Comprometido por pedido**: idem. Lo que SIGA tiene por pedido es la *fecha*
  de compromiso de su bolsa (`bolsa_fecha_compromiso`), no el monto atribuible.
- **Clasificador SIGA ↔ desglose SIAF 1:1**: no cruza. Por eso el cruce oficial
  se hace a nivel meta y se muestran `EXP_SIAF`/`CCP` como identificadores para
  verificación manual en SIAF.

---

## 2. La trampa de consistencia (con números reales)

Medido sobre el snapshot 2026:

| Métrica | Valor |
|---|---|
| Pedidos vivos 2026 | **1,782** |
| Metas con pedidos | **120** |
| Pedidos por meta (promedio) | **14.85** |
| Máx. pedidos en una sola meta | **151** (meta 73) |
| Metas con más de un pedido | 103 de 120 |
| Pedidos que comparten bolsa (ambiguos, `n_candidatos_ccmn > 1`) | **741 (41.6%)** |

Dos magnitudes de dinero que **no son comparables por fila**:

| Magnitud | Total 2026 (metas con pedidos) | Qué es |
|---|---|---|
| `monto_total` SIGA de los pedidos | **S/ 17,620,464** | lo solicitado/valorizado en el pedido |
| PIM MEF de esas metas | S/ 51,797,341 | techo presupuestal de la meta completa |
| Comprometido MEF | S/ 32,079,228 | ejecución de **toda** la meta |
| Devengado MEF | **S/ 26,499,495** | ejecución de **toda** la meta |

El monto del pedido es una fracción de la meta (la meta incluye planilla,
servicios sin pedido, otros pedidos…). **Ponerlos en la misma columna sumable es
un error categorial.**

### 2.1 El inflado, cuantificado

Si se repite el devengado de la meta en cada fila-pedido y se suma:

| Cálculo | Resultado |
|---|---|
| Devengado correcto (1× por meta) | S/ 26,499,495 |
| Devengado "por fila" (× nº pedidos de la meta) | **S/ 924,150,585** |
| **Factor de inflado** | **× 34.9** |

> Este es *el* número que justifica toda la arquitectura de la vista. Cualquier
> diseño que ofrezca comprometido/devengado por fila-pedido con un total al pie
> tiene que resolver esto explícitamente, o no se publica.

### 2.2 La segunda trampa: rastro "propio" vs "del grupo"

El 41.6% de pedidos comparten bolsa. Para ellos, las fechas `bolsa_fecha_*`
(cotización, cuadro, certificación, orden, compromiso…) son **avance del grupo**,
no necesariamente de ESE pedido — es la misma honestidad que el Kanban ya cuida
con la bandeja "avance por confirmar" y el `estado='grupo'` del timeline. El
rastro por fila **debe distinguir visualmente** esos tramos (no pintarlos como
hechos ciertos del pedido). El dato para hacerlo ya está: `n_candidatos_ccmn` y
`confianza_ccmn` por card.

### 2.3 Cobertura del rastro histórico (viabilidad de la propuesta B)

¿Hay fechas suficientes para dibujar un mini-timeline por fila? Sí:

| Etapa | Pedidos con fecha | Cobertura |
|---|---|---|
| Pedido registrado | 1,782 | 100% |
| Aprobado | 1,763 | 99% |
| Cotización | 1,553 | 87% |
| Cuadro adquisición | 1,517 | 85% |
| Certificación | 1,552 | 87% |
| Orden emitida | 1,517 | 85% |
| Compromiso SIAF | 1,515 | 85% |
| Ejecución | 1,327 | 74% |
| Devengado (bolsa) | 757 | 42% |

La caída hacia el final es real (muchos pedidos aún no llegan a esas fases), no
un hueco de datos. El rastro por fila tiene contenido que mostrar.

---

## 3. La vista pivote Meta × Fase — probada y consistente

La forma **correcta** de meter comprometido/devengado en una tabla es agrupar
por meta. Prototipo ejecutado contra la BD (extracto real):

| Meta | Pedidos | En contrat. | En ejec. | Ped. SIGA | Comprom. MEF | Deveng. MEF |
|---|---|---|---|---|---|---|
| 73 | 151 | 12 | 138 | 885,609 | 1,002,497 | 696,787 |
| 30 | 125 | 28 | 95 | 734,577 | 928,927 | 811,864 |
| 124 | 98 | 32 | 51 | … | 2,002,440 | 982,496 |
| 61 | 89 | 28 | 60 | 213,722 | 401,291 | 380,682 |
| 123 | 85 | 27 | 38 | 292,477 | 359,927 | 354,287 |

Cada fila = una meta. Los pedidos se distribuyen por fase (columnas sumables,
sin doble conteo). El comprometido/devengado aparece **una sola vez por meta**.
Esto es el "reporte gerencial" honesto: *"la meta 73 tiene 151 pedidos, 138 ya
en ejecución, y el MEF le devengó S/ 696k de la meta completa"*.

Se arma con un JOIN por `sec_func` entre `v_pipeline_pedido` (agrupado) y
`v_ejecucion_meta_anual`. Sin desarrollo de datos nuevo; solo un endpoint que lo
exponga (o cálculo en frontend a partir de dos llamadas que ya existen).

---

## 4. Alternativas de diseño

Las columnas por macrofase que pediste caben en cualquiera de estas; la
diferencia es cómo tratan el dinero MEF para no mentir.

### Alternativa A — Tabla por pedido + rastro en la fila (sin montos MEF por fila)

- Una fila = un pedido. Columnas: N°, Motivo, CC, Meta, **6 celdas de macrofase
  con su fecha** (el rastro), Días, Estado, **Monto del pedido (SIGA)**.
- Comprometido/devengado **no** van por fila. Van en:
  - la **fila de subtotal del grupo** cuando se agrupa por meta (1× por meta), y
  - el **pie de totales** (suma de metas distintas, no de filas).
- Totales por etapa = conteo + suma de `monto_total` SIGA por macrofase (esto sí
  es sumable por fila, es dinero SIGA del pedido).
- **Pro:** el rastro histórico literal que pediste; cero riesgo de inflado.
  **Contra:** el dinero MEF no está en la misma fila que el pedido (está en el
  grupo). Es la solución más honesta.

### Alternativa B — Tabla por pedido con agrupación colapsable por Meta/CC (recomendada)

Igual que A, pero la agrupación es de primera clase (estilo pivot de Excel):

- **Encabezado de grupo (Meta o CC)**: nombre + `nº pedidos` + **PIM /
  comprometido / devengado MEF de la meta (1×)** + % devengado + semáforo.
- **Filas hijas (pedidos)**: recorrido de macrofases con fechas + monto SIGA del
  pedido. Colapsable.
- **Pie**: totales correctos (MEF sumado por meta distinta; SIGA sumado por
  pedido; ambos rotulados para que nadie los confunda).
- **Pro:** responde las dos preguntas a la vez —"¿cómo va cada pedido?" (fila) y
  "¿cuánto ejecutó la meta?" (grupo)— sin doble conteo. Encaja con los filtros
  por CC y meta como dimensión natural de agrupación. **Contra:** más trabajo de
  UI (grupos colapsables, dos niveles de subtotal).

### Alternativa C — Modo pivote puro Meta × Fase (§3)

- Una fila = una meta. Columnas = las 6 macrofases (conteo + monto SIGA) +
  bloque MEF (comprometido, devengado, % , semáforo).
- Es el reporte de una sola mirada para decisores. No muestra pedidos
  individuales (se llega a ellos haciendo drill-down a A/B).
- **Pro:** el más "profesional/gerencial", totalmente consistente, exportable
  tal cual. **Contra:** no es el rastro por pedido; es el complemento, no el
  sustituto.

### Alternativa D — Gantt temporal (línea de tiempo)

- Filas = pedidos o metas; eje X = meses; barra por macrofase entre primera y
  última fecha alcanzada. Usa el mismo mapa `fechas`.
- **Pro:** delata estancamientos visualmente. **Contra:** no es tabla ni
  exporta a Excel de forma natural; es una cuarta pestaña opcional, no el núcleo.

**Recomendación:** **B como vista principal** (tabla por pedido con agrupación
por Meta/CC y montos MEF en el grupo) + **C como pestaña "Resumen por meta"**.
A es el fallback si B resulta caro; D queda como mejora futura.

---

## 5. Cómo obtener la tabla (opciones técnicas)

### Opción 1 — Todo en frontend, con lo que ya existe (más rápido)

- `useKanban()` ya trae todas las cards con CC, meta, `fechas`, macrofase,
  monto SIGA → alimenta la tabla por pedido y el rastro por fila **sin backend**.
- Para el dinero MEF por meta hace falta el desagregado por `sec_func`. Hoy el
  frontend solo tiene el resumen agregado (`useResumenSaldos`). **Falta exponer
  `ejecucion_por_meta` como endpoint** (el repo ya existe; es un endpoint
  delgado). Con eso el frontend hace el JOIN meta→MEF en memoria.
- Export a Excel en cliente (SheetJS) desde lo filtrado.
- **Costo:** 1 endpoint nuevo (lista de metas visibles con montos MEF) + toda la
  UI. No toca vistas SQL ni jobs.

### Opción 2 — Endpoint agregado en backend (más robusto)

- Nuevo endpoint `GET /interno/pipeline/reporte` que devuelve la matriz
  Meta × Fase ya calculada (JOIN `v_pipeline_pedido` ⋈ `v_ejecucion_meta_anual`
  por `sec_func`), respetando el alcance por CC (RN-04/RN-06) y auditando la
  exportación (RN-08) si se exporta desde backend con openpyxl.
- **Costo:** endpoint + query + tests de la zona de montos (crítica). Frontend
  consume una respuesta ya consistente, sin riesgo de que un cálculo de UI
  reintroduzca el inflado.
- **Recomendado para los montos**, porque centraliza la regla anti-doble-conteo
  donde ya viven las demás (una sola definición de "devengado MEF").

### Opción híbrida (recomendada)

Tabla y rastro por pedido → **frontend con `useKanban()`** (Opción 1, sin
backend). Bloque de montos MEF por meta y el pivote → **endpoint backend**
(Opción 2) para que la regla anti-inflado esté en un solo lugar y auditada.

---

## 6. Reglas de negocio que la vista debe respetar

- **RN-01/RN-03:** montos presupuestales SIEMPRE del MEF (`v_ejecucion_meta_anual`),
  nunca del PIM SIGA. El `monto_total` de la fila es SIGA e **informativo del
  pedido**, rotulado como tal.
- **RN-06:** filtro por CC según rol (operativo = sus CC; decisor = jerarquía;
  admin = todo). El endpoint MEF por meta debe intersectar con las metas
  visibles del usuario.
- **RN-08:** si se exporta a Excel desde backend, auditar la exportación.
- **Honestidad del puente (§2.2):** los tramos de rastro que vienen de
  `bolsa_fecha_*` en pedidos con `n_candidatos_ccmn > 1` se marcan como "avance
  del grupo", no como hecho cierto del pedido.
- **Semáforo temporal:** el % devengado se mide contra el **mes de corte** del
  snapshot, no contra el calendario (memoria: datos-backup-no-tiempo-real).
- **Diseño institucional:** 4 colores, sin emojis, color+texto (nunca color
  solo), densidad de información sobre minimalismo.

---

## 7. Columnas propuestas (borrador para la tabla por pedido, Alternativa B)

| Columna | Fuente | Sumable | Nota |
|---|---|---|---|
| N° pedido | `nro_pedido` | — | con copiar |
| Motivo | `motivo` | — | lo que el funcionario reconoce |
| Centro de costo | `centro_costo` | — | filtro/grupo |
| Meta | `sec_func` (+ nombre) | — | filtro/grupo |
| Solicitud → Cierre (6 celdas) | `fechas[etapa]` | — | **rastro histórico**, fecha por macrofase |
| Etapa actual | `etapa_label` | — | |
| Días en etapa | `dias_en_etapa` | — | rojo si estancado |
| Estado | `alerta` | — | color + texto |
| Monto pedido (SIGA) | `monto_total` | **sí (por pedido)** | informativo |
| — subtotal de grupo (Meta) — | | | |
| PIM meta (MEF) | `v_ejecucion_meta_anual.pim` | **sí (por meta, 1×)** | en fila de grupo |
| Comprometido (MEF) | `.comprometido` | **sí (por meta, 1×)** | en fila de grupo |
| Devengado (MEF) | `.devengado` | **sí (por meta, 1×)** | en fila de grupo |
| % devengado + semáforo | derivado | — | temporal |

> Regla de oro de la vista: **lo que se suma por fila es dinero SIGA del pedido;
> lo que se suma por meta es dinero MEF.** Nunca se cruzan las dos en la misma
> operación de suma. El pie de tabla lleva dos totales rotulados, no uno.

---

## 8. Consultas de verificación usadas (reproducibles)

Todas contra `sicop_postgres_dev`, año 2026. Ver commits/historial de este
análisis para el detalle; las clave:

1. Cardinalidad meta→pedido (1,782 pedidos / 120 metas / máx 151).
2. Comparación de magnitudes SIGA vs MEF (S/17.6M pedidos vs S/26.5M devengado).
3. Cobertura de fechas por etapa (rastro viable, 100%→42%).
4. Factor de inflado por fila (× 34.9) — la prueba de por qué el dinero MEF no
   va por fila-pedido.
5. **Cobertura órdenes→SIAF:** 100% de las órdenes traen `exp_siaf`, pero
   `v_ejecucion_normalizada` no expone `exp_siaf` → devengado NO atribuible a
   expediente (habilita §9.0).
6. **Órdenes vs comprometido MEF por meta:** órdenes = 36.6% del comprometido en
   promedio; en 70/112 metas cubren <50% → el prorrateo debe rotularse como
   "ejecución de la parte comprada", no de la meta (habilita §9.1).
7. **Clasificador orden ↔ SIAF:** el clasificador de la ORDEN cruza mal
   (formato mezclado), PERO el clasificador del **pedido-ítem** SÍ cruza tras
   normalizar (ver §9.7 — hallazgo que corrige la conclusión inicial).
8. **Clasificador pedido-ítem ↔ SIAF (normalizado):** 390 celdas cruzan, 0
   solo-SIGA, **93.6%** del devengado de bienes y servicios cubierto. La llave
   `SEC_FUNC + clasificador(5 niveles)` es real y baja el grano de meta a
   específica (habilita §9.7).

---

## 9. Alternativas de solución inteligentes (el problema difícil)

Las alternativas del §4 son *layouts*. Esta sección ataca el problema de fondo:
**¿se puede poner comprometido/devengado por pedido de forma defendible, y
reconstruir el rastro real, exprimiendo el modelo de datos?** Cada alternativa
va con la evidencia dura que la habilita o la descarta — para no vender una
cifra inventada como si fuera un dato.

### 9.0 Qué llaves existen realmente (medido)

Antes de proponer atribución de dinero por pedido, hay que saber qué cruza:

| Llave candidata | ¿Cruza? | Evidencia |
|---|---|---|
| `SEC_FUNC` (meta) | **Sí, 100%** | única llave que SIGA y SIAF comparten sin ambigüedad |
| **`SEC_FUNC` + clasificador (5 niveles)** | **Sí, 93.6%** | el clasificador del **pedido-ítem** normalizado cruza con el clasificador SIAF (ver §9.7). **Baja el grano de meta a específica de gasto** |
| Orden → `exp_siaf` | orden lo tiene al 100% | las 1,517 órdenes traen `exp_siaf` |
| `exp_siaf` → ejecución SIAF | **No** | `v_ejecucion_normalizada` NO expone `exp_siaf`; imposible atribuir devengado a un expediente |
| Clasificador de la **orden** ↔ SIAF | **No** | el clasificador que trae `siga.ordenes` viene en formato mezclado y no cruza; pero el del pedido-ítem sí (§9.7) |
| Pedido → orden (bolsa) | parcial | 58.4% resuelto; 41.6% comparte bolsa (`n_candidatos_ccmn > 1`) |

**Conclusión (corregida por §9.7):** no hay cadena que lleve un monto devengado
hasta un pedido *individual*, pero sí hasta una **celda `SEC_FUNC +
clasificador`** que agrupa en promedio 3.51 pedidos (vs 14.85 por meta). El
devengado por pedido sigue siendo una **estimación por reparto**, pero repartido
dentro de una celda 4× más fina y homogénea — y en el 27.7% de celdas hay un
solo pedido, donde la atribución es **directa, sin reparto**.

### 9.1 Alternativa I — Atribución en cascada de tres capas (dato → estimación → contexto)

La idea inteligente: **cada pedido muestra el mejor dato disponible según hasta
dónde llegó su cadena**, y la vista es explícita sobre qué capa está viendo.

1. **Capa dura (comprometido real del pedido):** cuando el puente pedido→orden
   está resuelto (`unico`/`declarado`/`resuelto_manual` — el 58.4%), el pedido
   tiene una o más órdenes con `total_fact_soles` y `estado_siaf`. **Ese monto de
   orden SÍ es atribuible al pedido** como "comprometido vía compra". Es dato
   duro, no estimación.
2. **Capa estimada (devengado prorrateado):** el devengado real es de la meta.
   Se reparte entre los pedidos **con orden** de esa meta, proporcional a su
   `total_fact_soles`. Se muestra en una columna **rotulada "estimado"** con
   tipografía diferenciada (no tabular-nums sólido). Nunca se suma en el total
   de la meta (el total sigue siendo el devengado MEF real, 1×).
3. **Capa contexto (sin cadena):** pedidos sin orden (aún en solicitud/
   programación) no reciben monto de ejecución; muestran solo su `monto_total`
   SIGA solicitado.

**Por qué es defendible y no ficción:** el reparto se aplica solo sobre la
porción de la meta que **sí pasó por órdenes**, no sobre el devengado completo.
Medición que lo sostiene: las órdenes de una meta suman en promedio el **36.6%**
del comprometido MEF — el resto (planilla, servicios continuos) no tiene pedido
al cual atribuirse, y correctamente queda fuera del reparto.

- **Pro:** da la columna "comprometido/devengado por pedido" que el usuario pide,
  con una capa 100% dura y una capa estimada honesta y acotada.
- **Contra:** la capa estimada exige disciplina de UI (rótulo "est.", tooltip que
  explique el reparto, excluirla de sumas). Complejidad conceptual media-alta.
- **Riesgo controlado:** en 70/112 metas las órdenes cubren <50% del comprometido
  → el prorrateo NO debe presentarse como "así se gastó la meta", sino como "así
  se ejecutó **la parte comprada** de la meta". El copy es parte del diseño.

### 9.2 Alternativa II — Fila de pedido con "barra de ejecución de la meta" (contexto sin mentir)

En vez de repartir el dinero, **cada fila-pedido muestra la ejecución de SU meta
como contexto compartido**, con una mini-barra: `devengado / PIM` de la meta,
idéntica para todos los pedidos de esa meta. No se suma nunca (es un ratio, no un
monto de fila).

- La fila dice: *"este pedido pertenece a la meta 73, que va 70% devengada"*.
- **Pro:** cero riesgo de inflado (un % no se suma), da la lectura presupuestal
  que faltaba, trivial de calcular (ya está en `ejecucion_por_meta`).
- **Contra:** no es "devengado de este pedido"; es "devengado de su meta" repetido
  como contexto. Menos ambicioso que I, pero imposible de malinterpretar como
  suma. Combina bien con la agrupación por meta (la barra vive en el grupo y se
  hereda visualmente a las filas).

### 9.3 Alternativa III — Motor de reglas de "salud" por pedido (analítica, no solo tabla)

Subir de "tabla que muestra datos" a "tabla que **razona**". Por cada pedido se
calcula un conjunto de señales derivadas que hoy no existen:

- **Velocidad de avance:** días entre hitos consecutivos del rastro (`fechas`),
  comparado con la mediana de su macrofase. Detecta el pedido que "se durmió"
  antes de que cruce el umbral de estancado.
- **Cuello de botella de la meta:** la macrofase donde se acumulan más pedidos de
  esa meta (moda del estado por meta). Señala dónde intervenir.
- **Riesgo de sub-ejecución:** metas con muchos pedidos vivos pero bajo % de
  devengado MEF contra el mes de corte (semáforo temporal). Cruza pipeline
  (volumen) con MEF (dinero) — la síntesis que ningún widget da hoy.
- **Coherencia SIGA↔MEF:** pedidos cuya orden está comprometida (`estado_siaf`)
  pero cuya meta no mueve devengado — posible atasco en tesorería.

- **Pro:** convierte el reporte en herramienta de decisión; todo derivable de
  datos ya disponibles; sin doble conteo (son indicadores, no sumas).
- **Contra:** es trabajo de backend real (definir y testear cada señal, zona
  crítica). Alto valor, mayor costo. Se puede entregar incremental (una señal
  por iteración).

### 9.4 Alternativa IV — Rastro reconstruido con distinción propio/grupo (el timeline honesto por fila)

El mini-timeline por fila (§4-B) se vuelve inteligente resolviendo la segunda
trampa (§2.2): **cada celda de macrofase se pinta según la certeza de su fecha**.

- **Verde sólido:** hito con fecha propia del pedido (`fecha_pedido`,
  `fecha_aprob`, y en bienes `fecha_ingreso`/`fecha_pecosa`).
- **Verde tramado / con marca "grupo":** hito cuya fecha viene de `bolsa_fecha_*`
  en un pedido con `n_candidatos_ccmn > 1` (41.6% de los casos). Cierto para la
  bolsa, no atribuible al pedido.
- **Azul:** macrofase actual. **Gris:** no alcanzada.
- Al hover, cada celda da la fecha exacta y, si es "grupo", cuántos candidatos y
  el nº de bolsa.

- **Pro:** es el rastro literal que pediste, pero sin la mentira de pintar avance
  ajeno como propio. Reutiliza toda la honestidad que el Kanban ya construyó.
- **Contra:** requiere pasar `n_candidatos_ccmn`/`confianza_ccmn` a la celda (ya
  vienen en la card) y un patrón visual para "grupo" que sea legible en una
  tabla densa.

### 9.5 Alternativa V — Vista materializada de reporte pre-agregada (rendimiento a escala)

Para que la vista sea instantánea con 1,782 pedidos × columnas derivadas: una
**materialized view `siga.v_reporte_pipeline`** que precompute por pedido la
etapa, las 6 fechas de macrofase, el flag propio/grupo, y por meta el bloque MEF
(comprometido/devengado/%), refrescada por el job de sync que ya existe.

- **Pro:** una sola query sirve toda la tabla; la lógica anti-inflado vive en SQL
  (una sola definición); export backend directo desde la vista.
- **Contra:** una migración + mantener la vista en el job de sync. Justificable
  solo si la vista va a ser muy usada o el cálculo en vivo se nota lento.

### 9.7 Alternativa VI — Cruce por clasificador de gasto (la vía fina, verificada)

**Hallazgo (idea del usuario, confirmada con datos):** el clasificador de gasto
es un identificador normado nacional (Clasificador de Gastos del MEF), y **es el
mismo en SIGA y SIAF** a nivel de específica-detalle. Esto abre un cruce mucho
más fino que la meta.

#### El mapeo, verificado

El clasificador del **pedido-ítem** (`siga.pedido_items.clasificador`) viene en
formato de ancho fijo con espacios: `2.3. 1  5. 1  2`. Sus posiciones 2-6 son
exactamente `generica.subgenerica.subgenerica_det.especifica.especifica_det` de
`siaf.v_ejecucion_normalizada`:

| Componente | Pedido SIGA `2.3. 1 10. 1  1` | SIAF |
|---|---|---|
| (tipo transacción) | `2` | — (implícito, gasto) |
| genérica | `3` | `generica = 3` (BIENES Y SERVICIOS) |
| subgenérica | `1` | `subgenerica = 1` (COMPRA DE BIENES) |
| subgen. detalle | `10` | `subgenerica_det = 10` |
| específica | `1` | `especifica = 1` |
| espec. detalle | `1` | `especifica_det = 1` |

> Cuidado con el parseo: los subcampos pueden tener **2 dígitos** (`10`, `11`,
> `99`), así que hay que parsear por ancho fijo dentro de cada grupo separado por
> puntos, no concatenar dígitos crudos (eso desalinea). La llave normalizada
> resultante: `3.1.10.1.1`, idéntica en ambos sistemas.

#### La medición (bienes y servicios, genérica 3, año 2026)

| Métrica | Valor |
|---|---|
| Celdas `SEC_FUNC + clasificador` que cruzan | **390** |
| Celdas solo-SIGA (pedido sin ejecución SIAF) | **0** |
| Celdas solo-SIAF (ejecución sin pedido: caja chica, compra directa) | 406 |
| **Devengado de bienes/servicios cubierto por celdas con pedido** | **93.6%** (S/4.66M de S/4.98M) |
| Pedidos por celda (promedio) | **3.51** (vs 14.85 por meta → **4× más fino**) |
| Máx. pedidos en una celda | 66 |
| Celdas con un solo pedido (atribución directa, sin reparto) | **27.7%** (108 de 390) |

#### Qué habilita

- **Columna "devengado de la celda" por pedido**, mucho más creíble: el reparto
  se hace dentro de la celda `SEC_FUNC + clasificador` (3.5 pedidos), no dentro
  de la meta (15 pedidos). En el 27.7% de celdas ni siquiera hay reparto.
- **Un pivote de dos niveles** Meta → Clasificador con el devengado/comprometido
  SIAF real por específica de gasto. Es exactamente el reporte presupuestal fino
  que un decisor pide: "en la meta 30, específica 2.3.1.5.1.2 (combustibles) se
  devengó S/X, y estos 4 pedidos la componen".
- **Detección de descuadres:** celdas solo-SIAF = gasto ejecutado sin pedido
  formal (posible compra irregular o fuera del pipeline); celdas donde el
  `monto_total` del pedido supera el PIM de su clasificador = sobre-programación.

#### Límites (para no sobrevender)

- **Solo aplica a genérica 3 (bienes y servicios).** Planilla (genérica 1) y
  activos (genérica 6, gasto de capital) no pasan por pedidos SIGA de este
  pipeline. El cruce fino cubre el universo de compras, que es justo el del
  pipeline — coherente.
- El **reparto dentro de la celda sigue siendo estimación** cuando hay >1 pedido.
  Mejora el grano, no elimina el supuesto. Se rotula igual que en §9.1.
- La orden puede pagar un clasificador distinto al que el pedido-ítem declaró
  (raro, pero ocurre); el cruce es pedido↔SIAF por clasificador declarado, no
  pedido↔orden↔SIAF. Es una aproximación por clasificador, no una cadena dura.

#### Costo

- Requiere una función de normalización del clasificador SIGA (parseo por ancho
  fijo) — trivial en SQL, reutilizable. Idealmente materializada en la vista de
  reporte (§9.5) para no recomputar.
- Un JOIN adicional `SEC_FUNC + clasificador` contra `v_ejecucion_normalizada`.

### 9.6 Combinación recomendada

| Capa | Alternativa | Por qué |
|---|---|---|
| Dinero por pedido | **VI** (clasificador) + **I** (comprometido duro) | VI da el devengado SIAF real por celda fina (93.6% cubierto); I añade el comprometido duro de la orden donde el puente resuelve |
| Devengado estimado | **VI capa reparto**, opt-in y rotulado | reparto dentro de celda de 3.5 pedidos, no de meta; directo en el 27.7% de celdas |
| Contexto presupuestal | **II** (barra de meta) | para pedidos sin celda cruzada (aún sin ejecución) |
| Rastro por fila | **IV** | el timeline honesto propio/grupo |
| Inteligencia | **III**, incremental | una señal por iteración; §9.7 habilita "descuadre SIGA↔SIAF por clasificador" |
| Rendimiento | **V** solo si hace falta | la normalización del clasificador vive aquí si se materializa |

La regla que gobierna todas: **un dato duro se muestra sólido y se suma; una
estimación se muestra rotulada y NO se suma; un contexto de meta se muestra como
ratio y no se suma.** El cruce por clasificador (VI) **sube el grano del dato
duro**: donde antes solo había estimación por meta, ahora hay devengado SIAF real
por celda fina, y atribución directa en más de una cuarta parte de los casos.

---

## 10. Pendiente de decisión (para el usuario)

1. ¿Alternativa **B** (tabla por pedido + grupos por meta con MEF en el grupo)
   como principal, con **C** (pivote por meta) como segunda pestaña? ¿O empezar
   solo por una?
2. **¿Se adopta el cruce por clasificador (§9.7)?** Es la vía que da devengado
   SIAF real por celda fina (93.6% cubierto, atribución directa en 27.7%). Sube
   bastante el valor de la vista pero añade la normalización del clasificador y
   un pivote de dos niveles Meta→Clasificador. Recomendado si el objetivo es un
   reporte presupuestal serio, no solo operativo.
3. ¿Los montos MEF se exponen vía **endpoint nuevo** (recomendado, centraliza la
   regla anti-inflado y el cruce por clasificador) o se arma en frontend?
4. ¿Exportar a Excel entra en esta v2? ¿En cliente o backend (con auditoría)?
5. ¿Cómo se alterna Kanban ↔ Profesional: toggle en la misma página, pestañas, o
   ruta aparte?
