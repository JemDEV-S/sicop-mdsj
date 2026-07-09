# Diccionario de Datos Unificado — SIAF ↔ SIGA

> Municipalidad Distrital de San Jerónimo — Cusco
> Entregable formal de la Actividad 1 · Fase de Diseño
> Consolida los campos de la API MEF (SIAF e Invierte.pe) y la base de datos SIGA, con las llaves de cruce validadas.
> Julio 2026

---

## 1. Alcance

Este documento consolida los campos relevantes de las tres fuentes de datos del sistema, agrupados por dominio funcional:

| Fuente | Origen técnico | Cobertura temporal |
|---|---|---|
| **SIAF** | API Datos Abiertos MEF — `datastore_search_sql` — resource `615644aa-ef73-4358-b4e0-0c20931632f3` | Solo 2026 en el resource explorado |
| **Invierte.pe** | API Datos Abiertos MEF — resource `f9cc4ba0-931a-4b70-86c9-eacbd8c68596` | Solo 2026 en el resource explorado |
| **SIGA** | SQL Server local — esquema `dbo` — ~937 tablas | 2023 – 2026 |

Cada dominio incluye: campos utilizados por el sistema, su equivalente en la otra fuente cuando aplica, y observaciones para el diseño.

---

## 2. Identificación de la Entidad

Todos los cruces del sistema requieren esta entidad como filtro fijo.

| Concepto | SIAF (API) | Invierte.pe (API) | SIGA (SQL) | Valor |
|---|---|---|---|---|
| Código de unidad ejecutora | `SEC_EJEC` | `SEC_EJEC` | `SEC_EJEC` (todas las tablas) | `300687` |
| Nombre de la ejecutora | `EJECUTORA_NOMBRE` | `ENTIDAD` | `EJECUTORA.nombre` | MUNICIPALIDAD DISTRITAL DE SAN JERONIMO |
| Nivel de gobierno | `NIVEL_GOBIERNO` = `GOBIERNOS LOCALES` | `NIVEL` = `GL` | — | Gobierno Local |
| Departamento | `DEPARTAMENTO_EJECUTORA_NOMBRE` = `CUSCO` | `DEPARTAMENTO` = `CUSCO` | — | Cusco |
| Distrito | `DISTRITO_EJECUTORA_NOMBRE` = `SAN JERONIMO` | `DISTRITO` = `SAN JERONIMO` | — | San Jerónimo |
| UBIGEO | — | `UBIGEO` = `080104` | — | 080104 |
| Pliego / Sector | `PLIEGO`, `SECTOR` (vacíos para GL) | — | — | No aplica para gobiernos locales |

> **Regla de diseño:** Toda consulta a la API MEF debe filtrar por `SEC_EJEC = '300687'`. Toda consulta a SIGA debe filtrar por `SEC_EJEC = 300687` y `ANO_EJE = <año>`.

---

## 3. Cadena Funcional Programática

Es la columna vertebral del presupuesto público. La jerarquía es idéntica en ambas fuentes.

```
FUNCION → DIVISION_FUNCIONAL → GRUPO_FUNCIONAL → PROGRAMA_PPTO
  → PRODUCTO/PROYECTO → ACTIVIDAD/ACCION/OBRA → FINALIDAD → META
```

| Nivel | SIAF (API) | SIGA (SQL) | Descripción |
|---|---|---|---|
| Función | `FUNCION` / `FUNCION_NOMBRE` | `META.funcion` (2) — tabla `FUNCION` | Ej: TRANSPORTE, SANEAMIENTO |
| División funcional | `DIVISION_FUNCIONAL` / `..._NOMBRE` | — | Solo en SIAF |
| Grupo funcional | `GRUPO_FUNCIONAL` / `..._NOMBRE` | — | Solo en SIAF |
| Programa presupuestal | `PROGRAMA_PPTO` / `..._NOMBRE` | `META.programa` (3) — tabla `PROGRAMA` | Ej: 0082 Saneamiento Urbano |
| Sub-programa | — | `META.sub_programa` (4) — tabla `SUB_PROGRAMA` | Solo en SIGA |
| Producto / Proyecto | `PRODUCTO_PROYECTO` / `..._NOMBRE` | `META.act_proy` (7) — tabla `ACT_PROY` | **Llave de cruce con Invierte.pe** |
| Componente | — | `META.componente` (7) — tabla `COMPONENTE` | Solo en SIGA |
| Categoría de gasto | `CATEGORIA_GASTO` (`5` corriente, `6` capital) | — | Solo en SIAF |
| Tipo actividad/proyecto | `TIPO_ACT_PROY` (`2` proyecto, `3` actividad) | Derivado del prefijo de `act_proy` | `2xxxxxx` = Invierte.pe; `3999999` = actividad genérica; `3xxxxxx ≠ 3999999` = actividad PP |
| Actividad / Acción / Obra | `ACTIVIDAD_ACCION_OBRA` / `..._NOMBRE` | — | Solo en SIAF |
| Finalidad | `FINALIDAD` | `META.finalidad` (10) — tabla `FINALIDAD` | Máximo detalle funcional |
| Departamento de la meta | `DEPARTAMENTO_META` / `..._NOMBRE` | — | Solo en SIAF |
| Meta | `META` (5) | `META.meta` (5) | Código de meta |
| Secuencia funcional de la meta | `SEC_FUNC` | `META.sec_func` | **Llave principal de cruce SIAF↔SIGA** |
| Nombre descriptivo | `META_NOMBRE` | `META.nombre` (150) | Nombre humano de la meta |

---

## 4. Meta Presupuestal (tabla `META` en SIGA)

Núcleo del cruce. Toda ejecución del sistema se relaciona con una fila de esta tabla.

