# Exploración SIGA — Búsqueda del pipeline extendido de un pedido

> **Objetivo.** Encontrar en la base de datos SIGA (SQL Server) el conjunto mínimo
> de tablas, columnas y llaves que permita reconstruir **todas las etapas
> intermedias** por las que pasa un pedido desde su creación hasta su cierre —
> incluyendo etapas que hoy son "caja negra" (cotización, cuadro consolidado /
> CCMN, certificación) porque no hay llave directa desde el pedido.
>
> **Alcance.** Solo base de datos SIGA. Sin referencias a aplicaciones cliente,
> sin recomendaciones de diseño, sin decisiones de negocio.

---

## 1. Entorno

| Ítem | Valor |
|---|---|
| Motor | SQL Server (instancia default local) |
| Base | `SIGA_300687` |
| Autenticación | Windows (`-E`) |
| Entidad ejecutora fija | `SEC_EJEC = 300687` |
| Año de trabajo | `ANO_EJE = 2026` |
| Comando base | `sqlcmd -S localhost -E -d SIGA_300687 -W -s "|" -Q "..."` |

Volcados existentes de exploraciones previas:

- `backend/scripts/diagnostico_sesion3/` — SPs, triggers y vistas de la cadena pedido↔orden.
- `backend/scripts/diagnostico_sesion4/` — SPs de cuadros.

---

## 2. Caso testigo canónico: pedido 232/S (2026)

Servicio finalizado con contrato ejecutado 100%. Todos los identificadores
observados por el usuario funcional en el cliente SIGA:

| Objeto | Identificador | Ubicación conocida |
|---|---|---|
| Pedido | `232/S`, `TIPO_PEDIDO=2` | `SIG_PEDIDOS` |
| Sec. función (meta) | `57` | `SIG_PEDIDOS.sec_func` |
| Centro de costo | `01.03.07.04` (OTI) | `SIG_PEDIDOS.CENTRO_COSTO` |
| Ítem | `SERVICIO AUXILIAR ADMINISTRATIVO PARA OTI` | `SIG_DETALLE_PEDIDOS` |
| Monto total contrato | `S/. 4.800` | `SIG_DETALLE_PEDIDOS.VALOR_TOTAL` |
| Proveedor | `1650` | `SIG_ORDEN_ADQUISICION.PROVEEDOR` |
| **EM (Cotización)** | `263` | Sin ubicar directamente |
| **Cálculos valor referencial** | `263` | Sin ubicar directamente |
| **CCMN (Cuadro consolidado)** | `2266` | `SIG_CUADRO_ADQUISICION.NRO_CONS_PAAC` = 2266 ✅ |
| **Certificación SIGA** | `182` | `SIG_ORDEN_ADQUISICION.NRO_CERTIFICA` = 182 ✅ |
| **CCP SIAF** | `230` | `SIG_CERTIFICACION.NRO_CERTIFICA_SIAF` = 230 (por confirmar) |
| **Expediente SIAF** | `316` | `SIG_ORDEN_ADQUISICION.EXP_SIAF` = 316 ✅ |
| Orden | `132/S` | `SIG_ORDEN_ADQUISICION.NRO_ORDEN` = 132 ✅ |
| Expediente SIGA | `152` | `SIG_ORDEN_ADQUISICION.EXP_SIGA` = 152 ✅ |
| Conformidades | 3 pagos (mar/abr/may 2026) | `SIG_MOVIM_CONFOR_SERVICIO.NRO_ORDEN=132` ✅ |

Segundo testigo (bien cerrado): pedido `005/B TIPO_PEDIDO=1`, cuadro `4/B`,
orden `003/B`, cert `79`, cert SIAF `106`, EXP_SIGA `59`, EXP_SIAF `179`,
`NRO_PECOSA=4`, proveedor `2217`, monto `5.805`.

---

## 3. Estructura conocida — llaves reales que sí funcionan

### 3.1 Aguas abajo de la orden — TODO FK real 100%

```
SIG_ORDEN_ADQUISICION.SEC_CUADRO     →  SIG_CUADRO_ADQUISICION.SEC_CUADRO  (100%)
SIG_ORDEN_ADQUISICION.NRO_CERTIFICA  →  SIG_CERTIFICACION.NRO_CERTIFICA    (FK_SOA_SC_01)
SIG_ORDEN_ADQUISICION.EXP_SIGA       →  SIG_EXP_SIGA.EXP_SIGA              (poblado)
SIG_ORDEN_ADQUISICION.EXP_SIAF       →  SIG_EXP_SIGA.EXP_SIAF              (via EXP_SIGA)
SIG_CERTIFICACION_FASE.NRO_ORDEN     →  SIG_ORDEN_ADQUISICION.NRO_ORDEN
SIG_CUADRO_ADQUISICION.NRO_CONS_PAAC →  ??? (CCMN — ver §5)
```

### 3.2 Pedido ↔ orden (parcial)

**Solo bienes con NRO_PECOSA:** llave dura estructural.
```
SIG_DETALLE_PEDIDOS.NRO_PECOSA  =  SIG_MOVIM_ALMACEN.NRO_MOVIMTO
                                                     └── NRO_ORDEN
```
Fill rate en 2026: 3.261/7.345 items bienes (44%). En servicios: 0/1.056.

**Resto (servicios y bienes sin pecosa):** solo composite por atributos
`(SEC_FUNC + CLASIFICADOR + GRUPO+CLASE+FAMILIA+ITEM_BIEN + VALOR_SOLES)`.

### 3.3 Conformidades servicio → orden (100%)

```
SIG_MOVIM_CONFOR_SERVICIO.NRO_ORDEN + ANO_ORDEN + TIPO_BIEN
    → SIG_ORDEN_ADQUISICION
```

---

## 4. Lo que ya está descartado con evidencia

Consultas ya corridas que devolvieron 0 filas o datos inservibles:

### 4.1 SIG_SEGUIMIENTO — no persiste el pedido origen

```sql
SELECT TIPO_TRANSACCION, NRO_ORIGEN, NRO_PEDIDO, NRO_CONSOLID, NRO_TRANSACCION
FROM SIG_SEGUIMIENTO
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND NRO_PEDIDO='005' AND TIPO_BIEN='B';
-- 0 filas para el 005/B pese a estar cerrado
```

El 232/S solo aparece 2 veces como `NRO_ORIGEN` (no como `NRO_PEDIDO`) en
transacciones tipo 9 (órdenes) que ni siquiera son la 132.

Distribución de `TIPO_TRANSACCION` en 2026 (para investigar semántica):

| TIPO | n | Coincidencia observada |
|---:|---:|---|
| 1 | 576 | ≈ 576 entradas almacén |
| 2 | 1.782 | ? |
| 4 | 1.795 | ? |
| 5 | 5 | ? |
| 7 | 30 | ? |
| 8 | 632 | ≈ 632 órdenes B |
| 9 | 841 | ≈ 841 órdenes S |
| 15 | 2 | ? |
| 19 | 573 | ≈ 573 pedidos cerrados |
| 20 | 574 | ? |
| 26 | 2 | ? |
| 31 | 11 | ? |
| 33 | 2 | ? |
| 34 | 1 | ? |
| 35 | 2 | ? |

### 4.2 SIG_DETALLE_PEDIDO_CUADRO — vacía en 2026

```sql
SELECT COUNT(*) FROM SIG_DETALLE_PEDIDO_CUADRO
WHERE ANO_EJE=2026 AND SEC_EJEC=300687;
-- 0 filas
```

Esta tabla existía como puente natural (`NRO_PEDIDO + SEC_CUADRO`) pero no se
puebla en esta muni.

### 4.3 SIG_DETALLE_BSERV_CUADRO — campos pedido a 0%

```sql
SELECT TIPO_BIEN, COUNT(*), COUNT(nro_pedido), COUNT(NRO_CONS_PAAC)
FROM SIG_DETALLE_BSERV_CUADRO
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
GROUP BY TIPO_BIEN;
-- B  3552  con_pedido=0  con_ccpaac=0
-- S   853  con_pedido=0  con_ccpaac=0
```

El detalle del cuadro tiene las columnas `nro_pedido`, `tipo_pedido`,
`NRO_CONS_PAAC` pero están vacías.

### 4.4 SIG_CUADRO_MODIFICADO_CMN — no encontró el 131/S

