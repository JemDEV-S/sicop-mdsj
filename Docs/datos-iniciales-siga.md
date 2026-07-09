# Base de Datos SIGA — Documentación Técnica
> Municipalidad Distrital de San Jerónimo — Cusco  
> Elaborado mediante análisis exploratorio directo de la BD · Julio 2025

---

## 1. ¿Qué es el SIGA?

El **SIGA (Sistema Integrado de Gestión Administrativa)** es una herramienta informática del Estado peruano desarrollada y distribuida por el **Ministerio de Economía y Finanzas (MEF)**. Automatiza los procesos administrativos de las entidades públicas siguiendo las normas de los Órganos Rectores de los Sistemas Administrativos.

Integra los procedimientos técnico-administrativos de **Presupuesto, Logística, Patrimonio y Tesorería**, con interfaz directa hacia el **SIAF (Sistema Integrado de Administración Financiera)**.

---

## 2. Características técnicas de la instancia

### 2.1 Motor y esquema

| Parámetro | Valor |
|---|---|
| Motor de base de datos | **SQL Server 2022** (16.0.1180.1) |
| Esquema principal | `dbo` |
| Total de tablas | **~937** |
| Tablas operativas (con data) | **~840** |
| Tablas temporales/staging | **~95** |
| Entidad | Municipalidad Distrital de San Jerónimo |
| Integración SIAF activa | ❌ No (tablas `SIG_INT_*` vacías) |
| Cobertura temporal | Años 2023 – 2026 |

### 2.2 Datos de conexión (entorno de desarrollo local)

Instancia SQL Server nativa en Windows, backup SIGA_300687 restaurado localmente.

| Parámetro | Valor |
|---|---|
| **Nombre lógico servidor** | `PC_OTI_03` (por defecto de la máquina) |
| **Host / Data Source** | `.` o `localhost` (instancia default `MSSQLSERVER`) |
| **Puerto** | `1433` (default TCP) |
| **Base de datos** | `SIGA_300687` |
| **Autenticación** | **Windows Authentication (integrada)** en dev · SQL Auth para prod |
| **Encrypt** | `no` |
| **TrustServerCertificate** | `yes` |
| **ODBC Driver** | `ODBC Driver 17 for SQL Server` |

> **Nota — otras instancias detectadas en la máquina:** `MSSQLSERVER01` es otra instancia con nombre que también corre pero **no contiene** SIGA_300687 (solo `master`). Usar siempre la instancia default (`.`).

> **Nota — otras BDs presentes en la instancia:** `DBPLANILLASPLUSMDSJ2026`, `RENTAS`, `Rentas_2024_12`. No forman parte del alcance del proyecto SICOP.

### 2.3 Connection string ODBC (referencia)

```
DRIVER={ODBC Driver 17 for SQL Server};SERVER=.;DATABASE=SIGA_300687;Trusted_Connection=yes;TrustServerCertificate=yes;Encrypt=no;
```

En el backend Python se resuelve mediante `app/config.py` (soporta ambos modos):

```env
MSSQL_AUTH=windows        # o "sql"
MSSQL_SERVER=.
MSSQL_PORT=1433
MSSQL_DB=SIGA_300687
MSSQL_ODBC_DRIVER=ODBC Driver 17 for SQL Server
MSSQL_TRUST_CERT=yes
MSSQL_ENCRYPT=no
# Solo con MSSQL_AUTH=sql:
MSSQL_USER=
MSSQL_PASSWORD=
```

Ver módulo `backend/app/siga/conexion.py` y smoke test `backend/scripts/ping_siga.py`.

### 2.4 Volúmenes reales por año (validación empírica — julio 2026)

Verificación ejecutada por `scripts/ping_siga.py` sobre la instancia local:

| Tabla | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|
| `META` | 171 | 207 | 188 | 175 |
| `SIG_ORDEN_ADQUISICION` | 396 | 3,269 | 3,160 | 1,473 |
| `SIG_TECHO_PRESUPUESTO` | 1,919 | 4,038 | 1,874 | 2,218 |
| `SIG_PEDIDOS` | 705 | 5,292 | 4,728 | 2,358 |
| `SIG_CONTRATISTAS` | — | — | — | 2,645 (total, sin `ano_eje`) |

> Los 3,160 órdenes 2025 coinciden exactamente con el valor documentado en §12.4 abajo.

### 2.5 Consideraciones para producción

- En producción el backend usará **SQL Auth** con un usuario dedicado `db_datareader` sobre `SIGA_300687`.
- La conexión se hará por red interna de la muni (no expuesta a internet).
- El backend correrá como servicio contenedor. Se debe configurar `MSSQL_SERVER=host.docker.internal` (Windows/Docker Desktop) o la IP de la red interna cuando aplique.

---

## 3. Estructura de módulos

La nomenclatura de prefijos de las tablas revela el módulo al que pertenecen:

| Prefijo | Módulo | Tablas aprox. |
|---|---|---|
| `SIG_` (general) | Logística, Patrimonio y operativo general | ~340 |
| `SIG_TMP_` / `TMP_` / `TEMP_` | Tablas temporales y staging | ~95 |
| `SIG_PPR_` | Presupuesto por Resultados | ~49 |
| `SI_` | Módulo web de programación multianual | ~47 |
| `SIG_TES_` | Tesorería | ~31 |
| `SIG_INT_` | Integración SIAF | ~25 |
| `SIG_PROY_` | Comisiones de servicio y viáticos | ~24 |
| `SIG_PAAC_` | Plan Anual de Adquisiciones y Contrataciones | ~15 |
| `SEG_` | Seguridad y gestión de usuarios | ~15 |
| `SGE_` | Exportación al MEF | ~13 |
| `SIG_INM_` | Inmuebles | ~13 |
| `SIG_MSG_` | Mensajería interna | ~11 |
| `MP_` | Módulo Patrimonio (tablas propias) | ~10 |
| `DNPP_` | Dirección Nacional de Presupuesto Público | ~9 |
| `TA_` / sin prefijo / otras | Catálogos y tablas maestras | ~50 |

### Módulos principales

#### Logística (ML) — el núcleo del sistema
Gestiona toda la cadena de abastecimiento del Estado peruano:

```
Cuadro de Necesidades → PAAC → Convocatoria → Proceso de Selección
→ Contrato → Orden de Compra/Servicio → Devengado
```

Tablas más relevantes: `SIG_PEDIDOS`, `SIG_ORDEN_ADQUISICION`, `SIG_CONTRATOS`, `SIG_CUADRO_NECESIDAD`, `SIG_CERTIFICACION`, `SIG_DEVENGADO`, `SIG_KARDEX_INVENTARIO`, `SIG_MOVIM_ALMACEN`, `SIG_DETALLE_PECOSA`

#### Patrimonio (MP)
Control de bienes patrimoniales: muebles, inmuebles, construcciones, concesiones.  
Tablas clave: `SIG_PATRIMONIO`, `SIG_INM_UNIDAD_ACTIVO`, `SIG_INVENTARIO_FISICO`

#### Presupuesto por Resultados (PPR)
Programas presupuestales vinculados a metas físicas y financieras.  
Tablas clave: `SIG_PPR_KIT_ITEMS`, `SIG_PPR_META_MENSUAL`, `SIG_PPR_ESTABLECIMIENTO`

#### Tesorería
Caja, caja chica, recibos de ingreso, detracciones y arqueos.  
Tablas clave: `SIG_TES_CAJA`, `SIG_TES_CAJA_CHICA`, `SIG_TES_RECIBO_INGRESO`

#### Seguridad (`SEG_`)
Control de acceso, roles, privilegios, auditoría y políticas de contraseñas.  
Tablas clave: `SEG_USUARIO`, `SEG_ROL`, `SEG_ROL_PAGINA_PRIVILEGIO`, `SEG_AUDITORIA`, `SEG_POLITICA`