| Campo SIGA | Tipo | Descripción | Equivalente SIAF |
|---|---|---|---|
| `ano_eje` | numeric | **PK** — año fiscal | `ANO_EJE` |
| `sec_ejec` | numeric | **PK** — ejecutora | `SEC_EJEC` |
| `sec_func` | numeric | **PK** — secuencia única de la meta | `SEC_FUNC` |
| `funcion` | varchar(2) | Código de función | `FUNCION` |
| `programa` | varchar(3) | Código de programa | `PROGRAMA_PPTO` |
| `sub_programa` | varchar(4) | Código de sub-programa | — |
| `act_proy` | varchar(7) | Código de actividad/proyecto | `PRODUCTO_PROYECTO` (proyectos con prefijo `2`) |
| `componente` | varchar(7) | Código de componente | — |
| `meta` | varchar(5) | Código de meta | `META` |
| `finalidad` | varchar(10) | Código de finalidad | `FINALIDAD` |
| `nombre` | varchar(150) | Nombre descriptivo | `META_NOMBRE` |
| `monto` | numeric | Presupuesto asignado (aparece en 0 — usar `SIG_TECHO_PRESUPUESTO`) | — |
| `cantidad` | numeric | Meta física | — |
| `unidad_med` | varchar(3) | Unidad de medida | — |
| `estado` | varchar(1) | `A` = Activo | — |

**Volumen:** 741 metas | Integridad: 771 → 771 sin huérfanos.

---

## 5. Clasificadores de Gasto

Cadena `Genérica → Sub-genérica → Sub-genérica detalle → Específica → Específica detalle`.

| Nivel | SIAF (API) | SIGA (SQL) | Notas |
|---|---|---|---|
| Genérica | `GENERICA` / `GENERICA_NOMBRE` | Contenida dentro de `CLASIFICADOR` (compuesto) | Valores: `1` Personal, `2` Pensiones, `3` Bienes/Servicios, `6` Adq. Activos |
| Sub-genérica | `SUBGENERICA` / `..._NOMBRE` | Idem | |
| Sub-genérica detalle | `SUBGENERICA_DET` / `..._NOMBRE` | Idem | |
| Específica | `ESPECIFICA` / `..._NOMBRE` | Idem | |
| Específica detalle | `ESPECIFICA_DET` / `..._NOMBRE` | Idem | |
| Clasificador completo | Concatenación de los 5 niveles | `SIG_ORDEN_PRESUPUESTO.CLASIFICADOR`, `SIG_TECHO_PRESUPUESTO.CLASIFICADOR`, `SIG_CERTIFICACION_PPTO.CLASIFICADOR` | En SIGA el clasificador viene como cadena compuesta |

> **Diseño:** El backend deberá normalizar el clasificador SIGA a los cinco niveles para poder unirlo con los códigos SIAF individuales cuando se cruce por clasificador.

---

## 6. Fuentes de Financiamiento

| Concepto | SIAF (API) | SIGA (SQL) | Valores observados |
|---|---|---|---|
| Fuente | `FUENTE_FINANCIAMIENTO` / `..._NOMBRE` | `FUENTE_FINANC` (en múltiples tablas) | `1` RO, `2` RDR, `4` Donaciones, `5` R. Determinados |
| Rubro | `RUBRO` / `RUBRO_NOMBRE` | — | `00`, `07` FONCOMUN, `08` Impuestos Municipales, `09` RDR, `13` Donaciones, `18` Canon |
| Tipo de recurso | `TIPO_RECURSO` / `..._NOMBRE` | `SIG_METAS_X_CENTRO.tipo_recurso` | |
| Tipo de transacción | `TIPO_TRANSACCION` | — | Solo valor `2` observado |

---

## 7. Montos Presupuestales y de Ejecución

Estos campos alimentan los dashboards de ejecución y el módulo de saldos.

### 7.1 Desde SIAF (API MEF)

| Campo | Descripción | Notas |
|---|---|---|
| `MONTO_PIA` | Presupuesto Institucional de Apertura | **Aparece en `0` en 2026** — no confiable en el resource actual |
| `MONTO_PIM` | Presupuesto Institucional Modificado | Usar `MES_EJE = 0` para el PIM vigente |
| `MONTO_CERTIFICADO` | Monto certificado | |
| `MONTO_COMPROMETIDO_ANUAL` | Compromiso anual | |
| `MONTO_COMPROMETIDO` | Compromiso mensual | |
| `MONTO_DEVENGADO` | Monto devengado | |
| `MONTO_GIRADO` | Monto girado / pagado | |

### 7.2 Desde SIGA (`SIG_TECHO_PRESUPUESTO`)

Tabla principal de saldos. PK compuesta por `ANO_EJE + SEC_EJEC + sec_func + CLASIFICADOR + CENTRO_COSTO`.

| Campo | Descripción | Equivalente SIAF |
|---|---|---|
| `PPTO_PIA` | PIA | `MONTO_PIA` |
| `PPTO_MODIF` | **PIM vigente** | `MONTO_PIM` |
| `mnto_acum_cert` | Certificado acumulado | `MONTO_CERTIFICADO` |
| `mnto_acum_coma` | Compromiso anual acumulado | `MONTO_COMPROMETIDO_ANUAL` |
| `mnto_acum_comm` | Compromiso mensual acumulado | `MONTO_COMPROMETIDO` |
| `MNTO_ACUM_DEVGDO_SIGA` | Devengado acumulado (fuente SIGA) | `MONTO_DEVENGADO` |
| `MNTO_ACUM_DEVGDO_SIAF` | Devengado acumulado (fuente SIAF) | `MONTO_DEVENGADO` |
| `PPTO_DISP_SIAF` | **Saldo disponible según SIAF** | Derivable |
| `MNTO_RESERVA_PEDIDO` | Reservado por pedidos pendientes | — |
| `EJEC_01` … `EJEC_12` | Ejecución mensual | Derivable por `MES_EJE` |
| `PRE_EJEC_01` … `PRE_EJEC_12` | Ejecución prevista mensual | — |