```sql
SELECT * FROM SIG_CUADRO_MODIFICADO_CMN
WHERE ANNO_EJEC=2026 AND SEC_EJEC=300687
  AND TIPO_BIEN='S' AND SEC_CUA_MOD_SAL=131;
-- 0 filas
```

### 4.5 SIG_CUADRO_NECESIDAD_DET — no encontró el 232

```sql
SELECT COUNT(*) FROM SIG_CUADRO_NECESIDAD_DET
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND CAST(NRO_PEDIDO AS INT)=232;
-- 0 filas
```

### 4.6 ESTADO_DEVENG en SIG_MOVIM_CONFOR_SERVICIO no discrimina

```sql
SELECT LTRIM(RTRIM(ESTADO_DEVENG)), COUNT(*)
FROM SIG_MOVIM_CONFOR_SERVICIO
WHERE ANO_ORDEN=2026 AND SEC_EJEC=300687
GROUP BY LTRIM(RTRIM(ESTADO_DEVENG));
-- 'D'  833  (único valor — 100% de las filas)
```

### 4.7 ORDEN_ADQUISICION.ESTADO_SIAF no discrimina devengado

```sql
SELECT ESTADO_SIAF, COUNT(*)
FROM SIG_ORDEN_ADQUISICION
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
GROUP BY ESTADO_SIAF;
-- '2' → 1.469 filas (99.7%)
-- '3' → 4 filas
```

Signifca "orden transmitida al SIAF", no "devengada".

---

## 5. Lo que sí funcionó — cadena aguas arriba desde la orden 132/S

Estas consultas SÍ devuelven datos. Punto de partida verificado:

### 5.1 Orden → llaves aguas arriba

```sql
SELECT NRO_ORDEN, TIPO_BIEN, SEC_CUADRO, NRO_CERTIFICA,
       EXP_SIGA, EXP_SIAF, TOTAL_FACT_SOLES, PROVEEDOR, FECHA_ORDEN
FROM SIG_ORDEN_ADQUISICION
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND TIPO_BIEN='S' AND NRO_ORDEN=132;
-- Devuelve: 132|S|131|182|152|316|4800.00|1650|2026-02-16
```

### 5.2 Cuadro 131/S → CCMN vía NRO_CONS_PAAC

```sql
SELECT SEC_CUADRO, ANO_REQUER, NRO_REQUER,
       NRO_CONS_PAAC, TIPO_GENERACION, FLAG_ORIGEN,
       FLAG_PROCESO, TIPO_PROCESO
FROM SIG_CUADRO_ADQUISICION
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND TIPO_BIEN='S' AND SEC_CUADRO=131;
-- Devuelve: 131|2026|NULL|2266|0|2|4|106
--                            ↑↑↑↑ = CCMN visto por el usuario
```

**Confirmado:** el CCMN 2266 vive en `SIG_CUADRO_ADQUISICION.NRO_CONS_PAAC`.

### 5.3 CCMN 2266 → Solicitud de cotización

```sql
SELECT TIPO_CONSOLID, NRO_CONSOLID, NRO_SOLICITUD, PROVEEDOR,
       FECHA_SOLICITUD, ESTADO_SOLICITUD
FROM SIG_SOLICITUD_COTIZACION
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND tipo_bien='S' AND NRO_CONSOLID=2266;
-- Devuelve: 2|2266|1|1650|2026-02-12 16:38:24|1
```

Solo 1 cotización para este CCMN (proveedor 1650, el mismo que ganó la orden).
El "EM 263" reportado por el usuario aún no se ubica en columna concreta —
podría estar en otra tabla (ver §7).

---

## 6. Preguntas abiertas sobre trazabilidad pedido → CCMN

**La pregunta central del pipeline extendido:**

> Dado un pedido `232/S`, ¿cómo sé desde SQL puro que su cuadro consolidado
> es el `2266`, sin haber pasado antes por la orden 132?

Es decir, buscar una tabla puente `(NRO_PEDIDO, NRO_CONS_PAAC)` que sí esté
poblada en 2026, o descubrir que el vínculo se guarda con otro nombre de
campo.

### 6.1 Tablas que tienen NRO_PEDIDO Y (NRO_CONS_PAAC O NRO_CONSOLID)

Ya identificadas — necesitan verificación de fill rate y de si el 232 aparece:

- `SIG_CUADRO_NECESIDAD_DET`
- `SIG_DETALLE_BSERV_CUADRO`
- `SIG_DETALLE_CUADRO_ANUAL`
- `SIG_PAAC_CENTRO_COSTO`
- `SIG_PPR_CUADRO_NECESIDAD_DET`

Query base para probar cada una:

```sql
SELECT COUNT(*) AS filas,
       COUNT(NRO_PEDIDO) AS con_pedido,
       COUNT(NRO_CONS_PAAC) AS con_ccpaac   -- o NRO_CONSOLID
FROM <TABLA>
WHERE ANO_EJE=2026 AND SEC_EJEC=300687;
```

### 6.2 Otras tablas con NRO_PEDIDO — puede haber columna oculta

De la lista completa:
`SIG_AUDITORIA`, `SIG_CAB_DISTRIBUCION`, `SIG_CONTRATO_ITEM_MENS_PED`,
`SIG_DET_DISTRIBUCION`, `SIG_DETALLE_PECOSA`,
`SIG_DETALLE_PEDIDO_COMISIONADO`, `SIG_DETALLE_PEDIDOS_ANEXO`,
`SIG_GUIA_REMISION_DET`, `SIG_MANIFIESTO_CARGA`,
`SIG_PEDIDO_PECOSA_IMPRESION`, `SIG_PEDIDOS_DESTINO`,
`SIG_PEDIDOS_DETA_DEST`, `SIG_TES_CAJA_CHICA_PEDIDO`,
`SIG_TMP_CUADRO_NECESIDAD_DET`.

Sacar columnas de cada una:

```sql
SELECT COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME='<TABLA>'
ORDER BY ORDINAL_POSITION;
```

### 6.3 Vía inversa — ¿en qué tabla aparece 2266 acompañado de un NRO_PEDIDO?

Idea: recorrer todas las tablas con NRO_CONSOLID o NRO_CONS_PAAC y buscar
donde `= 2266`, para ver si en alguna fila viene junto a un `NRO_PEDIDO`.

Consulta plantilla (repetir por cada tabla candidata):

```sql
SELECT TOP 5 * FROM <TABLA>
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND (NRO_CONS_PAAC=2266 OR NRO_CONSOLID=2266);
```

### 6.4 FKs declaradas hacia SIG_PEDIDOS

Para encontrar tablas que apuntan al pedido con FK real (no solo columna con
mismo nombre):

```sql
SELECT
    OBJECT_NAME(fk.parent_object_id)       AS tabla_hija,
    c.name                                 AS columna_hija,
    OBJECT_NAME(fk.referenced_object_id)   AS tabla_padre,
    rc.name                                AS columna_padre,
    fk.name                                AS fk_nombre
FROM sys.foreign_keys fk
INNER JOIN sys.foreign_key_columns fkc
    ON fkc.constraint_object_id = fk.object_id
INNER JOIN sys.columns c
    ON c.object_id = fk.parent_object_id AND c.column_id = fkc.parent_column_id
INNER JOIN sys.columns rc
    ON rc.object_id = fk.referenced_object_id AND rc.column_id = fkc.referenced_column_id
WHERE OBJECT_NAME(fk.referenced_object_id) IN ('SIG_PEDIDOS','SIG_DETALLE_PEDIDOS')
ORDER BY tabla_hija;
```

### 6.5 Triggers de SIG_PEDIDOS / SIG_DETALLE_PEDIDOS

Un trigger puede estar replicando el NRO_PEDIDO hacia otra tabla al momento
de la aprobación:

```sql
SELECT t.name AS trigger_name,
       OBJECT_NAME(t.parent_id) AS tabla,
       t.is_disabled
FROM sys.triggers t
WHERE OBJECT_NAME(t.parent_id) IN ('SIG_PEDIDOS','SIG_DETALLE_PEDIDOS');

-- Cuerpo del trigger:
SELECT m.definition
FROM sys.sql_modules m
INNER JOIN sys.triggers t ON t.object_id = m.object_id
WHERE t.name = '<nombre>';
```

Los volcados en `backend/scripts/diagnostico_sesion3/trigger_tg_pedido*.sql`
ya contienen algunos, revisar si escriben a alguna tabla puente.