---

## 4. Tablas hub — las más referenciadas del sistema

Las tablas con mayor grado de conectividad (más FKs apuntando hacia ellas):

| Tabla | Tablas que la referencian | Rol |
|---|---|---|
| `SIG_CENTRO_COSTO` | **30 tablas** | Backbone organizacional — toda operación se vincula a una unidad orgánica |
| `META` | **9 tablas** | Núcleo presupuestal — las metas estructuran el gasto |
| `SIG_DEPEN_META_CUADRO` | 2 tablas | Detalle del cuadro de necesidades por dependencia |
| `SIG_DETALLE_METAS_CUADRO` | 1 tabla | Intermedio entre META y el cuadro de necesidades |
| `SIG_CENTRO_COSTO_TAREA` | 1 tabla | Tareas definidas a nivel de unidad orgánica |

> **`SIG_CENTRO_COSTO` es la tabla más estratégica del sistema.** Todos los movimientos — pedidos, órdenes, patrimonio, almacén, PAAC, techo presupuestal — se asocian a una unidad orgánica.

---

## 5. Modelo relacional: Metas y Unidades Orgánicas

### Tablas del ecosistema de metas

| Tabla | Filas | Descripción |
|---|---|---|
| `META` | 741 | Tabla maestra de metas presupuestales |
| `SIG_METAS_X_CENTRO` | 771 | Puente: asigna metas a unidades orgánicas |
| `SIG_META_CENTRO_TAREA` | 3,766 | Desglose de metas por tarea y centro de costo |
| `SIG_DEPEN_META_CUADRO` | 27,021 | Detalle del cuadro de necesidades por dependencia y meta |
| `SIG_CENTRO_COSTO` | 333 | Unidades orgánicas / centros de costo |
| `SIG_METAS_PROP_X_CENTRO` | 248 | Metas propuestas por centro (fase de formulación) |
| `SIG_META_PROPUESTA` | 373 | Propuestas de metas |
| `FINALIDAD` | 726 | Finalidades presupuestales |
| `COMPONENTE` | 581 | Componentes de la cadena funcional |
| `ACT_PROY` | 487 | Actividades y proyectos |
| `SUB_PROGRAMA` | 204 | Sub-programas |
| `PROGRAMA` | 138 | Programas |
| `FUNCION` | 67 | Funciones |
| `SIG_SEDES` | 13 | Sedes físicas de la entidad |

### Cadena funcional programática

La meta presupuestal se compone de la siguiente jerarquía:

```
FUNCION → PROGRAMA → SUB_PROGRAMA → ACT_PROY → COMPONENTE → FINALIDAD
```

Cada nivel tiene tablas de nombres descriptivos: `ACT_PROY_NOMBRE`, `COMPONENTE_NOMBRE`, `FUNCION_FASE`, etc.

### Estructura de la tabla META

| Campo | Tipo | Descripción |
|---|---|---|
| `ano_eje` | numeric | **PK** — año de ejecución |
| `sec_ejec` | numeric | **PK** — código de unidad ejecutora |
| `sec_func` | numeric | **PK** — secuencia única de la meta |
| `funcion` | varchar(2) | Código de función |
| `programa` | varchar(3) | Código de programa |
| `sub_programa` | varchar(4) | Código de sub-programa |
| `act_proy` | varchar(7) | Código de actividad/proyecto |
| `componente` | varchar(7) | Código de componente |
| `meta` | varchar(5) | Código de meta |
| `finalidad` | varchar(10) | Código de finalidad |
| `nombre` | varchar(150) | Nombre descriptivo de la meta |
| `monto` | numeric | Presupuesto asignado |
| `cantidad` | numeric | Meta física |
| `unidad_med` | varchar(3) | Unidad de medida |
| `estado` | varchar(1) | Estado: `A` = Activo |
| `TIPO_TAREA` | char(1) | Tipo de tarea vinculada |
| `PROGRAMA_INSTITUCIONAL` | varchar(6) | Programa institucional |

### Estructura de SIG_CENTRO_COSTO (Unidades Orgánicas)

| Campo | Tipo | Descripción |
|---|---|---|
| `ANO_EJE` | numeric | **PK** — año de ejecución |
| `SEC_EJEC` | numeric | **PK** — unidad ejecutora |
| `CENTRO_COSTO` | varchar(15) | **PK** — código del centro de costo |
| `NOMBRE_DEPEND` | varchar(100) | Nombre de la unidad orgánica |
| `ABREVIADO_DEPEND` | varchar(50) | Nombre abreviado |
| `CENTRO_PADRE` | varchar(15) | **FK autorreferencial** — unidad padre en la jerarquía |
| `SEDE` | numeric | FK a `SIG_SEDES` |
| `TIPO_DEPEND` | char(1) | Tipo de dependencia |
| `ESTADO` | char(1) | `A` = Activo |
| `NRO_PERSONAL` | numeric | Cantidad de personal |
| `FLAG_CN` | varchar(1) | Participa en cuadro de necesidades |
| `FLAG_PRESUPUESTO` | varchar(1) | Tiene presupuesto asignado |
| `flag_ppr` | varchar(1) | Participa en PPR |
| `FLAG_AREA_ESTRATEGICA` | varchar(1) | Es área estratégica |

> **Jerarquía de unidades:** `CENTRO_PADRE` se autorreferencia al mismo `CENTRO_COSTO`. Esto permite modelar árbol organizacional: Gerencia → Sub-gerencia → Área → Unidad.

### Puente META ↔ Unidad Orgánica: SIG_METAS_X_CENTRO

| Campo | Tipo | Descripción |
|---|---|---|
| `ano_eje` | numeric | **PK** — año |
| `sec_ejec` | numeric | **PK** — ejecutora |
| `centro_costo` | varchar(15) | **PK · FK** → `SIG_CENTRO_COSTO` |
| `secuencia` | numeric | **PK** — secuencia del vínculo |
| `sec_func` | numeric | **FK lógica** → `META.sec_func` |
| `fuente_financ` | varchar(2) | Fuente de financiamiento asignada al centro para esa meta |
| `tipo_recurso` | varchar(2) | Tipo de recurso |
| `porc_techo` | numeric | % del techo presupuestal |

### Relación detallada del cuadro de necesidades

```
META (741)
  └─→ SIG_DETALLE_METAS_CUADRO  (tabla intermedia — descubierta vía FKs)
        └─→ SIG_DEPEN_META_CUADRO (27,021)
              ├─ SEC_META     → sec_func de la meta
              ├─ CENTRO_COSTO → unidad orgánica solicitante
              ├─ CANT_DEPEND  → cantidad requerida por la dependencia
              ├─ VALOR_DEPEND → valor monetario
              └─ PORC_GASTO   → % del gasto que corresponde a esa dependencia
```

---

## 6. Integridad de datos

| Relación | Total | Íntegros | Huérfanos | Estado |
|---|---|---|---|---|
| `SIG_METAS_X_CENTRO` → `META` (via sec_func) | 771 | 771 | 0 | ✅ Perfecto |
| `SIG_METAS_X_CENTRO` → `SIG_CENTRO_COSTO` | 771 | 771 | 0 | ✅ Perfecto |
| `SIG_DEPEN_META_CUADRO` → `META` (via sec_meta) | 27,021 | 27,021 | 0 | ✅ Perfecto |
| `SIG_CENTRO_COSTO` → `CENTRO_PADRE` (jerarquía) | 333 | 329 | **4** | ⚠️ 4 huérfanos leves |

Los 4 huérfanos en la jerarquía de centros corresponden a centros que tienen `CENTRO_PADRE` configurado apuntando a un padre inexistente. Impacto menor — no afectan la operación del sistema.

---

## 7. Relaciones formales (FK declaradas en el motor)