> **Regla de diseño:** Para dashboards de saldo, la fuente autoritativa es `SIG_TECHO_PRESUPUESTO` (más granular, tiene el saldo pre-calculado). El SIAF sirve como reconciliación diaria.

### 7.3 Dimensión temporal

| Concepto | SIAF | SIGA |
|---|---|---|
| Año fiscal | `ANO_EJE` | `ANO_EJE` |
| Mes de ejecución | `MES_EJE` | `EJEC_01`…`EJEC_12` (columnas por mes) |
| Interpretación mes 0 | `MES_EJE = 0` → PIM vigente, sin ejecución mensual | — |
| Meses disponibles 2026 (a julio) | 0, 1, 2, 3, 4, 5, 6, 7 | — |

---

## 8. Proyectos de Inversión — Dataset Invierte.pe

Complementa el SIAF con avance físico, georreferenciación y estado de fase. Solo aplica a proyectos (`TIPO_ACT_PROY = '2'` en SIAF).

### 8.1 Identificación

| Campo | Descripción | Cruce |
|---|---|---|
| `CODIGO_UNICO` | Código único Invierte.pe / SNIP | **= `PRODUCTO_PROYECTO` en SIAF y `META.act_proy` en SIGA** |
| `NOMBRE_INVERSION` | Nombre completo | ≈ `PRODUCTO_PROYECTO_NOMBRE` |
| `TIPO_INVERSION` | `PROYECTO DE INVERSIÓN` o `INVERSIONES IOARR` | |
| `MARCO` | `INVIERTE` o `SNIP` | |
| `ESTADO` | `ACTIVO` / `CERRADO` | |
| `SITUACION` | `VIABLE`, `APROBADO` | |
| `ANIO_PROCESO` | Solo `2026` en el resource actual | |

### 8.2 Avance físico y financiero

| Campo | Descripción | Uso en el sistema |
|---|---|---|
| `AVANCE_FISICO` | % avance físico | Portal de obras — indicador principal |
| `AVANCE_EJECUCION` | % avance financiero | Portal de obras |
| `TIENE_AVAN_FISICO` | `SI`/`NO` — reporta avance | Filtro para mostrar barra de progreso |
| `PIM_ANIO_ACTUAL` | PIM del año para el proyecto | |
| `DEV_ANIO_ACTUAL` | Devengado del año | |
| `DEVEN_ACUMUL_ANIO_ANT` | Devengado acumulado histórico | |
| `COMPROM_ANUAL_ANIO_ACTUAL` | Compromiso anual | |
| `CERTIF_ANIO_ACTUAL` | Certificado del año | |
| `PIA_ANIO_ACTUAL` | PIA del año | |
| `COSTO_ACTUALIZADO` | Costo total actualizado del proyecto | Ficha de obra |
| `MONTO_VIABLE` | Monto al momento de la viabilidad | Ficha de obra |
| `SALDO_EJECUTAR` | Saldo por ejecutar (en millones) | |
| `PMI_ANIO_1` … `PMI_ANIO_4` | Programación multianual | |
| `PRIMER_DEVENGADO` / `ULTIMO_DEVENGADO` | Fechas de ejecución | Timeline del proyecto |

### 8.3 Etapas Invierte.pe (formatos)

| Campo | Descripción | Semáforo sugerido |
|---|---|---|
| `TIENE_F8` / `ETAPA_F8` | Formato 8 — ficha de ejecución física | A=formulación, B=expediente, C=ejecución |
| `TIENE_F9` / `FEC_REG_F9` / `ETAPA_F9` | Formato 9 — liquidación / cierre | |
| `TIENE_F12B` | Formato 12B | |
| `INFORME_CIERRE` | `SI`/`NO` | |
| `REGISTRADO_PMI` | Registrado en Programación Multianual | |
| `EXPEDIENTE_TECNICO` | Tiene expediente técnico aprobado | |

### 8.4 Modalidad, cronograma y ubicación

| Campo | Descripción | Uso |
|---|---|---|
| `DES_MODALIDAD` | `ADMINISTRACIÓN DIRECTA` / `CONTRATA` | Ficha de obra |
| `DES_TIPOLOGIA` | Tipo de obra (pistas, riego, edificación…) | Filtro del portal |
| `FUNCION` / `PROGRAMA` / `SUBPROGRAMA` | Cadena funcional | Cruce con SIAF |
| `FEC_INI_EJECUCION` / `FEC_FIN_EJECUCION` | Plazo contractual | Timeline |
| `FEC_INI_EJEC_FISICA` / `FEC_FIN_EJEC_FISICA` | Fechas físicas del F8 | Timeline |
| `FECHA_VIABILIDAD` / `FECHA_REGISTRO` | Fechas del ciclo Invierte.pe | |
| `LATITUD` / `LONGITUD` | Coordenadas WGS84 | **Mapa de obras** — disponible en ~83% |
| `UBIGEO` | `080104` para San Jerónimo | |
| `DEPARTAMENTO` / `PROVINCIA` / `DISTRITO` | Ubicación textual | |

### 8.5 Unidades institucionales del proyecto

| Campo | Descripción |
|---|---|
| `NOMBRE_UEI` | Unidad Ejecutora de Inversiones |
| `NOMBRE_UF` | Unidad Formuladora |
| `NOMBRE_OPMI` | Oficina de Programación Multianual |
| `NOMBRE_UEP` | Unidad Ejecutora de Presupuesto |
| `NUM_HABITANTES_BENEF` | Beneficiarios (poco confiable, mayormente vacío) |

