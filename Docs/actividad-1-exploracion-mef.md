# Actividad 1 — Exploración y Mapeo de Datos: API SIAF-MEF

> Municipalidad Distrital de San Jerónimo — Cusco  
> Elaborado mediante consultas exploratorias a la API de Datos Abiertos del MEF · Julio 2026

---

## 1. Identificación de la Entidad en la API

| Parámetro | Valor |
|---|---|
| **Nombre** | MUNICIPALIDAD DISTRITAL DE SAN JERONIMO |
| **SEC_EJEC** | `300687` |
| **Departamento** | CUSCO |
| **Provincia** | CUSCO |
| **Distrito** | SAN JERONIMO |
| **Nivel de Gobierno** | GOBIERNOS LOCALES |
| **PLIEGO** | *(vacío en la API — no disponible en este dataset)* |
| **SECTOR** | *(vacío en la API — no disponible en este dataset)* |

> **Nota:** Existen cuatro ejecutoras con nombre similar en la API (incluyendo `300272 - MUNICIPALIDAD DISTRITAL DE SAN JERONIMO` que corresponde a otra región). El código `300687` es el confirmado para San Jerónimo — Cusco, validado por `DEPARTAMENTO_EJECUTORA_NOMBRE = CUSCO` y `DISTRITO_EJECUTORA_NOMBRE = SAN JERONIMO`.

---

## 2. Endpoint y Resource ID

| Concepto | Valor |
|---|---|
| **Base URL** | `https://api.datosabiertos.mef.gob.pe/DatosAbiertos/v1/` |
| **Endpoint consulta** | `datastore_search` |
| **Endpoint SQL** | `datastore_search_sql` |
| **Resource ID** | `615644aa-ef73-4358-b4e0-0c20931632f3` |
| **Autenticación** | Ninguna — API pública |
| **Formato de respuesta** | JSON |
| **Años disponibles** | Solo **2026** en este resource_id |

---

## 3. Estructura de campos — Diccionario de Datos

El dataset contiene **64 campos** por registro. Se clasifican en las siguientes categorías:

### 3.1 Identificadores de la Entidad

| Campo | Tipo | Descripción |
|---|---|---|
| `ANO_EJE` | String | Año fiscal de ejecución |
| `MES_EJE` | String | Mes de ejecución. `0` = presupuesto inicial (PIM), `1-12` = mes de ejecución real |
| `NIVEL_GOBIERNO` | String | Código nivel de gobierno |
| `NIVEL_GOBIERNO_NOMBRE` | String | Nombre nivel de gobierno (ej: `GOBIERNOS LOCALES`) |
| `SECTOR` | String | Código de sector *(vacío para gobiernos locales)* |
| `SECTOR_NOMBRE` | String | Nombre de sector *(vacío para gobiernos locales)* |
| `PLIEGO` | String | Código de pliego *(vacío para gobiernos locales)* |
| `PLIEGO_NOMBRE` | String | Nombre de pliego *(vacío para gobiernos locales)* |
| `SEC_EJEC` | String | **Código de unidad ejecutora** — clave principal de filtro |
| `EJECUTORA_NOMBRE` | String | Nombre de la unidad ejecutora |
| `DEPARTAMENTO_EJECUTORA` | String | Código de departamento de la ejecutora |
| `DEPARTAMENTO_EJECUTORA_NOMBRE` | String | Nombre del departamento |
| `PROVINCIA_EJECUTORA` | String | Código de provincia |
| `PROVINCIA_EJECUTORA_NOMBRE` | String | Nombre de provincia |
| `DISTRITO_EJECUTORA` | String | Código de distrito |
| `DISTRITO_EJECUTORA_NOMBRE` | String | Nombre de distrito |

### 3.2 Cadena Funcional Programática