SIGA **sí tiene FKs formales** declaradas en el motor SQL Server, todas con política `NO_ACTION` en borrado y actualización. Las principales:

| Restricción | Tabla origen | Tabla destino | Descripción |
|---|---|---|---|
| `FK_EJECUTORA_META` | `META` | `EJECUTORA` | Toda meta pertenece a una ejecutora |
| `FK_TAREA_META` | `META` | `SIG_TAREA` | Vínculo meta-tarea |
| `FK_CTRO_COSTO_X_METAS_CTRO` | `SIG_METAS_X_CENTRO` | `SIG_CENTRO_COSTO` | Meta asignada a centro de costo |
| `FK_FTE_FTO_X_METAS_CTRO` | `SIG_METAS_X_CENTRO` | `FUENTE_FINANC_EJEC` | Fuente de financiamiento por meta-centro |
| `FK_META_SIG_CUADRO_NECE` | `SIG_CUADRO_NECESIDAD` | `META` | Cuadro de necesidades referencia meta |
| `FK_SIG_CENTRO_COSTO_CUAD_NECE` | `SIG_CUADRO_NECESIDAD` | `SIG_CENTRO_COSTO` | Cuadro de necesidades referencia centro |
| `FK_META_X_TECHO_PRESUPUESTO` | `SIG_TECHO_PRESUPUESTAL` | `META` | Techo presupuestal por meta |
| `FK_CTRO_COSTO_X_TECHO_PRESUP` | `SIG_TECHO_PRESUPUESTAL` | `SIG_CENTRO_COSTO` | Techo presupuestal por centro |
| `FK_META_X_SIG_PAAC_METAS` | `SIG_PAAC_METAS` | `META` | PAAC referencia metas |
| `FK_SIG_CENTRO_COSTO_SIG_PAT` | `SIG_PATRIMONIO` | `SIG_CENTRO_COSTO` | Bienes patrimoniales por centro |
| `FK_CTRO_COSTO_X_PEDIDOS` | `SIG_PEDIDOS` | `SIG_CENTRO_COSTO` | Pedidos por unidad orgánica |
| `FK_SIG_CC_TAREA_DEPE_MET_CUAD` | `SIG_DEPEN_META_CUADRO` | `SIG_CENTRO_COSTO_TAREA` | Cuadro detalle referencia tarea por centro |

> **Nota importante:** La relación `SIG_METAS_X_CENTRO.sec_func → META.sec_func` **no tiene FK formal** declarada en el motor — es una relación lógica aplicada por código. Sin embargo, la validación con datos reales confirma integridad perfecta (0 huérfanos).

---

## 8. Tablas en estado vacío (módulos no usados)

Las siguientes tablas están presentes en el esquema pero sin datos, lo que indica módulos no implementados o no activos en esta entidad:

| Tabla | Módulo | Observación |
|---|---|---|
| `SIG_INT_HT_META` / `SIG_INT_CONSOLIDADO_SIAF` | Integración SIAF | Integración no activa |
| `METASIAF` | Integración SIAF | Sin sincronización con SIAF |
| `SIG_EQUIVALENCIA_CCOSTO_META` | Equivalencias | No configurado |
| `SIG_SEDE_DEPENDIENCIA` | Sedes | Sedes registradas pero sin jerarquía sede-dependencia |
| `SIG_META_X_SEDE` / `SIG_META_X_TAREA` | Metas | Sin uso |
| `SIG_PPR_META_MENSUAL` | PPR | Sin programación mensual PPR |
| `SIG_SUB_FINALIDAD` | Cadena funcional | No utilizado |
| `SIG_FUNCION` | Cadena funcional | No usado (se usa tabla `FUNCION`) |

---

## 9. Hallazgos sobre la entidad: Municipalidad de San Jerónimo

### Organización
- **333 centros de costo** registrados en el sistema
- **64 unidades orgánicas** con metas asignadas en 2025
- **13 sedes** físicas registradas (sin jerarquía sede-dependencia configurada)
- Estructura jerárquica: Municipalidad → Alcaldía / Gerencias → Sub-gerencias → Oficinas → Unidades / Áreas

### Metas 2025
- **741 metas** totales registradas en el sistema
- **771 asignaciones** meta-centro (algunas metas compartidas entre unidades)
- **174 combinaciones únicas** meta-unidad orgánica identificadas
- Promedio: ~2.7 metas por unidad orgánica activa

### Tipología de metas 2025

| Tipo | Descripción | Identificación |
|---|---|---|
| **Actividad** | Actividad genérica de funcionamiento | `act_proy = 3999999` |
| **Proyecto de Inversión** | Proyecto con código Invierte.pe | `act_proy` empieza con `2` (ej: `2456126`) |
| **Actividad PP** | Actividad de Programa Presupuestal | `act_proy` empieza con `3` ≠ `3999999` (ej: `3000848`) |

### Unidades con mayor carga de metas (2025)
Las unidades orgánicas con más metas asignadas son principalmente las de **ejecución de obras** (Subgerencia de Ejecución de Inversiones, Ofic. General de Supervisión y Liquidación) y las de **medio ambiente** (Subgerencia de Gestion de Residuos Sólidos, Subgerencia de Mantenimiento).

---

## 10. Observaciones técnicas

1. **Sin módulo de integración SIAF activo** — todas las tablas `SIG_INT_*` están vacías. La entidad puede estar transmitiendo al SIAF por otro mecanismo o esta es una copia de trabajo.

2. **Tablas duplicadas de techo presupuestal** — existen dos tablas (`SIG_TECHO_PRESUPUESTAL` y `SIG_TECHO_PRESUPUESTO`) que ambas referencian `META` y `SIG_CENTRO_COSTO`. Probablemente una corresponde al PIA y la otra al PIM (presupuesto modificado).

3. **Duplicados en el resultado de metas** — la query de metas genera filas duplicadas porque `SIG_METAS_X_CENTRO` puede tener la misma combinación meta-centro con distintas `fuente_financ` o `tipo_recurso`. Para análisis se debe aplicar `DISTINCT` o agrupar por `(sec_func, centro_costo)`.

4. **Datos de monto en cero** — el campo `monto` en `META` aparece en `0.00` para todos los registros analizados. Los montos reales probablemente residen en `SIG_TECHO_PRESUPUESTAL` o `SIG_TECHO_PRESUPUESTO`.

5. **Módulo PPR parcialmente configurado** — `SIG_PPR_ESTABLECIMIENTO`, `SIG_PPR_DISA`, `SIG_PPR_UGEL` tienen estructura pero sin datos de programación mensual (`SIG_PPR_META_MENSUAL` = 0 filas).

---

## 11. Queries de referencia

### Obtener metas 2025 por unidad orgánica (deduplicado)
```sql
SELECT DISTINCT
    m.sec_func,
    m.nombre            AS nombre_meta,
    m.act_proy,
    cc.CENTRO_COSTO,
    cc.NOMBRE_DEPEND    AS unidad_organica,
    cp.NOMBRE_DEPEND    AS unidad_padre
FROM META m
INNER JOIN SIG_METAS_X_CENTRO mxc
    ON m.ano_eje = mxc.ano_eje AND m.sec_ejec = mxc.sec_ejec AND m.sec_func = mxc.sec_func
INNER JOIN SIG_CENTRO_COSTO cc
    ON mxc.ano_eje = cc.ANO_EJE AND mxc.sec_ejec = cc.SEC_EJEC AND mxc.centro_costo = cc.CENTRO_COSTO
LEFT JOIN SIG_CENTRO_COSTO cp
    ON cc.ANO_EJE = cp.ANO_EJE AND cc.SEC_EJEC = cp.SEC_EJEC AND cc.CENTRO_PADRE = cp.CENTRO_COSTO
WHERE m.ano_eje = 2025
ORDER BY m.sec_func;
```