### 8.6 Financiero contractual

| Campo | Descripción |
|---|---|
| `MONTO_ET_F8` | Monto del Expediente Técnico en F8 |
| `MONTO_FIANZA` | Fianza contractual |
| `MONTO_LAUDO` | Laudo arbitral |
| `CTRL_CONCURR` | Control de concurrencia |

---

## 9. Unidades Orgánicas — Centros de Costo

Toda operación SIGA se ancla en una unidad orgánica.

### 9.1 `SIG_CENTRO_COSTO`

| Campo | Tipo | Descripción |
|---|---|---|
| `ANO_EJE` / `SEC_EJEC` / `CENTRO_COSTO` | PK | Año + ejecutora + código del centro |
| `NOMBRE_DEPEND` | varchar(100) | Nombre de la unidad orgánica |
| `ABREVIADO_DEPEND` | varchar(50) | Nombre abreviado |
| `CENTRO_PADRE` | varchar(15) | **FK autorreferencial** — árbol organizacional |
| `SEDE` | numeric | FK → `SIG_SEDES` |
| `TIPO_DEPEND` | char(1) | Tipo de dependencia |
| `ESTADO` | char(1) | `A` = Activo |
| `NRO_PERSONAL` | numeric | Personal asignado |
| `FLAG_CN` | varchar(1) | Participa en cuadro de necesidades |
| `FLAG_PRESUPUESTO` | varchar(1) | Tiene presupuesto asignado |
| `flag_ppr` | varchar(1) | Participa en PPR |
| `FLAG_AREA_ESTRATEGICA` | varchar(1) | Es área estratégica |

**Volumen:** 333 centros | 64 con metas asignadas en 2025.

### 9.2 Puente Meta ↔ Centro: `SIG_METAS_X_CENTRO`

| Campo | Descripción |
|---|---|
| `ano_eje` / `sec_ejec` / `centro_costo` / `secuencia` | PK |
| `sec_func` | **FK lógica** → `META.sec_func` |
| `fuente_financ` | Fuente asignada al centro para esa meta |
| `tipo_recurso` | Tipo de recurso |
| `porc_techo` | % del techo presupuestal |

**Volumen:** 771 asignaciones | Integridad perfecta con META y con SIG_CENTRO_COSTO.

### 9.3 Sedes

| Tabla | Uso |
|---|---|
| `SIG_SEDES` | 13 sedes físicas registradas — sin jerarquía sede-dependencia poblada |

---

## 10. Cadena Logística — Del Pedido al Devengado

Modela el ciclo operativo SIGA que alimenta el pipeline del panel interno.

### 10.1 Flujo completo

```
CUADRO DE NECESIDADES → PAAC → PEDIDO → ORDEN DE COMPRA/SERVICIO
    → CERTIFICACIÓN → CONFORMIDAD → DEVENGADO → GIRADO (SIAF)
```

### 10.2 Pedidos — `SIG_PEDIDOS` + `SIG_DETALLE_PEDIDOS`

**Cabecera `SIG_PEDIDOS`** — 13,083 registros (2023-2026):

| Campo | Descripción |
|---|---|
| `ANO_EJE` / `SEC_EJEC` / `NRO_PEDIDO` / `TIPO_BIEN` | PK |
| `TIPO_BIEN` | `B` = Bien, `S` = Servicio |
| `TIPO_PEDIDO` | `1` = pedido de almacén, `2` = compra/servicio directo |
| `CENTRO_COSTO` | Unidad solicitante |
| `sec_func` | Meta presupuestal |
| `ACT_PROY` | Proyecto/actividad |
| `ESTADO` | `0` borrador, `1` aprobado, `7` cerrado |
| `FECHA_PEDIDO` / `FECHA_APROB` / `FECHA_ATENC` | Fechas de las etapas |
| `MOTIVO_PEDIDO` | Justificación |
| `NOMBRE_EMPLEADO` | Solicitante |
| `FUENTE_FINANC` | Fuente |

**Detalle `SIG_DETALLE_PEDIDOS`** — 47,018 ítems:

| Campo | Descripción |
|---|---|
| `NRO_PEDIDO` / `SECUENCIA` | PK del ítem |
| `ITEM_BIEN` | FK → `CATALOGO_BIEN_SERV` |
| `CANT_SOLICITADA` / `CANT_APROBADA` / `CANT_ATENDIDA` | Cantidades por etapa |
| `VALOR_TOTAL` | Monto del ítem |
| `CLASIFICADOR` | Clasificador de gasto |
| `NRO_ORDEN` | **FK → `SIG_ORDEN_ADQUISICION`** |
| `ESTADO_PED` / `ESTADO_ATEND` / `ESTADO_CONFOR` / `ESTADO_COMPRA` | Estados por dimensión |
| `FECHA_CONFOR` | Fecha de la conformidad |

**Estados observados en 2025:** 9,861 ítems en proceso (`PED=1,ATEND=0,CONFOR=0`) | 7,768 completados (`PED=8,ATEND=1,CONFOR=1`).

### 10.3 Órdenes — `SIG_ORDEN_ADQUISICION` + `SIG_ORDEN_PRESUPUESTO`

**Cabecera `SIG_ORDEN_ADQUISICION`** — 8,298 registros:

