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

### 3.1 Organización de schemas

| Schema | Propósito |
|---|---|
| `auth` | Usuarios, roles, sesiones, tokens |
| `siaf` | Snapshots diarios de la API SIAF e Invierte.pe |
| `sistema` | Configuración de umbrales, alertas revisadas, observaciones ciudadanas, anotaciones internas, documentos y fotos de obras |
| `logs` | Auditoría de acciones + logs de sincronización |

### 3.2 Schema `auth`

#### `auth.usuarios`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `uuid` PK | Identificador |
| `usuario` | `varchar(60)` UNIQUE | Login |
| `password_hash` | `text` | bcrypt |
| `nombre_completo` | `varchar(150)` | |
| `email` | `varchar(150)` | |
| `rol_id` | `int` FK → `auth.roles` | |
| `estado` | `varchar(10)` | `activo`, `inactivo`, `bloqueado` |
| `intentos_fallidos` | `int` DEFAULT 0 | Para bloqueo |
| `bloqueado_hasta` | `timestamptz` NULL | |
| `debe_cambiar_password` | `boolean` DEFAULT true | Primer login |
| `creado_en` | `timestamptz` DEFAULT now() | |
| `actualizado_en` | `timestamptz` | |

#### `auth.roles`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `serial` PK | |
| `codigo` | `varchar(30)` UNIQUE | `ciudadano`, `operativo`, `decisor`, `admin` |
| `nombre` | `varchar(80)` | |

#### `auth.usuarios_centros_costo`

Relación muchos-a-muchos: qué centros de costo puede ver cada usuario.

| Columna | Tipo | Descripción |
|---|---|---|
| `usuario_id` | `uuid` FK | |
| `centro_costo` | `varchar(15)` | Referencia lógica al `CENTRO_COSTO` de SIGA (no FK física porque SIGA es externo) |
| `es_raiz_jerarquia` | `boolean` | Si es `true`, el usuario ve todos los descendientes de este CC (jerarquía por `CENTRO_PADRE`) |

**Índice:** `PRIMARY KEY (usuario_id, centro_costo)`.

#### `auth.refresh_tokens`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `uuid` PK | |
| `usuario_id` | `uuid` FK | |
| `token_hash` | `text` | SHA-256 del token (no plaintext) |
| `expira_en` | `timestamptz` | |
| `revocado` | `boolean` DEFAULT false | |
| `creado_en` | `timestamptz` DEFAULT now() | |
| `user_agent` | `text` | Info del navegador |

### 3.3 Schema `siaf`

Contiene el snapshot diario de la API MEF. Se sobrescribe cada noche; para la v2 se añadirá `siaf.snapshot_historico` particionado por año.

#### `siaf.ejecucion_presupuestal`

Snapshot del resource `615644aa-ef73-4358-b4e0-0c20931632f3` filtrado por `SEC_EJEC=300687`.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | |
| `ano_eje` | `smallint` | |
| `mes_eje` | `smallint` | 0 = PIM base, 1-12 = mes de ejecución |
| `sec_ejec` | `varchar(10)` | Fijo `300687` |
| `sec_func` | `varchar(20)` | **Llave de cruce con SIGA** |
| `producto_proyecto` | `varchar(20)` | |
| `producto_proyecto_nombre` | `text` | |
| `tipo_act_proy` | `char(1)` | `2` proyecto, `3` actividad |
| `meta` | `varchar(10)` | |
| `meta_nombre` | `text` | |
| `funcion` | `varchar(4)` | |
| `funcion_nombre` | `varchar(120)` | |
| `programa_ppto` | `varchar(10)` | |
| `programa_ppto_nombre` | `text` | |
| `categoria_gasto` | `char(1)` | `5`/`6` |
| `generica` | `varchar(4)` | |
| `generica_nombre` | `varchar(120)` | |
| `subgenerica` | `varchar(4)` | |
| `especifica` | `varchar(4)` | |
| `especifica_det` | `varchar(4)` | |
| `fuente_financiamiento` | `varchar(4)` | |
| `fuente_financiamiento_nombre` | `varchar(120)` | |
| `rubro` | `varchar(4)` | |
| `monto_pia` | `numeric(18,2)` | Viene en 0 en la API — usar SIGA como fuente real |
| `monto_pim` | `numeric(18,2)` | |
| `monto_certificado` | `numeric(18,2)` | |
| `monto_comprometido_anual` | `numeric(18,2)` | |
| `monto_comprometido` | `numeric(18,2)` | |
| `monto_devengado` | `numeric(18,2)` | |
| `monto_girado` | `numeric(18,2)` | |
| `sincronizado_en` | `timestamptz` DEFAULT now() | |

**Índices:**
- `(ano_eje, mes_eje, sec_func)` — consultas del dashboard
- `(ano_eje, producto_proyecto)` — cruce con Invierte.pe
- `(ano_eje, mes_eje, funcion)` — agregaciones por función
- `(ano_eje, mes_eje, fuente_financiamiento)` — agregaciones por fuente

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
| `sincronizado_en` | `timestamptz` DEFAULT now() | |

**Índices:**
- `codigo_unico` UNIQUE
- `(latitud, longitud)` para el mapa
- `des_tipologia`, `funcion` para filtros

