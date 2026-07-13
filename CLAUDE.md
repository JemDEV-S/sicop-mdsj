# CLAUDE.md — Contexto compacto del proyecto

Este archivo se carga siempre. Contiene lo esencial para trabajar sin re-leer documentos largos. Los detalles están en `Docs/` — cítalos por sección cuando los necesites.

## Qué es el proyecto

Sistema web dual para la **Municipalidad Distrital de San Jerónimo (Cusco)**:
- Portal público de transparencia (obras + ejecución presupuestal)
- Panel interno para funcionarios (pipeline, saldos, cruce SIAF-SIGA, reportes)

## Datos fijos del proyecto

| Concepto | Valor |
|---|---|
| Entidad ejecutora | `SEC_EJEC = 300687` |
| UBIGEO San Jerónimo | `080104` |
| Año vigente MVP | `2026` |
| Cobertura SIGA local | 2023 – 2026 |
| Resource SIAF ejecución | `615644aa-ef73-4358-b4e0-0c20931632f3` |
| Resource Invierte.pe | `f9cc4ba0-931a-4b70-86c9-eacbd8c68596` |
| Base API MEF | `https://api.datosabiertos.mef.gob.pe/DatosAbiertos/v1/` |
| SIGA dev (SQL Server) | Instancia default `.` (localhost), BD `SIGA_300687`, Windows Auth |
| ODBC Driver | `ODBC Driver 17 for SQL Server` |

## Stack

- **Backend:** Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy (engine) + pyodbc
- **Base intermedia:** PostgreSQL 16 (schemas `auth`, `ref`, `siaf`, `sistema`, `logs`) + `ltree` + `uuid-ossp`
- **Fuente SIGA:** SQL Server (solo lectura, queries SQL crudas)
- **Frontend:** React 18 + Vite 5 + TypeScript + Tailwind + shadcn/ui + TanStack Query + Zustand
- **Gráficos:** Recharts · **Mapas:** Leaflet · **Cache:** Redis · **Jobs:** APScheduler
- **Export:** openpyxl (Excel) + WeasyPrint (PDF)
- **Contenerización:** Docker Compose · **Proxy:** Nginx

## Reglas de negocio no negociables

1. **Filtro obligatorio:** toda query SIGA/SIAF fija `SEC_EJEC=300687`.
2. **Solo lectura sobre SIGA/SIAF.** Toda escritura va a PostgreSQL.
3. **Fuentes autoritativas** (cuando el dato existe en varios lugares):
   - PIM → `SIG_TECHO_PRESUPUESTO.PPTO_MODIF`
   - PIA → `SIG_TECHO_PRESUPUESTO.PPTO_PIA` (el de SIAF viene en 0)
   - Saldo disponible → `SIG_TECHO_PRESUPUESTO.PPTO_DISP_SIAF`
   - Devengado → `SIG_TECHO_PRESUPUESTO.MNTO_ACUM_DEVGDO_SIGA` o `ESTADO_SIAF='2'`
   - Avance físico obra → Invierte.pe `AVANCE_FISICO`
4. **Llave cruce SIAF↔SIGA:** `ANO_EJE + SEC_EJEC + SEC_FUNC` (+ `EXP_SIAF` como secundaria).
5. **API MEF:** máximo 8 columnas por query, `LIMIT 100 OFFSET n`, sin tildes en filtros.
   - **Granularidad SIAF:** `PIA` y `PIM` solo tienen valor en `MES_EJE=0`. En meses 1-N vienen en 0.
   - **Montos de ejecución** (`devengado`, `girado`, `certificado`, `comprometido`) son flujos mensuales, **no acumulados**. Para el total anual hay que `SUM` de todos los meses `> 0` agrupando por `sec_func`.
   - **Trampa:** tomar solo `MAX(mes_eje)` borra el PIA/PIM de las metas activas → subcuenteo grave. Ver `Docs/hallazgos-granularidad-siaf.md`.