| Campo | Descripción |
|---|---|
| `ANO_EJE` / `SEC_EJEC` / `NRO_ORDEN` / `TIPO_BIEN` | PK |
| `TIPO_BIEN` | `B` = compra, `S` = servicio |
| **`EXP_SIAF`** | **Número de expediente SIAF — llave de cruce con SIAF** |
| `EXP_SIGA` | Expediente interno SIGA |
| `ESTADO_SIAF` | `0` pendiente, `2` aceptado SIAF, `3` rechazado |
| `ESTADO` | `1` vigente |
| `TOTAL_FACT_SOLES` | Monto total |
| `CONCEPTO` | Descripción |
| `FECHA_ORDEN` | Emisión |
| `NRO_CONTRATO` / `ANO_CONTRATO` / `SEC_CONTRATO` | Contrato asociado |
| `PROVEEDOR` | FK → `SIG_CONTRATISTAS` |

**Afectación `SIG_ORDEN_PRESUPUESTO`** — 8,927 registros:

| Campo | Descripción |
|---|---|
| `ANO_EJE` / `SEC_EJEC` / `NRO_ORDEN` / `TIPO_BIEN` | FK → `SIG_ORDEN_ADQUISICION` |
| **`SEC_FUNC`** | **FK → `META.sec_func`** — llave de cruce con SIAF |
| `CLASIFICADOR` | Clasificador de gasto |
| `FUENTE_FINANC` | Fuente |
| `EXP_SIAF` | Expediente SIAF (redundante, útil para JOIN directo) |
| `VALOR_SOLES` | Monto de la afectación |
| `FASE` | Fase presupuestal |

**Ítems `SIG_ORDEN_ITEM_PPTO`** — 25,429 registros con detalle presupuestal por ítem.

### 10.4 Certificaciones

| Tabla | Volumen | Rol |
|---|---|---|
| `SIG_CERTIFICACION_PPTO` | 18,461 | Certificación presupuestal: `NRO_CERTIFICA`, `SEC_FUNC`, `CLASIFICADOR`, `VALOR_SOLES`, `FECHA_REG` |
| `SIG_CERTIFICACION_FASE` | 16,387 | Relaciona certificación con orden: `NRO_CERTIFICA` ↔ `NRO_ORDEN`, `NRO_CERTIFICA_SIAF`, `FLAG_COMPROMETIDO` |

### 10.5 Conformidades

**`SIG_MOVIM_CONFOR_SERVICIO`** — 4,943 registros:

| Campo | Descripción |
|---|---|
| `NRO_ORDEN` / `ANO_ORDEN` / `TIPO_BIEN` | FK → `SIG_ORDEN_ADQUISICION` |
| `FECHA_MOVIMTO` | Fecha de conformidad |
| `INDI_CONFOR` | Indicador |
| `NOMBRE_PROVEEDOR` | Proveedor |
| `ESTADO_DEVENG` | Estado del devengado |
| `EXPEDIENTE_SIAF` | Expediente SIAF |
| `RESPONSABLE` | Quien conformó |
| `OBSERVACION` | Observaciones |

### 10.6 Expedientes SIGA

| Tabla | Volumen | Contenido |
|---|---|---|
| `SIG_EXP_SIGA` | 8,124 | Cabecera del expediente: `EXP_SIGA`, `TIPO_FASE`, `TIPO_BIEN`, `EXP_SIAF`, `ESTADO_SIAF`, `PROVEEDOR` |
| `SIG_EXP_SIGA_PPTO` | 8,926 | Detalle presupuestal: `SEC_FUNC`, `CLASIFICADOR`, `VALOR_SOLES` |
| `SIG_EXP_SIGA_DOCU` | 8,294 | Documentos: `TIPO_DOCUMENTO`, `NRO_DOCUMENTO`, `FECHA_DOCUMENTO`, `MODAL_COMPRA`, `EXP_SIAF`, `FASE_CONTRACTUAL` |

### 10.7 Devengado

| Tabla | Volumen | Observación |
|---|---|---|
| `SIG_DEVENGADO` | 7 | **Casi vacío** — no es la fuente principal |
| `SIG_DEVENGADO_ITEM_PPTO` | 2 | Idem |

> **Diseño:** El devengado real se lee desde `SIG_ORDEN_ADQUISICION.ESTADO_SIAF = '2'` (aceptado en SIAF) o desde `SIG_TECHO_PRESUPUESTO.MNTO_ACUM_DEVGDO_SIGA`.

### 10.8 Seguimiento del pipeline

**`SIG_SEGUIMIENTO`** — 39,212 registros: log completo del flujo con `NRO_PEDIDO`, `TIPO_TRANSACCION`, `CENTRO_COSTO`, `SOLICITANTE`, `FECHA_TRANSACCION`, `ESTADO_TRANSACCION`.

### 10.9 Detección de etapas del pipeline

| Etapa | Condición SIGA |
|---|---|
| Solicitado | `SIG_PEDIDOS.ESTADO = '1'` y `SIG_DETALLE_PEDIDOS.ESTADO_PED = '1'` sin `NRO_ORDEN` |
| Con orden emitida | `SIG_DETALLE_PEDIDOS.NRO_ORDEN > 0` y `SIG_ORDEN_ADQUISICION.ESTADO = '1'` |
| En conformidad | `SIG_DETALLE_PEDIDOS.ESTADO_CONFOR = '1'` o hay `SIG_MOVIM_CONFOR_SERVICIO` |
| Devengado / pagado | `SIG_ORDEN_ADQUISICION.ESTADO_SIAF = '2'` |
| Cerrado | `SIG_PEDIDOS.ESTADO = '7'` |

---

## 11. Proveedores

### `SIG_CONTRATISTAS` — 2,645 proveedores

