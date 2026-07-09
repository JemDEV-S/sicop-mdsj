# Actividad 3 — Arquitectura Técnica

> Municipalidad Distrital de San Jerónimo — Cusco
> Entregable formal de la Actividad 3 · Fase de Diseño
> Diagrama de componentes, modelo de datos PostgreSQL, definición de API, estrategia de sincronización y despliegue.
> Julio 2026

---

## 1. Stack tecnológico definitivo

| Capa | Tecnología | Motivo |
|---|---|---|
| **Backend** | Python 3.12 + FastAPI + Pydantic v2 | Ecosistema maduro para APIs REST + docs OpenAPI autogeneradas + excelente soporte SQL Server con `pyodbc` + análisis de datos con `pandas` para exportación |
| **Base intermedia** | PostgreSQL 16 | Estándar libre, robusto, buen soporte JSON para snapshots API |
| **Fuente SIGA** | Microsoft SQL Server (existente en la muni) | Consulta directa vía `pyodbc` / `pymssql`, solo lectura |
| **Fuente SIAF** | API pública MEF (Datos Abiertos) | Snapshot diario a PostgreSQL |
| **Frontend** | React 18 + Vite 5 + TypeScript 5 | Ecosistema más amplio para dashboards, mejor soporte de librerías de gráficos y mapas |
| **UI / estilos** | Tailwind CSS + shadcn/ui | Sistema de diseño rápido y consistente |
| **Estado en cliente** | TanStack Query (React Query) + Zustand | Caché de datos del servidor + estado global mínimo |
| **Gráficos** | Recharts | Componentes React nativos, cubre barras/líneas/dona/áreas |
| **Mapas** | Leaflet + React-Leaflet + OpenStreetMap | Libre, sin costo por tiles, suficiente para el MVP |
| **Caché backend** | Redis 7 | Para queries pesadas SIGA con TTL corto |
| **Jobs programados** | APScheduler (embebido en FastAPI) | Sin infraestructura extra; suficiente para el job nocturno SIAF |
| **Excel export** | openpyxl | Formato, fórmulas, estilos |
| **PDF export** | WeasyPrint (HTML/CSS → PDF) | Mejor fidelidad visual, mismo layout que la UI |
| **Auth** | JWT (access 15min + refresh 8h en httpOnly cookie) | Estándar, seguro, sin estado en servidor |
| **Hashing contraseñas** | bcrypt (via `passlib`) | Estándar de la industria |
| **Contenerización** | Docker + Docker Compose | Portable Windows/Linux, reproducible |
| **Reverse proxy** | Nginx (contenedor) | TLS, gzip, servir estáticos del frontend, rate-limit |
| **Logs** | `structlog` (JSON estructurado a archivo) + tabla `logs.auditoria` | Sin infra externa; auditoría de negocio en BD |

---

## 2. Diagrama de componentes

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          RED MUNICIPAL DE SAN JERÓNIMO                     │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     SERVIDOR LOCAL (Docker Compose)                  │  │
│  │                                                                       │  │
│  │  ┌──────────────┐   ┌──────────────────────────┐   ┌──────────────┐ │  │
│  │  │              │   │      Backend FastAPI      │   │              │ │  │
│  │  │    Nginx     │──▶│    (uvicorn + workers)   │──▶│   Redis 7    │ │  │
│  │  │   (443/80)   │   │                           │   │   (cache)    │ │  │
│  │  │  reverse    │   │  ┌─────────────────────┐  │   └──────────────┘ │  │
│  │  │   proxy +   │   │  │  APScheduler        │  │                    │  │
│  │  │  frontend   │   │  │  · Job SIAF (03:00) │  │   ┌──────────────┐ │  │
│  │  │  estático   │   │  │  · Job Invierte.pe  │  │   │ PostgreSQL 16│ │  │
│  │  │             │   │  └─────────────────────┘  │──▶│              │ │  │
│  │  └──────┬──────┘   │                           │   │  Schemas:    │ │  │
│  │         │          │  Módulos:                 │   │  · auth      │ │  │
│  │         │          │  · publico/               │   │  · siaf      │ │  │
│  │         │          │  · interno/               │   │  · sistema   │ │  │
│  │         │          │  · admin/                 │   │  · logs      │ │  │
│  │         │          └───────┬──────────────────┘   └──────────────┘ │  │
│  │         │                  │                                        │  │
│  │         │                  │                                        │  │
│  │         │                  ▼                                        │  │
│  │         │        ┌───────────────────┐                              │  │
│  │         │        │  Adaptador SIGA   │                              │  │
│  │         │        │  (pyodbc, SQL     │                              │  │
│  │         │        │   crudo + repo)   │                              │  │
│  │         │        └────────┬──────────┘                              │  │
│  │         │                 │                                         │  │
│  │         │                 ▼                                         │  │
│  │         │        ┌─────────────────────────┐                        │  │
│  │         │        │  SQL Server SIGA        │ (existente en la muni) │  │
│  │         │        │  Solo lectura           │                        │  │
│  │         │        └─────────────────────────┘                        │  │
│  │         │                                                           │  │
│  │         │        ┌─────────────────────────┐                        │  │
│  │         │        │ Filesystem              │                        │  │
│  │         │        │ /var/data/uploads/      │ (fotos, PDFs obras)    │  │
│  │         │        │ /var/log/presupuesto/   │ (logs)                 │  │
│  │         │        │ /var/backups/           │ (pg_dump diario)       │  │
│  │         │        └─────────────────────────┘                        │  │
│  │         │                                                           │  │
│  └─────────┼───────────────────────────────────────────────────────────┘  │
└────────────┼──────────────────────────────────────────────────────────────┘
             │
             │ HTTPS
             ▼
   ┌──────────────────────┐        ┌──────────────────────────────────────┐
   │  Ciudadano (browser) │        │  Funcionario (browser en red interna)│
   │  React SPA público   │        │  React SPA panel interno + login    │
   └──────────────────────┘        └──────────────────────────────────────┘

Flujo saliente (job nocturno):
   Backend ──▶ https://api.datosabiertos.mef.gob.pe (SIAF + Invierte.pe)
```

**Notas:**
- El backend, Nginx, PostgreSQL y Redis corren en el mismo host mediante Docker Compose.
- SQL Server del SIGA es externo al stack y solo se lee.
- Fotos y documentos se guardan en un volumen montado del host, expuestos mediante Nginx bajo `/media/`.
- El portal público se expone mediante una IP pública/DNS + certificado TLS (Let's Encrypt o interno).

---

## 3. Modelo de datos PostgreSQL

> **Nota — Revisión julio 2026:** el modelo original se refactorizó tras evaluar
> propuesta interna sobre catálogos y separación de dimensiones. Cambios clave:
> nuevo schema `ref` con dimensiones espejadas de SIGA, uso de `ltree` para
> jerarquía de centros de costo, UUID solo donde es semánticamente necesario,
> ENUMs para estados cerrados, y vista normalizada sobre la tabla de hechos.

### 3.0 Principios de diseño

1. **Fuentes autoritativas ≠ persistencia local.** SIGA es la fuente de verdad para metas y centros de costo; PostgreSQL guarda un espejo (`ref.*`) para evitar ir a SIGA en cada request.
2. **Staging + swap atómico** para snapshots externos (SIAF, Invierte.pe, catálogos SIGA). Nunca se sirve una tabla a medio poblar.
3. **Vista normalizada** entre datos externos (nombres que pueden cambiar en la fuente) y el frontend. Si el MEF renombra `FUNCION_NOMBRE`, cambia solo la vista.
4. **UUID solo donde el ID sale al mundo** (URLs públicas, tokens, referencias entre servicios). `bigserial` para todo lo interno.
5. **ENUMs para valores cerrados y estables.** `varchar` cuando el conjunto crece con el tiempo (ej. `logs.auditoria.accion`).
6. **`ltree` para jerarquías** de centros de costo — con índice GIST, las consultas "todos los descendientes de X" son sub-milisegundo.

### 3.1 Organización de schemas

| Schema | Propósito | Fuente |
|---|---|---|
| `auth` | Usuarios, roles, tokens, permisos por CC | Propio del sistema |
| `ref` | **Dimensiones espejadas de SIGA** (centros de costo, metas, sus relaciones) + catálogos fijos MEF (fuentes, rubros, funciones) | Snapshot diario de SIGA + seed MEF |
| `siaf` | Snapshots de la API MEF (ejecución presupuestal + Invierte.pe) | Snapshot diario de API MEF |
| `sistema` | Configuración (umbrales, alertas), datos de negocio propios (observaciones, anotaciones, documentos) | Propio del sistema |
| `logs` | Auditoría de acciones + logs de sincronización | Propio del sistema |

### 3.1.1 Extensiones PostgreSQL requeridas

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- generación de UUIDs
CREATE EXTENSION IF NOT EXISTS "ltree";       -- jerarquía de centros de costo
CREATE EXTENSION IF NOT EXISTS "btree_gin";   -- índices compuestos con jsonb
```

