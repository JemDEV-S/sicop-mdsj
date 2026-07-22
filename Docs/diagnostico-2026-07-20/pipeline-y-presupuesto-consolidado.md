# Diagnóstico consolidado — Pipeline y presupuesto (interno)

> **Fecha:** 2026-07-20
> **Alcance:** revisar dónde estamos con el pipeline de pedidos y el cruce
> MEF↔SIGA del panel interno, con datos reales de la BD, y proponer un plan
> concreto de ajuste para no seguir programando "a ciegas".
> **Fuente de queries:** SQL Server local `SIGA_300687` + Postgres `sicop`
> (contenedor `sicop_postgres_dev`), ambas verificadas el día del diagnóstico.
>
> Los detalles largos (mapa canónico de tablas, cadena de FKs, testigos) están
> en `Docs/exploracion-siga-pipeline-extendido.md` §16-§17. Este archivo no los
> repite; los cita.

---

## 1. Qué está funcionando bien

Antes de listar fricciones, dejar claro lo que **no** hay que tocar:

- **Taxonomía de 6 macrofases + 16 etapas** ([backend/app/schemas/pipeline.py](../../backend/app/schemas/pipeline.py))
  respeta 1:1 el mapa canónico de la exploración §17.6. Códigos estables
  (`pedido_registrado`, `ccmn_em_cvr`, …), labels legibles y numeración 1..16.
  El front consume estos mismos códigos ([features/dashboard/types.ts](../../frontend/src/features/dashboard/types.ts)).
  Ninguna duplicación entre miniatura del dashboard y vista completa.
- **Filtro por CC en toda la cadena.** `permisos_service.restringir_a_subrama`
  se aplica en `/interno/pipeline/kanban`, `/interno/pedidos`,
  `/interno/alertas/pedidos-estancados`, `/interno/saldos*`. Cambiar el chip
  de CC en el topbar dispara refetch automático porque el `queryKey` incluye
  `ccCodigo` (dashboard/api.ts §22-58).
- **Snapshot MEF en Postgres.** `siaf.ejecucion_presupuestal` tiene 9.249 filas
  para 2026 (181 metas, meses 0..7), última sincronización 2026-07-14 16:45.
  El widget de saldos ya distingue *devengado oficial* (MEF, sin filtro por CC)
  vs. *ejecución interna* (SIGA, filtrada por CC), documentando en tooltip por
  qué difieren (`WidgetSaldos.tsx` §67-158).
- **Umbrales configurables por macrofase.** `sistema.umbrales_alertas`
  guarda `dias_por_macrofase` en JSON:
  `{"solicitud":15,"programacion":30,"certificacion":30,"contratacion":45,"ejecucion":180,"cierre":null}`.
  El servicio lo lee con fallback a defaults (`pipeline_service._cargar_umbrales`).
- **Timeline del pedido en detalle.** `pipeline_service.construir_timeline`
  arma los 13/16 hitos con fecha y flag `alcanzada`. Se pinta en
  [PedidoDetalle.tsx](../../frontend/src/features/pipeline/PedidoDetalle.tsx)
  con `Timeline`.
- **Cadena estructural pedido → orden con FK dura.** `SIG_DETALLE_PEDIDOS.
  SEC_CUA_MOD_SAL → SIG_CUADRO_MODIFICADO_CMN → SIG_PAAC_CONSOLIDADO →
  SIG_CUADRO_ADQUISICION → SIG_CERTIFICACION → SIG_ORDEN_ADQUISICION` está
  toda usada por el repo (`pipeline_repo._SQL_KANBAN` §95-185).

---

## 2. Estado real de los datos (verificado hoy)

Todas las cifras salen de queries directas a la BD, no de suposiciones.

### 2.1 Universo del pipeline 2026