| Campo | Tipo | Descripción |
|---|---|---|
| `FUNCION` | String | Código de función |
| `FUNCION_NOMBRE` | String | Nombre de función (ej: `TRANSPORTE`, `SANEAMIENTO`, `EDUCACION`) |
| `DIVISION_FUNCIONAL` | String | Código de división funcional |
| `DIVISION_FUNCIONAL_NOMBRE` | String | Nombre de división funcional |
| `GRUPO_FUNCIONAL` | String | Código de grupo funcional |
| `GRUPO_FUNCIONAL_NOMBRE` | String | Nombre de grupo funcional |
| `PROGRAMA_PPTO` | String | Código de programa presupuestal |
| `PROGRAMA_PPTO_NOMBRE` | String | Nombre del programa presupuestal |
| `CATEGORIA_GASTO` | String | `5` = Gasto Corriente, `6` = Gasto de Capital |
| `CATEGORIA_GASTO_NOMBRE` | String | Nombre de categoría de gasto |
| `TIPO_ACT_PROY` | String | `2` = Proyecto de inversión, `3` = Actividad |
| `TIPO_ACT_PROY_NOMBRE` | String | Nombre del tipo |
| `PRODUCTO_PROYECTO` | String | **Código Invierte.pe del proyecto o código de actividad** — clave de cruce con SIGA |
| `PRODUCTO_PROYECTO_NOMBRE` | String | Nombre del proyecto o actividad |
| `ACTIVIDAD_ACCION_OBRA` | String | Código de actividad/acción/obra dentro del proyecto |
| `ACTIVIDAD_ACCION_OBRA_NOMBRE` | String | Nombre de la actividad/acción/obra |
| `FINALIDAD` | String | Código de finalidad presupuestal |
| `DEPARTAMENTO_META` | String | Código del departamento de la meta |
| `DEPARTAMENTO_META_NOMBRE` | String | Nombre del departamento de la meta |
| `META` | String | **Código de meta presupuestal** — clave de cruce con SIGA |
| `META_NOMBRE` | String | Nombre descriptivo de la meta |
| `SEC_FUNC` | String | **Secuencia funcional única de la meta** — equivale a `sec_func` en SIGA |

### 3.3 Clasificadores de Gasto

| Campo | Tipo | Descripción | Valores observados |
|---|---|---|---|
| `GENERICA` | String | Código de genérica de gasto | `1` Personal, `2` Pensiones, `3` Bienes/Servicios, `6` Adq. Activos |
| `GENERICA_NOMBRE` | String | Nombre de genérica | |
| `SUBGENERICA` | String | Código de sub-genérica | |
| `SUBGENERICA_NOMBRE` | String | Nombre de sub-genérica | |
| `SUBGENERICA_DET` | String | Código de sub-genérica detalle | |
| `SUBGENERICA_DET_NOMBRE` | String | Nombre de sub-genérica detalle | |
| `ESPECIFICA` | String | Código de específica de gasto | |
| `ESPECIFICA_NOMBRE` | String | Nombre de específica | |
| `ESPECIFICA_DET` | String | Código de específica detalle | |
| `ESPECIFICA_DET_NOMBRE` | String | Nombre de específica detalle | |

### 3.4 Fuentes de Financiamiento

| Campo | Tipo | Descripción | Valores observados |
|---|---|---|---|
| `FUENTE_FINANCIAMIENTO` | String | Código de fuente | `1`, `2`, `4`, `5` |
| `FUENTE_FINANCIAMIENTO_NOMBRE` | String | Nombre de fuente | Recursos Ordinarios, Rec. Directamente Recaudados, Donaciones y Transferencias, Recursos Determinados |
| `RUBRO` | String | Código de rubro | `00`, `07`, `08`, `09`, `13`, `18` |
| `RUBRO_NOMBRE` | String | Nombre de rubro | Recursos Ordinarios, FONCOMUN, Impuestos Municipales, RDR, Donaciones, Canon y Sobrecanón |
| `TIPO_RECURSO` | String | Código de tipo de recurso | |
| `TIPO_RECURSO_NOMBRE` | String | Nombre de tipo de recurso | |
| `TIPO_TRANSACCION` | String | Tipo de transacción | `2` (único valor observado) |

### 3.5 Montos Presupuestales y de Ejecución

| Campo | Tipo | Descripción |
|---|---|---|
| `MONTO_PIA` | Numérico | Presupuesto Institucional de Apertura |
| `MONTO_PIM` | Numérico | Presupuesto Institucional Modificado |
| `MONTO_CERTIFICADO` | Numérico | Monto certificado |
| `MONTO_COMPROMETIDO_ANUAL` | Numérico | Compromiso anual |
| `MONTO_COMPROMETIDO` | Numérico | Compromiso mensual |
| `MONTO_DEVENGADO` | Numérico | Monto devengado |
| `MONTO_GIRADO` | Numérico | Monto girado/pagado |

