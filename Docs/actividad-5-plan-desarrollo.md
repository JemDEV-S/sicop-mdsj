# Actividad 5 — Plan de Desarrollo

> Municipalidad Distrital de San Jerónimo — Cusco
> Entregable formal de la Actividad 5 · Fase de Diseño
> Descomposición en tareas por capas, con citas puntuales a docs para optimizar tokens del agente.
> Julio 2026

---

## 1. Cómo usar este plan

**Estrategia de tokens:**
- Cada tarea cita **solo las secciones .md específicas** que necesita.
- Nunca leer un doc completo — usar `Read` con `offset`/`limit` para leer la sección citada.
- `CLAUDE.md` en la raíz del proyecto se carga siempre y contiene lo esencial (stack, reglas, datos fijos).

**Formato de tarea:**
```
T-XX · Título corto              [prioridad MoSCoW · capa]
Descripción: qué hacer y por qué.
Consultar: doc.md §N (título de la sección) — solo si aplica
Archivos: rutas de archivos a crear/editar
Done cuando: criterios verificables
Depende de: T-YY, T-ZZ
```

**Convenciones:**
- ID `T-XX` (`T-01`, `T-02`, ...) se usa en commits: `T-14: agregar endpoint /publico/obras`.
- Trunk-based: commits directos a `main`, sin feature branches.
- Cada tarea completada = un commit descriptivo.
- Smoke test manual tras cada tarea antes de pasar a la siguiente.

**Orden global (por capas):**

```
FASE 1 · Infraestructura        [T-01 → T-05]
FASE 2 · Fundaciones backend    [T-06 → T-11]
FASE 3 · Backend por dominio    [T-12 → T-30]
FASE 4 · Fundaciones frontend   [T-31 → T-36]
FASE 5 · Frontend por dominio   [T-37 → T-55]
FASE 6 · Integración y cierre   [T-56 → T-62]
```

---

## FASE 1 · Infraestructura (5 tareas)

### T-01 · Inicializar monorepo y estructura de carpetas
**M · infra**

Descripción: Crear la estructura de carpetas del monorepo, `.gitignore`, `README.md` inicial, inicializar git.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §11 (estructura del monorepo).

Archivos a crear:
- `.gitignore` (Python, Node, IDE, Docker)
- `README.md` (breve)
- `Makefile` (comandos base)
- `backend/`, `frontend/`, `nginx/` (carpetas vacías con `.gitkeep`)

Done cuando: `git init` hecho, `git status` muestra la estructura, primer commit `T-01: init monorepo`.

Depende de: —

---

### T-02 · Docker Compose de desarrollo
**M · infra**

Descripción: Definir `docker-compose.yml` con servicios `postgres`, `redis`, y placeholder para backend/frontend. Sin backend/frontend aún (se agregan cuando existan).

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §9.1-9.2 (Docker Compose + env vars).

Archivos a crear:
- `docker-compose.yml`
- `docker-compose.dev.yml`
- `.env.example`

Done cuando: `docker compose up postgres redis` levanta ambos servicios; `docker compose ps` los muestra saludables.

Depende de: T-01.

---

### T-03 · Setup PostgreSQL con Alembic
**M · infra**

Descripción: Inicializar proyecto Python (poetry), configurar SQLAlchemy engine, inicializar Alembic contra PostgreSQL local.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §11 (estructura backend) y §9.2 (vars POSTGRES_*).

Archivos:
- `backend/pyproject.toml` con deps: fastapi, uvicorn, sqlalchemy, alembic, psycopg2-binary, pydantic-settings
- `backend/app/config.py` (Settings via pydantic-settings)
- `backend/app/database.py` (engine + SessionLocal)
- `backend/alembic.ini`, `backend/alembic/env.py`
- `backend/.env.example`

Done cuando: `alembic current` corre sin error contra la BD del compose.

Depende de: T-02.

---

### T-04 · Restaurar backup SIGA en SQL Server local
**M · infra**

Descripción: Levantar contenedor SQL Server, restaurar el backup SIGA_300687 provisto por la muni. Crear usuario `lector_presupuesto` con `db_datareader`.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §9.2 (vars SIGA_*).

Archivos:
- `docker-compose.dev.yml` — añadir servicio `sqlserver`
- `scripts/restore-siga.sh` (o `.ps1`) — comando de restore
- `scripts/create-lector-user.sql`

Done cuando: `SELECT COUNT(*) FROM META WHERE ano_eje=2025 AND sec_ejec=300687` devuelve ~741 filas. Usuario `lector_presupuesto` puede hacer SELECT.

Depende de: T-02.

Nota: si el backup aún no está disponible, dejar el contenedor SQL Server listo con placeholders y marcar la tarea como "esperando backup".

---

### T-05 · Conectividad backend → SIGA
**M · infra**

Descripción: Instalar `pyodbc` en la imagen backend, verificar que se conecta al SQL Server dockerizado y ejecuta una query simple.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §5.1 (adaptador SIGA).

Archivos:
- `backend/app/siga/conexion.py` — factory de conexión pyodbc
- `backend/app/siga/__init__.py`
- `backend/scripts/ping-siga.py` — script CLI que ejecuta `SELECT TOP 1 * FROM META`

Done cuando: `python -m backend.scripts.ping-siga` imprime 1 fila de `META`.

Depende de: T-03, T-04.

---

## FASE 2 · Fundaciones backend (6 tareas)

### T-06 · Migración inicial de schemas PostgreSQL
**M · backend**

Descripción: Crear los 4 schemas (`auth`, `siaf`, `sistema`, `logs`) y todas las tablas del modelo con Alembic.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §3 completa (modelo de datos).