### 3.1.2 ENUMs globales

```sql
CREATE TYPE estado_usuario           AS ENUM ('activo', 'inactivo', 'bloqueado');
CREATE TYPE estado_observacion       AS ENUM ('pendiente', 'leida', 'respondida', 'spam');
CREATE TYPE estado_sync              AS ENUM ('en_curso', 'exito', 'error');
CREATE TYPE tipo_documento_obra      AS ENUM ('foto', 'expediente_tecnico', 'contrato', 'f8', 'f9', 'otro');
CREATE TYPE tipo_entidad_anotacion   AS ENUM ('pedido', 'orden', 'meta', 'obra', 'contrato');
CREATE TYPE tipo_entidad_alerta      AS ENUM ('pedido', 'contrato', 'meta');
CREATE TYPE direccion_semaforo       AS ENUM ('mayor', 'menor');  -- mayor = más = mejor
CREATE TYPE codigo_rol               AS ENUM ('ciudadano', 'operativo', 'decisor', 'admin');
```

### 3.2 Schema `auth`

#### `auth.roles`

Catálogo pequeño y cerrado — se pobla por seed.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `smallserial` PK | |
| `codigo` | `codigo_rol` UNIQUE | ENUM: `ciudadano`, `operativo`, `decisor`, `admin` |
| `nombre` | `varchar(80)` | Nombre humano |

#### `auth.usuarios`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `uuid` PK DEFAULT `uuid_generate_v4()` | Usado en JWT (`sub`), URLs de admin |
| `usuario` | `varchar(60)` UNIQUE NOT NULL | Login |
| `password_hash` | `text` NOT NULL | bcrypt |
| `nombre_completo` | `varchar(150)` NOT NULL | |
| `email` | `varchar(150)` | |
| `rol_id` | `smallint` FK → `auth.roles` NOT NULL | |
| `estado` | `estado_usuario` NOT NULL DEFAULT `'activo'` | ENUM |
| `intentos_fallidos` | `smallint` NOT NULL DEFAULT 0 | Para bloqueo |
| `bloqueado_hasta` | `timestamptz` NULL | |
| `debe_cambiar_password` | `boolean` NOT NULL DEFAULT true | Primer login |
| `creado_en` | `timestamptz` NOT NULL DEFAULT `now()` | |
| `actualizado_en` | `timestamptz` NOT NULL DEFAULT `now()` | Trigger `moddatetime` |

**Índices:** `(email) WHERE email IS NOT NULL`, `(rol_id)`.

#### `auth.usuarios_centros_costo`

Relación muchos-a-muchos: qué centros de costo puede ver cada usuario. Las jerarquías se resuelven contra `ref.centros_costo` (con `ltree`), por lo que no hay que replicar la jerarquía aquí — basta un flag.

| Columna | Tipo | Descripción |
|---|---|---|
| `usuario_id` | `uuid` FK → `auth.usuarios` | |
| `centro_costo` | `varchar(15)` FK → `ref.centros_costo(codigo)` | |
| `es_raiz_jerarquia` | `boolean` NOT NULL DEFAULT false | Si `true`, el usuario ve descendientes vía `ltree` |
| `creado_en` | `timestamptz` NOT NULL DEFAULT `now()` | |

**PK compuesta:** `(usuario_id, centro_costo)`.

#### `auth.refresh_tokens`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `uuid` PK DEFAULT `uuid_generate_v4()` | Se compara con hash del token |
| `usuario_id` | `uuid` FK → `auth.usuarios` NOT NULL | |
| `token_hash` | `text` NOT NULL | SHA-256 del token (no plaintext) |
| `expira_en` | `timestamptz` NOT NULL | |
| `revocado` | `boolean` NOT NULL DEFAULT false | |
| `creado_en` | `timestamptz` NOT NULL DEFAULT `now()` | |
| `user_agent` | `text` | Info del navegador |
| `ip_origen` | `inet` | |

**Índices:** `(usuario_id, revocado)`, `(expira_en)` para limpieza de tokens vencidos.

### 3.3 Schema `ref` — Dimensiones espejadas de SIGA

Snapshots diarios de tablas maestras de SIGA. Se sobrescriben con staging + swap.
El job `sync_catalogos_siga` corre junto al sync SIAF (03:00 diario).

#### `ref.centros_costo`

Espejo de `SIG_CENTRO_COSTO` filtrado por `SEC_EJEC=300687` y `ANO_EJE` vigente.
La columna `ruta` es un `ltree` que representa la jerarquía completa desde la raíz.

| Columna | Tipo | Descripción |
|---|---|---|
| `codigo` | `varchar(15)` PK | `SIG_CENTRO_COSTO.CENTRO_COSTO` |
| `nombre` | `varchar(200)` NOT NULL | `NOMBRE_DEPEND` |
| `abreviado` | `varchar(60)` | `ABREVIADO_DEPEND` |
| `centro_padre` | `varchar(15)` FK auto-ref | `CENTRO_PADRE` (nullable en raíces) |
| `ruta` | `ltree` NOT NULL | Reconstruido al final del sync. Ej: `root.0700.0714` |
| `nivel` | `smallint` NOT NULL | Profundidad en el árbol (root = 0) |
| `sede` | `smallint` | FK lógica a `SIG_SEDES` |
| `tipo_dependencia` | `char(1)` | `TIPO_DEPEND` |
| `nro_personal` | `smallint` | |
| `flag_cn` | `boolean` | Participa en cuadro de necesidades |
| `flag_presupuesto` | `boolean` | Tiene presupuesto asignado |
| `flag_ppr` | `boolean` | Participa en PPR |
| `activo` | `boolean` NOT NULL DEFAULT true | `ESTADO='A'` |
| `sincronizado_en` | `timestamptz` NOT NULL DEFAULT `now()` | |

**Índices:**
- `USING GIST (ruta)` — consultas jerárquicas rápidas
- `(centro_padre)`
- `(activo)` parcial

**Query típica** (todos los descendientes de OTI para un decisor):
```sql
SELECT * FROM ref.centros_costo WHERE ruta <@ 'root.0700.0714';
```

#### `ref.metas`

Espejo de `META` filtrado por `SEC_EJEC=300687` y `ANO_EJE` vigente.

| Columna | Tipo | Descripción |
|---|---|---|
| `sec_func` | `bigint` PK | `META.sec_func` (llave principal cruce SIAF↔SIGA) |
| `ano_eje` | `smallint` NOT NULL | |
| `meta` | `varchar(5)` NOT NULL | Código de meta |
| `nombre` | `varchar(200)` NOT NULL | |
| `funcion` | `varchar(2)` | |
| `programa` | `varchar(3)` | |
| `sub_programa` | `varchar(4)` | |
| `act_proy` | `varchar(7)` | Prefijo determina tipo (ver `tipo_meta`) |
| `componente` | `varchar(7)` | |
| `finalidad` | `varchar(10)` | |
| `tipo_meta` | `varchar(20)` NOT NULL | Calculado: `actividad_generica` (`3999999`), `proyecto_inversion` (`2xxxxxx`), `actividad_pp` (`3xxxxxx≠3999999`) |
| `unidad_med` | `varchar(3)` | |
| `activo` | `boolean` NOT NULL DEFAULT true | |
| `sincronizado_en` | `timestamptz` NOT NULL DEFAULT `now()` | |

**Índices:**
- `(ano_eje, tipo_meta)` para filtros del dashboard
- `(act_proy)` para cruce con Invierte.pe
- `(funcion)`, `(programa)` para filtros

#### `ref.metas_centro_costo`

Espejo de `SIG_METAS_X_CENTRO` — puente meta ↔ centro de costo con fuente/tipo recurso.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | Interno |
| `sec_func` | `bigint` FK → `ref.metas` NOT NULL | |
| `centro_costo` | `varchar(15)` FK → `ref.centros_costo` NOT NULL | |
| `secuencia` | `smallint` NOT NULL | Del SIGA original |
| `fuente_financ` | `varchar(2)` | |
| `tipo_recurso` | `varchar(2)` | |
| `porc_techo` | `numeric(8,4)` | |
| `sincronizado_en` | `timestamptz` NOT NULL DEFAULT `now()` | |