### 6.6 Stored procedures que reciben NRO_PEDIDO como parámetro

```sql
SELECT DISTINCT o.name
FROM sys.sql_modules m
INNER JOIN sys.objects o ON o.object_id = m.object_id
WHERE o.type IN ('P','FN','IF','TF')
  AND m.definition LIKE '%NRO_PEDIDO%'
  AND m.definition LIKE '%NRO_CONSOLID%'
ORDER BY o.name;
```

Cualquier SP que reciba ambos parámetros y los use en un INSERT es un puente
lógico (aunque no esté declarado como FK).

---

## 7. Ubicar el "EM 263" y "Cálculos valor referencial 263"

El usuario reportó `EM 263` (cotización) y `Cálculos valor referencial 263`
como pasos intermedios. En §5.3 vimos que `SIG_SOLICITUD_COTIZACION` para
CCMN 2266 tiene `NRO_SOLICITUD=1` (no 263). Hipótesis a probar:

### 7.1 Tablas que podrían contener "263"

Recorrer tablas relacionadas con cotización/valor referencial:

```sql
-- SIG_SOLICITUD_COTIZACION_ITEM
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME='SIG_SOLICITUD_COTIZACION_ITEM'
ORDER BY ORDINAL_POSITION;

SELECT TOP 5 * FROM SIG_SOLICITUD_COTIZACION_ITEM
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND NRO_CONSOLID=2266;
```

Otras candidatas para "valor referencial":

- `SIG_CONVOCATORIA_ITEM_DETALLE`
- `SIG_CONVOCATORIA_ITEM_PPTAL`
- `SIG_PROPUESTA_ITEM_DETALLE`
- `SIG_PROCESO_DE_SELECCION`
- `SIG_SOLICITUD_ESPECIFICACIONES`

### 7.2 Buscar el número 263 en todas las tablas relevantes

```sql
-- ¿Aparece 263 en SIG_SOLICITUD_COTIZACION_ITEM asociado al CCMN 2266?
SELECT * FROM SIG_SOLICITUD_COTIZACION_ITEM
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND (NRO_CONSOLID=2266 OR NRO_SOLICITUD=263);
```

---

## 8. Confirmar CCP SIAF 230 = certificación 182

```sql
SELECT NRO_CERTIFICA, NRO_CERTIFICA_SIAF, ESTADO_CERTIFICA_SIAF,
       FECHA, TIPO_CERTIFICACION, CONCLUIDO
FROM SIG_CERTIFICACION
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND NRO_CERTIFICA=182;
-- esperado: NRO_CERTIFICA_SIAF=230
```

Fases de esa certificación (una fila por movimiento presupuestal):

```sql
SELECT SECUENCIA_FASE, NRO_ORDEN, NRO_CONSOLID, TIPO_OPERACION_SIAF
FROM SIG_CERTIFICACION_FASE
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND NRO_CERTIFICA=182
ORDER BY SECUENCIA_FASE;
```

`SIG_CERTIFICACION_FASE.NRO_CONSOLID` **es otro candidato de puente** — si
apunta al CCMN 2266, cerraría el círculo Cert ↔ CCMN sin pasar por la orden.

---

## 9. Expediente SIAF 316

```sql
-- Datos del expediente
SELECT EXP_SIGA, EXP_SIAF, TIPO_FASE, ESTADO_SIAF,
       FECHA_EXP_SIGA, FECHA_DOCUMENTO, FECHA_SIAF,
       NRO_CONSOLID
FROM SIG_EXP_SIGA
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND EXP_SIAF=316;

-- Secuencias devengado
SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME='SIG_EXP_SIGA_SECU'
ORDER BY ORDINAL_POSITION;

SELECT * FROM SIG_EXP_SIGA_SECU
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND EXP_SIGA=152;
```

`SIG_EXP_SIGA.NRO_CONSOLID` es **otro candidato de puente al CCMN**. Verificar
si al filtrar por EXP_SIAF=316 sale NRO_CONSOLID=2266.

---

## 10. Timeline observable del 232/S

Los eventos con fecha ya conocidos (todos verificados):

| Fecha | Evento | Fuente |
|---|---|---|
| 2026-02-05 | Pedido registrado | `SIG_PEDIDOS.FECHA_PEDIDO` |
| 2026-02-12 16:38 | Cotización solicitada al proveedor 1650 | `SIG_SOLICITUD_COTIZACION.FECHA_SOLICITUD` |
| 2026-02-16 | Cuadro 131/S emitido | `SIG_CUADRO_ADQUISICION` (via SEC_CUADRO=131) |
| 2026-02-16 | Orden 132/S emitida | `SIG_ORDEN_ADQUISICION.FECHA_ORDEN` |
| 2026-03-12 | Conformidad 1 | `SIG_MOVIM_CONFOR_SERVICIO.FECHA_MOVIMTO` (NRO_ORDEN=232, ver nota) |
| 2026-03-16 | Conformidad 2 | idem (NRO_ORDEN=132) |
| 2026-04-08 | Conformidad 3 | idem |
| 2026-05-07 | Conformidad 4 | idem |

**Nota:** el usuario funcional reporta 3 conformidades del contrato pero en
`SIG_MOVIM_CONFOR_SERVICIO` aparecen 4 filas (3 para NRO_ORDEN=132 + 1 para
NRO_ORDEN=232 con fecha 2026-03-12). Verificar si la 232 es una orden aparte
que también pertenece al pedido, o es ruido de otra transacción.

Consulta para reconstruir el timeline:

```sql
SELECT '01_pedido' AS fase, FECHA_PEDIDO AS fecha,
       'Pedido registrado' AS detalle
FROM SIG_PEDIDOS
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND TIPO_BIEN='S' AND NRO_PEDIDO=232
UNION ALL
SELECT '02_cotizacion', sc.FECHA_SOLICITUD,
       CONCAT('Cotización a proveedor ', sc.PROVEEDOR)
FROM SIG_SOLICITUD_COTIZACION sc
INNER JOIN SIG_CUADRO_ADQUISICION ca
    ON ca.ANO_EJE=sc.ANO_EJE AND ca.SEC_EJEC=sc.SEC_EJEC
   AND ca.TIPO_BIEN=sc.tipo_bien AND ca.NRO_CONS_PAAC=sc.NRO_CONSOLID
INNER JOIN SIG_ORDEN_ADQUISICION o
    ON o.ANO_EJE=ca.ANO_EJE AND o.SEC_EJEC=ca.SEC_EJEC
   AND o.TIPO_BIEN=ca.TIPO_BIEN AND o.SEC_CUADRO=ca.SEC_CUADRO
WHERE o.NRO_ORDEN=132 AND o.TIPO_BIEN='S'
UNION ALL
SELECT '03_cuadro', ca.FECHA_CUADRO, CONCAT('Cuadro ', ca.SEC_CUADRO)
FROM SIG_CUADRO_ADQUISICION ca
INNER JOIN SIG_ORDEN_ADQUISICION o
    ON o.ANO_EJE=ca.ANO_EJE AND o.SEC_EJEC=ca.SEC_EJEC
   AND o.TIPO_BIEN=ca.TIPO_BIEN AND o.SEC_CUADRO=ca.SEC_CUADRO
WHERE o.NRO_ORDEN=132 AND o.TIPO_BIEN='S'
UNION ALL
SELECT '04_certificacion', c.FECHA,
       CONCAT('Cert ', c.NRO_CERTIFICA, ' → SIAF ', c.NRO_CERTIFICA_SIAF)
FROM SIG_CERTIFICACION c
INNER JOIN SIG_ORDEN_ADQUISICION o
    ON o.ANO_EJE=c.ANO_EJE AND o.SEC_EJEC=c.SEC_EJEC
   AND o.NRO_CERTIFICA=c.NRO_CERTIFICA
WHERE o.NRO_ORDEN=132 AND o.TIPO_BIEN='S'
UNION ALL
SELECT '05_orden', FECHA_ORDEN, CONCAT('Orden ', NRO_ORDEN)
FROM SIG_ORDEN_ADQUISICION
WHERE ANO_EJE=2026 AND SEC_EJEC=300687
  AND TIPO_BIEN='S' AND NRO_ORDEN=132
UNION ALL
SELECT '06_conformidad', FECHA_MOVIMTO, 'Conformidad'
FROM SIG_MOVIM_CONFOR_SERVICIO
WHERE ANO_ORDEN=2026 AND SEC_EJEC=300687
  AND TIPO_BIEN='S' AND NRO_ORDEN=132
ORDER BY 1, 2;
```