Archivos:
- `backend/app/models/auth.py` (Usuario, Rol, UsuarioCentroCosto, RefreshToken)
- `backend/app/models/siaf.py` (EjecucionPresupuestal, Inversion)
- `backend/app/models/sistema.py` (UmbralSemaforo, UmbralAlerta, AlertaRevisada, AnotacionInterna, ObservacionCiudadana, DocumentoObra)
- `backend/app/models/logs.py` (Auditoria, Sincronizacion)
- `backend/alembic/versions/0001_initial.py` — autogenerado + revisado
- Semilla: `backend/alembic/versions/0002_seed_roles_umbrales.py` — inserta roles (ciudadano, operativo, decisor, admin) y umbrales default

Done cuando: `alembic upgrade head` crea todo. `\dn` en psql muestra los 4 schemas.

Depende de: T-03.

---

### T-07 · Bootstrap FastAPI + health check
**M · backend**

Descripción: Crear `app.main` con FastAPI, endpoint `/health` y `/health/detallado`, CORS configurado.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §10.3 (métricas) y §4.7 (CORS).

Archivos:
- `backend/app/main.py`
- `backend/app/routers/health.py`
- `backend/Dockerfile`

Done cuando: `uvicorn app.main:app` levanta. `curl localhost:8000/health` → 200. Swagger en `/api/v1/docs`.

Depende de: T-03.

---

### T-08 · Auth: login, refresh, JWT, bcrypt
**M · backend**

Descripción: Implementar los endpoints `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`, `/auth/cambiar-password`. JWT con `python-jose`, hash con `passlib[bcrypt]`. Cookie httpOnly para refresh.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §7 (auth JWT) y `Docs/actividad-2-requerimientos-funcionales.md` §5 HU-08 (criterios).

Archivos:
- `backend/app/routers/auth.py`
- `backend/app/services/auth_service.py`
- `backend/app/security/jwt.py`
- `backend/app/security/passwords.py`
- `backend/app/schemas/auth.py` (LoginRequest, TokenResponse, MeResponse)
- Tests: `backend/tests/test_auth.py` — login exitoso, login fallido, bloqueo tras 5 intentos, refresh, logout

Done cuando: Los tests pasan. Puedes hacer login con un usuario semilla (Admin) creado por seed.

Depende de: T-06, T-07.

---

### T-09 · Middleware de autorización + filtro por CC
**M · backend**

Descripción: Dependency `get_current_user` que valida JWT y expone rol + centros de costo permitidos. Helper `get_centros_permitidos(user)` que resuelve la jerarquía para decisores consultando `SIG_CENTRO_COSTO` recursivamente.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §4.6 (autorización) y `Docs/actividad-2-requerimientos-funcionales.md` §2 RN-04.

Archivos:
- `backend/app/security/deps.py` (get_current_user, require_role)
- `backend/app/services/permisos_service.py` (resuelve jerarquía CC)
- Tests: `backend/tests/test_permisos.py` — Operativo ve solo sus CC; Decisor ve descendientes; Admin ve todo

Done cuando: Test unitario pasa con fixtures. Endpoint dummy protegido responde 401 sin token, 200 con token válido.

Depende de: T-08.

---

### T-10 · Logs de auditoría (utilidad transversal)
**M · backend**

Descripción: Helper `log_auditoria(accion, detalle, request)` que inserta en `logs.auditoria`. Integrar con dependency que capture IP y user-agent.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §10.2 y `Docs/actividad-2-requerimientos-funcionales.md` §2 RN-05.

Archivos:
- `backend/app/services/auditoria_service.py`
- Integración en `backend/app/routers/auth.py` (login exitoso/fallido)

Done cuando: Un login exitoso inserta fila en `logs.auditoria` con IP y user-agent correctos.

Depende de: T-06, T-08.

---

### T-11 · Configuración logging estructurado (structlog)
**S · backend**

Descripción: Configurar `structlog` con salida JSON a stdout + archivo rotativo. Middleware que registra cada request con duración.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §10.1 (logs estructurados).

Archivos:
- `backend/app/logging_config.py`
- `backend/app/middleware/request_logging.py`

Done cuando: Cada request emite un log JSON en stdout con `method, path, status, duration_ms`.

Depende de: T-07.

---

## FASE 3 · Backend por dominio (19 tareas)

### T-12 · Job sincronización SIAF ejecución
**M · backend**

Descripción: Job `sync_siaf_ejecucion` que consume `datastore_search_sql` de la API MEF, pagina, guarda en staging y hace swap atómico a `siaf.ejecucion_presupuestal`.

Consultar:
- `Docs/actividad-3-arquitectura-tecnica.md` §6 (sync SIAF)
- `Docs/actividad-1-exploracion-mef.md` §4 (limitaciones API) y §10 (queries validadas)

Archivos:
- `backend/app/jobs/sync_siaf.py`
- `backend/app/services/mef_client.py` (cliente HTTP con reintentos)
- Tests: `backend/tests/test_sync_siaf.py` — mock de API con respuestas realistas

Done cuando: Ejecutar manualmente `python -m backend.jobs.sync_siaf` puebla `siaf.ejecucion_presupuestal` con datos reales. Registra en `logs.sincronizacion`.

Depende de: T-06.

---

### T-13 · Job sincronización Invierte.pe
**M · backend**

Descripción: Análogo a T-12 pero para el resource `f9cc4ba0`.

Consultar:
- `Docs/actividad-3-arquitectura-tecnica.md` §6.2
- `Docs/actividad-1-exploracion-mef.md` §12 (Invierte.pe)

Archivos:
- `backend/app/jobs/sync_invierte.py`
- Tests: `backend/tests/test_sync_invierte.py`

Done cuando: `siaf.inversiones` tiene los ~70 proyectos de San Jerónimo tras ejecutar el job.

Depende de: T-06, T-12.

---

### T-14 · APScheduler bootstrap
**M · backend**

