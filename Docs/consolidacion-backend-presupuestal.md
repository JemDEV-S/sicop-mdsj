# Consolidación del backend presupuestal — auditoría y plan

> **Fecha:** 2026-08-04
> **Objetivo:** antes de construir el frontend de Saldos (T-48), Cruce
> SIAF-SIGA (T-50/T-51), Proveedores (T-53) y Contratos, dejar el backend
> **coherente y consistente** — que "un mismo concepto signifique lo mismo en
> todas las pantallas". Se corrige la lógica de negocio, no la frescura de los
> datos (ver §0).
> **Alcance:** solo backend. El frontend arranca cuando este documento esté
> ejecutado y con tests verdes.

---

## 0. Marco: qué SÍ consolidamos y qué NO

**Contexto de datos:** el desarrollo corre sobre un **backup del SIGA**, no
sobre la BD real (la conexión directa vendrá después). En consecuencia:

- **NO es objetivo de esta fase** la frescura/rezago de los datos: el snapshot
  MEF con 21 días de rezago y meses 0..7, o el SIGA "de hace unos meses", son
  la condición de trabajo actual, no defectos a corregir.
- **SÍ es objetivo** todo lo que sea **lógica de negocio, coherencia entre
  módulos y consistencia de reglas** — eso seguirá siendo válido cuando se
  conecte la BD real y es lo que evita construir frontend sobre arena.

**Regla de oro heredada (CLAUDE.md §3, memoria del proyecto):** el presupuesto
sale SIEMPRE del MEF. SIGA aporta proceso, fechas, estados y llaves de cruce.
Toda cifra presupuestal en pantalla debe poder trazarse al snapshot MEF.

**Patrón de referencia: el portal público (ya concluido).** El servicio
[ejecucion_service.py](../backend/app/services/ejecucion_service.py) es el
estándar correcto que el interno debe replicar:

- Fuente única `siaf.v_ejecucion_normalizada`.
- Granularidad SIAF respetada: PIA/PIM desde `mes_eje=0`; ejecución sumando
  todos los `mes_eje > 0` (ver `Docs/hallazgos-granularidad-siaf.md` §4).
- **Cada fase de ejecución lleva su nombre propio y correcto:** `certificado`,
  `comprometido_anual`, `comprometido`, `devengado`, `girado`. Nunca renombra
  una fase como otra.
- `porcentaje_ejecucion = devengado / pim` (el devengado **real**, no un proxy).

El backend interno debe converger a este patrón. No reinventamos; copiamos lo
que ya funciona y está validado en producción pública.

---

## 0.1 · Corrección conceptual: la cadena de ejecución presupuestaria

Las fases del gasto público son secuenciales y **no son intercambiables**:

```
Certificación  →  Compromiso  →  Devengado  →  Girado
(hay crédito)     (se obliga)    (se recibió    (se pagó)
                                  el bien/serv.)
```

Certificación y compromiso son fases **anteriores**; el devengado es
**posterior** (nace cuando el bien/servicio se recibió y hay obligación de
pago). Por eso:

> **`cert + comprometido` NO es "devengado".** Etiquetarlo así es un error
> conceptual que confunde al funcionario y contradice el portal público. Son
> tres fases distintas y deben mostrarse con sus tres nombres.

Este error está hoy en `saldos_repo` y en el proxy del widget. La consolidación
lo elimina (ver §1.1 y §3).

---

## 1. Incoherencias verificadas (leyendo el código)

Cada una está confirmada citando el archivo y la línea. No son hipótesis.

### 1.1 · "Devengado" significa tres cosas distintas — y ninguna es la correcta 🔴 CRÍTICO

El concepto más central del sistema tiene tres definiciones conviviendo, **dos
de ellas conceptualmente erróneas** (ver §0.1):