> **Observación importante:** `MONTO_PIA` y `MONTO_PIM` aparecen en `0` en todos los registros con `MES_EJE > 0`. Solo vienen con valor en `MES_EJE = 0` (fila maestra de presupuesto).
>
> Los montos de ejecución (`MONTO_DEVENGADO`, `MONTO_GIRADO`, `MONTO_CERTIFICADO`, `MONTO_COMPROMETIDO`) son **flujos del período mensual**, NO acumulados del año. Para obtener el total anual hay que sumar todos los meses disponibles (`MES_EJE > 0`). Ver análisis completo en `Docs/hallazgos-granularidad-siaf.md`.

---

## 4. Comportamiento de la API — Limitaciones Documentadas

| Limitación | Descripción |
|---|---|
| **Un solo año por dataset** | El resource_id `615644aa...` contiene solo datos del año fiscal actual (2026). Los años anteriores probablemente se encuentran en resource_id distintos. |
| **Error 409 en SELECT amplio** | La API retorna HTTP 409 cuando la consulta SQL selecciona más de ~8-10 columnas simultáneamente junto con filtros complejos. Solución: dividir en múltiples consultas con menos campos. |
| **Error 500** | Ocurre con GROUP BY + funciones de agregación (SUM, COUNT) combinadas con múltiples columnas. Las agregaciones simples con pocas columnas sí funcionan. |
| **Campos vacíos para GL** | `PLIEGO`, `PLIEGO_NOMBRE`, `SECTOR`, `SECTOR_NOMBRE` retornan vacíos para gobiernos locales. |
| `MONTO_PIA` en cero | El campo PIA aparece en 0 en registros con MES_EJE > 0. |
| **Sin paginación automática** | La API usa parámetros `LIMIT` y `OFFSET`. Máximo recomendado: 100 registros por consulta. |
| **Codificación de caracteres** | Las búsquedas con tildes (JERÓNIMO) en la URL fallan. Usar versión sin tilde (JERONIMO) o filtrar por código. |

### Estrategia recomendada para el backend

```
Para cada consulta al SIAF hacer:
1. Filtrar SIEMPRE por SEC_EJEC = '300687' AND ANO_EJE = '{año}'
2. Seleccionar máximo 8 columnas por request
3. Paginar con LIMIT 100 OFFSET n
4. Para PIA/PIM: filtrar MES_EJE=0 y agrupar por sec_func (SUM)
5. Para ejecución (devengado/girado/certificado): SUM de todos los meses > 0 por sec_func
   — NO tomar solo el mes más reciente; los montos son flujos mensuales, no acumulados
```

---

## 5. Volumen de Datos — Entidad San Jerónimo 2026

| Concepto | Valor |
|---|---|
| **Total registros en el dataset** | ~6,191,929 (todas las entidades) |
| **Años disponibles en este resource_id** | Solo 2026 |
| **Meses con datos (MES_EJE)** | 0, 1, 2, 3, 4, 5, 6, 7 (al momento de exploración, julio 2026) |
| **TIPO_TRANSACCION observado** | Solo `2` |

---

## 6. Catálogo de Proyectos de Inversión 2026

Se identificaron **70 proyectos de inversión activos** (`TIPO_ACT_PROY = '2'`) para la Municipalidad Distrital de San Jerónimo en 2026, distribuidos por función:

| Función | Cantidad de proyectos |
|---|---|
| TRANSPORTE | ~17 |
| CULTURA Y DEPORTE | ~6 |
| AGROPECUARIA | ~9 |
| EDUCACION | ~5 |
| SANEAMIENTO | ~4 |
| VIVIENDA Y DESARROLLO URBANO | ~3 |
| INDUSTRIA | ~4 |
| COMERCIO | ~2 |
| TURISMO | ~1 |
| PLANEAMIENTO, GESTION Y RESERVA | ~4 |
| ORDEN PUBLICO Y SEGURIDAD | ~1 |

### Proyectos representativos por función