Descripción: Configurar APScheduler embebido para ejecutar `sync_siaf` y `sync_invierte` diariamente a las 03:00. Endpoint `/admin/jobs/sincronizar-siaf` para trigger manual.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §6.3 (trigger manual) y §11 (jobs/scheduler.py).

Archivos:
- `backend/app/jobs/scheduler.py`
- `backend/app/routers/admin_jobs.py`

Done cuando: Al arrancar el server, el scheduler queda activo. Endpoint manual dispara el job y devuelve `job_id`.

Depende de: T-12, T-13.

---

### T-15 · Repositorio SIGA: metas y centros de costo
**M · backend**

Descripción: Queries SQL crudas para `META`, `SIG_CENTRO_COSTO`, `SIG_METAS_X_CENTRO`. Métodos: `listar_metas`, `obtener_meta`, `listar_centros_costo`, `obtener_jerarquia_cc`.

Consultar:
- `Docs/datos-iniciales-siga.md` §5 (relacional metas)
- `Docs/diccionario-datos-unificado.md` §4 (META) y §9 (centros de costo)

Archivos:
- `backend/app/repositories/metas_repo.py`
- `backend/app/repositories/centros_costo_repo.py`
- Tests: `backend/tests/test_metas_repo.py` (contra SIGA local)

Done cuando: Métodos devuelven datos reales. Test valida que la meta 00121 existe para 2025.

Depende de: T-05.

---

### T-16 · Repositorio SIGA: saldos presupuestales
**M · backend**

Descripción: Query autoritativa contra `SIG_TECHO_PRESUPUESTO` con JOIN a `META`. Filtro por CC del usuario.

Consultar:
- `Docs/actividad-3-arquitectura-tecnica.md` §5.3 (query saldos)
- `Docs/diccionario-datos-unificado.md` §7.2

Archivos:
- `backend/app/repositories/saldos_repo.py`
- Tests: `backend/tests/test_saldos_repo.py`

Done cuando: Método `listar_saldos(ano, centros)` devuelve filas con PIM > 0 correctamente filtradas.

Depende de: T-15.

---

### T-17 · Endpoints saldos (HU-15, HU-16)
**M · backend**

Descripción: Implementar `/interno/saldos` y `/interno/saldos/metas-rezagadas`. Aplicar filtro por CC vía `get_centros_permitidos`.

Consultar:
- `Docs/actividad-3-arquitectura-tecnica.md` §4.4 (endpoints saldos)
- `Docs/actividad-2-requerimientos-funcionales.md` §7 HU-15 y HU-16

Archivos:
- `backend/app/routers/saldos.py`
- `backend/app/schemas/saldos.py`
- `backend/app/services/saldos_service.py` (aplica semáforo con umbrales de BD)

Done cuando: `GET /api/v1/interno/saldos?ano=2025` con token de Admin devuelve JSON válido con semáforos.

Depende de: T-09, T-16.

---

### T-18 · Repositorio SIGA: pedidos, órdenes, pipeline
**M · backend**

Descripción: Queries para `SIG_PEDIDOS`, `SIG_DETALLE_PEDIDOS`, `SIG_ORDEN_ADQUISICION`, `SIG_ORDEN_PRESUPUESTO`. Método principal: `pipeline_kanban(ano, centros)` que devuelve pedidos agrupados por etapa (según §10.9 del diccionario).

Consultar:
- `Docs/datos-iniciales-siga.md` §12 (cadena logística) y §13.1 (pipeline)
- `Docs/diccionario-datos-unificado.md` §10 (cadena logística) y §10.9 (detección de etapas)

Archivos:
- `backend/app/repositories/pipeline_repo.py`
- Tests: `backend/tests/test_pipeline_repo.py`

Done cuando: Query devuelve 5 buckets (solicitado, con orden, conformidad, devengado, cerrado) con conteos coherentes.

Depende de: T-15.

---

### T-19 · Endpoints pipeline (HU-09, HU-10)
**M · backend**

Descripción: `/interno/pipeline/kanban`, `/interno/pedidos`, `/interno/pedidos/{nro}/{tipo}`. Detección de "estancado" (RN-02) según umbrales.

Consultar:
- `Docs/actividad-3-arquitectura-tecnica.md` §4.4 (pipeline)
- `Docs/actividad-2-requerimientos-funcionales.md` §5 HU-09, HU-10, HU-11
- `Docs/actividad-2-requerimientos-funcionales.md` §2 RN-02

Archivos:
- `backend/app/routers/pipeline.py`
- `backend/app/services/pipeline_service.py`
- `backend/app/schemas/pipeline.py`

Done cuando: Endpoint responde con estructura de kanban. Al menos un pedido marcado como estancado si supera el umbral.

Depende de: T-09, T-18.

---

### T-20 · Anotaciones internas (HU-10)
**S · backend**

Descripción: POST/GET/DELETE de anotaciones en `sistema.anotaciones_internas`.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §5 HU-10 (AC-10.4).

Archivos:
- `backend/app/routers/anotaciones.py`
- `backend/app/schemas/anotaciones.py`

Done cuando: Puedes anotar un pedido y verlo en la respuesta del detalle.

Depende de: T-09.

---

### T-21 · Repositorio SIGA: cruce SIAF-SIGA
**M · backend**

Descripción: Queries que resuelven la cadena `EXP_SIAF ↔ orden ↔ pedido ↔ meta` y viceversa. Método `buscar_por_exp_siaf(exp)`, `consolidado_por_meta(sec_func)`.

Consultar:
- `Docs/diccionario-datos-unificado.md` §17 (llaves de cruce) y §10.3 (SIG_ORDEN_ADQUISICION + SIG_ORDEN_PRESUPUESTO)
- `Docs/datos-iniciales-siga.md` §12.3 (validación cruce) y §12.6 (queries)