### Contar metas por unidad orgánica
```sql
SELECT
    cc.CENTRO_COSTO,
    cc.NOMBRE_DEPEND           AS unidad_organica,
    cp.NOMBRE_DEPEND           AS unidad_padre,
    COUNT(DISTINCT m.sec_func) AS total_metas
FROM SIG_CENTRO_COSTO cc
INNER JOIN SIG_METAS_X_CENTRO mxc
    ON cc.ANO_EJE = mxc.ano_eje AND cc.SEC_EJEC = mxc.sec_ejec AND cc.CENTRO_COSTO = mxc.centro_costo
INNER JOIN META m
    ON mxc.ano_eje = m.ano_eje AND mxc.sec_ejec = m.sec_ejec AND mxc.sec_func = m.sec_func
LEFT JOIN SIG_CENTRO_COSTO cp
    ON cc.ANO_EJE = cp.ANO_EJE AND cc.SEC_EJEC = cp.SEC_EJEC AND cc.CENTRO_PADRE = cp.CENTRO_COSTO
WHERE m.ano_eje = 2025
GROUP BY cc.CENTRO_COSTO, cc.NOMBRE_DEPEND, cp.NOMBRE_DEPEND
ORDER BY total_metas DESC;
```

### Validar integridad de relaciones
```sql
SELECT
    'MXC → META'      AS relacion, COUNT(*) AS total,
    SUM(CASE WHEN m.sec_func IS NOT NULL THEN 1 ELSE 0 END) AS integros,
    SUM(CASE WHEN m.sec_func IS NULL     THEN 1 ELSE 0 END) AS huerfanos
FROM SIG_METAS_X_CENTRO mxc
LEFT JOIN META m
    ON mxc.ano_eje = m.ano_eje AND mxc.sec_ejec = m.sec_ejec AND mxc.sec_func = m.sec_func;
```

---

## 12. Módulo de Ejecución — Cadena Logística SIGA (Exploración Julio 2026)

### 12.1 Tablas del flujo de ejecución del gasto

| Tabla | Filas | Años | Rol en el flujo |
|---|---|---|---|
| `SIG_ORDEN_ADQUISICION` | 8,298 | 2023-2026 | Cabecera de órdenes de compra (B) y servicio (S) |
| `SIG_ORDEN_PRESUPUESTO` | 8,927 | 2023-2026 | Afectación presupuestal de cada orden — contiene `SEC_FUNC` y `EXP_SIAF` |
| `SIG_ORDEN_ITEM_PPTO` | 25,429 | 2023-2026 | Detalle de ítems presupuestales por orden — también tiene `SEC_FUNC` |
| `SIG_EXP_SIGA` | 8,124 | 2023-2026 | Expedientes SIGA — cabecera de la fase de gasto (`TIPO_FASE`) |
| `SIG_DEVENGADO` | 7 | 2023-2024 | Registro de devengados (casi vacío — no es la fuente principal) |
| `SIG_DEVENGADO_ITEM_PPTO` | 2 | 2024 | Detalle presupuestal del devengado (casi vacío) |

### 12.2 Campos clave identificados

#### SIG_ORDEN_ADQUISICION (cabecera de orden)

| Campo | Descripción |
|---|---|
| `ANO_EJE` / `SEC_EJEC` / `NRO_ORDEN` / `TIPO_BIEN` | PK compuesta |
| `TIPO_BIEN` | `B` = Bien (orden de compra), `S` = Servicio (orden de servicio) |
| `EXP_SIAF` | **Número de expediente SIAF** — llave de cruce con la API MEF |
| `EXP_SIGA` | Número de expediente interno SIGA |
| `ESTADO_SIAF` | `2` = enviado/aceptado SIAF, `0` = pendiente, `3` = rechazado |
| `ESTADO` | Estado de la orden: `1` = vigente |
| `TOTAL_FACT_SOLES` | Monto total de la orden en soles |
| `CONCEPTO` | Descripción del bien o servicio |
| `FECHA_ORDEN` | Fecha de emisión |
| `NRO_CONTRATO` / `ANO_CONTRATO` / `SEC_CONTRATO` | Referencia al contrato |
| `DES_MODALIDAD` (via TIPO_PROCESO) | Modalidad de adquisición |
| `PROVEEDOR` | Código del proveedor |

#### SIG_ORDEN_PRESUPUESTO (afectación presupuestal)

| Campo | Descripción |
|---|---|
| `ANO_EJE` / `SEC_EJEC` / `NRO_ORDEN` / `TIPO_BIEN` | FK → `SIG_ORDEN_ADQUISICION` |
| `SEC_FUNC` | **FK → `META.sec_func`** — llave de cruce con META y con API SIAF |
| `CLASIFICADOR` | Clasificador de gasto (genérica.sub-genérica.específica) |
| `FUENTE_FINANC` | Fuente de financiamiento (`00`=RO, `09`=RDR, `18`=Canon, etc.) |
| `EXP_SIAF` | Número de expediente SIAF (redundante con cabecera, útil para JOIN directo) |
| `VALOR_SOLES` | Monto de la afectación presupuestal |
| `FASE` | Fase presupuestal de la afectación |

#### SIG_EXP_SIGA (expedientes SIGA)

| Campo | Descripción |
|---|---|
| `EXP_SIGA` / `ANO_EJE` / `SEC_EJEC` | PK del expediente |
| `TIPO_FASE` | Tipo de fase: `D` = Devengado (todos los registros 2025) |
| `TIPO_BIEN` | `B` = Bien, `S` = Servicio |
| `EXP_SIAF` | Número de expediente SIAF correspondiente |
| `ESTADO_SIAF` | Estado de sincronización con SIAF |
| `PROVEEDOR` | Proveedor del expediente |

### 12.3 Llave de cruce SIAF ↔ SIGA — Validación completa

La cadena de cruce validada es:

```
API SIAF (EXP_SIAF / SEC_FUNC)
    ↓
SIG_ORDEN_PRESUPUESTO (EXP_SIAF, SEC_FUNC)
    ↓
SIG_ORDEN_ADQUISICION (NRO_ORDEN, TIPO_BIEN, EXP_SIAF)
    ↓
META (sec_func → act_proy, nombre, funcion)
```

**Resultados de validación (año 2025):**

| Validación | Resultado |
|---|---|
| Órdenes 2025 con `EXP_SIAF` registrado | **3,152 / 3,160** (99.7%) |
| Órdenes 2025 con cruce completo `EXP_SIAF + SEC_FUNC` | **3,350** registros |
| `SEC_FUNC` distintos en órdenes 2025 | **160** |
| `SEC_FUNC` de órdenes con match en `META` | **160 / 160** ✅ (100%) |

> La cobertura es perfecta: todas las órdenes de 2025 se pueden cruzar con su meta presupuestal en META y, a través de `EXP_SIAF`, con el registro de ejecución en la API SIAF.

### 12.4 Volumen de órdenes 2025 por tipo

| TIPO_BIEN | Descripción | Cantidad órdenes | Monto total (S/) |
|---|---|---|---|
| `S` | Servicios | 1,607 | 9,282,977.56 |
| `B` | Bienes (compras) | 1,553 | 13,957,434.96 |
| **Total** | | **3,160** | **23,240,412.52** |

### 12.5 Top proyectos por ejecución en SIGA 2025 (ESTADO_SIAF = 2)