**Unique:** `(sec_func, centro_costo, secuencia)`.
**Índices:** `(centro_costo, sec_func)` para "metas de mi unidad".

#### `ref.fuentes_financiamiento`

Catálogo pequeño y estable — se pobla por seed. No cambia año a año.

| Columna | Tipo | Descripción |
|---|---|---|
| `codigo` | `varchar(2)` PK | `1`, `2`, `4`, `5` |
| `nombre` | `varchar(80)` NOT NULL | RO, RDR, Donaciones, R. Determinados |

#### `ref.rubros`

Catálogo pequeño y estable — seed.

| Columna | Tipo | Descripción |
|---|---|---|
| `codigo` | `varchar(2)` PK | `00`, `07`, `08`, `09`, `13`, `18` |
| `nombre` | `varchar(120)` NOT NULL | |
| `fuente_financ_codigo` | `varchar(2)` FK → `ref.fuentes_financiamiento` | |

#### `ref.funciones`

Catálogo de funciones presupuestales (67 según diccionario). Estable — seed inicial + refresh anual desde SIAF si aparecen nuevas.

| Columna | Tipo | Descripción |
|---|---|---|
| `codigo` | `varchar(4)` PK | `03`, `05`, `08`, `15`, ... |
| `nombre` | `varchar(120)` NOT NULL | TRANSPORTE, SANEAMIENTO, EDUCACION, ... |

#### `ref.programas_presupuestales`

Los 21 programas activos (ver Actividad 1 §7). Seed + refresh anual.

| Columna | Tipo | Descripción |
|---|---|---|
| `codigo` | `varchar(4)` PK | `0002`, `0082`, `0148`, `9001`, ... |
| `nombre` | `varchar(200)` NOT NULL | |

### 3.4 Schema `siaf`

Contiene el snapshot diario de la API MEF. Patrón staging + swap atómico (ver §6).
Para la v2 se añadirá `siaf.snapshot_historico` particionado por año.

#### `siaf.ejecucion_presupuestal`

Snapshot del resource `615644aa-ef73-4358-b4e0-0c20931632f3` filtrado por `SEC_EJEC=300687`.
Se mantiene denormalizada (incluye nombres inline del MEF) para permitir reconciliación con SIGA sin JOIN forzoso. El frontend consume la vista `siaf.v_ejecucion_normalizada` (ver abajo).

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | Interno |
| `ano_eje` | `smallint` NOT NULL | |
| `mes_eje` | `smallint` NOT NULL | 0 = PIM base, 1-12 = mes de ejecución |
| `sec_ejec` | `varchar(10)` NOT NULL | Fijo `300687` |
| `sec_func` | `bigint` NOT NULL | **Llave de cruce con `ref.metas`** |
| `producto_proyecto` | `varchar(20)` | |
| `producto_proyecto_nombre` | `text` | Nombre bruto del MEF (autoritativo: `ref.metas`) |
| `tipo_act_proy` | `char(1)` | `2` proyecto, `3` actividad |
| `meta` | `varchar(10)` | |
| `meta_nombre` | `text` | |
| `funcion` | `varchar(4)` | |
| `funcion_nombre` | `varchar(120)` | Bruto del MEF (autoritativo: `ref.funciones`) |
| `programa_ppto` | `varchar(10)` | |
| `programa_ppto_nombre` | `text` | Bruto del MEF (autoritativo: `ref.programas_presupuestales`) |
| `categoria_gasto` | `char(1)` | `5`/`6` |
| `generica` | `varchar(4)` | |
| `generica_nombre` | `varchar(120)` | |
| `subgenerica` | `varchar(4)` | |
| `especifica` | `varchar(4)` | |
| `especifica_det` | `varchar(4)` | |
| `fuente_financiamiento` | `varchar(4)` | |
| `fuente_financiamiento_nombre` | `varchar(120)` | Bruto (autoritativo: `ref.fuentes_financiamiento`) |
| `rubro` | `varchar(4)` | |
| `monto_pia` | `numeric(18,2)` NOT NULL DEFAULT 0 | Viene en 0 en la API — usar SIGA como fuente real |
| `monto_pim` | `numeric(18,2)` NOT NULL DEFAULT 0 | |
| `monto_certificado` | `numeric(18,2)` NOT NULL DEFAULT 0 | |
| `monto_comprometido_anual` | `numeric(18,2)` NOT NULL DEFAULT 0 | |
| `monto_comprometido` | `numeric(18,2)` NOT NULL DEFAULT 0 | |
| `monto_devengado` | `numeric(18,2)` NOT NULL DEFAULT 0 | |
| `monto_girado` | `numeric(18,2)` NOT NULL DEFAULT 0 | |
| `sincronizado_en` | `timestamptz` NOT NULL DEFAULT `now()` | |

**Índices:**
- `(ano_eje, mes_eje, sec_func)` — consultas del dashboard
- `(ano_eje, producto_proyecto)` — cruce con Invierte.pe
- `(ano_eje, mes_eje, funcion)` — agregaciones por función
- `(ano_eje, mes_eje, fuente_financiamiento)` — agregaciones por fuente
- `(sec_func)` — JOIN con `ref.metas`

#### `siaf.v_ejecucion_normalizada` (vista)

Vista que combina `siaf.ejecucion_presupuestal` con los catálogos de `ref` para servir nombres autoritativos. **Todo el frontend consume esta vista, no la tabla base.**

**Tratamiento de huérfanos** (filas SIAF sin match en `ref.metas`): `LEFT JOIN` + `COALESCE` a placeholder + flag `es_huerfano` para que el frontend pueda distinguirlas. Las discrepancias también quedan registrables desde una vista auxiliar (§ abajo).

```sql
CREATE VIEW siaf.v_ejecucion_normalizada AS
SELECT
    e.id, e.ano_eje, e.mes_eje, e.sec_ejec, e.sec_func,
    -- Meta: autoritativa desde ref; si no hay match, placeholder + nombre bruto del MEF como fallback
    COALESCE(m.meta,   e.meta,          '(sin código)')       AS meta_codigo,
    COALESCE(m.nombre, e.meta_nombre,   'Meta desconocida')   AS meta_nombre,
    m.tipo_meta,
    COALESCE(m.act_proy, e.producto_proyecto)                 AS producto_proyecto,
    -- Función: autoritativa desde ref
    COALESCE(f.codigo, e.funcion)                             AS funcion_codigo,
    COALESCE(f.nombre, e.funcion_nombre, 'Función desconocida') AS funcion_nombre,
    -- Fuente
    COALESCE(ff.codigo, e.fuente_financiamiento)              AS fuente_codigo,
    COALESCE(ff.nombre, e.fuente_financiamiento_nombre)       AS fuente_nombre,
    -- Clasificador (bruto del MEF — no hay catálogo por ahora)
    e.generica, e.generica_nombre, e.especifica, e.especifica_det,
    e.categoria_gasto,
    -- Montos
    e.monto_pia, e.monto_pim, e.monto_certificado,
    e.monto_comprometido_anual, e.monto_comprometido,
    e.monto_devengado, e.monto_girado,
    e.sincronizado_en,
    -- Flag para el frontend: fila sin match en ref.metas (usable para badge/alerta)
    (m.sec_func IS NULL)                                      AS es_huerfano
FROM siaf.ejecucion_presupuestal e
LEFT JOIN ref.metas m                    ON m.sec_func = e.sec_func
LEFT JOIN ref.funciones f                ON f.codigo = e.funcion
LEFT JOIN ref.fuentes_financiamiento ff  ON ff.codigo = e.fuente_financiamiento;
```

**Vista auxiliar de auditoría** para detectar discrepancias de sincronización:

```sql
CREATE VIEW siaf.v_ejecucion_huerfana AS
SELECT
    e.ano_eje, e.mes_eje, e.sec_func, e.meta, e.meta_nombre,
    e.producto_proyecto, e.producto_proyecto_nombre,
    e.monto_pim, e.monto_devengado, e.sincronizado_en
FROM siaf.ejecucion_presupuestal e
LEFT JOIN ref.metas m ON m.sec_func = e.sec_func
WHERE m.sec_func IS NULL;
```

Consumida por `/admin/reconciliacion` (v2) o revisada manualmente tras cada sync.

**Ventajas del enfoque:**
- Si el MEF renombra "TRANSPORTES" → "TRANSPORTE", solo se actualiza `ref.funciones` una vez.
- Si SIGA aún no sincroniza una meta nueva del MEF, la fila no se pierde — se muestra con placeholder y aparece en `v_ejecucion_huerfana` para atención manual.
- El frontend puede mostrar un badge "Meta pendiente de catalogar" cuando `es_huerfano = true`.