Archivos:
- `backend/app/repositories/cruce_repo.py`
- Tests: `backend/tests/test_cruce_repo.py`

Done cuando: Buscar un `EXP_SIAF` real de 2025 devuelve meta + orden + pedido + conformidad correctamente.

Depende de: T-15, T-18.

---

### T-22 · Endpoints cruce (HU-12, HU-13, HU-14)
**M · backend**

Descripción: `/interno/cruce/expediente-siaf/{exp}`, `/interno/cruce/meta/{sec_func}`, `/interno/cruce/meta/{sec_func}/{recurso}`.

Consultar:
- `Docs/actividad-3-arquitectura-tecnica.md` §4.4 (cruce)
- `Docs/actividad-2-requerimientos-funcionales.md` §6 HU-12 a HU-14

Archivos:
- `backend/app/routers/cruce.py`
- `backend/app/services/cruce_service.py` (mezcla datos SIAF snapshot + SIGA en vivo)
- `backend/app/schemas/cruce.py`

Done cuando: Buscar por expediente y por meta responde con datos consolidados.

Depende de: T-21.

---

### T-23 · Repositorio SIGA: proveedores y contratos
**M · backend**

Descripción: Queries para `SIG_CONTRATISTAS` y `SIG_CONTRATOS`. Métodos: `listar_proveedores`, `obtener_proveedor(ruc)`, `ordenes_por_proveedor`, `contratos_por_vencer(dias)`.

Consultar:
- `Docs/diccionario-datos-unificado.md` §11 (proveedores) y §12 (contratos)
- `Docs/datos-iniciales-siga.md` §13.3 y §13.4

Archivos:
- `backend/app/repositories/proveedores_repo.py`
- `backend/app/repositories/contratos_repo.py`

Done cuando: Listado devuelve 2,645 proveedores. Contratos por vencer con umbral 30 días devuelve subset esperado.

Depende de: T-15.

---

### T-24 · Endpoints proveedores y contratos (HU-07, HU-19, HU-20)
**M · backend**

Descripción: `/publico/proveedores`, `/interno/proveedores/{ruc}`, `/interno/contratos`, `/interno/alertas/contratos-por-vencer`.

Consultar:
- `Docs/actividad-3-arquitectura-tecnica.md` §4.2 y §4.4
- `Docs/actividad-2-requerimientos-funcionales.md` §4 HU-07 · §9 HU-19, HU-20

Archivos:
- `backend/app/routers/proveedores.py`
- `backend/app/routers/contratos.py`

Done cuando: Endpoint público devuelve directorio sin exponer email/teléfono; endpoint interno sí los expone.

Depende de: T-09, T-23.

---

### T-25 · Repositorio SIAF: obras (usando snapshot)
**M · backend**

Descripción: Queries contra `siaf.ejecucion_presupuestal` y `siaf.inversiones` (PostgreSQL) para el portal de obras. Método: `listar_obras(filtros)`, `obtener_obra(codigo_unico)`, `obras_para_mapa()`.

Consultar:
- `Docs/diccionario-datos-unificado.md` §8 (Invierte.pe) y §18.8 (categorización de metas)
- `Docs/actividad-1-exploracion-mef.md` §12 (dataset Invierte.pe)

Archivos:
- `backend/app/repositories/obras_repo.py`

Done cuando: Devuelve 70 proyectos activos con datos combinados de ambos snapshots.

Depende de: T-06, T-12, T-13.

---

### T-26 · Endpoints obras (HU-01, HU-02, HU-04)
**M · backend**

Descripción: `/publico/obras`, `/publico/obras/{codigo}`, `/publico/obras/mapa`. Combina snapshot SIAF + SIGA live (para contratos y proveedores del proyecto).

Consultar:
- `Docs/actividad-3-arquitectura-tecnica.md` §4.2 (endpoints públicos)
- `Docs/actividad-2-requerimientos-funcionales.md` §3 HU-01 a HU-04

Archivos:
- `backend/app/routers/obras.py`
- `backend/app/services/obras_service.py`
- `backend/app/schemas/obras.py`

Done cuando: Listado devuelve 70 fichas con avance físico y semáforo. Endpoint mapa devuelve solo lo necesario (código, lat, lng, avance).

Depende de: T-25, T-15.

---

### T-27 · Endpoints dashboard público (HU-05, HU-06)
**M · backend**

Descripción: `/publico/ejecucion/resumen`, `/publico/ejecucion/por-funcion`, `/publico/ejecucion/por-fuente`, `/publico/ejecucion/mensual`, `/publico/ejecucion/detalle`.

Consultar:
- `Docs/actividad-3-arquitectura-tecnica.md` §4.2
- `Docs/actividad-2-requerimientos-funcionales.md` §4 HU-05, HU-06

Archivos:
- `backend/app/routers/ejecucion_publico.py`
- `backend/app/services/ejecucion_service.py`

Done cuando: KPIs suman PIM/Certificado/Devengado del año; agregado por función coincide con SIGA cuando se cruza.

Depende de: T-25.

---

### T-28 · Documentos y fotos de obras (HU-02, HU-03)
**S · backend**

Descripción: Subida y descarga de archivos. Almacenamiento en `/var/data/uploads/obras/{codigo}/{tipo}/`. Metadata en `sistema.documentos_obra`.

Consultar:
- `Docs/actividad-3-arquitectura-tecnica.md` §3.4 (tabla documentos_obra) y §9.2 (UPLOAD_*)
- `Docs/actividad-2-requerimientos-funcionales.md` §3 HU-03

Archivos:
- `backend/app/routers/obras_documentos.py`
- `backend/app/services/uploads_service.py`

Done cuando: Puedes subir una foto JPG y descargarla desde `/media/uploads/obras/{codigo}/foto/...`.

Depende de: T-09, T-26.

---

### T-29 · Buzón de observaciones ciudadanas (HU-24)
**C · backend**