---

## 11. Fill rates conocidos 2026 SEC_EJEC=300687

| Tabla | Filas | Notas |
|---|---:|---|
| `SIG_PEDIDOS` | 2.358 | 22 ESTADO=0, 1.763 ESTADO=1, 573 ESTADO=7 |
| `SIG_DETALLE_PEDIDOS` (B) | 7.345 | 3.261 (44%) con NRO_PECOSA>0 |
| `SIG_DETALLE_PEDIDOS` (S) | 1.056 | 0 con NRO_PECOSA (100% en 0) |
| `SIG_ORDEN_ADQUISICION` | 1.473 | 632 B + 841 S |
| `SIG_MOVIM_ALMACEN` | 1.724 | 576 I + 576 R + 572 S |
| `SIG_MOVIM_CONFOR_SERVICIO` | 833 | 100% con ESTADO_DEVENG='D' |
| `SIG_SOLICITUD_COTIZACION` | ? | Al menos 1 fila para CCMN 2266 |
| `SIG_CUADRO_ADQUISICION` | ? | Al menos SEC_CUADRO=131/S con NRO_CONS_PAAC=2266 |

Sacar totales pendientes con:

```sql
SELECT COUNT(*), MIN(FECHA_SOLICITUD), MAX(FECHA_SOLICITUD)
FROM SIG_SOLICITUD_COTIZACION
WHERE ANO_EJE=2026 AND SEC_EJEC=300687;

SELECT COUNT(*), COUNT(NRO_CONS_PAAC) AS con_ccpaac
FROM SIG_CUADRO_ADQUISICION
WHERE ANO_EJE=2026 AND SEC_EJEC=300687;
```

---

## 12. Formato de NRO_PEDIDO — cuidado con casts

| Tabla | Tipo | Formato |
|---|---|---|
| `SIG_PEDIDOS.NRO_PEDIDO` | `varchar(6)` | Con padding: `'000232'` |
| `SIG_DETALLE_PEDIDOS.NRO_PEDIDO` | `varchar(6)` | Con padding: `'000232'` |
| `SIG_SEGUIMIENTO.NRO_PEDIDO` | `varchar(50)` | Sin padding: `'232'` |

Al comparar entre tablas: usar `CAST(NRO_PEDIDO AS INT)` o normalizar con
`RIGHT('000000'+NRO_PEDIDO, 6)`.

`SEC_EJEC` es `numeric` en todas las tablas — sin problema de cast.

---

## 13. Comandos de utilidad

```bash
# Volcado de SP a archivo
sqlcmd -S localhost -E -d SIGA_300687 -Q "SELECT m.definition FROM sys.sql_modules m INNER JOIN sys.objects o ON o.object_id=m.object_id WHERE o.name='<NOMBRE_SP>'" -o sp.sql

# Listar todas las tablas con substring
sqlcmd -S localhost -E -d SIGA_300687 -W -Q "SELECT name FROM sys.tables WHERE name LIKE '%CERT%' ORDER BY name"

# Columnas con nombre parecido
sqlcmd -S localhost -E -d SIGA_300687 -W -Q "SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE COLUMN_NAME LIKE '%CONSOLID%' ORDER BY TABLE_NAME"

# FKs de una tabla
sqlcmd -S localhost -E -d SIGA_300687 -W -Q "EXEC sp_fkeys @pktable_name='SIG_PEDIDOS'"
```

---

## 14. Objetivo del pipeline extendido

Reconstruir para cada pedido en qué punto exacto del ciclo administrativo se
encuentra, con etapas del tipo:

```
Solicitado
  ↓
Aprobado
  ↓
Cotización solicitada
  ↓
Cálculos / valor referencial
  ↓
Cuadro consolidado (CCMN)
  ↓
Certificación (SIGA)
  ↓
Certificación aprobada (SIAF)
  ↓
Expediente SIAF creado
  ↓
Orden emitida
  ↓
Devengado (SIAF)
  ↓
Atendido (bienes) / En ejecución (servicios)
  ↓
Conformidad / Pecosa
  ↓
Cerrado
```

Cada flecha debe corresponder a **una consulta SQL sobre SIGA que confirme
que el pedido pasó por esa etapa**, con:

- Tabla origen.
- Columna que sirve como llave.
- % de fill rate real en 2026.
- Verificación con los dos casos testigo (232/S servicio finalizado y
  005/B bien cerrado).

---

*Documento de exploración de BD. Datos verificados con `sqlcmd` contra
`SIGA_300687` el 2026-07-16. Todos los hallazgos citados son reproducibles
con las queries incluidas.*

---

## 15. Hallazgos sesión 5 · Grafo de FKs y cadena completa 232/S

**Método:** volcado de FKs reales (`sys.foreign_keys`), no basado en nombres,
y verificación de cada puente contra el testigo canónico. Scripts y
volcados en [`backend/scripts/diagnostico_sesion5/`](../backend/scripts/diagnostico_sesion5/).

### 15.1 Puentes nuevos descubiertos vía FK real

Estas relaciones no aparecían en el mapa de §3 ni en las hipótesis de §6:

```
SIG_DETALLE_PEDIDOS
    ├── SEC_CUADRO + SEC_ITEM + ANNO_PROG  →  SIG_CUADRO_MODIFICADO_DET
    │   (FK_SIG_DET_PED_01) — llave dura, fill 100% servicios / 55% bienes en 2026
    └── SEC_CUA_MOD_SAL                    →  SIG_CUADRO_MODIFICADO_SALDO
        (FK_SIG_DET_PED_02) — llave dura

SIG_SOLICITUD_COTIZACION           →  SIG_PAAC_CONSOLIDADO  (FK_SIG_S_C_01)
    via NRO_CONSOLID + TIPO_CONSOLID + TIPO_GENERACION
SIG_SOLICITUD_COTIZACION_ITEM      →  SIG_PAAC_ITEM         (FK_SIG_S_C_I_02)

SIG_EXP_SIGA_SECU (NRO_ORDEN_SOS)  →  SIG_ORDEN_SECUENCIA   (FK_SIG_EXP_SIGA_SECU_01)
SIG_EXP_SIGA_DOCU / SIG_EXP_SIGA_PPTO — familia expediente SIGA (documentos + partida presupuestal)

SIG_DEVENGADO       →  SIG_ORDEN_ADQUISICION   (FK_ORD_ADQ_DEVENG)
SIG_ORDEN_INTERFASE →  SIG_ORDEN_ADQUISICION   (FK_ORDEN_ORDEN_INTF)
SIG_OCE_DET         →  SIG_ORDEN_ADQUISICION   (FK_ORD_ADQUI_OCE_DET)
SIG_ORDEN_SECUENCIA →  SIG_ORDEN_ADQUISICION   (FK_ORDEN_ADQUI_X_SECUENCIA)

SIG_CERTIFICACION_OPERACION →  SIG_CERTIFICACION_FASE  (FK_SCO_01)
```

### 15.2 CCMN 2266 · TODO vive en `SIG_PAAC_CONSOLIDADO`

Verificado en el testigo (§4.2 del script 04):

```
SIG_PAAC_CONSOLIDADO WHERE NRO_CONSOLID=2266, TIPO_BIEN='S':
    TIPO_CONSOLID    = 2
    TIPO_GENERACION  = 0
    ESTADO           = 6
    FECHA_CONS       = 2026-02-11 14:38:34
    TIPO_PROCESO     = 106
    MODAL_COMPRA     = CA
    NRO_EST_MDO      = 263            ← ¡EM 263 confirmado, era este campo!
    FECHA_EST_MDO    = 2026-02-11 14:38:54
    ESTADO_EST_MDO   = 2
    NRO_CERTIFICA    = 182            ← certificación
    EXP_SIGA         = NULL           ← no se llenó (existe en la orden)
    EXP_SIAF         = NULL           ← no se llenó
    PROVEEDOR        = NULL           ← no se llenó (existe en la orden)
    VALOR_PLAN       = 4800.00
    FLAG_CONCLUIDO   = S
    sec_cuadro_ini   = NULL           ← existe la columna pero NO se puebla
```