#### `siaf.inversiones`

Snapshot del resource `f9cc4ba0-931a-4b70-86c9-eacbd8c68596` (Invierte.pe).

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | |
| `codigo_unico` | `varchar(20)` | **Cruce con SIAF `producto_proyecto`** |
| `nombre_inversion` | `text` | |
| `tipo_inversion` | `varchar(40)` | |
| `marco` | `varchar(20)` | `INVIERTE` / `SNIP` |
| `estado` | `varchar(20)` | `ACTIVO` / `CERRADO` |
| `situacion` | `varchar(30)` | `VIABLE`, `APROBADO` |
| `anio_proceso` | `smallint` | |
| `sec_ejec` | `varchar(10)` | |
| `avance_fisico` | `numeric(6,2)` | % |
| `avance_ejecucion` | `numeric(6,2)` | % |
| `tiene_avan_fisico` | `char(2)` | `SI`/`NO` |
| `pim_anio_actual` | `numeric(18,2)` | |
| `dev_anio_actual` | `numeric(18,2)` | |
| `deven_acumul_anio_ant` | `numeric(18,2)` | |
| `comprom_anual_anio_actual` | `numeric(18,2)` | |
| `certif_anio_actual` | `numeric(18,2)` | |
| `costo_actualizado` | `numeric(18,2)` | |
| `monto_viable` | `numeric(18,2)` | |
| `saldo_ejecutar` | `numeric(18,2)` | En millones |
| `tiene_f8` | `char(2)` | |
| `etapa_f8` | `varchar(50)` | `A`, `B`, `C` |
| `tiene_f9` | `char(2)` | |
| `tiene_f12b` | `char(2)` | |
| `informe_cierre` | `char(2)` | |
| `expediente_tecnico` | `char(2)` | |
| `des_modalidad` | `varchar(40)` | `CONTRATA` / `ADMINISTRACIÓN DIRECTA` |
| `des_tipologia` | `varchar(80)` | |
| `funcion` | `varchar(80)` | |
| `programa` | `varchar(80)` | |
| `fec_ini_ejecucion` | `date` | |
| `fec_fin_ejecucion` | `date` | |
| `fec_ini_ejec_fisica` | `date` | |
| `fec_fin_ejec_fisica` | `date` | |
| `fecha_viabilidad` | `date` | |
| `primer_devengado` | `date` | |
| `ultimo_devengado` | `date` | |
| `latitud` | `numeric(10,7)` | |
| `longitud` | `numeric(10,7)` | |
| `ubigeo` | `varchar(6)` | |
| `departamento` | `varchar(60)` | |
| `provincia` | `varchar(60)` | |
| `distrito` | `varchar(60)` | |
| `nombre_uei` | `text` | |
| `nombre_uf` | `text` | |
| `nombre_opmi` | `text` | |
| `sincronizado_en` | `timestamptz` NOT NULL DEFAULT `now()` | |

**Índices:**
- `codigo_unico` UNIQUE
- `(latitud, longitud)` WHERE latitud IS NOT NULL — para el mapa
- `(des_tipologia)`, `(funcion)` para filtros
- `(sec_ejec, estado)` parcial

### 3.5 Schema `sistema`

#### `sistema.umbrales_semaforos`

Configuración de umbrales de semáforos por módulo. Los defaults se cargan por seed.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `smallserial` PK | Interno |
| `modulo` | `varchar(50)` NOT NULL | `portal_obras`, `saldos`, `metas`, `pipeline`, etc. |
| `metrica` | `varchar(50)` NOT NULL | `avance_fisico`, `avance_financiero`, `saldo_disponible`, ... |
| `umbral_verde` | `numeric(6,2)` NOT NULL | |
| `umbral_amarillo` | `numeric(6,2)` NOT NULL | |
| `direccion` | `direccion_semaforo` NOT NULL | ENUM: `mayor` (más = mejor) o `menor` |
| `actualizado_por` | `uuid` FK → `auth.usuarios` NULL | |
| `actualizado_en` | `timestamptz` NOT NULL DEFAULT `now()` | |

**Unique:** `(modulo, metrica)`.

#### `sistema.umbrales_alertas`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `smallserial` PK | |
| `codigo_alerta` | `varchar(50)` UNIQUE NOT NULL | `pedido_estancado`, `contrato_por_vencer`, `meta_baja_ejecucion` |
| `parametros` | `jsonb` NOT NULL | Ej: `{"dias": 15}` o `{"dias": 30}` o `{"pct_q3": 50, "pct_q4": 90}` |
| `actualizado_por` | `uuid` FK → `auth.usuarios` NULL | |
| `actualizado_en` | `timestamptz` NOT NULL DEFAULT `now()` | |

#### `sistema.alertas_revisadas`

Persistencia de alertas marcadas por el usuario como revisadas.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | Interno — no sale al mundo |
| `usuario_id` | `uuid` FK → `auth.usuarios` NOT NULL | |
| `codigo_alerta` | `varchar(50)` NOT NULL | Coincide con `sistema.umbrales_alertas.codigo_alerta` |
| `entidad_tipo` | `tipo_entidad_alerta` NOT NULL | ENUM |
| `entidad_id` | `varchar(50)` NOT NULL | Identificador SIGA (`NRO_PEDIDO`, `NRO_CONTRATO`, `SEC_FUNC`) |
| `revisado_en` | `timestamptz` NOT NULL DEFAULT `now()` | |
| `comentario` | `text` NULL | |

**Índices:** `(usuario_id, codigo_alerta, entidad_id)` UNIQUE (evita duplicados).

#### `sistema.anotaciones_internas`

Notas que los funcionarios agregan a un pedido, orden, meta u obra. No tocan SIGA/SIAF.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | Interno |
| `entidad_tipo` | `tipo_entidad_anotacion` NOT NULL | ENUM |
| `entidad_id` | `varchar(50)` NOT NULL | |
| `usuario_id` | `uuid` FK → `auth.usuarios` NOT NULL | |
| `texto` | `text` NOT NULL | |
| `creado_en` | `timestamptz` NOT NULL DEFAULT `now()` | |

**Índices:** `(entidad_tipo, entidad_id, creado_en DESC)` para traer notas de una entidad ordenadas.

#### `sistema.observaciones_ciudadanas`

Buzón público de la ficha de obra. `id` es UUID porque sale al mundo (URL de confirmación al ciudadano).

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `uuid` PK DEFAULT `uuid_generate_v4()` | Expuesto en URL/email de confirmación |
| `codigo_unico_obra` | `varchar(20)` NOT NULL | Referencia a Invierte.pe |
| `nombre_ciudadano` | `varchar(150)` NULL | |
| `email_ciudadano` | `varchar(150)` NULL | |
| `texto` | `text` NOT NULL | |
| `estado` | `estado_observacion` NOT NULL DEFAULT `'pendiente'` | ENUM |
| `revisado_por` | `uuid` FK → `auth.usuarios` NULL | |
| `revisado_en` | `timestamptz` NULL | |
| `respuesta_interna` | `text` NULL | |
| `ip_origen` | `inet` | Para detectar abuso |
| `captcha_score` | `numeric(3,2)` NULL | Score de reCAPTCHA v3 |
| `creado_en` | `timestamptz` NOT NULL DEFAULT `now()` | |

**Índices:** `(codigo_unico_obra, creado_en DESC)`, `(estado)` parcial.

#### `sistema.documentos_obra`

Archivos subidos por funcionarios asociados a una obra. `id` es UUID porque forma parte de la URL pública de descarga.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `uuid` PK DEFAULT `uuid_generate_v4()` | Expuesto en URL de descarga |
| `codigo_unico_obra` | `varchar(20)` NOT NULL | |
| `tipo` | `tipo_documento_obra` NOT NULL | ENUM |
| `nombre_original` | `varchar(255)` NOT NULL | |
| `ruta_relativa` | `varchar(500)` NOT NULL | Bajo `/var/data/uploads/obras/{codigo}/...` |
| `mime_type` | `varchar(80)` NOT NULL | |
| `tamano_bytes` | `int` NOT NULL | |
| `subido_por` | `uuid` FK → `auth.usuarios` NOT NULL | |
| `subido_en` | `timestamptz` NOT NULL DEFAULT `now()` | |
| `publicado` | `boolean` NOT NULL DEFAULT true | Permite despublicar sin borrar |

