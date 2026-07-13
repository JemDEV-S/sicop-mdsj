# Hallazgos: Granularidad de la API MEF — SIAF Ejecución Presupuestal

**Fecha de descubrimiento:** 2026-07-13  
**Contexto:** Auditoría del endpoint `GET /api/v1/publico/ejecucion/resumen?ano=2026` que devolvía PIA=18.9M en lugar del valor real ~60M.

---

## 1. Estructura real de los datos en el dataset SIAF

El resource `615644aa-ef73-4358-b4e0-0c20931632f3` devuelve filas con dos roles distintos:

| `MES_EJE` | Qué contiene | Qué viene en 0 |
|---|---|---|
| `0` | PIA (`MONTO_PIA`) y PIM (`MONTO_PIM`) | Devengado, Girado, Certificado, Comprometido |
| `1`–`12` | Devengado, Girado, Certificado, Comprometido | PIA y PIM |

Cada fila representa una combinación `sec_func + generica + fuente_financiamiento + especifica + ...` (clasificador de gasto). Por tanto, una sola meta (`sec_func`) puede tener decenas de filas por mes.

### Verificado con datos reales (2026, SEC_EJEC=300687)

```
mes_eje | filas | metas |   pia_mes    |   pim_mes
--------+-------+-------+--------------+--------------
      0 |  2122 |   181 | 65116324.00  | 69500489.00
      1 |   428 |    49 |         0.00 |         0.00
      2 |   820 |    99 |         0.00 |         0.00
      3 |  1204 |   113 |         0.00 |         0.00
      4 |  1331 |   117 |         0.00 |         0.00
      5 |  1528 |   117 |         0.00 |         0.00
      6 |  1152 |   124 |         0.00 |         0.00
      7 |   628 |   120 |         0.00 |         0.00
```

Los montos de ejecución en meses 1–7 son **flujos del período mensual**, no acumulados del año. Para la misma meta, el devengado de julio es el devengado ejecutado en julio, no el total enero–julio.

---

## 2. Bug original en `ejecucion_service.py`

El CTE `_ULTIMOS_MESES_CTE` seleccionaba `MAX(mes_eje)` por `sec_func`:

- Para las 138 metas **con ejecución**: `max_mes = 7` → tomaba la fila mensual → PIA=0, PIM=0
- Para las 43 metas **sin ejecución aún**: `max_mes = 0` → tomaba la fila maestra → PIA real

Resultado: solo el PIA de las 43 metas inactivas sumaba al total → PIA=18.9M en lugar de 65.1M.

Adicionalmente, el devengado del endpoint era solo el de julio (1.7M) en lugar del total anual (30.8M).

### Snapshot incorrecto que devolvía el endpoint

```json
{ "pia": 18922280, "pim": 5955212, "devengado": 1694973, "girado": 3417030 }
```

### Snapshot correcto tras el fix

```json
{ "pia": 65116324, "pim": 69500489, "certificado": 43406692, "devengado": 30798719, "girado": 30133083, "porcentaje_ejecucion": 44.31 }
```

---

## 3. Solución implementada

Archivo: `backend/app/services/ejecucion_service.py`

Reemplazado `_ULTIMOS_MESES_CTE` por `_PRESUPUESTO_EJECUCION_CTE` bifurcado:

```sql
-- CTE maestros: PIA y PIM desde mes_eje=0, agregados por sec_func
WITH maestros AS (
    SELECT sec_func, SUM(monto_pia) AS monto_pia, SUM(monto_pim) AS monto_pim, ...
      FROM siaf.v_ejecucion_normalizada
     WHERE ano_eje = :ano AND sec_ejec = :sec_ejec AND mes_eje = 0
     GROUP BY sec_func
),
-- CTE ejecucion: suma de TODOS los meses > 0, agregados por sec_func
ejecucion AS (
    SELECT sec_func,
           SUM(monto_devengado) AS monto_devengado,
           SUM(monto_girado)    AS monto_girado,
           SUM(monto_certificado) AS monto_certificado, ...
      FROM siaf.v_ejecucion_normalizada
     WHERE ano_eje = :ano AND sec_ejec = :sec_ejec AND mes_eje > 0
     GROUP BY sec_func
),
-- vigentes: JOIN LEFT para incluir metas sin ejecución (devengado=0)
vigentes AS (
    SELECT m.*, COALESCE(e.monto_devengado, 0) AS monto_devengado, ...
      FROM maestros m LEFT JOIN ejecucion e ON e.sec_func = m.sec_func
)
```

---

## 4. Reglas de agregación — referencia permanente

| Columna MEF | Dónde está el valor | Cómo agregar |
|---|---|---|
| `MONTO_PIA` | Solo en `MES_EJE=0` | `SUM` de todas las filas con `mes_eje=0`, `GROUP BY sec_func` |
| `MONTO_PIM` | Solo en `MES_EJE=0` | Igual que PIA |
| `MONTO_DEVENGADO` | En cada mes `> 0` (flujo mensual) | `SUM` de **todos** los meses `> 0`, `GROUP BY sec_func` |
| `MONTO_GIRADO` | En cada mes `> 0` (flujo mensual) | Igual que devengado |
| `MONTO_CERTIFICADO` | En cada mes `> 0` (flujo mensual) | Igual que devengado |
| `MONTO_COMPROMETIDO_ANUAL` | En cada mes `> 0` | Igual que devengado |
| `MONTO_COMPROMETIDO` | En cada mes `> 0` | Igual que devengado |

> **Trampa frecuente:** tomar solo el `MAX(mes_eje)` para evitar duplicar PIA/PIM produce el efecto contrario: elimina el PIA/PIM de las metas con ejecución (que tienen `max_mes > 0`) y conserva solo el de las inactivas.

---

## 5. Comportamiento adicional verificado

- **`MONTO_GIRADO` puede superar a `MONTO_DEVENGADO` en un mes concreto.** Es válido: el girado de un mes puede incluir pagos de devengados de meses anteriores. La relación `girado ≤ devengado` se cumple en el acumulado anual, no necesariamente mes a mes.
- **No todas las metas aparecen en todos los meses.** Una meta con `max_mes=0` no tiene ejecución registrada aún — es correcto incluirla con devengado=0 (LEFT JOIN).
- **La granularidad más fina es `sec_func + generica + fuente_financiamiento + especifica_det + mes_eje`.** Nunca hay una sola fila por meta por mes.