| Código Invierte.pe | Nombre | Órdenes | Monto S/ |
|---|---|---|---|
| 2575084 | Mejoramiento Servicios Bibliotecarios | 278 | 1,453,934 |
| 2675139 | Mejoramiento Producción Piedras y Lajas | 16 | 1,087,864 |
| 2645558 | Construcción Sistema Pretratamiento Camal | 64 | 1,087,144 |
| 2626536 | Adecuación Centro Control y Monitoreo | 144 | 1,079,265 |
| 2601799 | Recuperación Servicios Culturales | 211 | 1,065,560 |
| 2593643 | Mejoramiento Servicios Apoyo Agropecuario | 159 | 982,099 |
| 2624245 | Movilidad Urbana APV Huayna Ccapac | 47 | 894,691 |
| 2675138 | Implementación Tecnologías Panadería | 21 | 857,395 |
| 2675137 | Servicios Gastronómicos Asoc. Mixtura | 9 | 788,200 |
| 2658123 | Remodelación Calle Rodaje Prol. Hospital | 58 | 593,767 |

### 12.6 Queries de referencia — módulo de ejecución

```sql
-- Ejecución completa por proyecto: SIGA → META → SIAF
SELECT
    m.act_proy                     AS codigo_inviertpe,
    m.nombre                       AS nombre_proyecto,
    m.funcion,
    COUNT(DISTINCT o.NRO_ORDEN)    AS nro_ordenes,
    SUM(o.TOTAL_FACT_SOLES)        AS monto_soles,
    p.FUENTE_FINANC                AS fuente
FROM SIG_ORDEN_ADQUISICION o
INNER JOIN SIG_ORDEN_PRESUPUESTO p
    ON o.ANO_EJE=p.ANO_EJE AND o.SEC_EJEC=p.SEC_EJEC
    AND o.NRO_ORDEN=p.NRO_ORDEN AND o.TIPO_BIEN=p.TIPO_BIEN
INNER JOIN META m
    ON p.SEC_FUNC=m.sec_func AND p.ANO_EJE=m.ano_eje
WHERE o.ANO_EJE=2025 AND o.ESTADO_SIAF='2'
GROUP BY m.act_proy, m.nombre, m.funcion, p.FUENTE_FINANC
ORDER BY monto_soles DESC;

-- Cruzar orden SIGA con expediente SIAF (para validación)
SELECT
    o.NRO_ORDEN, o.TIPO_BIEN, o.EXP_SIAF,
    o.TOTAL_FACT_SOLES, o.CONCEPTO,
    p.SEC_FUNC, p.CLASIFICADOR, p.FUENTE_FINANC,
    m.act_proy, m.nombre AS nombre_meta
FROM SIG_ORDEN_ADQUISICION o
INNER JOIN SIG_ORDEN_PRESUPUESTO p
    ON o.ANO_EJE=p.ANO_EJE AND o.SEC_EJEC=p.SEC_EJEC
    AND o.NRO_ORDEN=p.NRO_ORDEN AND o.TIPO_BIEN=p.TIPO_BIEN
INNER JOIN META m ON p.SEC_FUNC=m.sec_func AND p.ANO_EJE=m.ano_eje
WHERE o.ANO_EJE=2025 AND o.EXP_SIAF=<numero_exp_siaf>;
```

---

## 13. Módulos para Funcionarios — Tablas y Datos Identificados (Julio 2026)

Esta sección documenta los datos SIGA necesarios para los módulos del panel interno, según el plan del sistema (secciones 6.2.1 a 6.2.7).

### 13.1 Pipeline de Pedidos y Órdenes (Módulo 6.2.2)

#### Flujo del ciclo logístico en SIGA

```
REQUERIMIENTO → PEDIDO → ORDEN DE COMPRA/SERVICIO → CONFORMIDAD → DEVENGADO
     ↑               ↑              ↑                      ↑
SIG_PEDIDOS  SIG_DETALLE_PEDIDOS  SIG_ORDEN_ADQUISICION  SIG_MOVIM_CONFOR_SERVICIO
```

#### SIG_PEDIDOS — cabecera de pedido

| Campo | Descripción |
|---|---|
| `ANO_EJE` / `SEC_EJEC` / `NRO_PEDIDO` / `TIPO_BIEN` | PK del pedido |
| `TIPO_BIEN` | `B` = Bien, `S` = Servicio |
| `TIPO_PEDIDO` | `1` = Pedido de almacén, `2` = Pedido de compra/servicio directo |
| `CENTRO_COSTO` | Unidad orgánica solicitante |
| `sec_func` | Meta presupuestal del pedido |
| `ACT_PROY` | Código del proyecto/actividad |
| `ESTADO` | `0`=borrador, `1`=aprobado/vigente, `7`=atendido/cerrado |
| `FECHA_PEDIDO` | Fecha de emisión |
| `FECHA_APROB` | Fecha de aprobación |
| `FECHA_ATENC` | Fecha de atención |
| `MOTIVO_PEDIDO` | Descripción/justificación |
| `NOMBRE_EMPLEADO` | Solicitante |
| `FUENTE_FINANC` | Fuente de financiamiento |
- **Volumen:** 13,083 registros | Años 2023-2026

#### SIG_DETALLE_PEDIDOS — ítems del pedido

| Campo | Descripción |
|---|---|
| `NRO_PEDIDO` / `SECUENCIA` | PK del ítem |
| `ITEM_BIEN` | Código del bien/servicio del catálogo |
| `CANT_SOLICITADA` / `CANT_APROBADA` / `CANT_ATENDIDA` | Cantidades por etapa |
| `VALOR_TOTAL` | Monto total del ítem |
| `CLASIFICADOR` | Clasificador de gasto |
| `NRO_ORDEN` | **FK → `SIG_ORDEN_ADQUISICION`** — vínculo pedido → orden |
| `ESTADO_PED` | Estado del ítem en el pedido |
| `ESTADO_ATEND` | Estado de atención (`0`=pendiente, `1`=atendido) |
| `ESTADO_CONFOR` | Estado de conformidad (`0`=pendiente, `1`=con conformidad) |
| `ESTADO_COMPRA` | Estado del proceso de compra |
| `FECHA_CONFOR` | Fecha en que se registró la conformidad |
- **Volumen:** 47,018 registros | Años 2023-2026
- **Estados 2025:** `PED=1,ATEND=0,CONFOR=0` (en proceso): 9,861 ítems | `PED=8,ATEND=1,CONFOR=1` (completados): 7,768 ítems

#### Etapas del pipeline y cómo detectarlas

| Etapa | Condición en SIGA |
|---|---|
| Solicitado | `SIG_PEDIDOS.ESTADO = '1'` y `SIG_DETALLE_PEDIDOS.ESTADO_PED = '1'` y sin NRO_ORDEN |
| Con orden emitida | `SIG_DETALLE_PEDIDOS.NRO_ORDEN > 0` y `SIG_ORDEN_ADQUISICION.ESTADO = '1'` |
| En conformidad | `SIG_DETALLE_PEDIDOS.ESTADO_CONFOR = '1'` o `SIG_MOVIM_CONFOR_SERVICIO` tiene registro |
| Devengado/pagado | `SIG_ORDEN_ADQUISICION.ESTADO_SIAF = '2'` (aceptado en SIAF) |
| Cerrado | `SIG_PEDIDOS.ESTADO = '7'` |

#### SIG_MOVIM_CONFOR_SERVICIO — conformidades de servicio

| Campo | Descripción |
|---|---|
| `NRO_ORDEN` / `ANO_ORDEN` / `TIPO_BIEN` | FK → `SIG_ORDEN_ADQUISICION` |
| `FECHA_MOVIMTO` | Fecha de la conformidad |
| `INDI_CONFOR` | Indicador de conformidad |
| `NOMBRE_PROVEEDOR` | Nombre del proveedor |
| `ESTADO_DEVENG` | Estado de devengado |
| `EXPEDIENTE_SIAF` | Número de expediente SIAF asociado |
| `RESPONSABLE` | Responsable de la conformidad |
| `OBSERVACION` | Observaciones del conformador |
- **Volumen:** 4,943 registros | Años 2023-2026

#### SIG_SEGUIMIENTO — log de estados del pipeline