| Métrica | Valor |
|---|---:|
| Pedidos totales (ESTADO 0/1/7) | **2.358** |
| ESTADO='0' (borrador / en proceso) | 22 |
| ESTADO='1' (aprobado, en trámite) | **1.763** (75%) |
| ESTADO='7' (cerrado) | **573** (24%) |
| Pedidos B tipo=1 (atención interna) | 576 |
| Pedidos B tipo=2 (compra) | 734 |
| Pedidos S tipo=2 (compra de servicio) | 1.048 |
| CC distintos con pedidos | ~50 (top-3 absorbe el 54%) |
| Conformidades servicio (`SIG_MOVIM_CONFOR_SERVICIO`) | 833 filas / 626 órdenes |
| Ingresos almacén I+1 (bienes) | 574 filas / 572 órdenes |
| Cierres registrados (`SIG_SEGUIMIENTO t=19`) | 573 (= ESTADO=7 ✓) |
| Órdenes 2026 (`SIG_ORDEN_ADQUISICION`) | 1.473 · S/ 12.02M facturados |
| Contratos (`SIG_CONTRATOS`) | 30 |
| Cabeceras PAAC (`SIG_PAAC_CONSOLIDADO`) | 1.988 |
| Puente CMN (`SIG_CUADRO_MODIFICADO_CMN`) | 6.431 filas — 100% con NRO_CONSOLID |

Top-3 CC por volumen: `01.03.11.02` (547), `01.03.11.03` (427), `01.03.14.01`
(314). Cualquier smoke-test debe usar estos tres.

### 2.2 SIG_TECHO_PRESUPUESTO 2026

| Concepto | Valor |
|---|---:|
| Filas totales | 2.218 |
| Filas con `SEC_FUNC IS NULL` | **264** (12% de las filas) |
| **PIM cargado a nivel pliego (SEC_FUNC NULL)** | **S/ 116,595,423** |
| PIM desagregado a metas (SEC_FUNC NOT NULL) | **S/ 46,660,297** |
| Certificado a metas (`mnto_acum_cert`) | S/ 15,787,701 |
| Comprometido a metas (`mnto_acum_coma`) | S/ 12,880,410 |
| Devengado SIGA (`MNTO_ACUM_DEVGDO_SIGA`) | **S/ 0** ← columna no poblada |

El backend hoy **excluye las 264 filas SEC_FUNC NULL** de saldos y del widget
del dashboard (regla correcta según el diccionario §18). El % de ejecución
que muestra "Ejecución interna (SIGA)" es sobre PIM=46.7M, no sobre el techo
del pliego. Es lo esperado.

### 2.3 Snapshot MEF 2026 (Postgres)

| Concepto | Valor |
|---|---:|
| Filas totales | 9.249 · 181 metas |
| Meses cubiertos | 0..7 |
| **PIA** (SUM mes_eje=0) | **S/ 65,116,324** |
| **PIM** (SUM mes_eje=0) | **S/ 69,500,489** |
| **Devengado** (SUM mes_eje>0) | **S/ 30,891,090** |
| Girado (SUM mes_eje>0) | S/ 30,516,054 |
| Última sincronización | 2026-07-14 16:45 (6 días de rezago) |

### 2.4 La brecha SIGA vs. MEF que el usuario ya vio

- **PIM SIGA (a metas) = 46.7M** vs. **PIM MEF = 69.5M**.
  Diferencia = S/ 22.8M — fuentes cargadas en SIAF pero aún no desagregadas
  al SIGA (lag operativo de la muni, no bug).
- **Cert+Compr SIGA = 28.7M** vs. **Devengado MEF = 30.9M**. Es coherente
  con el flujo natural: devengado ≥ comprometido ≥ certificado.
- **MNTO_ACUM_DEVGDO_SIGA = 0** en 2026 — no se puebla en esta muni. Por eso
  el widget muestra "Cert. + Comprometido" y no "Devengado" en el bloque SIGA.

### 2.5 Umbrales activos hoy

`sistema.umbrales_alertas` tiene tres registros:

```
pedido_estancado    → {"dias": 15, "dias_por_macrofase": {
                          "solicitud":15,"programacion":30,"certificacion":30,
                          "contratacion":45,"ejecucion":180,"cierre":null}}
meta_baja_ejecucion → {"pct_q3": 50, "pct_q4": 90}
contrato_por_vencer → {"dias": 30}
```

---

## 3. Los cinco problemas concretos identificados

Ordenados por impacto sobre "el número que el funcionario ve".