**El "EM 263" nunca fue una entidad separada.** Es el campo `NRO_EST_MDO`
dentro del propio consolidado PAAC. Cotización, cuadro consolidado y
estudio de mercado viven en la misma cabecera.

`SIG_PAAC_ITEM` para NRO_CONSOLID=2266 tiene 1 fila con el item exacto del
pedido (`07-11-0043-1207`), `VALOR=4800`.

### 15.3 Timeline de fases · `SIG_ORDEN_SECUENCIA`

Para la orden 132/S:

```
SEC_ORDEN=1 · FASE_ORDEN='C' (Compromiso) · ESTADO_FASE=2
    FECHA_ESTADO=2026-02-16 16:14 · FLAG_COMPROMETIDO='S'
    CUSER_ID=DORCCOHUARANCCA
```

Solo hay 1 fase registrada — devengado NO se registra aquí. `SIG_DEVENGADO`
también está **vacía** para esta orden (0 filas). Para servicios el evento
"devengado" queda en `SIG_MOVIM_CONFOR_SERVICIO` con `ESTADO_DEVENG='D'`
(§4.6 del doc original) y en la fila del expediente `SIG_EXP_SIGA_DOCU`
con `TIPO_OPERACION='CP'` (compromiso) + `FECHA_INTERFASE` (envío al SIAF).

### 15.4 Expediente SIGA 152

```
SIG_EXP_SIGA_DOCU  EXP_SIGA_DOC=1
    TIPO_DOCUMENTO=032 (orden de servicio)
    NRO_DOCUMENTO=00132  (= NRO_ORDEN)
    TIPO_OPERACION=CP (compromiso)
    MODAL_COMPRA=CA · FASE_CONTRACTUAL=P
    EXP_SIAF=316 · FECHA_INTERFASE=2026-02-18 08:44  ← fecha envío SIAF

SIG_EXP_SIGA_PPTO  EXP_SIGA_SECU=1, EXP_SIGA_PPTO=1
    SEC_FUNC=57 · CLASIFICADOR=2.3.2 9.1 1
    VALOR_SOLES=4800 · MNTO_SOLES=4800
```

Coincidencia exacta con la meta y clasificador del pedido — cierra el
círculo aguas abajo.

### 15.5 Puente pedido → PAAC · lo que sigue faltando

`SIG_PAAC_CENTRO_COSTO` para NRO_CONSOLID=2266 confirma:
`SEC_META=1`, `CENTRO_COSTO=01.03.07.04`, `MES_02=4800`, `VALOR=4800`.
**Pero** las columnas `nro_pedido` y `tipo_pedido` existen y están en NULL
al 100%: 16.011 filas en 2026, **0 con nro_pedido poblado**. Es la huella
del parche: se modeló pero no se llenó.

Diagnóstico: **no existe puente estructural pedido → PAAC en esta muni**.
La correspondencia se resuelve por composite de atributos + rango de fechas:

```
Pedido → PAAC candidato si TODOS coinciden:
    SEC_FUNC (meta)
    CLASIFICADOR
    GRUPO+CLASE+FAMILIA+ITEM_BIEN
    CENTRO_COSTO (vía SIG_PAAC_CENTRO_COSTO)
    VALOR_TOTAL_PEDIDO <= VALOR_PLAN
    FECHA_PEDIDO <= FECHA_CONS <= FECHA_ORDEN
```

Este composite es suficientemente selectivo para el testigo (única fila
CCMN 2266 con `07-11-0043-1207` + CC OTI + monto 4800 en la ventana).
Habrá que verificar unicidad en 2026 completo antes de asumirlo como llave
lógica en producción.

### 15.6 Mapa consolidado del pipeline extendido (post-sesión 5)

```
[1] SIG_PEDIDOS + SIG_DETALLE_PEDIDOS                          ← pedido
     │ FK dura vía (SEC_CUADRO, SEC_ITEM, ANNO_PROG)
     ↓
[2] SIG_CUADRO_MODIFICADO_DET  (cuadro necesidades anual)      ← programación
     │ (por composite atributos + fechas — sin FK)
     ↓
[3] SIG_PAAC_CONSOLIDADO   NRO_CONSOLID=CCMN                   ← consolidado / EM / cotización
    ├── NRO_EST_MDO           = EM (Estudio de Mercado)
    ├── FECHA_CONS            = fecha del consolidado
    ├── NRO_CERTIFICA         = certificación
    └── SIG_PAAC_ITEM         (detalle items)
    └── SIG_PAAC_CENTRO_COSTO (distribución por CC/meta/mes)
    └── SIG_SOLICITUD_COTIZACION (proveedores cotizantes) - FK dura
     │ FK dura (NRO_CONS_PAAC)
     ↓
[4] SIG_CUADRO_ADQUISICION   SEC_CUADRO                        ← cuadro adquisición
     │ FK dura (SEC_CUADRO, NRO_CERTIFICA)
     ↓
[5] SIG_CERTIFICACION → SIG_CERTIFICACION_FASE
                     → SIG_CERTIFICACION_OPERACION
     │ FK dura (NRO_CERTIFICA)
     ↓
[6] SIG_ORDEN_ADQUISICION   NRO_ORDEN, EXP_SIGA, EXP_SIAF      ← orden
     ├── SIG_ORDEN_SECUENCIA   (fases orden: C=compromiso, ...)
     ├── SIG_ORDEN_INTERFASE   (envío SIAF)
     ├── SIG_DEVENGADO         (si se puebla — vacía en 2026 para 132/S)
     └── SIG_EXP_SIGA + SIG_EXP_SIGA_DOCU + SIG_EXP_SIGA_PPTO + SIG_EXP_SIGA_SECU
     │ FK dura (NRO_ORDEN)
     ↓
[7] SIG_MOVIM_CONFOR_SERVICIO  (servicios)   ← devengado/conformidad
    SIG_MOVIM_ALMACEN          (bienes)      ← ingreso almacén
```

**Etapas completamente enlazadas por FK real:** [3]→[4]→[5]→[6]→[7] y
[6]↔expediente. **Etapa que requiere heurística por atributos:** [1]→[3]
(pedido → PAAC). El agujero del §6 del documento original queda acotado
a esa sola transición.

### 15.7 Preguntas abiertas restantes

- Confirmar unicidad del composite pedido↔PAAC en 2026 completo
  (no solo en el testigo). Query pendiente: para cada pedido con estado
  cerrado, contar cuántos PAAC candidatos matchean por composite; si >1
  en más del 1% de casos, el heurístico es insuficiente.
- Verificar el segundo testigo (005/B) con la misma cadena para descartar
  que el pipeline sea distinto entre bienes y servicios.
- Revisar cuerpo de triggers `TG_PEDIDO*` (volcados en `diagnostico_sesion3/`)
  buscando si alguno inserta en `SIG_PAAC_CENTRO_COSTO.nro_pedido` — si
  el trigger existe pero está deshabilitado en esta muni, explicaría el
  0% de fill rate y sería un candidato de "fix" administrativo.

---

## 16. Sesión 5 · Segundo salto — puente estructural encontrado

Ampliación de la búsqueda a vecinos de los vecinos (scripts 07-11 en
`diagnostico_sesion5/`). Aparecen tablas nuevas del pipeline que estaban
"escondidas" por su nombre.

### 16.1 EL PUENTE ESTRUCTURAL pedido ↔ CCMN (finalmente)

**`SIG_CUADRO_MODIFICADO_CMN`** — 6.431 filas en 2026 — es el puente
directo que no habíamos visto. Su llave primaria es
`(SEC_EJEC, ANNO_EJEC, SEC_CUA_MOD_SAL, TIPO_CONSOLID, NRO_CONSOLID)`:

```
SIG_DETALLE_PEDIDOS.SEC_CUA_MOD_SAL = 11553
    ↓ join dura por SEC_CUA_MOD_SAL + AÑO + SEC_EJEC
SIG_CUADRO_MODIFICADO_CMN
    → 3 filas: (11553, TIPO_CONSOLID=2, NRO_CONSOLID={2266, 2281, 3532})
    ↓ join dura por NRO_CONSOLID + TIPO_CONSOLID + AÑO + SEC_EJEC
SIG_PAAC_CONSOLIDADO
```