| Código | Nombre | Función |
|---|---|---|
| 2669624 | Mejoramiento movilidad urbana Manantiales | TRANSPORTE |
| 2560559 | Construcción pista y vereda Portada del Valle | TRANSPORTE |
| 2637963 | Movilidad urbana Avenida Cantaritos | TRANSPORTE |
| 2461289 | Mejoramiento transitabilidad Av. Los Rosales | TRANSPORTE |
| 2186190 | Mejoramiento agua potable y alcantarillado JAAS | SANEAMIENTO |
| 2467397 | Mejoramiento agua potable Pallpancay-Collparo | SANEAMIENTO |
| 2235850 | Mejoramiento educación I.E. Rosario Fe y Alegría | EDUCACION |
| 2282904 | Mejoramiento servicio educativo I.E. integrada | EDUCACION |
| 2456126 | Creación sistema riego Picol Orccompucyo | AGROPECUARIA |
| 2486292 | Creación espacio deportivo Ayllu Rau Rau | CULTURA Y DEPORTE |
| 2153290 | Mejoramiento servicio bomberos San Jerónimo | ORDEN PUBLICO Y SEGURIDAD |

---

## 7. Programas Presupuestales Activos 2026

Se identificaron **21 programas presupuestales** (`PROGRAMA_PPTO`) activos para la entidad:

`0002, 0017, 0030, 0036, 0041, 0042, 0048, 0068, 0082, 0083, 0090, 0101, 0117, 0121, 0140, 0142, 0146, 0148, 1001, 9001, 9002`

Áreas temáticas cubiertas: salud materno-neonatal, control de enfermedades, seguridad ciudadana, gestión ambiental, saneamiento urbano y rural, educación, vivienda, transporte urbano, desarrollo cultural, agricultura, y acciones centrales.

---

## 8. Fuentes de Financiamiento Observadas

| Código | Nombre | Rubro |
|---|---|---|
| `1` | RECURSOS ORDINARIOS | 00 |
| `2` | RECURSOS DIRECTAMENTE RECAUDADOS | 09 |
| `4` | DONACIONES Y TRANSFERENCIAS | 13 |
| `5` | RECURSOS DETERMINADOS | 07 (FONCOMUN), 08 (Impuestos Municipales), 18 (Canon) |

---

## 9. Llaves de Cruce SIAF ↔ SIGA — Estado de Validación

### Campos disponibles en SIAF (API MEF)

| Campo SIAF | Descripción | Equivalente en SIGA |
|---|---|---|
| `ANO_EJE` | Año fiscal | `ano_eje` en tabla `META` |
| `SEC_EJEC` | Código ejecutora | `sec_ejec` en tabla `META` |
| `SEC_FUNC` | Secuencia funcional de la meta | `sec_func` en tabla `META` — **llave principal de cruce** |
| `PRODUCTO_PROYECTO` | Código Invierte.pe | `act_proy` en tabla `META` (proyectos con prefijo `2`) |
| `META` | Código de meta (`00001`, `00003`, etc.) | `meta` en tabla `META` |
| `GENERICA` | Genérica de gasto | Equivalente al clasificador de gasto en SIGA |

### Validación de la llave de cruce

La llave principal de cruce es:

```
ANO_EJE + SEC_EJEC + SEC_FUNC
```

- En SIAF: campo `SEC_FUNC` identifica unívocamente la meta presupuestal
- En SIGA: campo `sec_func` en tabla `META` es exactamente el mismo código
- La integridad de esta relación fue validada en la exploración del SIGA: **0 huérfanos** en `SIG_METAS_X_CENTRO → META`

### Campo pendiente de validar

El documento base menciona el **número de expediente SIAF** como llave de cruce para vincular órdenes SIGA con registros de ejecución SIAF. Este campo **no aparece** en el dataset de ejecución presupuestal de la API pública. Hipótesis:
- El expediente SIAF está registrado en las órdenes del SIGA (campo a identificar en tablas `SIG_ORDEN_ADQUISICION` o `SIG_DEVENGADO`)
- En la API, la granularidad más fina disponible es `SEC_FUNC + GENERICA + MES_EJE`, no el expediente individual

> **Acción pendiente:** Revisar en SIGA las tablas `SIG_DEVENGADO` y `SIG_ORDEN_ADQUISICION` para identificar el campo que almacena el número de expediente/registro SIAF, y confirmar si es posible cruzarlo con algún identificador de la API.

---

## 10. Ejemplo de Consultas SQL Validadas

### Consulta base — ejecución mensual de la entidad