### 3.1 · Fechas fantasma en pedidos activos → días en etapa mal calculados

**Hallazgo:** de los **1.785 pedidos activos** (ESTADO 0 o 1), **el 100% tiene
`FECHA_APROB=NULL` y `FECHA_ATENC=NULL`**. Solo los 573 cerrados tienen esas
fechas pobladas. Es decir, la cabecera del pedido solo llena FECHA_APROB al
cierre, no al aprobar.

**Impacto en el pipeline:**
- Un pedido en `certificacion_ccp` (etapa 8) cuya única fecha es `FECHA_PEDIDO`
  del 5 de febrero calcula `dias_en_etapa` como "hace 165 días" — se marca
  estancado aunque haya sido certificado ayer.
- El backend ya intenta usar fechas de la etapa (`fecha_ccmn`,
  `fecha_certificacion`, `fecha_orden`, `fecha_compromiso`, `fecha_ejecucion`,
  `fecha_pecosa`, `fecha_cierre_seg`) en `pipeline_service._fecha_etapa`, pero
  la cadena de fallback termina en `FECHA_APROB → FECHA_PEDIDO`, y cuando la
  fecha de la etapa correspondiente no salió en el JOIN (por ambigüedad CCMN
  o por falta de match), cae al `FECHA_PEDIDO`.

**Decisión del usuario:** *combinar ambas — usar `SIG_SEGUIMIENTO` para etapas
1-2 y las fechas de sub-tabla para etapas 3-16. Documentar el mapping
etapa→fuente_fecha en un solo lugar.*

**Cómo aplicarlo:**
1. Añadir en `pipeline_repo._SQL_KANBAN` un CTE `seguim_fechas` que traiga
   `MAX(FECHA_TRANSACCION)` de `SIG_SEGUIMIENTO` para `TIPO_TRANSACCION IN (2,4)`
   por pedido (aprobación y creación formal). Fill rate confirmado: 1.782 filas
   tipo=2 en 2026 ≈ pedidos aprobados.
2. Reemplazar en `_fecha_etapa`:
   - `ETAPA_PEDIDO_APROBADO`: `fecha_seg_aprob` primero, luego `FECHA_APROB`,
     luego `FECHA_PEDIDO`.
   - `ETAPA_PEDIDO_REGISTRADO`: `fecha_seg_creacion` primero, luego
     `FECHA_PEDIDO`.
   - Etapas 3-16 mantienen su fuente actual (fecha_ccmn/certif/orden/…),
     pero **el fallback deja de ser FECHA_APROB → FECHA_PEDIDO** y pasa a ser
     la última fecha *anterior* de una etapa alcanzada (evita saltar 6 meses
     hacia atrás sin razón).
3. Documentar el mapping etapa → columna_fecha en un docstring encima de
   `_fecha_etapa`, y añadir un test unitario con las 16 combinaciones.

---

### 3.2 · Puente pedido↔CCMN ambiguo → sobre-marca las etapas de programación

**Contexto:** en la sesión 5 de la exploración (§16.1) se encontró el puente
estructural `SIG_DETALLE_PEDIDOS.SEC_CUA_MOD_SAL → SIG_CUADRO_MODIFICADO_CMN →
SIG_PAAC_CONSOLIDADO`. Es FK real. Sin embargo, un mismo `SEC_CUA_MOD_SAL`
puede tener **N CCMN apuntándole** (varios procesos de compra distintos sobre
la misma partida). El testigo 232/S muestra 3 candidatos; en 2026 completo
el promedio es **3.86 CCMN candidatos por pedido y el máximo son 39**.

**Query de verificación:**
```
1912 pedidos consultados
1665 tienen ≥1 CCMN candidato (87%)
Promedio CCMN candidatos por pedido con match: 3.86
Máximo: 39
```

**Impacto en el pipeline actual:**
El backend hoy hace `MAX(CASE WHEN cmn.NRO_CONSOLID IS NOT NULL THEN 1 ELSE 0
END)` en `pipeline_repo` — es decir marca `tiene_ccmn=1`, `tiene_cotizacion=1`
y `tiene_cuadro_adq=1` en cuanto exista **algún** CCMN candidato. Consecuencia:
un pedido que en realidad todavía está en "solicitud aprobada" puede aparecer
en el kanban como "cuadro adquisición" solamente porque *otro* proceso de
compra sobre la misma partida sí llegó ahí.