| Campo | Descripción |
|---|---|
| `NRO_PEDIDO` / `NRO_TRANSACCION` | Vinculación con pedido |
| `TIPO_TRANSACCION` | Tipo de movimiento en el flujo |
| `CENTRO_COSTO` / `SOLICITANTE` | Quién generó el movimiento |
| `FECHA_TRANSACCION` / `ESTADO_TRANSACCION` | Cuándo y en qué estado |
- **Volumen:** 39,212 registros (log completo del flujo)

---

### 13.2 Saldos Presupuestales (Módulo 6.2.3)

#### SIG_TECHO_PRESUPUESTO — tabla principal de saldos

La tabla más completa para calcular saldos disponibles. Contiene tanto el presupuesto como la ejecución acumulada por clasificador, meta y centro de costo.

| Campo | Descripción |
|---|---|
| `ANO_EJE` / `SEC_EJEC` / `sec_func` / `CLASIFICADOR` / `CENTRO_COSTO` | PK compuesta |
| `FUENTE_FINANC` | Fuente de financiamiento |
| `PPTO_PIA` | Presupuesto Institucional de Apertura |
| `PPTO_MODIF` | **PIM** — Presupuesto Institucional Modificado |
| `mnto_acum_cert` | Monto certificado acumulado |
| `mnto_acum_coma` | Monto comprometido anual acumulado |
| `mnto_acum_comm` | Monto comprometido mensual acumulado |
| `MNTO_ACUM_DEVGDO_SIGA` | Devengado acumulado (fuente SIGA) |
| `MNTO_ACUM_DEVGDO_SIAF` | Devengado acumulado (fuente SIAF) |
| `PPTO_DISP_SIAF` | **Saldo disponible** según SIAF |
| `MNTO_RESERVA_PEDIDO` | Monto reservado por pedidos pendientes |
| `EJEC_01` … `EJEC_12` | Ejecución por mes (enero a diciembre) |
| `PRE_EJEC_01` … `PRE_EJEC_12` | Ejecución prevista por mes |
- **Volumen:** 10,049 registros | Años 2023-2026

> **Fórmula de saldo disponible:** `PPTO_MODIF - mnto_acum_cert` (o usar directamente `PPTO_DISP_SIAF`)

#### SIG_CERTIFICACION_PPTO — detalle de certificaciones

| Campo | Descripción |
|---|---|
| `NRO_CERTIFICA` | Número de certificación presupuestal |
| `SEC_FUNC` / `CLASIFICADOR` | Meta y clasificador afectados |
| `VALOR_SOLES` | Monto certificado |
| `FECHA_REG` | Fecha de la certificación |
- **Volumen:** 18,461 registros | Años 2023-2026

#### SIG_CERTIFICACION_FASE — relación certificación ↔ orden

| Campo | Descripción |
|---|---|
| `NRO_CERTIFICA` | FK → certificación |
| `NRO_ORDEN` / `TIPO_BIEN` | FK → `SIG_ORDEN_ADQUISICION` |
| `NRO_CERTIFICA_SIAF` | Número de certificación en SIAF |
| `VALOR_SOLES` | Monto de la fase |
| `FLAG_COMPROMETIDO` | Indica si ya está comprometido |
- **Volumen:** 16,387 registros | Años 2023-2026

---

### 13.3 Proveedores (Módulos 6.1.3 y 6.2.7)

#### SIG_CONTRATISTAS — registro de proveedores

| Campo | Descripción |
|---|---|
| `PROVEEDOR` | **PK** — código interno del proveedor (FK en todas las órdenes y contratos) |
| `NRO_RUC` | RUC del proveedor |
| `NOMBRE_PROV` | Razón social o nombre |
| `TIPO_PERSONA` | `01`=Natural, `02`=Jurídica |
| `GIRO_GENERAL` | Giro del negocio |
| `DIRECCION` | Dirección fiscal |
| `EMAIL` / `TELEFONOS` | Contacto |
| `DEPARTAMENTO` / `PROVINCIA` / `DISTRITO` | Ubicación (códigos) |
| `FLAG_MYPE` | Es MYPE: `S`/`N` |
| `FLAG_RNP` / `NRO_RNP` | Inscripción en RNP |
| `FLAG_CONSORCIO` | Es consorcio |
| `FECHA_ISANCION` / `FECHA_FSANCION` | Sanción vigente (si aplica) |
| `FLAG_SNP` | Es SNP (locador de servicios) |
- **Volumen:** 2,645 proveedores registrados

> **Nota:** La tabla `PERSONA` (con RUC también) está vacía. `SIG_CONTRATISTAS` es la fuente real de proveedores.

---

### 13.4 Contratos (Módulos 6.1.1 y 6.2.4)

#### SIG_CONTRATOS — cabecera de contratos

| Campo | Descripción |
|---|---|
| `ANO_EJE` / `SEC_EJEC` / `TIPO_CONTRATO` / `NRO_CONTRATO` / `SEC_CONTRATO` | PK |
| `TIPO_BIEN` | `B`=Bien, `S`=Servicio |
| `PROVEEDOR` | FK → `SIG_CONTRATISTAS` |
| `FECHA_INICIAL` / `FECHA_FINAL` | Plazo contractual |
| `FECHA_CESE` | Fecha de cese/término |
| `VALOR_SOLES` | Monto del contrato en soles |
| `OBJETO` | Objeto del contrato |
| `GLOSA` | Descripción detallada |
| `TIPO_COMPRA` / `MODAL_COMPRA` | Modalidad (AS, LP, CE, etc.) |
| `ID_PROCESO` | Código del proceso de selección |
| `ID_CONTRATO` | Identificador en OSCE/SEACE |
| `NRO_DOCUMENTO` | Número del documento contractual |
| `ESTADO` | Estado del contrato |
| `FLAG_SNP` | Es contrato SNP |
| `NRO_MESES` / `MONTO_SUELDO_SOLES` | Para contratos de personal |
- **Volumen:** 127 contratos | Años 2023-2026

---

### 13.5 Resumen de tablas para el panel de funcionarios

| Módulo del sistema | Tablas SIGA principales | Dato clave |
|---|---|---|
| **Pipeline pedidos** | `SIG_PEDIDOS`, `SIG_DETALLE_PEDIDOS`, `SIG_SEGUIMIENTO` | `ESTADO` + fechas por etapa |
| **Estado de órdenes** | `SIG_ORDEN_ADQUISICION`, `SIG_ORDEN_PRESUPUESTO` | `ESTADO_SIAF`, `EXP_SIAF` |
| **Conformidades** | `SIG_MOVIM_CONFOR_SERVICIO` | `FECHA_MOVIMTO`, `ESTADO_DEVENG` |
| **Saldos presupuestales** | `SIG_TECHO_PRESUPUESTO` | `PPTO_MODIF`, `PPTO_DISP_SIAF` |
| **Certificaciones** | `SIG_CERTIFICACION_PPTO`, `SIG_CERTIFICACION_FASE` | `NRO_CERTIFICA`, `VALOR_SOLES` |
| **Directorio proveedores** | `SIG_CONTRATISTAS` | `NRO_RUC`, `NOMBRE_PROV` |
| **Contratos** | `SIG_CONTRATOS` | `FECHA_FINAL`, `VALOR_SOLES`, `ID_CONTRATO` |
| **Cruce SIAF↔SIGA** | `SIG_ORDEN_PRESUPUESTO` → `META` | `SEC_FUNC`, `EXP_SIAF` |

### 13.6 Query de saldo disponible por meta y clasificador (2025)