6. **Filtro por CC:** Operativo = sus CC; Decisor = jerarquía por `CENTRO_PADRE`; Admin = todo.
7. **Umbrales configurables** en `sistema.umbrales_*` — no hardcodear.
8. **Auditoría** en `logs.auditoria` para: login, exportación, cambio de umbrales, subida docs, publicación observación.
9. **Datos maestros de SIGA** (metas, centros de costo, sus relaciones) NO se consultan contra SIGA en cada request. Se leen de `ref.*` (poblado por job `sync_catalogos_siga`).
10. **Frontend consume `siaf.v_ejecucion_normalizada`** (vista con JOIN a `ref.*`), no la tabla base `siaf.ejecucion_presupuestal`. Nombres autoritativos vienen de `ref`.
11. **Jerarquía CC:** usar `ruta <@ 'root.<código>'` (ltree) — no queries recursivas manuales.

## Índice de documentos (leer por sección, no completos)

| Doc | Cuándo consultarlo | Secciones útiles |
|---|---|---|
| [Docs/idea-principal.md](Docs/idea-principal.md) | Contexto general y módulos | §5 usuarios · §6 módulos · §10 priorización MVP |
| [Docs/diccionario-datos-unificado.md](Docs/diccionario-datos-unificado.md) | Cualquier query o modelo | §4 META · §7 montos · §8 Invierte.pe · §10 cadena logística · §17 llaves cruce · §18 reglas |
| [Docs/actividad-1-exploracion-mef.md](Docs/actividad-1-exploracion-mef.md) | Limitaciones API MEF y queries validadas | §3 diccionario campos · §4 limitaciones · §10 queries validadas · §12 Invierte.pe |
| [Docs/hallazgos-granularidad-siaf.md](Docs/hallazgos-granularidad-siaf.md) | Reglas de agregación SIAF (PIA/PIM vs ejecución) | §1 estructura real · §4 tabla reglas de agregación — leer antes de cualquier query de montos |
| [Docs/datos-iniciales-siga.md](Docs/datos-iniciales-siga.md) | Estructura SIGA y validación cruce | §2 conexión dev · §5 metas · §11 queries · §12 cadena logística · §13 módulos funcionarios |
| [Docs/actividad-2-requerimientos-funcionales.md](Docs/actividad-2-requerimientos-funcionales.md) | Antes de implementar una HU | §2 RN globales · §3-9 HU por módulo · §10 priorización MoSCoW |
| [Docs/actividad-3-arquitectura-tecnica.md](Docs/actividad-3-arquitectura-tecnica.md) | Setup, modelo BD, API, despliegue | §3.0 principios · §3.1 schemas · §3.1.2 ENUMs · §3.2 auth · §3.3 ref (ltree) · §3.4 siaf + vista · §3.5 sistema · §3.6 logs · §3.7 resumen · §4 endpoints · §5 adaptador SIGA · §6 sync SIAF · §9 despliegue · §11 estructura repo |
| [Docs/actividad-5-plan-desarrollo.md](Docs/actividad-5-plan-desarrollo.md) | Qué hacer y en qué orden | Índice de tareas + citas por tarea |

## Cómo trabajar (para el agente y el humano)

- **Trunk-based:** commits directos a `main`. No feature branches.
- **Cada tarea del plan** tiene ID `T-XX`. Al implementar, citar `T-XX` en el commit.
- **Al leer docs**, usar Read con `offset`/`limit` para leer solo la sección citada, no el archivo completo.
- **Tests solo en zonas críticas:** adaptador SIGA (queries autoritativas), auth, semáforos, exportación. UI se prueba manual.
- **Datos de desarrollo:** SIGA restaurado localmente en SQL Server dockerizado con el backup de la muni (2023-2026).
- **Entrega por tarea:** código funcional + smoke test manual (arrancar server, verificar endpoint/pantalla).
- **No inventar:** si un dato falta o la llave no cruza, marcar como pendiente y preguntar antes de hacer workaround.