```sql
-- Obtener todos los registros de ejecución de un mes específico
SELECT "ANO_EJE", "MES_EJE", "SEC_FUNC", "PRODUCTO_PROYECTO", "META", "GENERICA"
FROM "615644aa-ef73-4358-b4e0-0c20931632f3"
WHERE "SEC_EJEC" = '300687'
  AND "ANO_EJE" = '2026'
  AND "MES_EJE" = '6'
LIMIT 100
```

### Consulta — montos por meta (PIM + ejecución)

```sql
-- Por limitación de la API: máximo ~8 columnas por consulta
SELECT "SEC_FUNC", "PRODUCTO_PROYECTO", "META", "MONTO_PIM", "MONTO_DEVENGADO", "MONTO_GIRADO"
FROM "615644aa-ef73-4358-b4e0-0c20931632f3"
WHERE "SEC_EJEC" = '300687'
  AND "ANO_EJE" = '2026'
  AND "MES_EJE" = '0'
LIMIT 100
```

### Consulta — proyectos de inversión activos

```sql
SELECT DISTINCT "PRODUCTO_PROYECTO", "PRODUCTO_PROYECTO_NOMBRE", "TIPO_ACT_PROY_NOMBRE", "FUNCION_NOMBRE"
FROM "615644aa-ef73-4358-b4e0-0c20931632f3"
WHERE "SEC_EJEC" = '300687'
  AND "ANO_EJE" = '2026'
  AND "TIPO_ACT_PROY" = '2'
LIMIT 100
```

### Consulta — clasificadores de gasto distintos

```sql
SELECT DISTINCT "GENERICA", "GENERICA_NOMBRE", "FUENTE_FINANCIAMIENTO", "FUENTE_FINANCIAMIENTO_NOMBRE", "RUBRO", "RUBRO_NOMBRE"
FROM "615644aa-ef73-4358-b4e0-0c20931632f3"
WHERE "SEC_EJEC" = '300687'
  AND "ANO_EJE" = '2026'
LIMIT 50
```

---

## 11. Hallazgos y Decisiones de Diseño

| Hallazgo | Impacto en el sistema |
|---|---|
| Solo hay datos del año vigente en el resource_id explorado | El sistema deberá identificar o almacenar los resource_id históricos para comparativos multianuales |
| Los campos PLIEGO y SECTOR están vacíos para GL | No usar estos campos como filtro; usar siempre SEC_EJEC |
| La API falla con más de ~8 columnas por query | El backend debe dividir las consultas en múltiples requests y unirlas en memoria |
| MES_EJE = 0 contiene PIA y PIM; meses 1-N contienen ejecución | PIA/PIM: sumar filas de MES_EJE=0. Devengado/Girado/Certificado: sumar TODOS los meses > 0 (son flujos mensuales, no acumulados). Ver `Docs/hallazgos-granularidad-siaf.md`. |
| SEC_FUNC es la llave de cruce principal SIAF↔SIGA | Confirmar con exploración SIGA que el valor es el mismo numéricamente |
| ~70 proyectos de inversión activos en 2026 | El Portal de Obras tendrá fichas para todos ellos |
| TIPO_ACT_PROY = '2' para proyectos, '3' para actividades | Filtrar con el valor numérico, no el nombre texto |

---

## 12. API Invierte.pe — Detalle de Inversiones y Avance Físico

Dataset complementario al SIAF presupuestal. Contiene información de seguimiento físico, georreferenciación y estado de cada proyecto de inversión pública.

### 12.1 Endpoint y Resource ID

| Concepto | Valor |
|---|---|
| **Dataset** | Detalle de Inversiones |
| **Resource ID** | `f9cc4ba0-931a-4b70-86c9-eacbd8c68596` |
| **Endpoint SQL** | `https://api.datosabiertos.mef.gob.pe/DatosAbiertos/v1/datastore_search_sql` |
| **Autenticación** | Ninguna — API pública |
| **Total registros (todas las entidades)** | ~148,478 |
| **Registros para San Jerónimo (SEC_EJEC = 300687)** | **70 proyectos** |
| **Año disponible** | Solo **2026** (campo `ANIO_PROCESO`) |
| **UBIGEO San Jerónimo** | `080104` |

### 12.2 Diccionario de Campos (71 campos)

#### Identificación del proyecto