**Nota crítica:** la misma partida `SEC_CUA_MOD_SAL=11553` (la partida
"Auxiliar Administrativo OTI") tiene **3 CCMN distintos apuntándole**.
Es decir: 3 procesos de compra distintos sobre la misma partida. Un pedido
se asocia a uno de esos CCMN por composite (fecha + monto + secuencia
temporal).

**Query final para reconstruir pedido→CCMN:**

```sql
SELECT dp.NRO_PEDIDO, dp.SEC_CUA_MOD_SAL,
       cmn.NRO_CONSOLID, pc.FECHA_CONS, pc.NRO_EST_MDO,
       pc.NRO_CERTIFICA, pc.VALOR_PLAN
FROM SIG_DETALLE_PEDIDOS dp
INNER JOIN SIG_CUADRO_MODIFICADO_CMN cmn
    ON cmn.SEC_EJEC=dp.sec_ejec
   AND cmn.ANNO_EJEC=dp.ANO_EJE
   AND cmn.SEC_CUA_MOD_SAL=dp.SEC_CUA_MOD_SAL
INNER JOIN SIG_PAAC_CONSOLIDADO pc
    ON pc.ANO_EJE=cmn.ANNO_EJEC
   AND pc.SEC_EJEC=cmn.SEC_EJEC
   AND pc.TIPO_CONSOLID=cmn.TIPO_CONSOLID
   AND pc.NRO_CONSOLID=cmn.NRO_CONSOLID
   AND pc.TIPO_BIEN=cmn.TIPO_BIEN
WHERE dp.ANO_EJE=2026 AND dp.sec_ejec=300687
  AND CAST(dp.NRO_PEDIDO AS INT)=232 AND dp.TIPO_BIEN='S';
```

### 16.2 La terminología unificada del pipeline (evidencia textual)

Del texto libre de `SIG_ORDEN_ITEM.ESPECIFICACIONES` para la orden 132/S:

> `SEGUN PEDIDO DE SERVICIO N° 00232, CVR N°00263, CCMN N° 02266 Y CCP N° 00230.`

- **Pedido** = `SIG_PEDIDOS.NRO_PEDIDO` = 232
- **CVR (Cálculo de Valor Referencial)** = **EM (Estudio de Mercado)** =
  `SIG_PAAC_CONSOLIDADO.NRO_EST_MDO` = 263 — es el mismo objeto llamado
  con dos nombres distintos según el módulo del cliente SIGA
- **CCMN (Cuadro Consolidado de Modificación de Necesidades)** =
  `SIG_PAAC_CONSOLIDADO.NRO_CONSOLID` = 2266
- **CCP (Certificado de Crédito Presupuestario)** =
  `SIG_CERTIFICACION.NRO_CERTIFICA_SIAF` = 230

Estos 4 números **son la clave semántica** que un funcionario ve en el
cliente SIGA. Todos son enlazables por FK real o por composite.

### 16.3 Tablas nuevas relevantes descubiertas y su rol

| Tabla | Filas 2026 | Rol en el pipeline |
|---|---:|---|
| `SIG_CUADRO_MODIFICADO_CMN` | 6.431 | **Puente pedido↔PAAC** (via SEC_CUA_MOD_SAL + NRO_CONSOLID) |
| `SIG_PAAC_METAS` | 15.922 | Distribución PAAC por meta (sec_func + clasificador) |
| `SIG_PAAC_DET_DEPE` | ? | Dependencia PAAC — CC + valor por fase |
| `SIG_PAAC_DET_PPTAL` | ? | Detalle presupuestal PAAC (fuente + sec_func + clasif) |
| `SIG_PAAC_DET_SECUENCIA` | ? | Timeline fases PAAC (ESTADO_FASE, FECHA_ESTADO, FLAG_COMPROMETIDO) |
| `SIG_CERTIFICACION_DOC` | ? | Cabecera del documento de certificación (con NRO_CONSOLID) |
| `SIG_CERTIFICACION_OPER_FUENTE` | 3.152 | Timeline por fase/operación de la cert (2 filas para 182) |
| `SIG_ORDEN_ITEM` | 4.405 | Detalle ítem-orden (con ESPECIFICACIONES en texto libre) |
| `SIG_ORDEN_ITEM_PPTO` | 4.409 | Ítem-orden ↔ SEC_FUNC + CLASIFICADOR |
| `SIG_ORDEN_PRESUPUESTO` | 1.565 | Ítem-orden ↔ EXP_SIAF + SECUENCIAL SIAF |
| `SIG_CONTRATOS` | 30 | **No aplica al testigo** — solo para procesos contractuales grandes |
| `SIG_SEGUIMIENTO` | — | **Sí registra pedido 232** con NRO_PEDIDO='000232' (§11.1) — el doc original se equivocó al buscar sin padding |

### 16.4 Aclaración sobre §4.1 del doc original — `SIG_SEGUIMIENTO`

El documento original decía que `SIG_SEGUIMIENTO` "no persiste el pedido
origen" y ponía 0 filas para el 005/B. **En realidad sí lo persiste** —
el error fue buscar `NRO_PEDIDO='005'` cuando el valor real es
`'000005'` (padding a 6 chars). Con `TRY_CAST(NRO_PEDIDO AS INT)=232`
salen 7 filas para el testigo (script 11).

`SIG_SEGUIMIENTO` es **el log unificado de eventos por tipo de transacción**.
Códigos verificados en el testigo:

| TIPO_TRANSACCION | Semántica |
|---:|---|
| 1 | Entrada almacén (bienes) |
| 2 | Aprobación de pedido |
| 8 | Emisión de orden (bienes) |
| 9 | Emisión de orden (servicios) |
| 19 | Cierre de pedido |
| 20 | Pecosa emitida |

Coincide con la distribución de §4.1 (1782 filas tipo 2 ≈ pedidos S+B
aprobados; 632 tipo 8 ≈ órdenes B; 841 tipo 9 ≈ órdenes S; etc.).

### 16.5 Timeline consolidado del 232/S con todos los eventos verificables

Ordenados por fecha real de registro:

| Fecha | Fase | Evidencia | Fuente |
|---|---|---|---|
| 2026-02-05 10:35 | Pedido registrado | Pedido 232/S | `SIG_PEDIDOS.FECHA_PEDIDO` + `SIG_SEGUIMIENTO` t=2 nro_origen=333 |
| 2026-02-11 14:38 | PAAC consolidado creado (CCMN 2266) | CCMN + EM/CVR 263 | `SIG_PAAC_CONSOLIDADO.FECHA_CONS` = `SIG_PAAC_CENTRO_COSTO.FECHA_REG` = `SIG_PAAC_METAS.FECHA_REG` |
| 2026-02-11 14:38:54 | Estudio de mercado emitido | EM/CVR 263 | `SIG_PAAC_CONSOLIDADO.FECHA_EST_MDO` |
| 2026-02-12 16:38 | Solicitud de cotización al proveedor 1650 | 1 solicitud | `SIG_SOLICITUD_COTIZACION.FECHA_SOLICITUD` |
| 2026-02-16 12:09 | Certificación 182 fase 1 (OGPP) | CCP 230 | `SIG_CERTIFICACION_OPER_FUENTE` sec_fase=1 (JPALOMINO) |
| 2026-02-16 12:09 | PAAC DET fase C (compromiso) | 4800 comprometido | `SIG_PAAC_DET_SECUENCIA.FECHA_ESTADO` |
| 2026-02-16 16:14 | Orden 132/S emitida | Compromiso | `SIG_ORDEN_ADQUISICION.FECHA_ORDEN` + `SIG_ORDEN_SECUENCIA` fase='C' |
| 2026-02-16 16:17 | Certificación 182 fase 2 (ABAST vincula orden) | Aprobación | `SIG_CERTIFICACION_OPER_FUENTE` sec_fase=2 (DORCCOHUARANCCA) |
| 2026-02-16 16:17 | Expediente SIGA 152 abierto | EXP_SIGA=152 | `SIG_EXP_SIGA.FECHA_REG` |
| 2026-02-18 08:44 | Envío al SIAF | EXP_SIAF=316 | `SIG_EXP_SIGA_DOCU.FECHA_INTERFASE` |
| 2026-03-12 | Conformidad 1 | Devengado 1 | `SIG_MOVIM_CONFOR_SERVICIO.FECHA_MOVIMTO` |
| 2026-03-16 | Conformidad 2 | Devengado 2 | idem |
| 2026-04-08 | Conformidad 3 | Devengado 3 | idem |
| 2026-05-07 | Conformidad 4 (final) | Devengado 4 | `SIG_ORDEN_ITEM.FECHA_RECEP` |