**Ruta acordada con el usuario:**
La sesión 5 ya propuso desambiguar con **composite adicional** (fecha + monto
+ CC). Hay que aplicar ese composite en el repo del pipeline. Regla concreta
para elegir el CCMN "propio" del pedido:

```
Entre los N CCMN candidatos del pedido, elegir el único que cumpla TODOS:
  1. FECHA_PEDIDO <= PAAC.FECHA_CONS <= (FECHA_ORDEN si existe, o hoy)
  2. PAAC.VALOR_PLAN >= SUM(SIG_DETALLE_PEDIDOS.VALOR_TOTAL) del pedido
  3. Existe fila en SIG_PAAC_CENTRO_COSTO con CC = pedido.CENTRO_COSTO
```

Si tras el filtro queda **exactamente 1** → CCMN confiable. Si quedan
**≥2** → tomar el de fecha más cercana a FECHA_PEDIDO y marcar el pedido con
un flag `match_ccmn_confianza = 'baja'` que el front pinta como badge
"CCMN aproximado". Si quedan **0** → dejar `tiene_ccmn=0` (el pedido no ha
llegado a esa etapa aún).

**Cambios necesarios:**
- `pipeline_repo._SQL_KANBAN` — CTE `programacion` filtra por composite antes
  del MAX.
- `PedidoCard` — nuevo campo `match_ccmn_confianza: 'alta' | 'baja' | null`.
- `PedidoCardCompacto` en el front — badge cuando `baja`.
- Testigo 232/S debe seguir cayendo en CCMN=2266 tras el filtro (verificar
  con query).

---

### 3.3 · Cierre operativo cuando devengado ≥ TOTAL_FACT_SOLES

**Contexto:** hoy el pipeline marca "cerrado" solo por `ESTADO='7'` o
`SIG_SEGUIMIENTO t=19`. Pero muchos servicios están *funcionalmente* cerrados
antes de que SIGA les cambie el estado: cuando la sumatoria de conformidades
cubre el 100% del `TOTAL_FACT_SOLES` de la orden. La memoria del proyecto
(`project-siga-servicios-cierre.md`) documenta esta regla.

**Impacto actual:** en el widget "Últimos pedidos" del dashboard y en el
kanban aparecen como "en ejecución" varios pedidos que ya deberían estar en
"cierre operativo". El funcionario lo detecta al abrir el detalle y ver que
todas las conformidades ya sumaron el total del contrato.

**Decisión del usuario:** *"Marcar 'cierre operativo' cuando cubre 100%".*

**Cómo aplicarlo (sin romper la taxonomía):**
1. Añadir en `pipeline_repo` un CTE `ejecucion_por_orden` que sume el
   `TOTAL_FACT_SOLES` cubierto por conformidades por orden (para servicios) o
   por entradas al almacén I,1 (para bienes de compra directa). En SQL:
   ```
   SUM(CASE WHEN indi_confor='D' OR estado_deveng='D' THEN monto ELSE 0 END)
     >= o.TOTAL_FACT_SOLES  →  flag `cubierto_al_100 = 1`
   ```
   *Nota:* `SIG_MOVIM_CONFOR_SERVICIO` no tiene columna de monto por
   conformidad, solo la orden completa. Hay que confirmar si la muni marca
   una única conformidad final con `INDI_CONFOR='D'` (probable) o si suma en
   fracciones (necesita otra tabla, ver §5 abajo).
2. Nuevo flag en `PedidoCard`: `cierre_operativo: bool` (adicional a `estancado`).
3. En el kanban, un pedido con `cierre_operativo=true` se pinta con un chip
   verde "Ejecutado 100%" pero sigue en su columna actual (no lo movemos a
   `cierre` porque SIGA no ha cambiado su ESTADO — ambigüedad respetada).
4. Al abrir el detalle, la cabecera muestra el mismo chip y el timeline pinta
   `[15] Devengado` como alcanzado con la fecha de la última conformidad.