| Módulo | Lo que llama "devengado" | ¿Correcto? | Ubicación |
|---|---|---|---|
| Saldos (lista) | `cert + comprometido` | ❌ son fases previas | [saldos_repo.py:109](../backend/app/repositories/saldos_repo.py#L109) |
| Cruce por meta | `SUM(MNTO_ACUM_DEVGDO_SIGA)` → **siempre 0** | ❌ columna vacía | [cruce_repo.py:196](../backend/app/repositories/cruce_repo.py#L196) |
| Resumen MEF / pipeline | `SUM(monto_devengado)` mes>0 | ✅ devengado real | [ejecucion_mef_repo.py:53](../backend/app/repositories/ejecucion_mef_repo.py#L53) |

**El único correcto es el del MEF** — el mismo que usa el portal público.

**Dos consecuencias concretas:**

1. **Saldos** presenta `cert+compr` bajo la etiqueta "devengado" y calcula el
   semáforo con ese número inflado (compromiso ≥ devengado, casi siempre) →
   el % de "ejecución" del interno **no cuadra con el portal público** que ve
   el ciudadano. El funcionario y el vecino ven números distintos del mismo
   gasto.
2. **Cruce** ("Vista consolidada de meta", T-51) mostrará **devengado = S/ 0
   en toda meta**, porque usa la columna que el propio `saldos_repo` ya
   documentó como no poblada
   ([saldos_repo.py:18-19](../backend/app/repositories/saldos_repo.py#L18)).

La corrección es única para los dos: **traer el devengado real del snapshot MEF
por meta** (la vista de la Iteración 1) y mostrar cert/compr con sus nombres
propios como fases previas, no como devengado.

### 1.2 · El devengado oficial (MEF) no existe por meta 🔴 BLOQUEANTE

`ejecucion_mef_repo` solo tiene `resumen_mef` — el **total del pliego**. No hay
forma de pedir la ejecución MEF de UNA meta (`sec_func`).

**Consecuencia:** `resumen_saldos` **oculta el bloque MEF a cualquier usuario
con filtro de CC** ([saldos_service.py:93-97](../backend/app/services/saldos_service.py#L93)),
porque no puede desagregarlo a la subrama del usuario. Un **decisor de una
gerencia nunca ve el número oficial** — solo el admin sin filtro. Esto rompe la
promesa dual "lo mío (SIGA) vs. lo oficial (MEF)" para casi todos los usuarios.

Esta es la **pieza faltante que desbloquea Saldos Y Cruce a la vez**: una vista
`siaf.v_ejecucion_meta_anual` que agregue el snapshot por `sec_func`.

### 1.3 · Dos rutas distintas para el mismo cruce meta↔MEF ⚠️ MEDIO

El pipeline (`pipeline_v2.py`) ya cruza MEF↔meta por celda para el detalle de
pedido, con su propia lógica. `cruce_repo` va directo a SIGA sin pasar por MEF.
Cuando construyamos Saldos con la vista nueva, existirían **tres** rutas hacia
el mismo dato. Hay que converger a una: la vista + un repo común.

### 1.4 · Semáforo de saldos evalúa sobre base inconsistente ⚠️ MEDIO

`_con_semaforo` en saldos ([saldos_service.py:26](../backend/app/services/saldos_service.py#L26))
colorea sobre `porcentaje_devengado`, que en la lista es `(cert+compr)/PIM_SIGA`.
Pero el `resumen_saldos` colorea sobre `devengado_MEF/PIM_MEF`
([saldos_service.py:100](../backend/app/services/saldos_service.py#L100)). El
mismo semáforo en el mismo módulo mide dos porcentajes distintos según sea fila
o resumen. Al unificar la fuente, el semáforo debe evaluar siempre el mismo %.

### 1.5 · `contratos_por_vencer` usa `GETDATE()` sobre datos de backup ⚠️ BAJO

[contratos_repo.py:113](../backend/app/repositories/contratos_repo.py#L113)
filtra `FECHA_FINAL >= GETDATE()`. Sobre un backup viejo, casi todas las fechas
finales ya pasaron → el widget devolverá **0 contratos por vencer** de forma
permanente, aunque haya contratos vigentes en el corte del backup. No es un bug
de lógica, pero da una pantalla vacía engañosa en desarrollo. **Decisión a
tomar** (§4): parametrizar la "fecha de referencia" o documentar el
comportamiento esperado.

---

## 2. Lo que ya está coherente (no tocar)

- **Exclusión `SEC_FUNC IS NULL`** (techo de pliego sin desagregar): aplicada
  consistente en saldos ([saldos_repo.py:67](../backend/app/repositories/saldos_repo.py#L67)).
- **Granularidad SIAF** (PIA/PIM en mes 0, ejecución en meses>0): correcta en
  `ejecucion_mef_repo` y respeta CLAUDE.md §5.
- **Filtro por CC**: presente en saldos y cruce (`centros=None` admin,
  `centros=[]` sin acceso).
- **Normalización de keys SQL Server → snake_case** (`_norm`): patrón uniforme
  en los routers de cruce y proveedores.
- **Proveedores y contratos**: las queries en sí son correctas y usan las
  llaves oficiales (`PROVEEDOR`, `NRO_RUC`, FK a `SIG_CONTRATISTAS`).

---

## 3. Plan de consolidación (por iteración)

Orden pensado para que cada pieza habilite la siguiente. Todo con smoke test +
test unitario en las zonas críticas (adaptador SIGA / cruce autoritativo, según
CLAUDE.md "Cómo trabajar").

### Iteración 1 — Fuente única: ejecución MEF por meta 🔑 ✅ HECHA [2026-08-04]

**La pieza que desbloquea todo.** Decisión tomada: **vista SQL**.

> **Estado:** implementada y verificada contra la BD real.
> - Migración `a9f1c7d3e8b4_ejecucion_meta_anual` crea `siaf.v_ejecucion_meta_anual`.
> - `ejecucion_mef_repo`: nuevo `ejecucion_por_meta(db, ano, sec_funcs)` y
>   `resumen_mef` reescrito sobre la vista (fuente única).
> - **Regresión OK:** la vista suma exactamente igual que el portal público
>   (DELTA=0.00 en PIA/PIM/cert/dev/girado; 181 metas). Devengado real 2026 =
>   S/ 30,891,090.60 → 44.45% (no el % inflado de cert+compr).
> - 8 tests unitarios nuevos verdes + suite completa sin regresiones nuevas
>   (el fallo de `test_sync_invierte` es preexistente, no relacionado).

1. **Migración Alembic** `siaf.v_ejecucion_meta_anual`:
   ```sql
   CREATE VIEW siaf.v_ejecucion_meta_anual AS
   SELECT ano_eje, sec_ejec, sec_func,
          SUM(monto_pia)                FILTER (WHERE mes_eje = 0) AS pia,
          SUM(monto_pim)                FILTER (WHERE mes_eje = 0) AS pim,
          SUM(monto_certificado)        FILTER (WHERE mes_eje > 0) AS certificado,
          SUM(monto_comprometido_anual) FILTER (WHERE mes_eje > 0) AS comprometido,
          SUM(monto_devengado)          FILTER (WHERE mes_eje > 0) AS devengado,
          SUM(monto_girado)             FILTER (WHERE mes_eje > 0) AS girado,
          MAX(sincronizado_en)                                     AS sincronizado_en
   FROM siaf.ejecucion_presupuestal
   GROUP BY ano_eje, sec_ejec, sec_func;
   ```
   Respeta la regla de granularidad. Una fila por meta.
2. **`ejecucion_mef_repo.ejecucion_por_meta(db, ano, sec_funcs)`** → devuelve
   `dict[sec_func, {pia, pim, cert, compr, dev, girado, sincronizado_en}]`.
   Recibe la lista de `sec_func` visibles y filtra en la vista.
3. **`resumen_mef` se reescribe sobre la vista** (misma cifra, una sola fuente)
   para no tener dos SQL que sumen el snapshot.
4. **Test:** el total agregado de la vista == el total de `resumen_mef` actual
   (regresión: no cambiamos el número del pliego, solo lo desagregamos).

### Iteración 2 — Saldos duales reales por meta ✅ HECHA [2026-08-04]

> **Estado:** implementada y verificada contra la BD real.
> - **Camino elegido** (validado con datos): lista agregada **por meta**
>   (`sec_func`), cruce `sec_func↔sec_func` verificado **159/159 metas SIGA con
>   PIM cruzan 100% con MEF**. Evita multiplicar el devengado ×9.6 (filas
>   clasificador×CC por meta).
> - `saldos_repo`: `listar_saldos` agrega por meta y expone `certificado` /
>   `comprometido` con su nombre propio (sin "devengado"). `resumen_saldos` y
>   `metas_con_saldo` (antes `metas_rezagadas`) devuelven candidatas; el % y la
>   criticidad salen del MEF en el service. `contar_saldos` cuenta metas.
> - `saldos_service`: LEFT JOIN con `ejecucion_por_meta`; `porcentaje_devengado`
>   y semáforo sobre `devengado_mef/pim_mef`; **el bloque MEF ya aparece con
>   filtro de CC** (restringido a las metas visibles, ya no se oculta a
>   decisores).
> - `schemas`: `SaldoItem` con columnas duales `_mef` explícitas; `porcentaje`
>   nullable (meta sin cruce ⇒ None, no se inventa con cert+compr).
> - **Frontend**: `WidgetSaldos` deja de mostrar "Cert.+Comprometido" como
>   devengado; ahora muestra Certificado y Comprometido separados. `types.ts`
>   alineado. Typecheck TS limpio.
> - **Verificado en BD:** % global 44.45% = idéntico al portal público; meta
>   129 = 44.87% (dev_mef/pim_mef exacto); 60 metas críticas (<30% real).
>   7 tests de service nuevos + suite sin regresiones nuevas.

5. **`saldos_service.listar_saldos`** hace `LEFT JOIN` en Python: por cada fila
   SIGA (por `sec_func`), adjunta el bloque MEF de la vista. La respuesta gana:
   `pim_mef`, `devengado_mef`, `porcentaje_devengado_mef`.
   **Renombrado obligatorio en SIGA (§0.1):** la columna que hoy se llama
   `devengado` (= cert+compr) desaparece; en su lugar se exponen `certificado`
   y `comprometido` con sus nombres propios. Ningún campo SIGA vuelve a
   llamarse "devengado". El devengado, único y oficial, es `devengado_mef`.
6. **Semáforo unificado** (§1.4): evalúa `devengado_mef / pim_mef` cuando el
   dato MEF existe; fallback a SIGA solo si la meta no está en el snapshot.
   Mismo criterio en fila y en resumen.
7. **`resumen_saldos` deja de ocultar MEF a usuarios con CC** (§1.2): ahora
   suma la vista restringida a los `sec_func` visibles del usuario.
8. **Test:** decisor con CC ve bloque MEF ≠ null; suma de filas MEF == bloque
   MEF del resumen para el mismo alcance.

### Iteración 3 — Cruce alineado con MEF ✅ HECHA [2026-08-04]

> **Estado:** implementada y verificada contra la BD real.
> - `cruce_repo.consolidado_por_meta`: el bloque `presupuesto` deja de usar
>   `MNTO_ACUM_DEVGDO_SIGA` (daba devengado=0); expone cert + comprometido SIGA
>   con nombre propio.
> - Nuevo `cruce_service.consolidado_por_meta`: adjunta el devengado MEF real
>   desde la vista (Iter.1); % sobre `devengado_mef/pim_mef`. El router pasa a
>   usar el service (con `db`).
> - `PresupuestoMeta` schema: dual explícito (SIGA + `*_mef`), % nullable.
> - **Convergencia (§1.3):** `pipeline_read_repo.devengado_mef_por_sec_func`
>   ahora **delega en `ejecucion_por_meta`** (firma `dict[sec_func,float]`
>   intacta). Se elimina la 3.ª copia del SUM de devengado; verificado
>   equivalente al centavo (20 metas, 0 diferencias). 37 tests de pipeline
>   siguen verdes.
> - **Coherencia probada en BD (criterio §1.1):** para la meta 129,
>   `cruce.devengado_mef == saldos.devengado_mef == snapshot.devengado ==
>   2,423,595.91` y `% = 44.87%` en los tres. Los tres módulos cuadran.
> - 4 tests de cruce_service nuevos + suite sin regresiones nuevas.

9. **`cruce_repo.consolidado_por_meta`**: el bloque `presupuesto` deja de leer
   `MNTO_ACUM_DEVGDO_SIGA` (§1.1). Pasa a:
   - `devengado_mef`, `pim_mef`, etc. desde la vista (fuente única).
   - Conserva `certificado`/`comprometido` de SIGA como "referencia operativa".
   Decisión tomada: **alinear con MEF**.
10. **Converger la ruta** (§1.3): `consolidado_por_meta` y el cruce del pipeline
    consumen el mismo `ejecucion_por_meta`. Sin triplicar SQL.
11. **Test:** para una meta testigo, `devengado` del consolidado == el que
    muestra el widget de saldos == el del snapshot MEF. Los tres cuadran.

### Iteración 4 — Proveedores y contratos (coherencia menor)

12. **Contratos por vencer** (§1.5): decidir referencia temporal (§4) y aplicar.
13. **Revisión de consistencia proveedores↔contratos↔órdenes**: verificar que
    el `monto_acumulado` del proveedor (SUM de órdenes) y el `VALOR_SOLES` de
    sus contratos no se presenten como si fueran lo mismo en el frontend
    futuro. Documentar la diferencia (orden ≠ contrato) para T-53.

---

## 4. Decisiones abiertas antes de tocar código

1. **Referencia temporal de "contratos por vencer" sobre backup** (§1.5):
   ¿parametrizamos una `fecha_referencia` (default hoy, override en dev al corte
   del backup), o documentamos que en dev el widget puede salir vacío y punto?
2. **Materializar la vista**: ¿`VIEW` normal o `MATERIALIZED VIEW`? Con 9.249
   filas la vista normal es instantánea; se propone **VIEW normal** y se escala
   a materializada solo si el volumen multi-año lo pide.
3. **Nombre de columnas duales en la API**: ¿`pim_mef`/`pim_siga` explícitos, o
   `pim` (MEF, oficial) + `pim_operativo` (SIGA)? Se propone **sufijos
   explícitos** (`_mef`/`_siga`) para que el frontend no adivine la fuente.

---

## 5. Criterio de "consolidación terminada"

El backend está listo para el frontend cuando:

- [x] `siaf.v_ejecucion_meta_anual` existe y `ejecucion_por_meta` la consume.
- [x] Una meta testigo muestra el **mismo devengado** en saldos, cruce y MEF
      (meta 129 = S/ 2,423,595.91 en los tres).
- [x] Un decisor con filtro de CC recibe bloque MEF no nulo.
- [x] El semáforo de saldos evalúa el mismo % (devengado_mef/pim_mef) en fila y
      en resumen.
- [x] Tests unitarios verdes en las tres iteraciones críticas (1, 2, 3).
- [x] Ningún endpoint presupuestal lee ya `MNTO_ACUM_DEVGDO_SIGA` (saldos, cruce
      y pipeline convergen en la vista única).

Falta solo la Iteración 4 (proveedores/contratos, coherencia menor) para cerrar
el documento completo.

Cumplido esto, se arranca el frontend (T-48 → T-51 → T-53) sobre datos que ya
son coherentes entre sí.

---

## 6. Referencias

- `Docs/diagnostico-2026-07-20/pipeline-y-presupuesto-consolidado.md` §3.4
  (origen de la vista por meta).
- `CLAUDE.md` §5 (granularidad SIAF), §3 (fuentes autoritativas).
- Memoria: `project-datos-backup-no-tiempo-real`, `feedback-mef-unica-fuente-presupuesto`,
  `project-cruce-mef-siga`.
- Código auditado: `saldos_repo.py`, `saldos_service.py`, `cruce_repo.py`,
  `ejecucion_mef_repo.py`, `proveedores_repo.py`, `contratos_repo.py`.