Descripción: `POST /publico/obras/{codigo}/observaciones` con captcha. GET/PATCH admin.

Consultar:
- `Docs/actividad-3-arquitectura-tecnica.md` §3.4 (observaciones_ciudadanas) y §4.7 (rate limit)
- `Docs/actividad-2-requerimientos-funcionales.md` §9 HU-24

Archivos:
- `backend/app/routers/observaciones.py`
- `backend/app/services/recaptcha_service.py`

Done cuando: POST con captcha válido crea fila con estado `pendiente`. Rate limit efectivo (5/hora por IP).

Depende de: T-06, T-26.

---

### T-30 · Exportación Excel + PDF (HU-21)
**M · backend**

Descripción: Endpoints genéricos `/interno/exportar/excel` y `/interno/exportar/pdf`. Reciben `{tipo_reporte, filtros}`. Devuelven binario o `job_id` si >10K filas.

Consultar:
- `Docs/actividad-3-arquitectura-tecnica.md` §1 (openpyxl + WeasyPrint) y §4.4 (exportación)
- `Docs/actividad-2-requerimientos-funcionales.md` §9 HU-21

Archivos:
- `backend/app/routers/exportar.py`
- `backend/app/exportar/excel.py` (usa openpyxl)
- `backend/app/exportar/pdf.py` (usa WeasyPrint + Jinja templates)
- `backend/app/exportar/templates/*.html`

Done cuando: Exportar saldos a Excel genera archivo válido. Exportar la misma vista a PDF con logo y encabezado funciona.

Depende de: T-17 (saldos como primer caso de uso).

---

## FASE 4 · Fundaciones frontend (6 tareas)

### T-31 · Bootstrap React + Vite + Tailwind + shadcn
**M · frontend**

Descripción: Inicializar proyecto React con Vite, TypeScript strict, Tailwind CSS, shadcn/ui CLI, estructura de carpetas.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §8 (arquitectura frontend).

Archivos:
- `frontend/package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.ts`
- `frontend/src/main.tsx`, `App.tsx`, `styles/globals.css`
- Componentes shadcn iniciales: Button, Card, Table, Input, Dialog

Done cuando: `npm run dev` levanta en localhost:5173 con una página home básica.

Depende de: T-01.

---

### T-32 · Cliente API con axios + interceptor de auth
**M · frontend**

Descripción: Cliente HTTP centralizado con interceptores para: agregar `Authorization: Bearer`, refresh automático en 401, manejo de errores unificado.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §7.1 (flujo JWT) y §8.1 (lib/api-client.ts).

Archivos:
- `frontend/src/lib/api-client.ts`
- `frontend/src/lib/api-errors.ts`

Done cuando: Llamar a `apiClient.get('/api/v1/health')` funciona. Manejo de 401 dispara refresh.

Depende de: T-31.

---

### T-33 · Router + protección de rutas
**M · frontend**

Descripción: React Router v6 con rutas públicas, internas (require auth), admin (require role). Layouts diferenciados por audiencia.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §8.2 (enrutamiento).

Archivos:
- `frontend/src/app/router.tsx`
- `frontend/src/app/layouts/PublicLayout.tsx`
- `frontend/src/app/layouts/InternoLayout.tsx`
- `frontend/src/features/auth/RequireAuth.tsx`

Done cuando: `/` carga público, `/panel/*` redirige a `/login` sin sesión, `/admin/*` requiere rol admin.

Depende de: T-32.

---

### T-34 · Store de autenticación (Zustand) + Login page
**M · frontend**

Descripción: Zustand store con `accessToken`, `user`, `login()`, `logout()`. Página de login funcional.

Consultar:
- `Docs/actividad-3-arquitectura-tecnica.md` §8.1 (store)
- `Docs/actividad-2-requerimientos-funcionales.md` §5 HU-08 (mockup login)

Archivos:
- `frontend/src/store/auth.ts`
- `frontend/src/pages/Login.tsx`
- `frontend/src/features/auth/useAuth.ts`

Done cuando: Login con usuario semilla funciona. Tras login, redirige al dashboard interno.

Depende de: T-33, T-08 (backend auth listo).

---

### T-35 · TanStack Query provider + hooks base
**M · frontend**

Descripción: Configurar QueryClient con defaults sensatos (staleTime, retry). Hooks reutilizables por dominio.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §8.3 (TanStack Query).

Archivos:
- `frontend/src/lib/query-client.ts`
- `frontend/src/features/*/hooks.ts` (uno por dominio, se irán llenando)

Done cuando: `useQuery` con `apiClient` funciona en una página de prueba.

Depende de: T-32.

---

### T-36 · Componentes reutilizables base
**M · frontend**

Descripción: DataTable con orden/filtro/paginación, Semaforo (badge con color según valor + umbrales), FormatoDinero, FormatoFecha, WrapperGrafico (Recharts), WrapperMapa (Leaflet).

Consultar:
- `Docs/actividad-3-arquitectura-tecnica.md` §8.1 (components/)
- `Docs/actividad-2-requerimientos-funcionales.md` §2 RN-01 (semáforos)

Archivos:
- `frontend/src/components/tabla/DataTable.tsx`
- `frontend/src/components/Semaforo.tsx`
- `frontend/src/lib/formatters.ts`, `semaforo.ts`
- `frontend/src/components/grafico/`, `mapa/`

Done cuando: Story de cada componente funciona en una página de sandbox.

Depende de: T-31.

---

## FASE 5 · Frontend por dominio (19 tareas)

### T-37 · Home público
**M · frontend** · HU: navegación general

Descripción: Landing con enlaces a Obras, Ejecución, Proveedores, Mapa.

Consultar: `Docs/idea-principal.md` §6.1 (portal público).

Archivos:
- `frontend/src/pages/publico/Home.tsx`