| Campo | Tipo | Descripción |
|---|---|---|
| `CODIGO_UNICO` | String | Código único del proyecto en Invierte.pe / SNIP |
| `NOMBRE_INVERSION` | Text | Nombre completo del proyecto |
| `TIPO_INVERSION` | String | `PROYECTO DE INVERSIÓN` o `INVERSIONES IOARR` |
| `MARCO` | String | `INVIERTE` (Invierte.pe) o `SNIP` |
| `ESTADO` | String | `ACTIVO` / `CERRADO` |
| `SITUACION` | String | `VIABLE`, `APROBADO` |
| `ANIO_PROCESO` | String | Año del reporte (solo `2026`) |
| `SEC_EJEC` | String | Código ejecutora — mismo que dataset SIAF |

#### Avance físico y ejecución

| Campo | Tipo | Descripción | Observaciones |
|---|---|---|---|
| `AVANCE_FISICO` | Numeric | Porcentaje de avance físico | Vacío si `TIENE_AVAN_FISICO = 'NO'` |
| `AVANCE_EJECUCION` | Numeric | Porcentaje de avance financiero | |
| `TIENE_AVAN_FISICO` | String | `SI` / `NO` — indica si el proyecto reporta avance | ~50 de 70 reportan avance |
| `PIM_ANIO_ACTUAL` | Numeric | PIM del año corriente para este proyecto | |
| `DEV_ANIO_ACTUAL` | Numeric | Devengado del año corriente | |
| `DEVEN_ACUMUL_ANIO_ANT` | Numeric | Devengado acumulado de años anteriores | |
| `COMPROM_ANUAL_ANIO_ACTUAL` | Numeric | Compromiso anual del año | |
| `CERTIF_ANIO_ACTUAL` | Numeric | Monto certificado del año | |
| `PIA_ANIO_ACTUAL` | Numeric | PIA del año corriente | |
| `COSTO_ACTUALIZADO` | Numeric | Costo total actualizado del proyecto | |
| `MONTO_VIABLE` | Numeric | Monto al momento de la viabilidad | |
| `SALDO_EJECUTAR` | Numeric | Saldo por ejecutar (en millones) | |
| `PMI_ANIO_1` | Numeric | Programación Multianual Año +1 | |
| `PMI_ANIO_2` | Numeric | Programación Multianual Año +2 | |
| `PMI_ANIO_3` | Numeric | Programación Multianual Año +3 | |
| `PMI_ANIO_4` | Numeric | Programación Multianual Año +4 | |
| `PRIMER_DEVENGADO` | String | Fecha del primer devengado | |
| `ULTIMO_DEVENGADO` | String | Fecha del último devengado | |
| `DEV_ANIO_ACTUAL` | Numeric | Devengado año actual | |

#### Etapas y documentos (Invierte.pe)

| Campo | Tipo | Descripción |
|---|---|---|
| `TIENE_F8` | String | `SI`/`NO` — tiene Formato 8 (ficha de ejecución física) |
| `ETAPA_F8` | String | Etapa actual: `Aprobación (A)`, `Expediente técnico (B)`, `Ejecución física (C)` |
| `TIENE_F9` | String | `SI`/`NO` — tiene Formato 9 (liquidación/cierre) |
| `FEC_REG_F9` | String | Fecha de registro del F9 |
| `ETAPA_F9` | String | Etapa del F9 |
| `TIENE_F12B` | String | `SI`/`NO` — tiene Formato 12B |
| `INFORME_CIERRE` | String | `SI`/`NO` — tiene informe de cierre |
| `REGISTRADO_PMI` | String | `SI`/`NO` — registrado en la Programación Multianual |
| `EXPEDIENTE_TECNICO` | String | `SI`/`NO` — cuenta con expediente técnico aprobado |

#### Modalidad y tipología

| Campo | Tipo | Descripción | Valores observados |
|---|---|---|---|
| `DES_MODALIDAD` | String | Modalidad de ejecución | `ADMINISTRACIÓN DIRECTA`, `CONTRATA` |
| `DES_TIPOLOGIA` | String | Tipo de obra | ej: `PISTAS Y VEREDAS`, `SISTEMA DE RIEGO` |
| `FUNCION` | String | Función presupuestal | `TRANSPORTE`, `SANEAMIENTO`, etc. |
| `PROGRAMA` | String | Programa presupuestal | |
| `SUBPROGRAMA` | String | Sub-programa | |
| `ALTERNATIVA` | String | Alternativa seleccionada en formulación | |
| `IND_IOARR_EMERG` | String | `SI`/`NO` — IOARR de emergencia | |