**Dependencia:** para bienes, "devengado real por orden" requiere unir con
`siaf.ejecucion_presupuestal` por `sec_func` + `clasificador` + orden. Es más
sencillo dejar bienes con la regla actual (ingreso almacén = ejecución) y
aplicar el "cierre operativo" solo a servicios en el primer pase.

---

### 3.4 · Devengado por meta desde SIAF (Fix #2 pendiente en el código)

**Contexto:** el widget SIGA usa `cert + compr` como proxy de devengado porque
`MNTO_ACUM_DEVGDO_SIGA=0` en 2026. La tabla de saldos por meta
(`/interno/saldos`) sufre el mismo problema. En cambio el snapshot MEF sí
tiene devengado real por `sec_func + mes`, pero no está expuesto por meta al
front.

**Decisión del usuario:** *"Todas en orden A→B→C — primero sync SIAF por meta,
luego vista dual, luego microcopy explicativo."*

**Plan concreto:**

**A · Vista Postgres `siaf.v_ejecucion_meta_anual`** (o materializada, según
volumen):
```
SELECT ano_eje, sec_ejec, sec_func,
       SUM(monto_pia)                       FILTER (WHERE mes_eje = 0) AS pia,
       SUM(monto_pim)                       FILTER (WHERE mes_eje = 0) AS pim,
       SUM(monto_certificado)               FILTER (WHERE mes_eje > 0) AS certificado,
       SUM(monto_comprometido_anual)        FILTER (WHERE mes_eje > 0) AS comprometido,
       SUM(monto_devengado)                 FILTER (WHERE mes_eje > 0) AS devengado,
       SUM(monto_girado)                    FILTER (WHERE mes_eje > 0) AS girado,
       MAX(sincronizado_en) AS sincronizado_en
FROM siaf.ejecucion_presupuestal
WHERE ano_eje = :ano AND sec_ejec = :sec_ejec
GROUP BY ano_eje, sec_ejec, sec_func;
```
Nota: respeta la regla de granularidad SIAF (§5 CLAUDE.md).

**B · Nuevo repo `ejecucion_mef_repo.ejecucion_por_meta(ano, sec_funcs)`** —
devuelve `dict[sec_func, {pia, pim, cert, compr, dev, girado}]`. `saldos_service`
lo llama con la lista de `sec_func` visibles y hace `LEFT JOIN` en Python al
listado SIGA. La respuesta de `/interno/saldos` agrega columnas:
- `pim_siga` (lo que ya se llama `pim`)
- `pim_mef` (nuevo, del snapshot)
- `devengado_siga` (cert+compr actual)
- `devengado_mef` (nuevo, snapshot)
- `porcentaje_devengado_mef` (nuevo, oficial)
El semáforo pasa a evaluarse sobre `devengado_mef / pim_mef` si el dato existe,
si no, fallback a SIGA.

**C · Microcopy en la tabla y en el widget** — al lado del encabezado
"Ejecución interna (SIGA)" y "Devengado oficial (MEF)" un `TerminoMef` o
tooltip corto: *"MEF es el número que ve el ciudadano (portal transparencia).
SIGA es lo que la unidad tiene asignado internamente. Pueden diferir cuando
el pliego aún no desagrega el techo a metas."* — texto que ya existe en el
widget, hay que asegurar que la tabla de saldos también lo tenga.

**Dependencia:** el snapshot MEF tiene 6 días de rezago (última sincronización
2026-07-14). Confirmar frecuencia del job (`sync_ejecucion_mef` en APScheduler)
y si conviene subirla a diario. Anotar como issue backend si el rezago es
mayor a 2 días.

---

### 3.5 · Contratos por vencer sin filtro por CC (issue ya anotado)

Ya está documentado en `Docs/guia-frontend-interno.md` §5.2, no lo reabro
aquí, pero conviene resolverlo cuando toque T-53. La memoria del proyecto
lo trae también.

**Dato nuevo:** solo hay 30 contratos activos en 2026, muy pocos para
justificar un CTE complejo. La opción #2 del §5.2 de la guía (vía
`SIG_ORDENES` → JOIN CC) es la que menos duplicaciones produce.