```sql
SELECT
    t.sec_func,
    m.nombre                    AS nombre_meta,
    m.act_proy,
    t.CLASIFICADOR,
    t.FUENTE_FINANC,
    t.CENTRO_COSTO,
    t.PPTO_PIA                  AS pia,
    t.PPTO_MODIF                AS pim,
    t.mnto_acum_cert            AS certificado,
    t.mnto_acum_coma            AS comprometido_anual,
    t.MNTO_ACUM_DEVGDO_SIGA    AS devengado,
    t.PPTO_DISP_SIAF            AS saldo_disponible
FROM SIG_TECHO_PRESUPUESTO t
INNER JOIN META m ON t.sec_func=m.sec_func AND t.ANO_EJE=m.ano_eje
WHERE t.ANO_EJE=2025 AND t.PPTO_MODIF > 0
ORDER BY t.PPTO_MODIF DESC;
```

### 13.7 Query del pipeline de pedidos con su estado actual (2025)

```sql
SELECT
    p.NRO_PEDIDO,
    p.TIPO_BIEN,
    cc.NOMBRE_DEPEND            AS unidad_solicitante,
    p.NOMBRE_EMPLEADO           AS solicitante,
    p.FECHA_PEDIDO,
    p.ESTADO                    AS estado_pedido,
    dp.SECUENCIA                AS item,
    dp.VALOR_TOTAL,
    dp.NRO_ORDEN,
    dp.ESTADO_PED,
    dp.ESTADO_ATEND,
    dp.ESTADO_CONFOR,
    o.TOTAL_FACT_SOLES          AS monto_orden,
    o.EXP_SIAF,
    o.ESTADO_SIAF,
    c.NOMBRE_PROV               AS proveedor,
    c.NRO_RUC
FROM SIG_PEDIDOS p
INNER JOIN SIG_DETALLE_PEDIDOS dp
    ON p.ANO_EJE=dp.ANO_EJE AND p.SEC_EJEC=dp.sec_ejec
    AND p.TIPO_BIEN=dp.TIPO_BIEN AND p.NRO_PEDIDO=dp.NRO_PEDIDO
LEFT JOIN SIG_CENTRO_COSTO cc
    ON p.ANO_EJE=cc.ANO_EJE AND p.SEC_EJEC=cc.SEC_EJEC AND p.CENTRO_COSTO=cc.CENTRO_COSTO
LEFT JOIN SIG_ORDEN_ADQUISICION o
    ON dp.ANO_EJE=o.ANO_EJE AND dp.sec_ejec=o.SEC_EJEC
    AND dp.TIPO_BIEN=o.TIPO_BIEN AND dp.NRO_ORDEN=o.NRO_ORDEN
LEFT JOIN SIG_CONTRATISTAS c ON o.PROVEEDOR=c.PROVEEDOR
WHERE p.ANO_EJE=2025
ORDER BY p.FECHA_PEDIDO DESC;
```

---

---

## 14. Módulos adicionales explorados (Julio 2026)

### 14.1 Almacén

#### SIG_MOVIM_ALMACEN — movimientos de almacén

| Campo | Descripción |
|---|---|
| `ALMACEN` / `SEC_ALMACEN` | Código del almacén |
| `TIPO_MOVIMTO` | `I`=Ingreso, `S`=Salida, `R`=Recepción |
| `NRO_ORDEN` / `ANO_ORDEN` | FK → `SIG_ORDEN_ADQUISICION` |
| `PROVEEDOR` / `NOMBRE_PROVEEDOR` | Proveedor del ingreso |
| `CENTRO_COSTO` | Unidad orgánica destino |
| `FECHA_MOVIMTO` / `FECHA_ENTRADA` | Fechas del movimiento |
| `EXPEDIENTE_SIAF` | Número de expediente SIAF asociado |
| `ESTADO_DEVENG` | Estado del devengado |
| `NRO_FACTURA` / `FECHA_FACTURA` | Documento de respaldo |
- **Volumen:** 11,924 | Años 2023-2026 — 2025: 1,492 ingresos + 1,492 salidas + 1,492 recepciones

#### SIG_DETALLE_PECOSA — detalle de despacho por PECOSA

| Campo | Descripción |
|---|---|
| `NRO_PEDIDO` / `SECUENCIA` | FK → `SIG_PEDIDOS` |
| `NRO_PECOSA` | Número de PECOSA (comprobante de salida) |
| `CANT_ATENDIDA` / `PRECIO_UNIT` / `valor_total` | Cantidades y montos despachados |
| `NRO_MOVIMTO` | FK → `SIG_MOVIM_ALMACEN` |
- **Volumen:** 20,522 | Años 2023-2026

#### SIG_KARDEX_POR_ALMACEN — kardex de stock por almacén

| Campo | Descripción |
|---|---|
| `CODIGO_BIEN` / `ITEM_BIEN` | Código del bien en el catálogo |
| `MES_PROCESO` | Mes de corte del kardex |
| `STOCK_INICIAL` / `CANT_INGRESO` / `CANT_EGRESO` / `STOCK_ACTUAL` | Movimiento del período |
| `VALOR_INGRESO` / `VALOR_EGRESO` / `SALDO_VALOR` | Valorización |
| `PRECIO_PROMED` | Precio promedio |
| `ACTIVO_FIJO` | `S`=activo fijo, `N`=bien de consumo |
- **Volumen:** 16,633 | Años 2023-2026

#### SIG_KARDEX_INVENTARIO — inventario físico de stock

| Campo | Descripción |
|---|---|
| `CODIGO_BIEN` / `ITEM_BIEN` | Bien inventariado |
| `CANT_INVENT` / `CANT_BUENO` / `STOCK_ACTUAL` | Cantidades por estado |
| `precio_promed` | Precio promedio al momento del inventario |
- **Volumen:** 1,269 | Años 2024-2025

#### CATALOGO_BIEN_SERV — catálogo de bienes y servicios

| Campo | Descripción |
|---|---|
| `ITEM_BIEN` | **PK** — código del ítem |
| `TIPO_BIEN` | `B`=Bien, `S`=Servicio |
| `GRUPO_BIEN` / `CLASE_BIEN` / `FAMILIA_BIEN` | Clasificación jerárquica |
| `NOMBRE_ITEM` | Nombre descriptivo del bien o servicio |
| `UNIDAD_MEDIDA` | FK → tabla de unidades de medida |
| `PRECIO_REF` / `PRECIO_COMPRA` | Precios de referencia |
| `STOCK_MINIMO` / `STOCK_MAXIMO` | Parámetros de stock |
| `CODIGO_OSCE` | Código de catálogo OSCE |
- **Volumen:** 9,685 ítems (bienes + servicios)

---

### 14.2 Plan Anual de Adquisiciones y Contrataciones (PAAC)

#### SIG_PAAC_CONSOLIDADO — ítems del PAAC

Tabla principal del PAAC. Cada registro es un ítem de contratación planificado.

| Campo | Descripción |
|---|---|
| `TIPO_CONSOLID` / `NRO_CONSOLID` | PK del ítem |
| `TIPO_BIEN` | `B`=Bien, `S`=Servicio |
| `TIPO_PROCESO` | Código del proceso de selección |
| `TIPO_COMPRA` / `MODAL_COMPRA` | Tipo y modalidad |
| `OBJETO` | Código de objeto del gasto |
| `VALOR_PLAN` | Monto planificado en soles |
| `MES_PROPUESTO` | Mes propuesto de convocatoria |
| `ESTADO` | `1`=incluido, `5`=modificado, `6`=concluido/ejecutado, `7`=excluido |
| `EXP_SIAF` / `EXP_SIGA` | Expedientes cuando ya se ejecutó |
| `PROVEEDOR` | FK → `SIG_CONTRATISTAS` si ya tiene adjudicado |
| `NRO_CERTIFICA` | Número de certificación presupuestal |
| `FLAG_CONCLUIDO` | `S`=proceso terminado |
- **Volumen:** 9,958 registros
- **2025:** 3,188 concluidos (S/26.4M) + 769 incluidos (S/11.9M) + 64 excluidos
- **2026:** 1,672 concluidos (S/18.3M) + 216 incluidos (S/24.4M)

