# SICOP-MDSJ

**Sistema de Información y Control Presupuestal — Municipalidad Distrital de San Jerónimo (Cusco)**

Sistema web dual que integra datos del SIAF (API MEF) y del SIGA (SQL Server local) para ofrecer:

- **Portal público de transparencia** — obras públicas, ejecución presupuestal, directorio de proveedores.
- **Panel interno para funcionarios** — pipeline de pedidos, saldos, cruce SIAF-SIGA, reportes.

---

## Stack

- **Backend:** Python 3.12 + FastAPI + PostgreSQL 16
- **Fuente SIGA:** SQL Server (solo lectura)
- **Fuente SIAF:** API pública MEF (snapshot diario)
- **Frontend:** React 18 + Vite + TypeScript + Tailwind + shadcn/ui
- **Infra:** Docker Compose + Nginx + Redis

## Estructura del monorepo

```
sicop-mdsj/
├── CLAUDE.md          # Contexto compacto (siempre cargado)
├── Docs/              # Documentación de diseño (Actividades 1-5)
├── backend/           # FastAPI + Alembic
├── frontend/          # React + Vite
├── nginx/             # Reverse proxy + estáticos
├── scripts/           # Scripts operacionales (restore SIGA, backup)
├── docker-compose.yml
├── docker-compose.dev.yml
└── Makefile
```

## Bloqueadores Conocidos

> [!WARNING]
> ### 🛑 Bloqueadores Conocidos: Backup de SIGA
> El proyecto depende estrictamente de la base de datos **SIGA_300687** para los módulos de Proveedores y futura conciliación SIAF-SIGA.
> El archivo `SIGA_300687.bak` no se encuentra en el repositorio (ver T-04). El frontend se ha implementado mediante mocks unitarios (MSW) verificando el contrato Pydantic. 
> **Acción Requerida (Gestión Externa):** El backup oficial debe ser provisto por la Municipalidad y colocado en `scripts/siga-backup/` para desbloquear las pruebas E2E y la integración real.

> [!WARNING]
> ### 🛑 Bloqueadores Conocidos: Histórico 2025 en MEF
> El proyecto está calibrado contra el año fiscal 2025 (por la data del SIGA), pero la API pública del MEF (`datastore_search`) expone únicamente un `resource_id` para el año vigente (2026). No se ha encontrado el UUID histórico para Ejecución Presupuestal 2025 (ver `actividad-1-exploracion-mef.md` §13).
> **Mitigación Temporal:** Se utiliza el script `backend/scripts/dev_seed_sintetico_2025.py` para poblar datos sintéticos marcados con `[DEV-SEED]` y validar visualmente el frontend. El pipeline real (`sync_siaf.py`) permanece bloqueado hasta conseguir el UUID correcto.

## Documentación

| Doc | Contenido |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Contexto compacto: stack, reglas, datos fijos |
| [Docs/idea-principal.md](Docs/idea-principal.md) | Formalización del proyecto |
| [Docs/diccionario-datos-unificado.md](Docs/diccionario-datos-unificado.md) | Diccionario SIAF ↔ SIGA |
| [Docs/actividad-1-exploracion-mef.md](Docs/actividad-1-exploracion-mef.md) | Exploración API MEF |
| [Docs/datos-iniciales-siga.md](Docs/datos-iniciales-siga.md) | Estructura SIGA |
| [Docs/actividad-2-requerimientos-funcionales.md](Docs/actividad-2-requerimientos-funcionales.md) | HU + reglas de negocio |
| [Docs/actividad-3-arquitectura-tecnica.md](Docs/actividad-3-arquitectura-tecnica.md) | Arquitectura + modelo BD + API |
| [Docs/actividad-5-plan-desarrollo.md](Docs/actividad-5-plan-desarrollo.md) | Plan de 62 tareas |

## Cómo arrancar (dev)

```bash
# 1. Levantar PostgreSQL, Redis y SQL Server local (SIGA mock)
make dev-infra

# 2. Levantar el Backend (en Docker, con ODBC drivers y hot-reload habilitado)
make backend-dev

# 3. Frontend
make frontend-dev
```

## Convenciones de trabajo

- **Trunk-based:** commits directos a `main`, sin feature branches.
- **Nomenclatura de commits:** `T-XX: descripción breve` (ver plan de desarrollo).
- **Solo lectura** sobre SIGA/SIAF. Toda escritura va a PostgreSQL.
- **Filtro obligatorio:** `SEC_EJEC=300687` en cualquier query externa.