---

## 4. Lo que NO está roto pero conviene puntualizar

Cosas que no son bugs pero se malinterpretan al leer el código:

1. **`SIG_TECHO_PRESUPUESTO` no tiene granularidad mensual.** No tiene
   columna `mes_eje`. Es una foto acumulada a la fecha, con PK
   `(ano, sec_ejec, sec_func, clasificador, cc)`. Toda comparación
   "mensual" tiene que venir de `siaf.ejecucion_presupuestal`.
2. **1.782 pedidos aprobados en `SIG_SEGUIMIENTO t=2` vs. 1.763 con ESTADO=1
   en `SIG_PEDIDOS`.** Diferencia de 19 — son pedidos que se aprobaron y
   luego pasaron directo a ESTADO=7 sin volver a estado=1. Es esperado, no
   corregir.
3. **CCMN totales 2026 (1.988) < filas en el puente (6.431).** El puente
   guarda una fila por SEC_CUA_MOD_SAL × CCMN, no un solo mapping. Es lo
   que causa que un pedido con 1 sola línea tenga en promedio 3.86 CCMN
   candidatos.
4. **Fill rate de match pedido→orden ya se documenta en la card.**
   `match_metodo` = `'pecosa' | 'composite' | 'declarado' | null`. En el
   front se puede pintar como tooltip discreto para debug.
5. **`SIG_DEVENGADO` está vacía en 2026 para el 232/S.** No es una tabla en la
   que se pueda confiar en esta muni. El backend ya usa
   `SIG_EXP_SIGA_DOCU.TIPO_OPERACION='DV'` como proxy para bienes; para
   servicios no aplica.

---

## 5. Preguntas abiertas para el próximo pase

Cosas que quedan como TODO explícito y que hay que decidir antes de tocar
código:

1. **Fórmula exacta del "cierre operativo" para servicios.** El diccionario
   dice `devengado_SIAF >= TOTAL_FACT_SOLES`. ¿Ese devengado por orden se
   toma de `siaf.ejecucion_presupuestal` cruzando por `exp_siaf` de la
   orden? Verificar si el snapshot tiene la granularidad orden↔meta que
   necesitamos, o si hay que traer un dataset SIAF adicional (por
   `expediente`).
2. **Frecuencia del sync MEF.** Hoy tiene 6 días de rezago. ¿El job
   `sync_ejecucion_mef` corre semanal o diario? Si es semanal, subirlo a
   diario 03:00 sería low-hanging fruit. Confirmar en `backend/app/jobs/`.
3. **Anotaciones internas de pedido (HU-10):** ¿alcance por usuario o por
   unidad? Ya está en la guía §7 como abierta. No bloquea T-46 en su forma
   actual pero sí T-47 (marcar alertas revisadas).
4. **Testigo 232/S en producción.** Correr la nueva lógica de composite
   estricto y confirmar que sigue matcheando CCMN=2266. Si falla, revisar
   umbral de tolerancia de fecha (¿48 h? ¿5 días?).

---

## 6. Plan de acción propuesto (priorizado)

Orden pensado para maximizar valor por línea escrita:

### Iteración A — Pipeline confiable
1. **Fix fechas por etapa** (§3.1) — 1 sesión.
   Impacto: elimina ~1.700 falsos estancados; el kanban se vuelve creíble.
2. **Composite estricto CCMN** (§3.2) — 1 sesión.
   Impacto: las columnas de programación dejan de sobrevender.
3. **Testigos 232/S y 010/B end-to-end** con las dos correcciones anteriores
   — smoke test manual + tests unitarios.

### Iteración B — Saldos precisos
4. **Vista `siaf.v_ejecucion_meta_anual`** + repo + wire al service (§3.4·A+B)
   — 1 sesión.
5. **Nueva UI de saldos con columnas duales** + microcopy (§3.4·C)
   — 1 sesión.

### Iteración C — Cierre operativo y contratos
6. **Flag `cierre_operativo` en pipeline** (§3.3) — 0.5 sesión.
7. **Contratos por CC** (§3.5) — reservado para T-53.