**Índices:** `(codigo_unico_obra, tipo) WHERE publicado`, `(subido_por)`.

### 3.6 Schema `logs`

#### `logs.auditoria`

Auditoría de acciones de negocio. `accion` es **varchar (no enum)** porque el conjunto crece: cada nueva feature agrega códigos.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | Interno |
| `usuario_id` | `uuid` FK → `auth.usuarios` NULL | NULL para acciones públicas |
| `accion` | `varchar(50)` NOT NULL | `login_exitoso`, `login_fallido`, `exportacion`, `cambio_umbral`, `subida_documento`, `publicacion_observacion`, ... |
| `detalle` | `jsonb` | Payload variable |
| `ip` | `inet` | |
| `user_agent` | `text` | |
| `creado_en` | `timestamptz` NOT NULL DEFAULT `now()` | |

**Índices:**
- `(usuario_id, creado_en DESC)` — historial de un usuario
- `(accion, creado_en DESC)` — filtro por tipo de acción
- `USING gin (detalle jsonb_path_ops)` para queries sobre el payload

#### `logs.sincronizacion`

Estado de los jobs de sincronización.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | Interno |
| `job` | `varchar(50)` NOT NULL | `siaf_ejecucion`, `siaf_inversiones`, `catalogos_siga` |
| `inicio` | `timestamptz` NOT NULL DEFAULT `now()` | |
| `fin` | `timestamptz` NULL | |
| `estado` | `estado_sync` NOT NULL DEFAULT `'en_curso'` | ENUM |
| `registros_procesados` | `int` | |
| `error_mensaje` | `text` NULL | |

**Índices:** `(job, inicio DESC)` para ver historial de un job.

---

### 3.7 Resumen del modelo — 20 tablas + 2 vistas

| Schema | Tabla | PK | Notas |
|---|---|---|---|
| `auth` | `roles` | smallserial | seed |
| `auth` | `usuarios` | uuid | JWT sub |
| `auth` | `usuarios_centros_costo` | (usuario_id, centro_costo) | FK a `ref` |
| `auth` | `refresh_tokens` | uuid | |
| `ref` | `centros_costo` | varchar(15) | ltree para jerarquía |
| `ref` | `metas` | bigint | espejo `META` |
| `ref` | `metas_centro_costo` | bigserial | puente |
| `ref` | `fuentes_financiamiento` | varchar(2) | seed |
| `ref` | `rubros` | varchar(2) | seed |
| `ref` | `funciones` | varchar(4) | seed + refresh anual |
| `ref` | `programas_presupuestales` | varchar(4) | seed + refresh anual |
| `siaf` | `ejecucion_presupuestal` | bigserial | staging+swap diario |
| `siaf` | `inversiones` | bigserial | staging+swap diario |
| `siaf` | `v_ejecucion_normalizada` | (vista) | consumida por el frontend — COALESCE con placeholder para huérfanos |
| `siaf` | `v_ejecucion_huerfana` | (vista) | auditoría de filas SIAF sin match en `ref.metas` |
| `sistema` | `umbrales_semaforos` | smallserial | seed defaults |
| `sistema` | `umbrales_alertas` | smallserial | seed defaults |
| `sistema` | `alertas_revisadas` | bigserial | |
| `sistema` | `anotaciones_internas` | bigserial | |
| `sistema` | `observaciones_ciudadanas` | uuid | URL pública |
| `sistema` | `documentos_obra` | uuid | URL pública |
| `logs` | `auditoria` | bigserial | |
| `logs` | `sincronizacion` | bigserial | |

### 3.8 Trazabilidad de decisiones (revisión julio 2026)

| Decisión | Justificación | Aplicación |
|---|---|---|
| Schema `ref` con espejos de SIGA | Evita ir a SIGA en cada request; permite JOIN local rápido; centraliza el "árbol" de CC | `ref.centros_costo`, `ref.metas`, `ref.metas_centro_costo` |
| `ltree` para jerarquía CC | Consultas "descendientes de X" O(log n) con índice GIST vs recursividad | `ref.centros_costo.ruta` |
| UUID solo donde sale al mundo | Menor overhead en tablas internas; mejor localidad en índices | `usuarios`, `refresh_tokens`, `observaciones_ciudadanas`, `documentos_obra` |
| ENUM para estados cerrados | Validación en BD, ahorro de storage, autocompletado en herramientas | 8 ENUMs en §3.1.2 |
| Vista normalizada | Aísla el frontend de cambios en nombres del MEF; fuente autoritativa consistente | `siaf.v_ejecucion_normalizada` |
| Staging + swap atómico | Nunca servir tablas a medio poblar; rollback trivial | Todos los jobs de sync (§6) |
| **NO** `catalogos.periodos` (rechazado) | 3 filas no ganan a `smallint` directo | — |
| **NO** multi-tenant (rechazado) | Fuera del alcance MVP; el filtro `SEC_EJEC=300687` es regla no negociable | — |
| **NO** star schema puro (parcial) | Sobre-ingeniería para volumen actual (~5K filas/año) | Compromiso: `ref.*` como dimensiones ligeras |
| **NO** eliminar `_nombre` de `siaf.ejecucion` | Rechazado tras evaluación: los ~500KB de duplicación por año son despreciables vs el valor de reconciliación con el snapshot MEF exacto en el momento de la ingesta. Además `ref.metas` y `siaf.ejecucion` tienen ciclos de sync independientes — mantener los nombres brutos permite mostrar filas huérfanas con contexto en vez de vacío. | Los `_nombre` se mantienen en `siaf.ejecucion_presupuestal`. La vista `v_ejecucion_normalizada` prefiere `ref.*` (autoritativo) y hace fallback al bruto con COALESCE. |
| Manejo de huérfanos SIAF↔`ref.metas` | LEFT JOIN + COALESCE + placeholder "Meta desconocida" + flag `es_huerfano`. Vista auxiliar `siaf.v_ejecucion_huerfana` para auditoría. No perder filas de ejecución legítima. | En la vista `siaf.v_ejecucion_normalizada` (§3.4) |

---

## 4. Definición de la API REST

### 4.1 Convenciones

- Base URL: `https://<host>/api/v1/`
- Prefijos por audiencia:
  - `/publico/` — sin autenticación, cache-friendly, expuesto al portal ciudadano.
  - `/interno/` — requiere JWT válido, aplica filtros por rol y centro de costo.
  - `/admin/` — requiere rol `admin`.
- Respuestas: objetos JSON directos con status HTTP semántico.
- Errores: `{ "detail": "mensaje", "code": "CODIGO_INTERNO" }` con status 4xx/5xx.
- Paginación: query params `?page=1&size=25`, respuesta con headers `X-Total-Count` y `X-Total-Pages`.
- Ordenamiento: `?sort=campo:asc,otro:desc`.
- Filtros: query params por campo (`?funcion=TRANSPORTE&estado=activo`).
- Docs OpenAPI: `/api/v1/docs` (Swagger UI) y `/api/v1/openapi.json`.

### 4.2 Endpoints públicos

| Método | Ruta | Descripción | HU |
|---|---|---|---|
| GET | `/publico/obras` | Listado de proyectos de inversión con filtros y paginación | HU-01 |
| GET | `/publico/obras/{codigo_unico}` | Ficha detallada de una obra | HU-02 |
| GET | `/publico/obras/mapa` | Marcadores + filtros geo (respuesta ligera) | HU-04 |
| GET | `/publico/obras/{codigo_unico}/documentos` | Documentos publicados de una obra | HU-02 |
| GET | `/publico/obras/{codigo_unico}/fotos` | Fotos publicadas | HU-02 |
| POST | `/publico/obras/{codigo_unico}/observaciones` | Registrar observación (con captcha) | HU-24 |
| GET | `/publico/ejecucion/resumen` | KPIs para dashboard general | HU-05 |
| GET | `/publico/ejecucion/por-funcion` | Agregado por función | HU-05 |
| GET | `/publico/ejecucion/por-fuente` | Agregado por fuente de financiamiento | HU-05 |
| GET | `/publico/ejecucion/mensual` | Serie mensual acumulada | HU-05 |
| GET | `/publico/ejecucion/detalle` | Tabla detallada con filtros | HU-06 |
| GET | `/publico/proveedores` | Directorio público | HU-07 |
| GET | `/publico/proveedores/{ruc}` | Ficha pública del proveedor | HU-07 |
| GET | `/media/uploads/**` | Archivos estáticos publicados (Nginx) | HU-02 |