Done cuando: Carga sin errores y links funcionan.

Depende de: T-33.

---

### T-38 · Portal de obras — listado (HU-01)
**M · frontend**

Descripción: Grid de tarjetas con filtros. Cada tarjeta enlaza a la ficha.

Consultar:
- `Docs/actividad-2-requerimientos-funcionales.md` §3 HU-01 (mockup)

Archivos:
- `frontend/src/pages/publico/Obras.tsx`
- `frontend/src/features/obras/hooks.ts` (useObras)
- `frontend/src/features/obras/ObraCard.tsx`

Done cuando: Muestra 70 obras con paginación, filtros funcionan, tarjetas se ven según mockup.

Depende de: T-36, T-26 (endpoint listo).

---

### T-39 · Portal de obras — ficha detallada (HU-02)
**M · frontend**

Descripción: Página con secciones: identificación, avance, presupuesto, contratista, cronograma, ubicación, documentos, fotos.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §3 HU-02 (mockup completo).

Archivos:
- `frontend/src/pages/publico/Obra.tsx`
- `frontend/src/features/obras/secciones/*.tsx`

Done cuando: Ficha carga con datos reales, mini-mapa muestra la ubicación.

Depende de: T-38, T-28.

---

### T-40 · Mapa de obras (HU-04)
**M · frontend**

Descripción: Mapa Leaflet centrado en San Jerónimo con marcadores coloreados por semáforo, popup con datos clave, filtros.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §3 HU-04 (mockup).

Archivos:
- `frontend/src/pages/publico/Mapa.tsx`
- `frontend/src/features/obras/MapaObras.tsx`

Done cuando: Se ven 58 marcadores (proyectos con coords), listado aparte para los sin coords. Filtros aplican.

Depende de: T-36, T-38.

---

### T-41 · Dashboard público de ejecución (HU-05)
**M · frontend**

Descripción: KPIs superiores, gráfico barras por función, dona por fuente, línea mensual.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §4 HU-05 (mockup).

Archivos:
- `frontend/src/pages/publico/Ejecucion.tsx`
- `frontend/src/features/ejecucion/hooks.ts`
- `frontend/src/features/ejecucion/*.tsx` (KPIs, GraficoFuncion, etc.)

Done cuando: Dashboard muestra cifras coherentes con SIAF real.

Depende de: T-36, T-27.

---

### T-42 · Tabla detallada de ejecución (HU-06)
**M · frontend**

Descripción: DataTable con filtros, orden, paginación. Botón de exportar (llamando a T-30).

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §4 HU-06.

Archivos:
- `frontend/src/pages/publico/EjecucionDetalle.tsx`

Done cuando: Tabla muestra 741 metas con filtros. Export a Excel funciona.

Depende de: T-36, T-27, T-30.

---

### T-43 · Directorio público de proveedores (HU-07)
**S · frontend**

Descripción: DataTable con buscador. Sin datos de contacto.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §4 HU-07.

Archivos:
- `frontend/src/pages/publico/Proveedores.tsx`

Done cuando: Lista los ~2,645 proveedores con montos acumulados.

Depende de: T-36, T-24.

---

### T-44 · Dashboard interno de bienvenida (HU-22)
**M · frontend**

Descripción: Widgets de alertas + KPIs de saldo de la unidad + últimos pedidos.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §9 HU-22 (mockup).

Archivos:
- `frontend/src/pages/interno/Dashboard.tsx`
- `frontend/src/features/dashboard/widgets/*.tsx`

Done cuando: Al hacer login, dashboard carga con datos del usuario.

Depende de: T-34, T-17, T-19, T-24.

---

### T-45 · Pipeline kanban (HU-09)
**M · frontend**

Descripción: 5 columnas con tarjetas de pedido, filtros, indicador de estancado.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §5 HU-09 (mockup).

Archivos:
- `frontend/src/pages/interno/Pipeline.tsx`
- `frontend/src/features/pipeline/KanbanColumn.tsx`, `PedidoCard.tsx`

Done cuando: Muestra pedidos reales agrupados por etapa. Filtros aplican.

Depende de: T-36, T-19.

---

### T-46 · Detalle de pedido/orden (HU-10)
**M · frontend**

Descripción: Página con cabecera, ítems, orden asociada, timeline, anotaciones.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §5 HU-10 (mockup).

Archivos:
- `frontend/src/pages/interno/Pedido.tsx`
- `frontend/src/features/pipeline/PedidoDetalle.tsx`
- `frontend/src/features/pipeline/Anotaciones.tsx`

Done cuando: Se ve un pedido real con timeline y se puede agregar una anotación.

Depende de: T-45, T-20.

---

### T-47 · Alertas de pedidos estancados (HU-11)
**M · frontend**

Descripción: Widget + página completa. Botón "marcar revisada".

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §5 HU-11 (mockup).

Archivos:
- `frontend/src/features/alertas/PedidosEstancados.tsx`

Done cuando: Alertas visibles en dashboard. Marcar como revisada persiste.

Depende de: T-44.

---

### T-48 · Saldos presupuestales (HU-15)
**M · frontend**

Descripción: Tabla filtrable con semáforo, export.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §7 HU-15 (mockup).

Archivos:
- `frontend/src/pages/interno/Saldos.tsx`

Done cuando: Tabla con saldos reales, semáforo aplicando umbrales, export Excel/PDF.

Depende de: T-36, T-17, T-30.

---

### T-49 · Alertas de metas rezagadas (HU-16)
**M · frontend**

Descripción: Panel con lista, cada meta enlaza a la vista consolidada (T-51).

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §7 HU-16.

Archivos:
- `frontend/src/features/alertas/MetasRezagadas.tsx`

Done cuando: Muestra metas con devengado < umbral, enlaza correctamente.

Depende de: T-44, T-17.

---