Todo esto sin salirse del alcance del plan T-44..T-55 (ver
`Docs/guia-frontend-interno.md` §2). La iteración A pertenece a la mejora
de T-45/T-46; la B corresponde a T-48; la C se mezcla con T-47 y T-53.

---

## 7. Comandos útiles para reproducir el diagnóstico

```bash
# SIGA: cifras del universo pipeline
sqlcmd -S localhost -E -d SIGA_300687 -W -Q "SELECT ESTADO, COUNT(*) FROM SIG_PEDIDOS WHERE ANO_EJE=2026 AND SEC_EJEC=300687 GROUP BY ESTADO"

# SIGA: fill rate FECHA_APROB / FECHA_ATENC por estado
sqlcmd -S localhost -E -d SIGA_300687 -W -Q "SELECT ESTADO, COUNT(*), COUNT(FECHA_APROB), COUNT(FECHA_ATENC) FROM SIG_PEDIDOS WHERE ANO_EJE=2026 AND SEC_EJEC=300687 AND ESTADO IN ('0','1','7') GROUP BY ESTADO"

# SIGA: CCMN candidatos por pedido (composite débil)
sqlcmd -S localhost -E -d SIGA_300687 -W -i scripts/diagnostico/ccmn_candidatos.sql

# Postgres: snapshot MEF
docker exec sicop_postgres_dev psql -U sicop -d sicop -c "SELECT COUNT(*), SUM(CASE WHEN mes_eje=0 THEN monto_pim END) pim, SUM(CASE WHEN mes_eje>0 THEN monto_devengado END) dev FROM siaf.ejecucion_presupuestal WHERE ano_eje=2026 AND sec_ejec='300687';"

# Postgres: umbrales activos
docker exec sicop_postgres_dev psql -U sicop -d sicop -c "SELECT codigo_alerta, parametros FROM sistema.umbrales_alertas;"
```

Los resultados de referencia (con fecha) están en §2 de este documento.

---

## 8. Referencias

- `Docs/exploracion-siga-pipeline-extendido.md` §16-§17 — mapa canónico de
  tablas y testigos verificados.
- `Docs/hallazgos-granularidad-siaf.md` §4 — reglas de agregación SIAF
  (PIA/PIM en mes=0, ejecución en meses>0).
- `Docs/guia-frontend-interno.md` §5-§6 — bitácora de issues y decisiones
  del interno. Esta carpeta separada (`Docs/diagnostico-2026-07-20/`) es
  complementaria, no la reemplaza.
- Memoria del proyecto:
  - `project-siga-servicios-cierre.md` — regla cierre por devengado.
  - `project-cruce-mef-siga.md` — widget dual.
  - `project-umbrales-por-macrofase.md` — umbrales JSON por macrofase.
- Código clave citado:
  - [backend/app/repositories/pipeline_repo.py](../../backend/app/repositories/pipeline_repo.py)
  - [backend/app/services/pipeline_service.py](../../backend/app/services/pipeline_service.py)
  - [backend/app/repositories/saldos_repo.py](../../backend/app/repositories/saldos_repo.py)
  - [backend/app/services/saldos_service.py](../../backend/app/services/saldos_service.py)
  - [backend/app/repositories/ejecucion_mef_repo.py](../../backend/app/repositories/ejecucion_mef_repo.py)
  - [frontend/src/features/pipeline/PedidoDetalle.tsx](../../frontend/src/features/pipeline/PedidoDetalle.tsx)
  - [frontend/src/features/pipeline/secciones/PipelineKanban.tsx](../../frontend/src/features/pipeline/secciones/PipelineKanban.tsx)
  - [frontend/src/features/dashboard/widgets/WidgetSaldos.tsx](../../frontend/src/features/dashboard/widgets/WidgetSaldos.tsx)

---

*Diagnóstico ejecutado 2026-07-20 con datos reales de la BD. Este documento
vive fuera de `Docs/` "oficial" a propósito — es un snapshot de trabajo,
no doctrina permanente. Cuando las iteraciones A/B/C estén ejecutadas se
puede archivar o migrar sus decisiones a la guía interna.*