### 4.3 Endpoints de autenticación

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/login` | Recibe usuario/contraseña. Devuelve access token + setea refresh en httpOnly cookie |
| POST | `/auth/refresh` | Renueva access token usando refresh de la cookie |
| POST | `/auth/logout` | Revoca refresh token |
| POST | `/auth/cambiar-password` | Requiere access token válido |
| GET | `/auth/me` | Devuelve perfil y permisos del usuario actual |

### 4.4 Endpoints internos (autenticados)

**Pipeline y órdenes:**
| Método | Ruta | HU |
|---|---|---|
| GET | `/interno/pipeline/kanban` | HU-09 |
| GET | `/interno/pedidos` | HU-09 |
| GET | `/interno/pedidos/{nro_pedido}/{tipo_bien}` | HU-10 |
| GET | `/interno/ordenes` | HU-10 |
| GET | `/interno/ordenes/{nro_orden}/{tipo_bien}` | HU-10 |
| POST | `/interno/pedidos/{nro_pedido}/anotaciones` | HU-10 |

**Cruce SIAF-SIGA:**
| Método | Ruta | HU |
|---|---|---|
| GET | `/interno/cruce/expediente-siaf/{exp_siaf}` | HU-12 |
| GET | `/interno/cruce/meta/{sec_func}` | HU-13 (vista consolidada) |
| GET | `/interno/cruce/meta/{sec_func}/ordenes` | HU-13 / HU-14 |
| GET | `/interno/cruce/meta/{sec_func}/certificaciones` | HU-13 |
| GET | `/interno/cruce/meta/{sec_func}/conformidades` | HU-13 |
| GET | `/interno/cruce/meta/{sec_func}/pedidos` | HU-13 |

**Saldos:**
| Método | Ruta | HU |
|---|---|---|
| GET | `/interno/saldos` | HU-15 |
| GET | `/interno/saldos/metas-rezagadas` | HU-16 |

**Alertas y dashboard:**
| Método | Ruta | HU |
|---|---|---|
| GET | `/interno/dashboard` | HU-22 |
| GET | `/interno/alertas/pedidos-estancados` | HU-11 |
| GET | `/interno/alertas/contratos-por-vencer` | HU-20 |
| GET | `/interno/alertas/metas-rezagadas` | HU-16 |
| POST | `/interno/alertas/{id}/revisar` | HU-11 / HU-16 / HU-20 |

**Proveedores y contratos:**
| Método | Ruta | HU |
|---|---|---|
| GET | `/interno/proveedores` | HU-19 |
| GET | `/interno/proveedores/{ruc}` | HU-19 |
| GET | `/interno/proveedores/{ruc}/ordenes` | HU-19 |
| GET | `/interno/contratos` | HU-19 / HU-20 |
| GET | `/interno/contratos/{nro_contrato}` | HU-19 |

**Exportación:**
| Método | Ruta | HU |
|---|---|---|
| POST | `/interno/exportar/excel` | HU-21 |
| POST | `/interno/exportar/pdf` | HU-21 |
| GET | `/interno/exportar/{job_id}/estado` | HU-21 (para exports en background) |
| GET | `/interno/exportar/{job_id}/descarga` | HU-21 |

**Gestión de obra (rol operativo con permiso):**
| Método | Ruta | HU |
|---|---|---|
| POST | `/interno/obras/{codigo_unico}/documentos` | HU-03 |
| DELETE | `/interno/obras/{codigo_unico}/documentos/{id}` | HU-03 |
| POST | `/interno/obras/{codigo_unico}/fotos` | HU-03 |
| DELETE | `/interno/obras/{codigo_unico}/fotos/{id}` | HU-03 |

### 4.5 Endpoints admin

| Método | Ruta | HU |
|---|---|---|
| GET | `/admin/usuarios` | HU-17 |
| POST | `/admin/usuarios` | HU-17 |
| PATCH | `/admin/usuarios/{id}` | HU-17 |
| DELETE | `/admin/usuarios/{id}` | HU-17 (soft-delete) |
| GET | `/admin/roles` | HU-17 |
| GET | `/admin/configuracion/semaforos` | HU-18 |
| PUT | `/admin/configuracion/semaforos` | HU-18 |
| GET | `/admin/configuracion/alertas` | HU-18 |
| PUT | `/admin/configuracion/alertas` | HU-18 |
| GET | `/admin/logs/auditoria` | Consulta de logs |
| GET | `/admin/logs/sincronizacion` | Estado de jobs |
| POST | `/admin/jobs/sincronizar-siaf` | Trigger manual del job |
| GET | `/admin/observaciones-ciudadanas` | HU-24 (revisión) |
| PATCH | `/admin/observaciones-ciudadanas/{id}` | HU-24 (marcar estado) |

### 4.6 Autorización

- Middleware valida JWT en rutas `/interno/*` y `/admin/*`.
- Dependencia inyectada extrae `usuario_id`, `rol`, `centros_costo_permitidos` (calculado incluyendo descendientes para decisores).
- Cada handler que consulta SIGA aplica el filtro `WHERE CENTRO_COSTO IN (:permitidos)` cuando el rol lo requiere.
- Admin bypasea el filtro.

### 4.7 Rate limiting y CORS

- `/publico/*`: 60 req/min por IP (Nginx `limit_req_zone`).
- `/publico/*/observaciones`: 5 req/hora por IP + captcha obligatorio.
- `/interno/*` y `/admin/*`: 300 req/min por token.
- CORS: solo dominios de la muni (configurable en env).

---

## 5. Adaptador SIGA (SQL Server)

### 5.1 Estrategia de acceso

- Conexión: `pyodbc` + driver `ODBC Driver 18 for SQL Server`.
- Solo lectura: usuario dedicado con `db_datareader` sobre la base SIGA.
- Pool de conexiones administrado por `SQLAlchemy engine` (aunque las queries sean crudas, el pool se aprovecha).
- Todas las queries fijan `SEC_EJEC = 300687` y `ANO_EJE = :ano` como parámetros bind.

### 5.2 Capa de repositorio

Cada dominio tiene un módulo repositorio con queries SQL crudas parametrizadas. Ejemplo de organización:

```
backend/
  app/
    repositories/
      __init__.py
      pedidos_repo.py
      ordenes_repo.py
      metas_repo.py
      saldos_repo.py
      contratos_repo.py
      proveedores_repo.py
      cruce_repo.py
```

Cada método devuelve `list[dict]` o `dict` que Pydantic valida antes de responder. Los servicios (`app/services/`) orquestan varios repositorios cuando la vista lo requiere.

### 5.3 Queries autoritativas para el MVP

**Saldos (HU-15):**
```sql
SELECT
    t.sec_func, m.nombre AS nombre_meta, m.act_proy,
    t.CLASIFICADOR, t.FUENTE_FINANC, t.CENTRO_COSTO,
    t.PPTO_PIA AS pia, t.PPTO_MODIF AS pim,
    t.mnto_acum_cert AS certificado,
    t.MNTO_ACUM_DEVGDO_SIGA AS devengado,
    t.PPTO_DISP_SIAF AS saldo_disponible,
    t.MNTO_RESERVA_PEDIDO AS reservado
FROM SIG_TECHO_PRESUPUESTO t
INNER JOIN META m
    ON t.sec_func = m.sec_func AND t.ANO_EJE = m.ano_eje
WHERE t.ANO_EJE = :ano
  AND t.SEC_EJEC = :sec_ejec
  AND t.CENTRO_COSTO IN (:centros)
```

**Pipeline kanban (HU-09):** ver query base en el diccionario sección 20.2 (`HU-10`).

**Cruce meta consolidada (HU-13):** ver query base en el diccionario sección 12.6 del documento SIGA (adaptada al año y centros del usuario).

### 5.4 Caché de queries pesadas (Redis)

- Claves con prefijo `siga:` y namespace por dominio (`siga:saldos:...`).
- TTL sugerido:
  - Saldos consolidados: 5 minutos
  - Kanban pipeline: 2 minutos
  - Directorio proveedores: 30 minutos
  - Cruce por meta: 5 minutos
- Invalidación manual desde `/admin/cache/invalidar` (por si un funcionario nota desincronización tras un cambio en SIGA).

---

## 6. Sincronización con la API MEF

### 6.1 Job SIAF (nocturno)

**Cron:** diario a las 03:00 hora local (configurable).

**Flujo:**

1. Registrar inicio en `logs.sincronizacion` con estado `en_curso`.
2. Iterar meses (`MES_EJE` de 0 al mes actual).
3. Para cada mes, paginar con `LIMIT 100 OFFSET n` hasta agotar los registros.
4. Ejecutar hasta 8 columnas por request (limitación documentada de la API).
5. Insertar en una tabla staging `siaf.ejecucion_presupuestal_staging`.
6. Al finalizar exitosamente, `TRUNCATE siaf.ejecucion_presupuestal` y copiar de staging (transacción única).
7. Registrar fin con estado `exito` o `error` en `logs.sincronizacion`.

**Reintentos:**
- 3 intentos con backoff exponencial (10s, 30s, 90s) por request fallido.
- Si tras 3 intentos falla, aborta el job y mantiene el snapshot anterior. Notifica en logs.

### 6.2 Job Invierte.pe (mismo cron, ejecuta después)

Mismo patrón: staging + swap atómico. Volumen bajo (~70 registros).

### 6.3 Trigger manual

Endpoint `POST /admin/jobs/sincronizar-siaf` para forzar la sincronización sin esperar la ventana nocturna.

### 6.4 Frescura visible al usuario

- Cada respuesta pública de `/publico/ejecucion/*` incluye header `X-Sincronizado-En: <timestamp>`.
- El frontend muestra "Actualizado al DD/MM/YYYY HH:mm" en el pie del dashboard.

---

## 7. Autenticación y autorización

### 7.1 Flujo JWT

```
1. POST /auth/login  { usuario, password }
   → 200 { access_token }                  (Set-Cookie: refresh_token httpOnly, Secure, SameSite=Lax)

2. Frontend guarda access_token en memoria (Zustand) — NO en localStorage.
3. Cada request añade: Authorization: Bearer <access_token>

4. Cuando access_token expira (15 min):
   → POST /auth/refresh (envía cookie automáticamente)
   → 200 { access_token }  (nuevo)

5. Refresh token expira a las 8h. Al expirar → forzar re-login.

6. POST /auth/logout → revoca refresh_token (marca `revocado = true`) y borra la cookie.
```

### 7.2 Claims del access token

```json
{
  "sub": "<usuario_id>",
  "rol": "operativo|decisor|admin",
  "cc": ["CC-023", "CC-041"],
  "iat": 1720000000,
  "exp": 1720000900
}
```

Los centros de costo se resuelven al momento del login (incluyendo descendientes para decisores). Cuando se cambian los CC de un usuario, se le fuerza re-login.

### 7.3 Bloqueo por intentos fallidos

- Tras 5 intentos fallidos en 15 min: bloqueo por 15 min.
- Cada intento fallido incrementa `intentos_fallidos`; login exitoso lo resetea.

---

## 8. Frontend — Arquitectura

### 8.1 Estructura de carpetas

```
frontend/
  src/
    app/                  # Router (React Router v6) y layout raíz
    pages/
      publico/            # Portal ciudadano
        Home.tsx
        Obras.tsx
        Obra.tsx
        Mapa.tsx
        Ejecucion.tsx
        Proveedores.tsx
      interno/            # Panel funcionario
        Dashboard.tsx
        Pipeline.tsx
        Pedido.tsx
        Saldos.tsx
        Cruce.tsx
        MetaConsolidada.tsx
        Proveedores.tsx
        Contratos.tsx
      admin/
        Usuarios.tsx
        Configuracion.tsx
        Logs.tsx
    components/
      ui/                 # shadcn/ui (Button, Card, Table, ...)
      grafico/            # Wrappers Recharts
      mapa/               # Wrapper Leaflet
      tabla/              # DataTable con orden, filtro, paginación
    features/
      auth/               # useAuth, guardias de ruta
      exportar/           # Hook y modal de exportación
    lib/
      api-client.ts       # axios/fetch con interceptor de auth y refresh
      formatters.ts       # S/, %, fechas es-PE
      semaforo.ts         # Cálculo de color según umbrales
    store/
      auth.ts             # Zustand: access token, usuario
      umbrales.ts         # Zustand: umbrales cargados de la API
    styles/
      globals.css
```

### 8.2 Enrutamiento por audiencia

- `/` → landing pública con enlaces a los módulos ciudadanos
- `/obras`, `/obras/:codigo`, `/mapa`, `/ejecucion`, `/proveedores` → públicos
- `/login`
- `/panel/*` → protegido, redirige a `/login` si no hay sesión
- `/admin/*` → protegido + rol admin

### 8.3 TanStack Query

- Todas las llamadas GET van por `useQuery` con clave semántica.
- Datos públicos: `staleTime = 5 min` (coincide con TTL en Redis).
- Datos internos: `staleTime = 1 min` para pipeline, `staleTime = 5 min` para saldos.
- Mutaciones (subida de docs, revisión de alerta) con invalidación selectiva de queries.

### 8.4 Accesibilidad y responsive

- Componentes basados en Radix UI (shadcn) — accesibles por defecto.
- Layout mobile-first (Tailwind breakpoints `sm`, `md`, `lg`).
- Contraste AA en semáforos (no depender solo del color: añadir icono).

### 8.5 SEO del portal público

Para MVP se acepta SPA sin SSR (React + Vite). Se generan:
- Meta tags dinámicos con `react-helmet-async`
- `sitemap.xml` estático generado en build con las rutas de obras conocidas
- `robots.txt` que permite indexación pública, deniega `/panel/*`, `/admin/*`

Si se detecta que el SEO es crítico en v2, se evalúa migración a Next.js.

---

## 9. Despliegue

### 9.1 Docker Compose

```
docker-compose.yml
├── nginx        (imagen oficial, sirve frontend estático + reverse proxy → backend)
├── backend      (imagen construida: python:3.12-slim + uvicorn + APScheduler)
├── postgres     (postgres:16 con volumen persistente)
├── redis        (redis:7-alpine)
└── (opcional) certbot para renovación de Let's Encrypt
```

Volúmenes:
- `postgres_data:/var/lib/postgresql/data`
- `uploads:/var/data/uploads`
- `logs:/var/log/presupuesto`
- `backups:/var/backups`

Networks:
- Solo `nginx` expone puertos 80/443 al host.
- `backend`, `postgres`, `redis` se comunican por red interna Docker.

### 9.2 Variables de entorno

Archivo `.env` (no versionado). Ejemplo:

```
# App
APP_ENV=production
APP_SECRET_KEY=<random 32 bytes>
APP_JWT_ACCESS_MINUTES=15
APP_JWT_REFRESH_HOURS=8

# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_DB=presupuesto
POSTGRES_USER=app
POSTGRES_PASSWORD=<secreto>

# SIGA (SQL Server local)
SIGA_HOST=192.168.x.x
SIGA_PORT=1433
SIGA_DB=SIGA_300687
SIGA_USER=lector_presupuesto
SIGA_PASSWORD=<secreto>
SIGA_ODBC_DRIVER=ODBC Driver 18 for SQL Server

# API MEF
MEF_BASE_URL=https://api.datosabiertos.mef.gob.pe/DatosAbiertos/v1
MEF_RESOURCE_EJECUCION=615644aa-ef73-4358-b4e0-0c20931632f3
MEF_RESOURCE_INVERSIONES=f9cc4ba0-931a-4b70-86c9-eacbd8c68596

# Entidad
SEC_EJEC=300687
ANO_VIGENTE=2026

# Redis
REDIS_URL=redis://redis:6379/0

# Uploads
UPLOAD_MAX_MB_FOTO=5
UPLOAD_MAX_MB_DOCUMENTO=20
UPLOAD_PATH=/var/data/uploads

# CORS
CORS_ORIGINS=https://transparencia.munisanjeronimo.gob.pe

# Captcha
RECAPTCHA_SECRET=<secreto>
```

### 9.3 TLS y dominio

- Portal público bajo un dominio (ej. `transparencia.munisanjeronimo.gob.pe`).
- Certificado Let's Encrypt via certbot en el contenedor Nginx.
- HSTS activado tras verificar funcionamiento estable.

### 9.4 Backup

- Job diario a las 04:00 (después de la sincronización) ejecuta `pg_dump` a `/var/backups/postgres/YYYYMMDD.sql.gz`.
- Job semanal (domingo 05:00) copia los últimos 7 dumps + `uploads/` a almacenamiento externo (NAS de la muni o cloud).
- Retención local: últimos 30 días. Retención remota: últimas 12 semanas.

### 9.5 Seguridad operativa

- Firewall del servidor: solo 80/443 abiertos hacia afuera.
- Acceso SSH restringido a IPs de administradores.
- Contraseñas en secretos Docker (no en env plain-text si el server es multi-usuario).
- Rotación de credenciales SIGA cada 6 meses.
- Logs de Nginx con `access.log` y `error.log` rotados diariamente.

---

## 10. Observabilidad y logs

### 10.1 Logs estructurados

- Backend usa `structlog` con formato JSON.
- Nivel INFO por defecto, DEBUG activable via env.
- Salida: stdout (capturado por Docker) + archivo rotativo (`/var/log/presupuesto/app.log`, rotación diaria, retención 30 días).

Formato de log:
```json
{"ts": "2026-07-09T14:23:45.123Z", "level": "info", "service": "backend",
 "event": "request", "method": "GET", "path": "/api/v1/publico/obras",
 "status": 200, "duration_ms": 42, "usuario_id": null}
```

### 10.2 Auditoría de negocio

Se registra en `logs.auditoria` cada:
- Login exitoso / fallido
- Cambio de contraseña
- Exportación de reporte (usuario, endpoint, formato, filtros aplicados)
- Cambio de umbrales o alertas
- Publicación / cambio de estado de observación ciudadana
- Subida / eliminación de documentos y fotos
- Creación / edición / desactivación de usuarios

Las consultas GET normales NO se registran en `logs.auditoria` (solo en logs de acceso HTTP).

### 10.3 Métricas

Endpoint `/health` para chequeos:
- `GET /health` → 200 `{"status": "ok"}` sin autenticación
- `GET /health/detallado` → 200 `{postgres, redis, siga, siaf_snapshot_edad}` requiere auth admin

---

## 11. Estructura del monorepo

```
presupuesto/
├── Docs/                                  # Documentación (idea-principal, actividades)
├── backend/
│   ├── app/
│   │   ├── main.py                        # FastAPI app
│   │   ├── config.py                      # Settings (Pydantic BaseSettings)
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── publico.py
│   │   │   ├── interno.py
│   │   │   └── admin.py
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── models/                        # SQLAlchemy models (schemas auth, sistema, logs)
│   │   ├── schemas/                       # Pydantic response/request schemas
│   │   ├── jobs/
│   │   │   ├── scheduler.py               # APScheduler bootstrap
│   │   │   ├── sync_siaf.py
│   │   │   └── sync_invierte.py
│   │   ├── exportar/
│   │   │   ├── excel.py                   # openpyxl
│   │   │   └── pdf.py                     # WeasyPrint
│   │   ├── siga/
│   │   │   └── conexion.py                # pyodbc engine
│   │   └── utils/
│   ├── alembic/                           # Migraciones PostgreSQL
│   ├── tests/
│   ├── pyproject.toml                     # Poetry
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── Dockerfile
│   └── .env.example
├── nginx/
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
├── Makefile                               # comandos: make dev, make test, make build
├── .gitignore
└── README.md
```

### 11.1 Makefile (comandos comunes)

```
make dev            # Levanta stack completo en modo desarrollo con hot-reload
make backend-dev    # Solo backend con recarga
make frontend-dev   # Solo frontend con Vite
make test           # Corre tests de backend y frontend
make lint           # Ruff (backend) + ESLint (frontend)
make build          # Build de imágenes producción
make deploy         # Deploy usando compose de producción
make db-migrate     # Alembic upgrade head
make db-seed        # Carga datos iniciales (roles, umbrales default)
make backup-db      # pg_dump manual
```

---

## 12. Consideraciones de calidad

### 12.1 Testing

- **Backend:** pytest + pytest-asyncio. Cobertura mínima 70% en `services/` y `repositories/`. Tests de integración con PostgreSQL efímera (via `pytest-docker`).
- **Frontend:** Vitest + React Testing Library. Tests de componentes clave (tablas, gráficos, forms). Playwright para 3 flujos e2e críticos (login, ficha de obra, pipeline).
- **Contract tests SIGA:** un test lento que ejecuta las queries autoritativas contra una snapshot de SIGA y valida el schema de la respuesta.

### 12.2 Lint y formato

- Backend: `ruff` (lint + format) + `mypy` (strict en `services/` y `schemas/`)
- Frontend: `eslint` + `prettier` + `typescript --strict`
- Pre-commit hook con `pre-commit` framework

### 12.3 CI (para la fase de desarrollo)

Pipeline mínimo:
1. Lint
2. Tests unitarios
3. Build de imágenes Docker
4. (En rama principal) Push de imágenes a registry local o GitHub Container Registry

---

## 13. Riesgos técnicos identificados

| Riesgo | Mitigación |
|---|---|
| **API MEF caída** en la ventana nocturna | Job reintenta 3 veces; mantiene snapshot anterior si falla. Endpoint admin para trigger manual. |
| **SQL Server inaccesible** desde el contenedor | Health check `/health/detallado`. Alertas en logs si el pool no puede abrir conexiones. Documentar en runbook el procedimiento de red. |
| **Discrepancia SIGA vs SIAF** en devengado | Se documenta cuál fuente prevalece (RN-03). Vista de reconciliación en `/admin/reconciliacion` para v2. |
| **Fotos/documentos ocupando disco** | Cuota por proyecto (HU-03: 20 fotos + 10 docs máx). Alertas de disco por Prometheus (fase 2) o cron simple. |
| **Recuperación tras crash** | pg_dump diario + snapshots de volúmenes Docker semanales. Runbook de restore documentado. |
| **Cambio de esquema SIGA por parche del MEF** | Los repositorios usan queries explícitas. Test de contrato detecta cambios. Cambios requieren PR con revisión. |
| **JWT robado** | Access corto (15 min). Refresh en httpOnly cookie con `Secure` y `SameSite=Lax`. Revocación manual desde admin. |
| **Captcha bypass en observaciones** | reCAPTCHA v3 + rate limit por IP + moderación manual desde `/admin/observaciones-ciudadanas`. |

---

## 14. Trazabilidad con actividades previas

| Componente arquitectónico | Origen |
|---|---|
| Filtro `SEC_EJEC=300687` en todas las queries | [Diccionario §2](diccionario-datos-unificado.md#2-identificación-de-la-entidad) |
| Job SIAF nocturno con paginación de 8 columnas | [Diccionario §18.5](diccionario-datos-unificado.md#18-reglas-de-diseño-derivadas-del-diccionario), [Actividad 1 §4](actividad-1-exploracion-mef.md#4-comportamiento-de-la-api--limitaciones-documentadas) |
| Fuente autoritativa `SIG_TECHO_PRESUPUESTO` para saldos | [Diccionario §7.2](diccionario-datos-unificado.md#72-desde-siga-sig_techo_presupuesto), [Actividad 2 RN-03](actividad-2-requerimientos-funcionales.md#rn-03--fuentes-autoritativas) |
| Llave cruce `ANO_EJE + SEC_EJEC + SEC_FUNC` + `EXP_SIAF` | [Diccionario §17](diccionario-datos-unificado.md#17-llaves-de-cruce--resumen-consolidado) |
| Rol + centros de costo (RN-04) | [Actividad 2 §1.2](actividad-2-requerimientos-funcionales.md#12-perfiles-de-usuario), [Actividad 2 RN-04](actividad-2-requerimientos-funcionales.md#rn-04--filtro-por-centro-de-costo-operativos-y-decisores) |
| Umbrales configurables (RN-01) → `sistema.umbrales_*` | [Actividad 2 RN-01](actividad-2-requerimientos-funcionales.md#rn-01--semáforos-configurables) |
| Auditoría (RN-05) → `logs.auditoria` | [Actividad 2 RN-05](actividad-2-requerimientos-funcionales.md#rn-05--registro-en-logs-de-auditoría) |
| 18 HU Must-have cubiertas por endpoints §4.2–4.5 | [Actividad 2 §10](actividad-2-requerimientos-funcionales.md#10-resumen-de-historias-por-prioridad) |

---

## 15. Pendientes para la Actividad 4 (Diseño de UI)

Con la arquitectura definida, los siguientes puntos ingresan al alcance de la Actividad 4:

- Wireframes de baja fidelidad de las 18 HU Must-have (partiendo de los mockups textuales de la Actividad 2)
- Sistema de diseño: paleta, tipografía, componentes shadcn/ui personalizados con la identidad de la muni
- Mockups de alta fidelidad para el MVP
- Diseño responsive (mobile-first para el portal público)
- Validación con usuarios representativos

---

*Documento generado como Actividad 3 — Arquitectura Técnica · Fase de Diseño · Julio 2026. Se apoya en [idea-principal.md](idea-principal.md), [diccionario-datos-unificado.md](diccionario-datos-unificado.md) y [actividad-2-requerimientos-funcionales.md](actividad-2-requerimientos-funcionales.md).*