#### Financiero contractual

| Campo | Tipo | Descripción |
|---|---|---|
| `MONTO_ET_F8` | Numeric | Monto del Expediente Técnico en F8 |
| `MONTO_FIANZA` | Numeric | Monto de fianza contractual |
| `MONTO_LAUDO` | Numeric | Monto de laudo arbitral |
| `CTRL_CONCURR` | Numeric | Control de concurrencia |

#### Cronograma de ejecución

| Campo | Tipo | Descripción |
|---|---|---|
| `FEC_INI_EJECUCION` | Datetime | Fecha de inicio de ejecución (contrato) |
| `FEC_FIN_EJECUCION` | Datetime | Fecha de fin de ejecución (contrato) |
| `FEC_INI_EJEC_FISICA` | Datetime | Fecha de inicio de ejecución física (F8) |
| `FEC_FIN_EJEC_FISICA` | Datetime | Fecha de fin de ejecución física (F8) |
| `FECHA_VIABILIDAD` | Datetime | Fecha de declaración de viabilidad |
| `FECHA_REGISTRO` | Datetime | Fecha de registro en el sistema |
| `ULT_FEC_DECLA_ESTIM` | String | Última fecha de declaración estimada |

#### Georreferenciación

| Campo | Tipo | Descripción | Observaciones |
|---|---|---|---|
| `LATITUD` | Numeric | Latitud WGS84 | ~83% de proyectos la tienen |
| `LONGITUD` | Numeric | Longitud WGS84 | ~83% de proyectos la tienen |
| `UBIGEO` | String | Código UBIGEO del distrito | `080104` para San Jerónimo |
| `DEPARTAMENTO` | String | Departamento de la obra | `CUSCO` |
| `PROVINCIA` | String | Provincia de la obra | `CUSCO` |
| `DISTRITO` | String | Distrito de la obra | `SAN JERONIMO` |

#### Unidades institucionales

| Campo | Tipo | Descripción |
|---|---|---|
| `ENTIDAD` | String | Nombre de la entidad ejecutora |
| `NIVEL` | String | Nivel de gobierno: `GL` (Gobierno Local) |
| `SECTOR` | String | `GOBIERNOS LOCALES` |
| `NOMBRE_UEI` | String | Unidad Ejecutora de Inversiones |
| `NOMBRE_UF` | String | Unidad Formuladora |
| `NOMBRE_OPMI` | String | Oficina de Programación Multianual |
| `NOMBRE_UEP` | String | Unidad Ejecutora de Presupuesto |
| `NUM_HABITANTES_BENEF` | String | Número de habitantes beneficiarios |

### 12.3 Llave de cruce con el dataset SIAF

| Campo Invierte.pe | Campo SIAF (ejecución) | Descripción |
|---|---|---|
| `CODIGO_UNICO` | `PRODUCTO_PROYECTO` | **Código del proyecto** — llave principal de cruce entre ambos datasets |
| `SEC_EJEC` | `SEC_EJEC` | Código de ejecutora — mismo valor (`300687`) |
| `FUNCION` | `FUNCION_NOMBRE` | Función presupuestal |

> **Nota:** El campo `CODIGO_UNICO` en el dataset de Invierte.pe equivale al código que aparece en `PRODUCTO_PROYECTO` del dataset SIAF (cuando `TIPO_ACT_PROY = '2'`). Esta es la llave que permite cruzar el avance físico (Invierte.pe) con la ejecución financiera (SIAF).

### 12.4 Estado de proyectos San Jerónimo 2026

De los **70 proyectos activos**:

| Condición | Cantidad |
|---|---|
| Con avance físico registrado (`TIENE_AVAN_FISICO = 'SI'`) | ~38 |
| Sin avance físico aún | ~32 |
| En etapa de Ejecución Física (C) | ~45 |
| En etapa Expediente Técnico (B) | ~7 |
| En etapa Aprobación (A) | ~10 |
| Sin etapa asignada | ~8 |
| Con coordenadas GPS | ~58 (83%) |