### T-50 · Buscador por EXP_SIAF (HU-12)
**M · frontend**

Descripción: Página con input y resultado consolidado.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §6 HU-12 (mockup).

Archivos:
- `frontend/src/pages/interno/CruceExpediente.tsx`

Done cuando: Buscar un EXP_SIAF real devuelve meta + órdenes + pedido + conformidad.

Depende de: T-22.

---

### T-51 · Vista consolidada por meta (HU-13)
**M · frontend**

Descripción: Página con acordeón: presupuesto, órdenes, certificaciones, conformidades, pedidos. Export.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §6 HU-13 (mockup).

Archivos:
- `frontend/src/pages/interno/MetaConsolidada.tsx`

Done cuando: Vista carga con todos los componentes expandibles.

Depende de: T-22, T-30.

---

### T-52 · Drill-down con breadcrumbs (HU-14)
**S · frontend**

Descripción: Migas de pan + botones "ir a meta/orden" en tablas del cruce.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §6 HU-14.

Archivos:
- `frontend/src/components/Breadcrumbs.tsx`
- Integración en páginas de cruce

Done cuando: Navegación mantiene el contexto y las migas se actualizan.

Depende de: T-50, T-51.

---

### T-53 · Directorio interno de proveedores + contratos por vencer (HU-19, HU-20)
**S · frontend**

Descripción: Perfil de proveedor con historial. Widget de contratos por vencer en dashboard.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §9 HU-19, HU-20.

Archivos:
- `frontend/src/pages/interno/Proveedores.tsx`, `Proveedor.tsx`
- `frontend/src/features/alertas/ContratosPorVencer.tsx`

Done cuando: Perfil detallado se ve. Widget alerta funciona.

Depende de: T-24.

---

### T-54 · Gestión de usuarios (HU-17)
**M · frontend**

Descripción: CRUD de usuarios para Admin. Asignación de rol y centros de costo.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §8 HU-17 (mockup).

Archivos:
- `frontend/src/pages/admin/Usuarios.tsx`
- Endpoints admin correspondientes en backend (T-XX si hace falta)

Done cuando: Admin puede crear, editar, desactivar usuarios.

Depende de: T-33.

Nota: si los endpoints admin de usuarios no existen aún, agregar como sub-tarea de backend antes.

---

### T-55 · Configuración de umbrales y alertas (HU-18)
**S · frontend**

Descripción: Página con formularios por módulo. Solo Decisor/Admin.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §8 HU-18 (mockup).

Archivos:
- `frontend/src/pages/admin/Configuracion.tsx`

Done cuando: Cambios se persisten en `sistema.umbrales_*`. Al recargar el sistema, los semáforos reflejan los nuevos umbrales.

Depende de: T-33.

---

## FASE 6 · Integración y cierre (7 tareas)

### T-56 · Página de subida de docs/fotos (HU-03)
**S · frontend**

Descripción: UI para que funcionario con permiso suba archivos a una obra.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §3 HU-03 (mockup).

Archivos:
- `frontend/src/pages/interno/ObraEditar.tsx`

Done cuando: Subir fotos y documentos funciona. Se ven en el portal público.

Depende de: T-28, T-39.

---

### T-57 · Buzón ciudadano en ficha de obra (HU-24)
**C · frontend**

Descripción: Formulario en la ficha pública con reCAPTCHA.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §9 HU-24 (mockup).

Archivos:
- `frontend/src/features/observaciones/FormularioObservacion.tsx`

Done cuando: Enviar observación con captcha inserta en BD. Admin la ve en `/admin/observaciones-ciudadanas`.

Depende de: T-29, T-39.

---

### T-58 · Nginx reverse proxy + servir estáticos
**M · infra**

Descripción: Configurar Nginx para servir el build de React + proxy_pass al backend + rate limiting + gzip.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §9 (despliegue completo).

Archivos:
- `nginx/nginx.conf`
- `nginx/Dockerfile`
- Ajustes en `docker-compose.yml`

Done cuando: `docker compose up` en producción sirve todo desde `http://localhost/`.

Depende de: T-31 (build frontend disponible), T-07.

---

### T-59 · TLS con Let's Encrypt (o cert interno)
**M · infra**

Descripción: Certbot en contenedor o certificado interno de la muni.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §9.3.

Archivos:
- Servicio `certbot` en `docker-compose.yml`
- Renovación via cron o `certbot renew` en el contenedor

Done cuando: `https://<dominio>/` carga con certificado válido.

Depende de: T-58 + disponibilidad de dominio.

---

### T-60 · Backup automático de PostgreSQL
**M · infra**

Descripción: Script `pg_dump` corriendo diario vía cron del host o contenedor dedicado. Retención 30 días local + copia semanal externa.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §9.4.

Archivos:
- `scripts/backup-postgres.sh`
- Crontab del host o servicio backup

Done cuando: `/var/backups/postgres/YYYYMMDD.sql.gz` se crea diario. Restore probado en máquina limpia.

Depende de: T-58.

---

### T-61 · Smoke test end-to-end manual
**M · calidad**

Descripción: Guía + ejecución del check-list de smoke test manual: login, ver obra, ver mapa, ver saldo, ver pipeline, buscar por EXP_SIAF, exportar Excel, exportar PDF.

Consultar: `Docs/actividad-2-requerimientos-funcionales.md` §10 (HU Must-have).

Archivos:
- `Docs/smoke-test.md` (checklist)

Done cuando: Los 18 HU Must-have pasan el checklist en un ambiente limpio.

Depende de: T-56 y anteriores.

---

### T-62 · Documentación operacional
**S · docs**

Descripción: Runbook de operación: cómo levantar, cómo restaurar backup, cómo trigger manual del sync, cómo agregar usuario admin, cómo rotar contraseña SIGA.