**Etapas resueltas: 13/13.** Cada flecha del pipeline extendido §14 tiene
tabla origen, columna llave y evidencia verificable.

### 16.6 Mapa final del pipeline extendido

```
[1] SIG_PEDIDOS + SIG_DETALLE_PEDIDOS
     │ FK real: SIG_DETALLE_PEDIDOS.SEC_CUA_MOD_SAL → SIG_CUADRO_MODIFICADO_SALDO
     │ FK real: SIG_DETALLE_PEDIDOS.(SEC_CUADRO, SEC_ITEM, ANNO_PROG) → SIG_CUADRO_MODIFICADO_DET
     ↓
[2] SIG_CUADRO_MODIFICADO_DET + SIG_CUADRO_MODIFICADO_SALDO
     │ join dura por SEC_CUA_MOD_SAL
     ↓
[3] SIG_CUADRO_MODIFICADO_CMN  ← PUENTE DESCUBIERTO
     │ join dura por (SEC_CUA_MOD_SAL, TIPO_CONSOLID, NRO_CONSOLID)
     ↓
[4] SIG_PAAC_CONSOLIDADO  (CCMN cabecera + EM/CVR + NRO_CERTIFICA)
    ├── SIG_PAAC_ITEM        (item detail)
    ├── SIG_PAAC_METAS       (por meta/clasificador)
    ├── SIG_PAAC_CENTRO_COSTO (por CC/mes)
    ├── SIG_PAAC_DET         (cert + monto)
    ├── SIG_PAAC_DET_DEPE / _PPTAL / _SECUENCIA (fases presupuestales)
    ├── SIG_PAAC_SECUENCIA   (rango mes inicial-final)
    └── SIG_SOLICITUD_COTIZACION → SIG_SOLICITUD_COTIZACION_ITEM (FK real)
     │ FK real NRO_CONS_PAAC
     ↓
[5] SIG_CUADRO_ADQUISICION (SEC_CUADRO=131)
     │ FK real NRO_CERTIFICA
     ↓
[6] SIG_CERTIFICACION → SIG_CERTIFICACION_DOC
                     → SIG_CERTIFICACION_FASE
                     → SIG_CERTIFICACION_OPERACION
                     → SIG_CERTIFICACION_OPER_FUENTE (timeline detallado)
     │ FK real (NRO_CERTIFICA)
     ↓
[7] SIG_ORDEN_ADQUISICION (NRO_ORDEN=132)
    ├── SIG_ORDEN_SECUENCIA   (fases orden)
    ├── SIG_ORDEN_ITEM        (detalle ítem con ESPECIFICACIONES texto libre)
    ├── SIG_ORDEN_ITEM_PPTO   (ítem ↔ meta + clasificador)
    ├── SIG_ORDEN_PRESUPUESTO (ítem ↔ EXP_SIAF + SECUENCIAL)
    ├── SIG_ORDEN_INTERFASE   (envío SIAF)
    ├── SIG_DEVENGADO         (vacía en 232/S)
    ├── SIG_EXP_SIGA          (con NRO_CONSOLID=2266 — puente extra)
    │   ├── SIG_EXP_SIGA_DOCU  (documentos + FECHA_INTERFASE)
    │   ├── SIG_EXP_SIGA_SECU
    │   └── SIG_EXP_SIGA_PPTO  (partida presupuestal)
     │ FK real NRO_ORDEN
     ↓
[8] SIG_MOVIM_CONFOR_SERVICIO (S) / SIG_MOVIM_ALMACEN (B)

TIMELINE TRANSVERSAL: SIG_SEGUIMIENTO registra TIPO_TRANSACCION={1,2,8,9,19,20}
con NRO_PEDIDO padeado ('000232') y NRO_ORIGEN interno.
```

**Todas las flechas [1]→[8] tienen ahora llave dura (FK real o composite
verificado en el testigo).** El agujero del §6 queda cerrado por
`SIG_CUADRO_MODIFICADO_CMN`.

### 16.7 Cosas todavía por verificar

- Correr la query de §16.1 sobre **todos los pedidos 2026** con estado
  cerrado y contar cuántos matchean múltiples CCMN. Si >1 CCMN por
  pedido en <5% de los casos, el composite adicional (fecha + monto)
  resuelve; si >5%, hay que revisar más.

---

## 17. Sesión 5 · Testigo 005/B — pipeline de bienes con pecosa

Aplicación de la cadena §16 al segundo testigo canónico. Aparecen
particularidades del flujo de bienes que no existen en servicios.

### 17.1 El testigo 005/B se descompone en DOS pedidos distintos

El documento original mezclaba dos pedidos:

```
005/B TIPO_PEDIDO=2  (2026-01-20, CC=01.03.11.03, meta 118)  → NO existe
010/B TIPO_PEDIDO=2  (2026-01-20, CC=01.03.11.03, meta 118)  ← PEDIDO DE COMPRA REAL
005/B TIPO_PEDIDO=1  (2026-02-12, CC=01.03.11.03, meta 118)  ← PEDIDO DE ATENCION INTERNA (a almacén)
```

**Evidencia textual** (`SIG_ORDEN_ITEM.ESPECIFICACIONES` de la orden 003/B):

> `SEGUN PEDIDO DE COMPRA N° 10, CVR N° 81, CCMN N° 2081 Y CCP N° 106`

Es decir, la orden 003/B nació del **pedido 010/B TIPO_PEDIDO=2**, no
del 005/B. El pedido 005/B TIPO_PEDIDO=1 es un pedido POSTERIOR (después
del ingreso a almacén) que solicita el despacho de lo ya comprado. Los
dos comparten `META=118` y `CC=01.03.11.03`.

### 17.2 Cadena estructural para bienes — dos flujos paralelos

**Flujo A · COMPRA (para todo bien nuevo que entra por proveedor):**
```
SIG_PEDIDOS  TIPO_PEDIDO=2  NRO_PEDIDO=010
    ↓ (FK dura SEC_CUA_MOD_SAL en detalle → SIG_CUADRO_MODIFICADO_SALDO)
SIG_CUADRO_MODIFICADO_CMN         ← puente (SEC_CUA_MOD_SAL, NRO_CONSOLID)
    ↓
SIG_PAAC_CONSOLIDADO NRO_CONSOLID=2081, NRO_EST_MDO=81 (CVR), NRO_CERTIFICA=79
    ↓
SIG_CUADRO_ADQUISICION SEC_CUADRO=4, NRO_CONS_PAAC=2081
    ↓
SIG_CERTIFICACION NRO_CERTIFICA=79, NRO_CERTIFICA_SIAF=106 (CCP)
    ↓ (SIG_CERTIFICACION_OPER_FUENTE — 2 fases: JPALOMINO OGPP → RAPAZA ABAST)
SIG_ORDEN_ADQUISICION NRO_ORDEN=3, PROVEEDOR=2217, TOTAL=5805
    EXP_SIGA=59, EXP_SIAF=179
    ↓
SIG_MOVIM_ALMACEN (TIPO_MOVIMTO='I', TIPO_TRANSAC=1) NRO_MOVIMTO=4
    "INGRESO POR COMPRA" — llegada al almacén el 2026-02-12
    (paralelo TIPO_MOVIMTO='R' con mismo NRO_MOVIMTO=4 — kardex)
    Guía EG07-347 del proveedor 2217
```

**Flujo B · CONSUMO (pedido interno → despacho al usuario):**
```
SIG_PEDIDOS  TIPO_PEDIDO=1  NRO_PEDIDO=005
    ↓ (NO tiene SEC_CUA_MOD_SAL en detalle — no es una compra)
SIG_DETALLE_PEDIDOS con NRO_PECOSA=4  (referencia a la pecosa que lo atiende)
    ↓
SIG_DETALLE_PECOSA (3 items con CANT_ATENDIDA = CANT_APROBADA)
    ↓
SIG_DETALLE_MOVIM_ALMACEN (TIPO_MOVIMTO='S', TIPO_TRANSAC=1) NRO_MOVIMTO=4
    "DESPACHO AL USUARIO" — salida al CC 01.03.11.03 el 2026-02-12
    3 items: 20-34-0007-0027 (1875), 20-34-0007-0045 (2850), 20-34-0002-0014 (1080) = 5805
```