| Campo | Descripción |
|---|---|
| `PROVEEDOR` | **PK** — código interno (FK en órdenes y contratos) |
| `NRO_RUC` | RUC |
| `NOMBRE_PROV` | Razón social |
| `TIPO_PERSONA` | `01` Natural, `02` Jurídica |
| `GIRO_GENERAL` | Giro |
| `DIRECCION` | Dirección fiscal |
| `EMAIL` / `TELEFONOS` | Contacto |
| `DEPARTAMENTO` / `PROVINCIA` / `DISTRITO` | Ubicación (códigos) |
| `FLAG_MYPE` | `S`/`N` |
| `FLAG_RNP` / `NRO_RNP` | Inscripción en RNP |
| `FLAG_CONSORCIO` | Consorcio |
| `FECHA_ISANCION` / `FECHA_FSANCION` | Sanción vigente si aplica |
| `FLAG_SNP` | Es locador de servicios |

> La tabla `PERSONA` está vacía. `SIG_CONTRATISTAS` es la única fuente confiable de proveedores.

---

## 12. Contratos

### `SIG_CONTRATOS` — 127 contratos (2023-2026)

| Campo | Descripción |
|---|---|
| `ANO_EJE` / `SEC_EJEC` / `TIPO_CONTRATO` / `NRO_CONTRATO` / `SEC_CONTRATO` | PK |
| `TIPO_BIEN` | `B` / `S` |
| `PROVEEDOR` | FK → `SIG_CONTRATISTAS` |
| `FECHA_INICIAL` / `FECHA_FINAL` / `FECHA_CESE` | Plazos |
| `VALOR_SOLES` | Monto |
| `OBJETO` / `GLOSA` | Descripción |
| `TIPO_COMPRA` / `MODAL_COMPRA` | Modalidad (AS, LP, CE, etc.) |
| `ID_PROCESO` / `ID_CONTRATO` | Identificadores en OSCE/SEACE |
| `NRO_DOCUMENTO` | Documento contractual |
| `ESTADO` | Estado |
| `FLAG_SNP` | Contrato SNP |
| `NRO_MESES` / `MONTO_SUELDO_SOLES` | Para contratos de personal |

---

## 13. Plan Anual de Adquisiciones y Contrataciones (PAAC)

### `SIG_PAAC_CONSOLIDADO` — 9,958 registros

| Campo | Descripción |
|---|---|
| `TIPO_CONSOLID` / `NRO_CONSOLID` | PK |
| `TIPO_BIEN` | `B` / `S` |
| `TIPO_PROCESO` | Código del proceso de selección |
| `TIPO_COMPRA` / `MODAL_COMPRA` | Tipo y modalidad |
| `OBJETO` | Objeto del gasto |
| `VALOR_PLAN` | Monto planificado |
| `MES_PROPUESTO` | Mes propuesto de convocatoria |
| `ESTADO` | `1` incluido, `5` modificado, `6` concluido, `7` excluido |
| `EXP_SIAF` / `EXP_SIGA` | Expedientes cuando ya se ejecutó |
| `PROVEEDOR` | FK → `SIG_CONTRATISTAS` si adjudicado |
| `NRO_CERTIFICA` | Certificación presupuestal |
| `FLAG_CONCLUIDO` | `S` si terminado |

**Estado 2025:** 3,188 concluidos (S/26.4M) + 769 incluidos (S/11.9M) + 64 excluidos.
**Estado 2026:** 1,672 concluidos (S/18.3M) + 216 incluidos (S/24.4M).

---

## 14. Almacén

| Tabla | Volumen | Contenido |
|---|---|---|
| `SIG_MOVIM_ALMACEN` | 11,924 | `TIPO_MOVIMTO` (`I`/`S`/`R`), `NRO_ORDEN`, `PROVEEDOR`, `CENTRO_COSTO`, `EXPEDIENTE_SIAF`, `NRO_FACTURA` |
| `SIG_DETALLE_PECOSA` | 20,522 | `NRO_PECOSA`, `NRO_PEDIDO`, `CANT_ATENDIDA`, `PRECIO_UNIT`, `valor_total`, `NRO_MOVIMTO` |
| `SIG_KARDEX_POR_ALMACEN` | 16,633 | `CODIGO_BIEN`, `MES_PROCESO`, `STOCK_INICIAL`, `CANT_INGRESO`, `CANT_EGRESO`, `STOCK_ACTUAL`, `PRECIO_PROMED` |
| `SIG_KARDEX_INVENTARIO` | 1,269 | Inventarios físicos |
| `CATALOGO_BIEN_SERV` | 9,685 | Catálogo maestro: `ITEM_BIEN`, `TIPO_BIEN`, `GRUPO_BIEN`, `CLASE_BIEN`, `FAMILIA_BIEN`, `NOMBRE_ITEM`, `UNIDAD_MEDIDA`, `CODIGO_OSCE` |

---

## 15. Patrimonio

| Tabla | Volumen | Contenido |
|---|---|---|
| `SIG_PATRIMONIO` | 7,800 | `CODIGO_ACTIVO`, `TIPO_ACTIVO`, `CENTRO_COSTO`, `EMPLEADO`, `VALOR_COMPRA`, `NRO_SERIE`, `MARCA`, `MODELO`, `ESTADO_ACTUAL`, `FECHA_ALTA`, `NRO_ORDEN`, `NRO_PECOSA`, `CODIGO_BARRA`, `NRO_CONTRATO` |
| `SIG_INM_UNIDAD_ACTIVO` | 33 | Inmuebles: código, área, ubicación, título |

---

## 16. Modificaciones Presupuestales

### `SIG_DETALLE_MOVIM_PPTO` — 61,497 registros

Historial de modificaciones al PIM. Fuente para el análisis de cómo se llegó al PIM vigente.

| Campo | Descripción |
|---|---|
| `TIPO_MOVIMTO` | Tipo de modificación |
| `NRO_MOVIMTO` | Número del movimiento |
| `SEC_FUNC` | Meta afectada |
| `CLASIFICADOR` | Clasificador modificado |
| `FUENTE_FINANC` | Fuente |
| `CANT_ARTICULO` | Monto modificado |