> **Uso para el sistema:** El PAAC permite mostrar qué contrataciones están programadas para el año y cuál es su estado de avance (planificado → en proceso → ejecutado).

---

### 14.3 Patrimonio

#### SIG_PATRIMONIO — registro de bienes patrimoniales

| Campo | Descripción |
|---|---|
| `CODIGO_ACTIVO` | **PK** — código único del bien patrimonial |
| `TIPO_ACTIVO` | Tipo de activo (`1`=Mueble, etc.) |
| `DESCRIPCION` (campo real: ver `NOMBRE_ITEM` en catálogo) | Descripción del bien |
| `CENTRO_COSTO` | Unidad orgánica asignada |
| `EMPLEADO` | Usuario/responsable asignado |
| `VALOR_COMPRA` / `VALOR_INICIAL` / `VALOR_DEPREC` | Valores contables |
| `NRO_SERIE` / `MARCA` / `MODELO` | Identificación física |
| `ESTADO_ACTUAL` / `ESTADO_CONSERV` | Estado (`N`=Normal, etc.) |
| `FECHA_ALTA` / `FECHA_COMPRA` | Fechas de ingreso |
| `NRO_ORDEN` / `NRO_PECOSA` | Origen (orden de compra y PECOSA) |
| `ANO_PROCESO` / `MES_PROCESO` | Período de registro |
| `FEC_FIN_VIDA` / `VIDA_UTIL` / `TASA_DEPREC` | Vida útil y depreciación |
| `CODIGO_BARRA` | Código de barras para inventario |
| `NRO_CONTRATO` | FK → contrato si aplica |
- **Volumen:** 7,800 bienes patrimoniales (266 activos en 2025, valor S/443,539)

#### SIG_INM_UNIDAD_ACTIVO — inmuebles

| Campo relevante | Descripción |
|---|---|
| `CODIGO_ACTIVO` | Código del inmueble |
| Campos de área, ubicación, título | Ver estructura completa |
- **Volumen:** 33 inmuebles registrados

---

### 14.4 Modificaciones Presupuestales

#### SIG_DETALLE_MOVIM_PPTO — historial de modificaciones presupuestales

Registra cada movimiento de modificación (ampliaciones, reducciones, transferencias internas) que altera el presupuesto asignado por clasificador y meta.

| Campo | Descripción |
|---|---|
| `TIPO_MOVIMTO` | Tipo de modificación |
| `NRO_MOVIMTO` | Número del movimiento |
| `SEC_FUNC` | Meta afectada |
| `CLASIFICADOR` | Clasificador de gasto modificado |
| `FUENTE_FINANC` | Fuente de financiamiento |
| `CANT_ARTICULO` | Monto modificado |
- **Volumen:** 61,497 | Años 2023-2026 — es la fuente del historial de cambios al PIM

---

### 14.5 Expedientes SIGA (detalle)

#### SIG_EXP_SIGA_PPTO — detalle presupuestal del expediente SIGA

| Campo | Descripción |
|---|---|
| `EXP_SIGA` / `EXP_SIGA_DOC` / `EXP_SIGA_SECU` | PK del expediente |
| `SEC_FUNC` / `CLASIFICADOR` | Meta y clasificador afectados |
| `VALOR_SOLES` / `MNTO_SOLES` | Montos del expediente |
| `EXPEDIENTE` | Referencia interna |
- **Volumen:** 8,926 | Años 2023-2026

#### SIG_EXP_SIGA_DOCU — documentos del expediente SIGA

| Campo | Descripción |
|---|---|
| `EXP_SIGA` / `EXP_SIGA_DOC` | FK → expediente |
| `TIPO_DOCUMENTO` / `NRO_DOCUMENTO` / `FECHA_DOCUMENTO` | Comprobante de pago |
| `MODAL_COMPRA` | Modalidad de contratación |
| `EXP_SIAF` | Expediente SIAF correspondiente |
| `FASE_CONTRACTUAL` | Fase del proceso contractual |
- **Volumen:** 8,294 | Años 2023-2026

---

### 14.6 Tablas vacías confirmadas (módulos no activos)

| Tabla / Módulo | Estado |
|---|---|
| `SIG_TES_*` (Tesorería completa) | ❌ Vacía — módulo de tesorería no implementado |
| `SIG_PPR_*` (PPR completo) | ❌ Vacía — programación PPR no configurada |
| `SIG_PLANILLA_SNP` / `SIG_CONTRATO_MOVIM_PAGO` | ❌ Vacíos — planillas y pagos de contratos no usados en SIGA |
| `METASIAF` | ❌ Vacía — integración SIAF no activa |
| `SIG_ACUMULADO_DET` | ❌ Vacío |
| `SEG_AUDITORIA` / `SEG_USUARIO` | ❌ Vacíos — seguridad gestionada en otra capa |
| `SIG_DA_PRESUPUESTO` | ❌ Vacío |
| `SIG_GUIA_REMISION` | ❌ Vacío |
| `SIG_INVENTARIO_FISICO` | ⚠️ Solo 1 registro |

---

### 14.7 Resumen completo de tablas con datos relevantes para el proyecto

| Módulo del sistema | Tablas SIGA | Volumen aprox. |
|---|---|---|
| **Catálogo** | `CATALOGO_BIEN_SERV` | 9,685 ítems |
| **Presupuesto — apertura** | `SIG_TECHO_PRESUPUESTO`, `META` | 10,049 / 741 |
| **Presupuesto — modificaciones** | `SIG_DETALLE_MOVIM_PPTO` | 61,497 |
| **Presupuesto — certificaciones** | `SIG_CERTIFICACION_PPTO`, `SIG_CERTIFICACION_FASE` | 18,461 / 16,387 |
| **PAAC** | `SIG_PAAC_CONSOLIDADO`, `SIG_PAAC_ITEM` | 9,958 / 41,449 |
| **Pedidos** | `SIG_PEDIDOS`, `SIG_DETALLE_PEDIDOS` | 13,083 / 47,018 |
| **Seguimiento pipeline** | `SIG_SEGUIMIENTO` | 39,212 |
| **Órdenes** | `SIG_ORDEN_ADQUISICION`, `SIG_ORDEN_PRESUPUESTO`, `SIG_ORDEN_ITEM_PPTO` | 8,298 / 8,927 / 25,429 |
| **Conformidades** | `SIG_MOVIM_CONFOR_SERVICIO` | 4,943 |
| **Contratos** | `SIG_CONTRATOS`, `SIG_CONTRATO_MOVIMIENTO` | 127 / 8 |
| **Proveedores** | `SIG_CONTRATISTAS` | 2,645 |
| **Expedientes SIGA** | `SIG_EXP_SIGA`, `SIG_EXP_SIGA_PPTO`, `SIG_EXP_SIGA_DOCU` | 8,124 / 8,926 / 8,294 |
| **Almacén — movimientos** | `SIG_MOVIM_ALMACEN`, `SIG_DETALLE_PECOSA` | 11,924 / 20,522 |
| **Almacén — kardex** | `SIG_KARDEX_POR_ALMACEN`, `SIG_KARDEX_INVENTARIO` | 16,633 / 1,269 |
| **Patrimonio** | `SIG_PATRIMONIO`, `SIG_INM_UNIDAD_ACTIVO` | 7,800 / 33 |
| **Metas y estructura** | `META`, `SIG_METAS_X_CENTRO`, `SIG_CENTRO_COSTO` | 741 / 771 / 333 |

---

*Documento generado mediante análisis exploratorio progresivo de la base de datos — Julio 2025. Secciones 12-14 añadidas Julio 2026 (conexión directa al backup SIGA_300687).*