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
# 1. Levantar PostgreSQL y Redis
make dev-infra

# 2. Backend
make backend-dev

# 3. Frontend
make frontend-dev
```

## Convenciones de trabajo

- **Trunk-based:** commits directos a `main`, sin feature branches.
- **Nomenclatura de commits:** `T-XX: descripción breve` (ver plan de desarrollo).
- **Solo lectura** sobre SIGA/SIAF. Toda escritura va a PostgreSQL.
- **Filtro obligatorio:** `SEC_EJEC=300687` en cualquier query externa.