---

## 17. Llaves de Cruce — Resumen Consolidado

### 17.1 Cadena de cruce validada

```
┌──────────────────────────────────────────────────────────────────────┐
│  API SIAF (ejecución presupuestal)                                  │
│  SEC_EJEC + ANO_EJE + SEC_FUNC + PRODUCTO_PROYECTO                  │
└─────────────┬────────────────────────────────────────────────────────┘
              │  SEC_FUNC (idéntico)
              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  SIGA · META                                                         │
│  ano_eje + sec_ejec + sec_func → act_proy, nombre, funcion          │
└─────────────┬────────────────────────────────────────────────────────┘
              │  sec_func
              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  SIGA · SIG_ORDEN_PRESUPUESTO                                       │
│  SEC_FUNC + EXP_SIAF + CLASIFICADOR + FUENTE_FINANC                 │
└─────────────┬────────────────────────────────────────────────────────┘
              │  NRO_ORDEN + TIPO_BIEN
              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  SIGA · SIG_ORDEN_ADQUISICION                                       │
│  NRO_ORDEN + TIPO_BIEN + EXP_SIAF + PROVEEDOR + TOTAL_FACT_SOLES    │
└──────────────────────────────────────────────────────────────────────┘
              │
              │  PRODUCTO_PROYECTO / act_proy = CODIGO_UNICO
              ▼
┌──────────────────────────────────────────────────────────────────────┐
│  API Invierte.pe (avance físico y geo)                              │
│  CODIGO_UNICO + AVANCE_FISICO + LATITUD + LONGITUD + ETAPA_F8       │
└──────────────────────────────────────────────────────────────────────┘
```

### 17.2 Llave principal SIAF ↔ SIGA

```
ANO_EJE + SEC_EJEC + SEC_FUNC
```

- SIAF: campo `SEC_FUNC`.
- SIGA: campo `sec_func` en `META` y en todas las tablas de ejecución.
- **Validación empírica 2025:** 160/160 `SEC_FUNC` de las órdenes tienen match en `META` (100%).

### 17.3 Llave secundaria por expediente

```
ANO_EJE + SEC_EJEC + EXP_SIAF
```

- Presente en `SIG_ORDEN_ADQUISICION`, `SIG_ORDEN_PRESUPUESTO`, `SIG_EXP_SIGA`, `SIG_MOVIM_CONFOR_SERVICIO`, `SIG_MOVIM_ALMACEN`.
- Actualmente **no expuesto** en el resource público de la API SIAF — sirve como identificador único dentro de SIGA y para consulta directa por número de expediente.
- **Validación empírica 2025:** 3,152 / 3,160 órdenes (99.7%) con `EXP_SIAF` registrado.

### 17.4 Llave para proyectos de inversión

```
CODIGO_UNICO (Invierte.pe) = PRODUCTO_PROYECTO (SIAF) = META.act_proy (SIGA)
```

- Aplica solo cuando `TIPO_ACT_PROY = '2'` (proyectos de inversión).
- Los proyectos con prefijo `2xxxxxx` se cruzan directamente.
- 70 proyectos activos San Jerónimo 2026 en Invierte.pe con `SEC_EJEC = '300687'`.

### 17.5 Otras llaves derivadas

| Cruce | Campos |
|---|---|
| Orden ↔ Certificación | `SIG_CERTIFICACION_FASE.NRO_ORDEN + TIPO_BIEN` ↔ `SIG_ORDEN_ADQUISICION` |
| Pedido ↔ Orden | `SIG_DETALLE_PEDIDOS.NRO_ORDEN` ↔ `SIG_ORDEN_ADQUISICION.NRO_ORDEN` (+ `TIPO_BIEN`) |
| Orden ↔ Almacén | `SIG_MOVIM_ALMACEN.NRO_ORDEN + ANO_ORDEN + TIPO_BIEN` ↔ `SIG_ORDEN_ADQUISICION` |
| Orden ↔ Contrato | `SIG_ORDEN_ADQUISICION.NRO_CONTRATO + ANO_CONTRATO + SEC_CONTRATO` ↔ `SIG_CONTRATOS` |
| Proveedor | Cualquier tabla con `PROVEEDOR` ↔ `SIG_CONTRATISTAS.PROVEEDOR` |
| Meta ↔ Unidad orgánica | `SIG_METAS_X_CENTRO.sec_func + centro_costo` ↔ `META` + `SIG_CENTRO_COSTO` |
| Meta ↔ Saldo | `SIG_TECHO_PRESUPUESTO.sec_func + CLASIFICADOR + CENTRO_COSTO` ↔ `META` |

---

## 18. Reglas de Diseño Derivadas del Diccionario

Reglas de aplicación directa al modelar la base intermedia (PostgreSQL) y los endpoints del backend.

1. **Filtro obligatorio de entidad:** Toda consulta a cualquiera de las tres fuentes filtra por `SEC_EJEC = 300687`.
2. **PIM autoritativo:** Usar `SIG_TECHO_PRESUPUESTO.PPTO_MODIF` como PIM de referencia; SIAF sirve como reconciliación.
3. **Saldo disponible autoritativo:** `SIG_TECHO_PRESUPUESTO.PPTO_DISP_SIAF` — no recalcular.
4. **Devengado autoritativo:** Leer del `MNTO_ACUM_DEVGDO_SIGA` o del estado de la orden (`ESTADO_SIAF = '2'`), no de `SIG_DEVENGADO` (tabla casi vacía).
5. **API MEF — límite de columnas:** Máximo ~8 columnas por request. Dividir consultas amplias y unir en el backend.
6. **API MEF — sin tildes en la URL:** Filtrar por códigos, no por nombres con caracteres especiales.
7. **API MEF — mes 0 vs meses > 0:** `MES_EJE = 0` da el PIM vigente; el mes actual da la ejecución acumulada.
8. **Categorización de metas por prefijo de `act_proy`:**
   - `3999999` → Actividad genérica
   - `2xxxxxx` → Proyecto de inversión (cruce con Invierte.pe)
   - `3xxxxxx ≠ 3999999` → Actividad de programa presupuestal