**Rangos de avance físico observados:**
- Proyectos al 100%: 3 (completados pendientes cierre)
- Entre 80-99%: ~6 proyectos
- Entre 50-79%: ~10 proyectos
- Entre 20-49%: ~8 proyectos
- Entre 1-19%: ~5 proyectos
- En 0% (sin iniciar físicamente): ~6 proyectos

### 12.5 Consultas SQL validadas

```sql
-- Proyectos con avance físico de San Jerónimo
SELECT "CODIGO_UNICO", "NOMBRE_INVERSION", "AVANCE_FISICO", "AVANCE_EJECUCION",
       "PIM_ANIO_ACTUAL", "DEV_ANIO_ACTUAL", "ETAPA_F8", "TIENE_AVAN_FISICO"
FROM "f9cc4ba0-931a-4b70-86c9-eacbd8c68596"
WHERE "SEC_EJEC" = '300687'
LIMIT 100

-- Georreferenciación de proyectos
SELECT "CODIGO_UNICO", "NOMBRE_INVERSION", "LATITUD", "LONGITUD",
       "UBIGEO", "DISTRITO", "DES_TIPOLOGIA", "AVANCE_FISICO"
FROM "f9cc4ba0-931a-4b70-86c9-eacbd8c68596"
WHERE "SEC_EJEC" = '300687'
  AND "LATITUD" != ''
LIMIT 100

-- Ficha completa de un proyecto específico
SELECT "CODIGO_UNICO", "NOMBRE_INVERSION", "COSTO_ACTUALIZADO", "MONTO_VIABLE",
       "FEC_INI_EJECUCION", "FEC_FIN_EJECUCION", "DES_MODALIDAD", "DES_TIPOLOGIA",
       "AVANCE_FISICO", "AVANCE_EJECUCION", "ETAPA_F8", "LATITUD", "LONGITUD"
FROM "f9cc4ba0-931a-4b70-86c9-eacbd8c68596"
WHERE "CODIGO_UNICO" = '2471517'
LIMIT 1
```

### 12.6 Impacto en el diseño del sistema

| Hallazgo | Impacto |
|---|---|
| `AVANCE_FISICO` disponible directamente | El Portal de Obras puede mostrar % avance sin calcular — consumir directamente |
| Coordenadas GPS en ~83% de proyectos | Mapa de obras viable sin datos adicionales; ~12 proyectos sin coordenadas requieren georeferenciación manual |
| `CODIGO_UNICO` = `PRODUCTO_PROYECTO` (SIAF) | El cruce financiero-físico es directo con una sola llave |
| `ETAPA_F8` como estado del proceso | Usar para semáforo de estado: A=formulación, B=expediente, C=ejecución |
| `COSTO_ACTUALIZADO` vs `MONTO_VIABLE` vs `PIM_ANIO_ACTUAL` | Mostrar los tres: costo total, costo viable y presupuesto del año para contexto completo |
| Sin datos de años anteriores en este resource_id | Dataset es snapshot del año vigente; no permite histórico de avance físico por API |
| `NUM_HABITANTES_BENEF` presente pero mayormente vacío | No confiable como dato; complementar con formulación si se necesita |

---

## 13. Pendientes — Actividad 1 (continuación SIGA)

- [ ] Identificar en SIGA el campo que almacena el número de expediente/registro SIAF en `SIG_DEVENGADO` y `SIG_ORDEN_ADQUISICION`
- [ ] Confirmar que `SEC_FUNC` de la API coincide numéricamente con `sec_func` de la tabla `META` del SIGA para el año 2025 (los datos SIGA explorados son 2025; la API tiene 2026)
- [ ] Identificar resource_id para años anteriores (2024, 2025) en el portal de datos abiertos del MEF
- [x] ~~Explorar si existe un endpoint/dataset MEF para el estado físico de las obras~~ → **Resuelto:** dataset `f9cc4ba0-931a-4b70-86c9-eacbd8c68596` (sección 12)
- [ ] Verificar si existe resource_id histórico para el dataset Detalle de Inversiones (avance físico en años anteriores)
- [ ] Documentar estructura de `SIG_ORDEN_ADQUISICION` y `SIG_DEVENGADO` para completar el mapeo de cruce

---

*Documento generado como parte de la Actividad 1 — Exploración y Mapeo de Datos · Fase de Diseño · Julio 2026*