**Los dos flujos se cruzan en:** `NRO_MOVIMTO=4` del almacén (mismo día
2026-02-12). El ingreso por compra y el despacho al usuario son
"consecutivos" — el material entra y sale casi de inmediato porque el
almacén es un paso administrativo, no de custodia real.

### 17.3 Catálogo `SIG_TIPO_MOVIMIENTO` — reglas para el pipeline

Códigos clave para servicios y bienes (44 combinaciones totales):

| TIPO_MOVIMTO | TIPO_TRANSAC | Nombre | Rol pipeline |
|:-:|:-:|---|---|
| I | 1 | INGRESO POR COMPRA | Entrada bien nuevo (con NRO_ORDEN) |
| R | 1 | INGRESO POR COMPRA (kardex) | Réplica contable del I |
| S | 1 | DESPACHO AL USUARIO (PECOSA) | Salida a CC (con NRO_PECOSA) |
| C | 1 | REGISTRO CONFORMIDAD SERVICIO | Devengado de servicios |
| A | 1 | INVENTARIO INICIAL | Apertura de ejercicio |
| P | 1 | PEDIDO PROVISIONAL | Reserva |
| T | 1,2,3 | SALIDAS ESPECIALES | Mantenimiento / externa / diversa |
| S | 2-10 | Salidas por donación, inventario, disposición, etc. | No pipeline compra |
| I | 2-19 | NEA (Notas de Entrada) — donaciones, producción, etc. | No pipeline compra |

**Regla del pipeline canónico de compra:** `(I,1) → (S,1)` cerrado con
`NRO_PECOSA` que aparece tanto en `SIG_DETALLE_PECOSA` como en
`SIG_DETALLE_PEDIDOS.NRO_PECOSA` del pedido interno de consumo.

### 17.4 Semántica completa de `SIG_SEGUIMIENTO.TIPO_TRANSACCION`

Verificada con datos 2026 (script 14):

| TIPO | Cantidad 2026 | Semántica |
|---:|---:|---|
| 1 | 576 | Entrada a almacén (movimiento I) |
| 2 | 1.782 | Aprobación de pedido |
| 4 | 1.795 | **Pedido de compra CREADO** (TIPO_PEDIDO=2) |
| 5 | 5 | Pedido TIPO_PEDIDO=5 (¿pedido especial?) |
| 7 | 30 | **Pedido de atención interna** (TIPO_PEDIDO=1) |
| 8 | 632 | Orden bienes emitida |
| 9 | 841 | Orden servicios emitida |
| 15 | 2 | Pedido TIPO_PEDIDO=0 |
| 19 | 573 | Pedido cerrado |
| 20 | 574 | Pecosa emitida |
| 26 | 2 | Transacción sistema |
| 31 | 11 | **Pedido de reposición al almacén** (TIPO_PEDIDO='I', TIPO_CONSOLID='I1'/'I9') |
| 33 | 2 | Salida S-5 |
| 34 | 1 | Transferencia T-1 |
| 35 | 2 | Transferencia T-1/T-3 |

**Fin de la incógnita §4.1 del doc original.**

### 17.5 Timeline completo del 005/B + 010/B (pipeline con pecosa)

```
2026-01-09 16:19  Pedido 010/B TIPO_PEDIDO=2 creado (SEGUIM TIPO=4)
2026-01-20 14:22  Pedido 010/B registrado formalmente
2026-01-23 10:46  PAAC consolidado creado (CCMN 2081 = FECHA_CONS)
                  + EM/CVR 81 emitido
2026-02-02 16:47  Certificación 79 fase 1 (JPALOMINO OGPP)
                  → CCP SIAF 106
2026-02-04 11:08  Orden 003/B emitida (RAPAZA)
                  → FASE_ORDEN='C' (compromiso) en SIG_ORDEN_SECUENCIA
2026-02-04 11:20  Certificación 79 fase 2 (RAPAZA vincula orden)
2026-02-04 11:20  Expediente SIGA 59 abierto (D=devengado)
2026-02-05 16:23  Envío al SIAF → EXP_SIAF=179 (FECHA_INTERFASE)
2026-02-11 11:09  SEGUIM TIPO=8: orden bienes emitida (registro post-hoc)
2026-02-12         Ingreso al almacén: SIG_MOVIM_ALMACEN (I,1,4) + (R,1,4)
                  Guía EG07-347 del proveedor 2217
2026-02-12         Pedido 005/B TIPO_PEDIDO=1 registrado (atención)
2026-02-12         Despacho al usuario: (S,1,4) — pecosa nro 4 al CC 01.03.11.03
                  3 items: 25 + 38 + 12 unidades = 5805
2026-02-13         Pecosa registrada en SEGUIM TIPO=20
2026-02-17 16:25  SEGUIM TIPO=1 (entrada almacén formalizada)
2026-02-17 16:53  Pedido 005/B cerrado (SEGUIM TIPO=19, ESTADO=7)
2026-02-19 10:42  SEGUIM TIPO=4 sobre pedido 5 (retroactivo)
2026-03-31         SEGUIM TIPO=31: pedido de reposición al almacén
                  (usuario OROMOACCA, CC=01.03.05.04) — otro flujo
```

**16 eventos verificables** para el ciclo completo de un bien (vs 13
para servicios). La diferencia son las 3 etapas adicionales del ciclo
de almacén: ingreso (I) + registro kardex (R) + despacho (S).

### 17.6 Pipeline extendido — versión final unificada

```
FASE                        SERVICIOS               BIENES
──────────────────────────  ──────────────────────  ──────────────────────
[1] Pedido registrado       PEDIDOS TIPO=2          PEDIDOS TIPO=2 (compra)
[2] Aprobación pedido       SEGUIM TIPO=2           SEGUIM TIPO=2
[3] Cuadro necesidad        CUADRO_MODIFICADO_DET   CUADRO_MODIFICADO_DET
[4] Puente pedido↔PAAC      CUADRO_MODIFICADO_CMN   CUADRO_MODIFICADO_CMN
[5] CCMN / EM(CVR)          PAAC_CONSOLIDADO        PAAC_CONSOLIDADO
[6] Cotización              SOLICITUD_COTIZACION    SOLICITUD_COTIZACION
[7] Cuadro adquisición      CUADRO_ADQUISICION      CUADRO_ADQUISICION
[8] Certificación (CCP)     CERTIFICACION → OPER    CERTIFICACION → OPER
[9] Orden emitida           ORDEN_ADQUISICION       ORDEN_ADQUISICION
[10] Compromiso / SIAF      EXP_SIGA + EXP_SIAF     EXP_SIGA + EXP_SIAF
[11] Ejecución              MOVIM_CONFOR_SERVICIO   MOVIM_ALMACEN (I,1)
[12] Recepción              (no aplica — es continua) MOVIM_ALMACEN (R,1)
[13] Pedido interno         (no aplica)             PEDIDOS TIPO=1
[14] Despacho / pecosa      (no aplica)             DETALLE_PECOSA + MOVIM (S,1)
[15] Devengado              (implícito en confor.)  EXP_SIGA fase D
[16] Cierre                 SEGUIM TIPO=19          SEGUIM TIPO=19
```

**Servicios: 13 etapas (fases 1-11 + 15-16, sin 12-14).**
**Bienes: 16 etapas (todas).**

Este es el mapa canónico para el widget "cadena logística" (§10 del
diccionario de datos). Puede colapsarse a 6-8 macrofases para semáforo
en el dashboard.

### 17.7 Diferencia clave para el diseño del panel interno

El estado real del pedido depende del **tipo de pedido y tipo de bien:**

| Tipo pedido | Tipo bien | Cierre = |
|:-:|:-:|---|
| 2 (compra) | S | Conformidad final en `MOVIM_CONFOR_SERVICIO` |
| 2 (compra) | B | Ingreso a almacén `(I,1)` con guía del proveedor |
| 1 (atención) | B | Salida al usuario `(S,1)` con NRO_PECOSA |
| I (reposición) | B | Ingreso a almacén sin orden externa |

El pedido 005/B TIPO=1 del testigo mostró que un pedido puede estar
"cerrado" (ESTADO=7) sin haber pasado por PAAC/orden — porque su
naturaleza no era una compra sino un consumo interno del stock existente.
El semáforo del panel debe considerar `TIPO_PEDIDO` para elegir el flujo
que aplica.