9. **Deduplicación de metas:** Aplicar `DISTINCT` al unir `META ↔ SIG_METAS_X_CENTRO` para evitar duplicados por `fuente_financ` / `tipo_recurso`.
10. **Coordenadas GPS ausentes:** ~17% de proyectos Invierte.pe sin coordenadas — el mapa debe manejar el caso de proyectos sin `LATITUD`/`LONGITUD`.
11. **PIA vacío en SIAF:** El campo `MONTO_PIA` viene en 0 en la API para 2026 — usar `SIG_TECHO_PRESUPUESTO.PPTO_PIA` como fuente.
12. **Snapshot vs histórico:** Los resources actuales del MEF son solo 2026. Para comparativo histórico habrá que persistir snapshots en la base intermedia.

---

## 19. Módulos SIGA No Utilizados (No usar en el diseño)

Estas tablas existen en el esquema pero están vacías o casi vacías. **No modelarlas** en la base intermedia ni exponer endpoints que dependan de ellas.

| Módulo | Tablas | Razón |
|---|---|---|
| Integración SIAF interna | `SIG_INT_*`, `METASIAF`, `SIG_INT_HT_META`, `SIG_INT_CONSOLIDADO_SIAF` | La entidad transmite al SIAF por otro mecanismo |
| Tesorería | `SIG_TES_*` | Módulo no implementado |
| PPR (programación mensual) | `SIG_PPR_META_MENSUAL`, `SIG_PPR_ESTABLECIMIENTO`, `SIG_PPR_DISA`, `SIG_PPR_UGEL` | Sin datos de programación |
| Planillas / pagos de contratos | `SIG_PLANILLA_SNP`, `SIG_CONTRATO_MOVIM_PAGO` | No usados |
| Seguridad SIGA | `SEG_AUDITORIA`, `SEG_USUARIO` | Gestionada en otra capa |
| Guía de remisión | `SIG_GUIA_REMISION` | Vacío |
| Devengados detallados | `SIG_DEVENGADO` (7 filas), `SIG_DEVENGADO_ITEM_PPTO` (2 filas) | Usar `SIG_TECHO_PRESUPUESTO` + estado de orden |

---

## 20. Cobertura del Diccionario por Módulo del Sistema

Referencia cruzada con los módulos definidos en la [idea principal](idea-principal.md#6-módulos-del-sistema).

| Módulo | Fuentes principales |
|---|---|
| **6.1.1 Portal de Obras** | Invierte.pe (`f9cc4ba0...`) + SIAF (`615644aa...`) + `SIG_CONTRATOS`, `SIG_ORDEN_ADQUISICION`, `SIG_CONTRATISTAS` |
| **6.1.2 Ejecución presupuestal pública** | SIAF (todos los campos de montos + cadena funcional) |
| **6.1.3 Directorio de proveedores** | `SIG_CONTRATISTAS` + `SIG_ORDEN_ADQUISICION` (montos acumulados) |
| **6.1.4 Comparativo histórico** | SIAF (requiere snapshots persistidos) + `SIG_TECHO_PRESUPUESTO` (2023-2026) |
| **6.2.1 Ejecución interna** | SIAF + `SIG_TECHO_PRESUPUESTO` + `SIG_DETALLE_MOVIM_PPTO` |
| **6.2.2 Pipeline de pedidos** | `SIG_PEDIDOS`, `SIG_DETALLE_PEDIDOS`, `SIG_SEGUIMIENTO`, `SIG_MOVIM_CONFOR_SERVICIO` |
| **6.2.3 Saldos presupuestales** | `SIG_TECHO_PRESUPUESTO`, `SIG_CERTIFICACION_PPTO`, `SIG_CERTIFICACION_FASE` |
| **6.2.4 Cruce SIAF↔SIGA** | Sección 17 completa |
| **6.2.5 Alertas** | Derivado de estados en `SIG_PEDIDOS`, `SIG_ORDEN_ADQUISICION`, `SIG_TECHO_PRESUPUESTO`, `SIG_CONTRATOS` |
| **6.2.6 Reportes y exportación** | Todas las fuentes |
| **6.2.7 Directorio proveedores con historial** | `SIG_CONTRATISTAS` + `SIG_ORDEN_ADQUISICION` + `SIG_CONTRATOS` |
| **6.3.1 Mapa de obras** | Invierte.pe (`LATITUD`, `LONGITUD`, `UBIGEO`) |
| **6.3.2 SSI del MEF** | Fuera del alcance del diccionario actual — pendiente de exploración |

---

## 21. Pendientes que No Bloquean el Diseño

- Identificar resource_id históricos del dataset SIAF (2024, 2025) para el comparativo multianual.
- Identificar resource_id histórico del dataset Invierte.pe para avance físico histórico.
- Verificar si el `EXP_SIAF` interno puede resolverse contra la API pública del MEF por algún endpoint alterno.
- Explorar el dataset SSI del MEF para el módulo 6.3.2.

Ninguno de estos bloquea el arranque de la fase de diseño (Actividades 2-5). Se pueden resolver durante la fase de desarrollo o dejarse para la v2.

---

*Diccionario consolidado a partir de [actividad-1-exploracion-mef.md](actividad-1-exploracion-mef.md) y [datos-iniciales-siga.md](datos-iniciales-siga.md). Entregable formal de la Actividad 1 — Fase de Diseño.*