Consultar: `Docs/actividad-3-arquitectura-tecnica.md` §13 (riesgos y mitigaciones).

Archivos:
- `Docs/runbook.md`

Done cuando: Un funcionario TI puede seguir el runbook y operar el sistema sin ayuda.

Depende de: T-60.

---

## 2. Resumen del plan por fase

| Fase | Tareas | Descripción | Depende de |
|---|---|---|---|
| 1 · Infra | T-01 → T-05 | Monorepo, Docker, PostgreSQL, SIGA local | — |
| 2 · Backend base | T-06 → T-11 | Migraciones, FastAPI, auth, logging | Fase 1 |
| 3 · Backend dominios | T-12 → T-30 | Sync SIAF, todos los repos y endpoints | Fase 2 |
| 4 · Frontend base | T-31 → T-36 | React, router, auth, componentes base | Fase 1 |
| 5 · Frontend dominios | T-37 → T-55 | Todas las páginas del MVP | Fase 3 + Fase 4 |
| 6 · Cierre | T-56 → T-62 | Nginx, TLS, backup, smoke test, runbook | Fase 5 |

**Total: 62 tareas.**

---

## 3. Ruta crítica (para arrancar rápido)

Orden mínimo para ver algo funcional lo antes posible:

1. T-01 → T-02 → T-03 → T-04 → T-05 (**infra base**)
2. T-06 → T-07 → T-08 → T-09 (**backend base con auth**)
3. T-31 → T-32 → T-33 → T-34 → T-35 → T-36 (**frontend base con login**)
4. Elegir un dominio para primer end-to-end demo (sugerido: **saldos** por ser el más autocontenido):
   T-15 → T-16 → T-17 → **[login funciona con backend]** → T-48
5. Continuar con **obras** para el portal público:
   T-12 → T-13 → T-14 → T-25 → T-26 → T-38 → T-39
6. Añadir pipeline, cruce, dashboard, resto.

Este orden minimiza esperas y permite validar el flujo completo (auth + query + UI) desde temprano.

---

## 4. Estrategia de tokens del agente

Cada tarea de este plan cita solo las secciones exactas que necesita. El agente debe:

1. **Al arrancar una tarea**, leer:
   - `CLAUDE.md` (siempre cargado)
   - La tarea específica en este documento
   - Las secciones citadas en la tarea (usar `Read` con `offset`/`limit`)

2. **No leer** documentos completos "por si acaso". Los docs largos son:
   - `Docs/diccionario-datos-unificado.md` (900+ líneas)
   - `Docs/datos-iniciales-siga.md` (950+ líneas)
   - `Docs/actividad-1-exploracion-mef.md` (530+ líneas)
   - `Docs/actividad-2-requerimientos-funcionales.md` (900+ líneas)
   - `Docs/actividad-3-arquitectura-tecnica.md` (800+ líneas)

3. **Reutilizar contexto** dentro de la misma conversación: si una sesión ya cargó un doc para T-15, la siguiente tarea T-16 no necesita re-cargarlo mientras dure la sesión.

4. **Cuando la tarea sea ambigua**, el agente debe preguntar en vez de leer más — más rápido y ahorra tokens.

---

## 5. Cómo el agente entregará cada tarea

Para cada `T-XX`:

1. **Leer** `CLAUDE.md` + este documento (secciones de la tarea).
2. **Leer** las citas puntuales de la tarea (`offset`/`limit`).
3. **Implementar** los archivos listados. Solo lo pedido — sin refactores fuera de alcance.
4. **Correr smoke test manual** apropiado a la capa (arrancar server, ejecutar endpoint, cargar página).
5. **Reportar** al usuario:
   - Qué se hizo (1-2 líneas)
   - Cómo verificar (comando/URL)
   - Bloqueos o dudas si los hubo
6. **Commit** con mensaje `T-XX: <descripción breve>`.

---

## 6. Trazabilidad con las HU

| HU | Tarea backend | Tarea frontend |
|---|---|---|
| HU-01 Listado obras | T-25, T-26 | T-38 |
| HU-02 Ficha obra | T-25, T-26, T-28 | T-39 |
| HU-03 Subida docs/fotos | T-28 | T-56 |
| HU-04 Mapa obras | T-26 | T-40 |
| HU-05 Dashboard ejecución | T-27 | T-41 |
| HU-06 Tabla ejecución | T-27 | T-42 |
| HU-07 Directorio proveedores público | T-24 | T-43 |
| HU-08 Login | T-08 | T-34 |
| HU-09 Pipeline kanban | T-18, T-19 | T-45 |
| HU-10 Detalle pedido | T-19, T-20 | T-46 |
| HU-11 Alerta estancados | T-19 | T-47 |
| HU-12 Buscador EXP_SIAF | T-21, T-22 | T-50 |
| HU-13 Vista consolidada meta | T-22 | T-51 |
| HU-14 Drill-down | T-22 | T-52 |
| HU-15 Saldos | T-16, T-17 | T-48 |
| HU-16 Metas rezagadas | T-17 | T-49 |
| HU-17 Gestión usuarios | — (parte de T-08 semilla) | T-54 |
| HU-18 Config umbrales | T-06 (tablas) | T-55 |
| HU-19 Directorio proveedores interno | T-23, T-24 | T-53 |
| HU-20 Contratos por vencer | T-23, T-24 | T-53 |
| HU-21 Exportación | T-30 | (integrado en cada página) |
| HU-22 Dashboard bienvenida | T-17, T-19, T-24 | T-44 |
| HU-23 Job sync SIAF | T-12, T-13, T-14 | — |
| HU-24 Buzón ciudadano | T-29 | T-57 |

---

*Documento generado como Actividad 5 — Plan de Desarrollo · Fase de Diseño · Julio 2026. Diseñado para minimizar consumo de tokens del agente mediante citas puntuales a docs previos.*