### 3.4 Schema `sistema`

#### `sistema.umbrales_semaforos`

Configuración de umbrales de semáforos por módulo. Los defaults se cargan por migración.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `serial` PK | |
| `modulo` | `varchar(50)` | `portal_obras`, `saldos`, `metas`, `pipeline`, etc. |
| `metrica` | `varchar(50)` | `avance_fisico`, `avance_financiero`, `saldo_disponible`, ... |
| `umbral_verde` | `numeric(6,2)` | |
| `umbral_amarillo` | `numeric(6,2)` | |
| `direccion` | `char(4)` | `mayor` (más = mejor) o `menor` |
| `actualizado_por` | `uuid` FK → `auth.usuarios` | |
| `actualizado_en` | `timestamptz` | |

**Unique:** `(modulo, metrica)`.

#### `sistema.umbrales_alertas`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `serial` PK | |
| `codigo_alerta` | `varchar(50)` UNIQUE | `pedido_estancado`, `contrato_por_vencer`, `meta_baja_ejecucion` |
| `parametros` | `jsonb` | Ej: `{"dias": 15}` o `{"dias": 30}` o `{"pct_q3": 50, "pct_q4": 90}` |
| `actualizado_por` | `uuid` FK | |
| `actualizado_en` | `timestamptz` | |

#### `sistema.alertas_revisadas`

Persistencia de alertas marcadas por el usuario como revisadas.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | |
| `usuario_id` | `uuid` FK | |
| `codigo_alerta` | `varchar(50)` | |
| `entidad_tipo` | `varchar(30)` | `pedido`, `contrato`, `meta` |
| `entidad_id` | `varchar(50)` | Identificador en SIGA (`NRO_PEDIDO`, `NRO_CONTRATO`, `SEC_FUNC`) |
| `revisado_en` | `timestamptz` DEFAULT now() | |
| `comentario` | `text` NULL | |

#### `sistema.anotaciones_internas`

Notas que los funcionarios agregan a un pedido, orden, meta u obra. No tocan SIGA/SIAF.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | |
| `entidad_tipo` | `varchar(30)` | `pedido`, `orden`, `meta`, `obra`, `contrato` |
| `entidad_id` | `varchar(50)` | |
| `usuario_id` | `uuid` FK | |
| `texto` | `text` | |
| `creado_en` | `timestamptz` DEFAULT now() | |

#### `sistema.observaciones_ciudadanas`

Buzón público de la ficha de obra.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | |
| `codigo_unico_obra` | `varchar(20)` | Referencia a Invierte.pe |
| `nombre_ciudadano` | `varchar(150)` NULL | |
| `email_ciudadano` | `varchar(150)` NULL | |
| `texto` | `text` | |
| `estado` | `varchar(20)` DEFAULT `pendiente` | `pendiente`, `leida`, `respondida`, `spam` |
| `revisado_por` | `uuid` FK NULL | |
| `revisado_en` | `timestamptz` NULL | |
| `respuesta_interna` | `text` NULL | |
| `ip_origen` | `inet` | Para detectar abuso |
| `captcha_score` | `numeric(3,2)` NULL | Score de reCAPTCHA v3 |
| `creado_en` | `timestamptz` DEFAULT now() | |

#### `sistema.documentos_obra`

Archivos subidos por funcionarios asociados a una obra.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | |
| `codigo_unico_obra` | `varchar(20)` | |
| `tipo` | `varchar(30)` | `foto`, `expediente_tecnico`, `contrato`, `f8`, `f9`, `otro` |
| `nombre_original` | `varchar(255)` | |
| `ruta_relativa` | `varchar(500)` | Bajo `/var/data/uploads/obras/{codigo}/...` |
| `mime_type` | `varchar(80)` | |
| `tamano_bytes` | `int` | |
| `subido_por` | `uuid` FK | |
| `subido_en` | `timestamptz` DEFAULT now() | |
| `publicado` | `boolean` DEFAULT true | Permite despublicar sin borrar |

**Índice:** `(codigo_unico_obra, tipo)`.

### 3.5 Schema `logs`

#### `logs.auditoria`

Auditoría de acciones de negocio.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | |
| `usuario_id` | `uuid` FK NULL | NULL para acciones públicas |
| `accion` | `varchar(50)` | `login_exitoso`, `login_fallido`, `exportacion`, `cambio_umbral`, `subida_documento`, `publicacion_observacion`, ... |
| `detalle` | `jsonb` | Payload variable |
| `ip` | `inet` | |
| `user_agent` | `text` | |
| `creado_en` | `timestamptz` DEFAULT now() | |

**Índices:**
- `(usuario_id, creado_en DESC)`
- `(accion, creado_en DESC)`

#### `logs.sincronizacion`

Estado de los jobs de sincronización.

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | `bigserial` PK | |
| `job` | `varchar(50)` | `siaf_ejecucion`, `siaf_inversiones` |
| `inicio` | `timestamptz` | |
| `fin` | `timestamptz` NULL | |
| `estado` | `varchar(20)` | `en_curso`, `exito`, `error` |
| `registros_procesados` | `int` | |
| `error_mensaje` | `text` NULL | |

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
