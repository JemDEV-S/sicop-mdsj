# Guía operativa — Frontend interno (T-44 → T-55)

> Municipalidad Distrital de San Jerónimo (Cusco)
> Continuación de la Fase 5 · Panel de funcionarios
> Documento de trabajo — se actualiza a medida que avanza el rediseño

---

## 0. Contexto de esta guía

El **frontend público** (T-37 a T-43) ya está terminado con el sistema de diseño institucional consolidado (paleta, componentes base, layouts, navegación). Ahora toca el **panel interno para funcionarios** — de T-44 (dashboard de bienvenida) a T-55 (configuración de umbrales).

Ya existe una primera iteración del interno (Dashboard, sidebar, topbar, algunos widgets). **Se va a rediseñar por completo** para que sea profesional, denso y orientado al uso real de los funcionarios de la Municipalidad, no genérico.

Este trabajo se hará en **varios chats de Claude**. Esta guía es la referencia común entre sesiones para no perder contexto ni repetir decisiones.

**Documentos hermanos:**
- [Docs/frontend-design-master.md](frontend-design-master.md) — plano visual y decisiones por pantalla (fuente de verdad de diseño)
- [Docs/actividad-2-requerimientos-funcionales.md](actividad-2-requerimientos-funcionales.md) §5-§9 — HUs, criterios de aceptación, mockups textuales
- [Docs/actividad-5-plan-desarrollo.md](actividad-5-plan-desarrollo.md) — descripción y dependencias de cada T-XX
- [`.claude/skills/frontend-design-system/SKILL.md`](../.claude/skills/frontend-design-system/SKILL.md) — paleta, tono, checklist visual
- [Docs/frontend-interno-backend-issues.md](frontend-interno-backend-issues.md) — bitácora de correcciones al backend detectadas en el camino *(se crea al aparecer el primer hallazgo — ver §5 de esta guía)*

---

## 1. Filosofía del panel interno

El interno es la herramienta de trabajo diaria de un funcionario de una dependencia municipal (centro de costo). El usuario típico **no es un power-user** — es personal de una sub-gerencia u oficina que necesita ver su presupuesto, sus pedidos y sus alertas, sin curva de aprendizaje.

Por eso el diseño debe cumplir tres condiciones simultáneas:

1. **Intuitivo para el funcionario promedio.** Que un jefe de una sub-gerencia entre por primera vez y sepa en segundos: cuánto le queda de presupuesto, qué pedidos suyos están atorados, dónde ver el detalle.
2. **Denso y potente para el usuario avanzado.** Funcionarios de presupuesto, planificación o gerencia usan el sistema todo el día y necesitan filtros, cruces, exportación, drill-down. **Se deja la puerta abierta** — la información avanzada existe pero se activa progresivamente (patrón *progressive disclosure*), no invade la pantalla base.
3. **Profesional y estético.** Institucional no significa feo. La paleta institucional (azul `#3484A5`, verde `#2CA792`, amarillo `#F0C84F`), el espaciado consistente y una jerarquía tipográfica clara construyen una interfaz digna de un sistema público moderno.

**Principios operativos** (extendidos del design-master §1):

1. **Intuitividad primero.** Cada pantalla debe ser comprensible sin manual: etiquetas claras, iconografía apoyada por texto, tooltips en términos técnicos (`SEC_FUNC`, `EXP_SIAF`, `PIM`, `Devengado`, `Genérica`), microcopy explicativo cuando el dato lo amerita.
2. **Densidad progresiva.** La vista inicial de cada pantalla muestra lo esencial (`space-y-6`, `p-4` en cards). El detalle, los filtros avanzados y las tablas grandes se expanden bajo demanda, no de entrada.
3. **El contexto siempre está a la vista.** El usuario debe saber en todo momento: qué unidad/CC filtra, qué año, qué rol tiene, dónde está en la jerarquía de navegación.
4. **Filtros persistentes y visibles.** Los filtros activos se muestran como `FiltroChips` — no escondidos en un dropdown "avanzado". El default de cada filtro corresponde al alcance natural del rol (Operativo → sus CC; Decisor → su gerencia; Admin → todo).
5. **Respetar la jerarquía y estructura de datos del MEF.** Los conceptos y navegación reflejan el modelo oficial: **Categoría presupuestal → Programa/Producto/Proyecto → Función → División Funcional → Grupo Funcional → Meta (`SEC_FUNC`) → Genérica → Específica de gasto**. En paralelo, la **jerarquía de centros de costo** (`CENTRO_PADRE` / `ltree`) manda la visibilidad. Nunca inventar agrupaciones ni renombrar conceptos oficiales; sí traducirlos con lenguaje llano en tooltips ("Meta = actividad presupuestal específica del año").
6. **Priorizar el trabajo del día.** El dashboard responde a "¿qué debo mirar hoy?", no "aquí tienes todos los indicadores del municipio".
7. **Acciones a un clic.** Anotar, exportar, marcar revisada, ir al cruce — todos accesibles desde donde el usuario ya está mirando, no navegando de vuelta al menú.
8. **Lenguaje operativo pero humano.** "87 pedidos activos · 12 estancados" está bien; "Bienvenido al panel de gestión" es relleno. Términos MEF se respetan (PIM, PIA, Devengado, Genérica) porque son el vocabulario diario del funcionario, pero se acompañan de un tooltip la primera vez que aparecen en una pantalla.
9. **Estética institucional.** Nada de degradados chillones ni sombras exageradas. Bordes suaves (`rounded-lg`), sombras sutiles (`shadow-sm`), contrastes que cumplen WCAG AA, jerarquía tipográfica clara, blanco generoso alrededor de los datos importantes.
10. **Nada de emojis en JSX final.** Los mockups de HU los usan como marca de estado — se traducen a íconos Lucide con `aria-label`.
11. **Cero hardcoding de rol/CC en la UI.** Toda decisión de qué ver la resuelve el backend según JWT.
12. **Puertas abiertas para versiones futuras.** Widgets, filtros avanzados y módulos "power-user" (comparativos multi-año, proyecciones, dashboards ejecutivos) se anticipan en la arquitectura (feature aislado, hook por dominio) pero no se construyen ahora. Documentar en §7 lo que se difiere para no perderlo.

---

## 1.1 Patrones de intuitividad reutilizables

Antes de cada pantalla, revisar si aplica alguno de estos patrones. Aplicarlos de forma consistente es lo que hace que el sistema se sienta "de una sola pieza" en vez de una colección de páginas:

- **Encabezado con contexto pegajoso.** `PageHeader` siempre incluye: título de la pantalla, breadcrumb corto, año activo (chip), CC/unidad activa (chip). El usuario nunca se pregunta "¿de qué estoy viendo esto?".
- **Estado vacío educativo.** `EmptyState` no dice "Sin datos". Dice qué significa (ej. "Esta unidad no registra pedidos en el año 2026 todavía") y ofrece la acción siguiente (ej. "Cambiar año" o "Ver otros centros de costo").
- **Skeleton, no spinner.** `LoadingSkeleton` muestra la forma de lo que va a llegar (tabla con 5 filas grises, KPIs con placeholders). Se siente más rápido que un spinner genérico.
- **Error con salida.** `ErrorState` explica qué falló en lenguaje llano ("No pudimos cargar los saldos. Puede ser un corte temporal del SIGA.") y ofrece reintentar.
- **Tooltip sobre términos MEF.** Componente `TerminoMef` (a crear) que envuelve palabras como `PIM`, `Devengado`, `Genérica`, `Meta` y al hover muestra la definición corta. Se declara una sola vez por pantalla — no se satura con tooltips repetidos.
- **Semáforo con etiqueta.** El componente `Semaforo` nunca aparece solo con color; siempre acompaña texto ("En riesgo · 45% devengado"). El color es refuerzo, no la información.
- **Filtros con default sensato.** Cada pantalla arranca con filtros ya aplicados al alcance del rol y al año vigente. El usuario ve resultados inmediatos, no una tabla vacía esperando input.
- **Acción principal destacada.** En pantallas con muchas acciones, una sola es "primaria" (botón lleno, color institucional). El resto son secundarias (outline) o terciarias (link). Nunca 5 botones del mismo peso visual.
- **Zonas colapsables por defecto colapsadas** en pantallas de detalle largas (HU-13, HU-10). Se expande lo que el usuario decide mirar. Excepción: la primera sección se expande de entrada.
- **Números formateados humanamente.** `S/ 87,540.00` (dos decimales, separador de miles). Porcentajes con `%` pegado (`45%`). Fechas como `15 jul 2026` en vista, `2026-07-15` solo en filtros/inputs.
- **Vacío ≠ error ≠ cargando.** Cada uno tiene su componente. Nunca mezclar (ej. mostrar spinner cuando en realidad la respuesta llegó vacía).

---

## 1.2 Jerarquía MEF — referencia rápida

Todo el interno se organiza mentalmente sobre estas dos jerarquías. Cualquier navegación, filtro, agrupación o breadcrumb debe respetarlas. **Si una pantalla propone otra estructura, es señal de que hay que replantear.**

### Jerarquía presupuestal (SIAF/MEF)

```
Año fiscal (ANO_EJE = 2026)
└── Categoría presupuestal (APNOP / Programa presupuestal / Acciones centrales)
    └── Programa · Producto · Proyecto (según categoría)
        └── Función · División Funcional · Grupo Funcional
            └── Actividad / Meta (SEC_FUNC)          ← unidad operativa
                └── Fuente de financiamiento (FF) · Rubro (RB)
                    └── Genérica de gasto (2.3, 2.6, etc.)
                        └── Específica de gasto (2.3.1.5, etc.)
                            └── Ejecución (Certif. → Comprom. → Deveng. → Girado)
```

**En la UI:**
- El **filtro global** es el año (topbar).
- El **filtro de contexto** es el centro de costo / meta (según rol).
- Los **agrupadores más usados** son: función, fuente de financiamiento, genérica. En ese orden.
- El **identificador operativo** que un funcionario reconoce es la **Meta** (`SEC_FUNC` + nombre). Todo detalle se ancla ahí.

### Jerarquía organizacional (centros de costo · SIGA)

```
Municipalidad (raíz)
└── Gerencia / Oficina (CENTRO_PADRE nulo o raíz)
    └── Sub-gerencia
        └── Área / Unidad operativa (centro de costo hoja)
            └── Usuarios asignados (auth.usuarios_centro_costo)
```

**Regla de visibilidad** (RN del CLAUDE.md §6):
- **Operativo** → ve solo sus CC asignados.
- **Decisor** → ve toda la subrama descendiente de sus CC (`ruta <@ 'root.<codigo>'` en ltree).
- **Admin** → ve toda la municipalidad.

**En la UI:**
- El chip de "CC activo" en el topbar/sidebar debe mostrar el CC más granular con posibilidad de subir en la jerarquía (para decisores).
- Los breadcrumbs de navegación de un pedido/meta incluyen su CC de origen para dar contexto.
- Nunca se listan CC fuera del alcance del usuario, ni siquiera bloqueados: no existen para él.

---

## 2. Alcance y orden recomendado

Las tareas del interno con sus dependencias (según plan §5 y trazabilidad con HU):

| T | HU | Depende de backend | Comentario |
|---|---|---|---|
| **T-44** | HU-22 Dashboard bienvenida | T-17, T-19, T-24 | Ya existe primera iteración — rediseñar |
| **T-45** | HU-09 Pipeline kanban | T-19 | Nueva pantalla clave |
| **T-46** | HU-10 Detalle pedido/orden | T-19, T-20 | Timeline + anotaciones |
| **T-47** | HU-11 Alertas estancados | T-19 | Widget + página completa |
| **T-48** | HU-15 Saldos presupuestales | T-17, T-30 | Tabla con semáforo + export |
| **T-49** | HU-16 Metas rezagadas | T-17 | Enlaza a T-51 |
| **T-50** | HU-12 Buscador EXP_SIAF | T-22 | Input + resultado consolidado |
| **T-51** | HU-13 Vista consolidada meta | T-22, T-30 | Acordeón + export |
| **T-52** | HU-14 Drill-down / breadcrumbs | T-50, T-51 | Componente + integración |
| **T-53** | HU-19/20 Proveedores internos + contratos por vencer | T-24 | Perfil + widget de alertas |
| **T-54** | HU-17 Gestión de usuarios | T-08 | Admin only |
| **T-55** | HU-18 Configuración umbrales | T-06 | Decisor/Admin only |

**Orden sugerido de ejecución** (minimiza rework y valida el sistema temprano):

```
Etapa A — Rediseño base del interno
  1. Auditar el interno actual y limpiar lo que se descarta
  2. Refinar SidebarInterno / TopbarInterno (paleta, densidad, chip de CC/rol)
  3. T-44 · Dashboard bienvenida — rediseño completo

Etapa B — Núcleo operativo (lo que usa el operativo cada día)
  4. T-45 · Pipeline kanban
  5. T-46 · Detalle pedido
  6. T-47 · Alertas estancados (widget + página)

Etapa C — Saldos y alertas presupuestales
  7. T-48 · Saldos presupuestales
  8. T-49 · Metas rezagadas

Etapa D — Cruce SIAF-SIGA (el diferenciador del sistema)
  9. T-50 · Buscador EXP_SIAF
 10. T-51 · Vista consolidada meta
 11. T-52 · Breadcrumbs / drill-down

Etapa E — Complementos
 12. T-53 · Proveedores internos + contratos por vencer
 13. T-54 · Gestión de usuarios (admin)
 14. T-55 · Configuración de umbrales (decisor/admin)
```

Cada etapa se puede cerrar en 1 o 2 chats de Claude. **No mezclar etapas** en el mismo chat: cuando una está lista, se hace commit, se apunta lo que quedó pendiente en §5, y el próximo chat abre la siguiente.

---

## 3. Cómo abordar un chat de trabajo

Al iniciar un chat nuevo dedicado a una etapa/tarea, seguir este flujo:

### 3.1 Contexto mínimo a cargar

Le pides a Claude que lea, en este orden:

1. `CLAUDE.md` (ya se carga solo).
2. **Esta guía** (`Docs/guia-frontend-interno.md`) — sección relevante a la etapa que toca.
3. `Docs/frontend-design-master.md` — la sección específica de la pantalla (ej. §4 T-45 para Pipeline). **No leer el doc entero**.
4. `Docs/actividad-2-requerimientos-funcionales.md` — la HU específica (ej. HU-09 para T-45). Solo esa HU, con su mockup y criterios.
5. `Docs/actividad-5-plan-desarrollo.md` — la tarjeta T-XX específica, para ver dependencias y archivos previstos.
6. **La bitácora de issues backend** (`Docs/frontend-interno-backend-issues.md`, ver §5) si existe — para saber si hay algo pendiente que afecte esta pantalla.

### 3.2 Antes de escribir código

Confirmar con el usuario:

- ¿La HU tiene su endpoint backend listo y funcionando? (curl al endpoint, ver respuesta real).
- ¿La estructura de la respuesta coincide con lo que espera el diseño?
- ¿Hay decisiones abiertas que resolver antes? (ej. filtros por CC en Pipeline requieren saber cómo el JWT resuelve la jerarquía).

Si algo no está claro, **preguntar antes de asumir**. No inventar campos ni estructuras.

### 3.3 Al implementar

- Usar los componentes ya creados: `PageHeader`, `SectionCard`, `EmptyState`, `ErrorState`, `LoadingSkeleton`, `FiltroChips`, `KpiCard`, `Semaforo`, `DataTable`, `WrapperGrafico`, `WrapperMapa`.
- Feature aislado por dominio (ej. `features/pipeline/api.ts`, `types.ts`, `hooks.ts`, `secciones/*.tsx`).
- Cero acoplamiento entre público e interno (regla del design-master §1.2).
- Cero `slate/gray/blue-500/amber/emerald/indigo/violet`. Solo paleta institucional.
- Cero emojis en JSX final.
- Cero `console.log` residual.

### 3.4 Antes de cerrar la tarea

Ejecutar el **checklist del design-master §6** (los 10 puntos). Si alguno falla, corregir antes de commit.

Smoke test manual: arrancar `npm run dev`, entrar como funcionario semilla, recorrer la pantalla, probar filtros, probar edge cases (sin datos, error de red, filtro sin resultados).

### 3.5 Commit y cierre del chat

- Commit con formato: `T-XX: <descripción breve>` (regla del plan §5).
- Actualizar §4 de esta guía (Estado de avance) marcando la tarea como hecha.
- Actualizar §5 (Issues backend) si en el camino apareció algo que corregir.
- Anotar en §6 (Decisiones tomadas) cualquier decisión no trivial que se resolvió en el chat.

---

## 4. Estado de avance

> Se actualiza al cerrar cada tarea. `[ ]` pendiente · `[~]` en curso · `[x]` hecho.

### Etapa A — Rediseño base
- [x] Auditoría del interno actual (listar qué se conserva vs. se descarta) — ver §6 [2026-07-15]
- [x] Refinar `SidebarInterno` (jerarquía visual, chip de rol + CC activo, contraste) — [2026-07-15]
- [x] Refinar `TopbarInterno` (breadcrumbs auto, chips de año + CC, buscador, usuario) — [2026-07-15]
- [x] **T-44** · Dashboard bienvenida — rediseñar widgets y layout — [2026-07-15]

### Etapa B — Núcleo operativo
- [x] **T-45** · Pipeline kanban — [2026-07-16]
- [ ] **T-46** · Detalle pedido
- [ ] **T-47** · Alertas estancados

### Etapa C — Saldos y alertas
- [ ] **T-48** · Saldos presupuestales
- [ ] **T-49** · Metas rezagadas

### Etapa D — Cruce SIAF-SIGA
- [ ] **T-50** · Buscador EXP_SIAF
- [ ] **T-51** · Vista consolidada meta
- [ ] **T-52** · Breadcrumbs / drill-down

### Etapa E — Complementos
- [ ] **T-53** · Proveedores internos + contratos por vencer
- [ ] **T-54** · Gestión de usuarios
- [ ] **T-55** · Configuración de umbrales

---

## 5. Correcciones y hallazgos del backend (bitácora viva)

Durante el rediseño del interno es **muy probable** que aparezcan cosas para corregir o completar en el backend: campos faltantes en una respuesta, endpoints que devuelven una estructura incompatible con el diseño, filtros que no aplican bien por CC, permisos mal definidos, etc.

**Regla:** no arreglar el backend en el mismo chat del frontend salvo que sea trivial (1 línea, mismo commit). Todo hallazgo se **anota aquí** y se resuelve después en un chat dedicado al backend.

### 5.1 Formato de anotación

```
### [YYYY-MM-DD] · <Endpoint o área> · [Bloqueante | No bloqueante] · [Abierto | Resuelto en <commit>]

**Detectado en:** T-XX (pantalla/feature)
**Qué pasa:** descripción concreta del problema
**Impacto en frontend:** qué no se puede hacer o qué workaround temporal se aplicó
**Propuesta de fix:** cambio esperado en backend (endpoint, esquema, permiso, migración)
**Docs a revisar:** archivo.md §N si aplica
```

### 5.2 Anotaciones

### [2026-07-15] · `/interno/alertas/contratos-por-vencer` sin filtro por CC · No bloqueante · Abierto

**Detectado en:** T-44 (dashboard bienvenida) · widget de alertas.
**Qué pasa:** `SIG_CONTRATOS` en SIGA no tiene una relación directa con `CENTRO_COSTO`. El endpoint devuelve los contratos de toda la entidad (SEC_EJEC=300687) sin importar el CC activo del contexto, mientras que pedidos y saldos sí filtran por CC.
**Impacto en frontend:** el widget de alertas del dashboard muestra el mismo conteo de contratos por vencer para operativo, decisor y admin. El chip de CC activo del topbar no altera este número.
**Propuesta de fix:** decidir la fuente de amarre CC↔contrato. Opciones a evaluar en T-53:
1. Vía `SIG_ORDENES` (JOIN `NRO_CONTRATO/SEC_CONTRATO`) — cada orden tiene CC. Un contrato pertenece a los CC de sus órdenes.
2. Vía `META` (JOIN por `SEC_FUNC` en órdenes derivadas del contrato) — si conviene agrupar por meta antes que por CC.
3. Documentar como comportamiento intencional si el negocio lo confirma (los contratos son transversales).
**Docs a revisar:** `Docs/diccionario-datos-unificado.md` §10 (cadena logística), `Docs/datos-iniciales-siga.md` §12.

---

---

## 6. Decisiones tomadas durante el rediseño

Registro de decisiones no triviales que afectan a más de una pantalla o al sistema en conjunto. Formato:

```
### [YYYY-MM-DD] · <Título corto>
**Contexto:** por qué se planteó
**Decisión:** qué se resolvió
**Alternativas descartadas:** cuáles y por qué
**Impacto:** qué archivos/pantallas se ven afectadas
```

### [2026-07-15] · Auditoría del interno actual (Etapa A · paso 1)

**Contexto:** antes de rediseñar el panel interno era necesario mapear qué existe hoy y decidir qué se conserva, refina o descarta.

**Conservar:**
- `InternoLayout.tsx` (estructura flex desktop-first).
- `nav-config.ts` (modelo `navInterna` + `filtrarNavPorRol`) — extensible con las rutas T-45..T-55.
- Primitives del sistema de diseño (`PageHeader`, `SectionCard`, `EmptyState`, `ErrorState`, `LoadingSkeleton`, `FiltroChips`, `KpiCard`, `Semaforo`, `DataTable`, `WrapperGrafico`).
- Contratos con backend en `features/dashboard/api.ts` y `types.ts`.
- Buscador `EXP_SIAF` en topbar y menú de usuario con logout.

**Refinar:**
- `SidebarInterno`: añadir chip de rol + CC activo en footer, mejorar jerarquía visual.
- `TopbarInterno`: incorporar selector global de año y chip de CC activo; conectar breadcrumbs automáticos desde el router.
- Dashboard T-44: reemplazar saludo "Bienvenido" por `PageHeader` con contexto (año/CC/rol), rediseñar widgets para responder "¿qué debo mirar hoy?", eliminar `AccesosRapidos` (duplica sidebar).
- `UltimosPedidos`: usar `DataTable` real, etiquetas MEF con tooltip, click-through al detalle HU-10.
- `WidgetPipeline`: reemplazar `var(--chart-1..5)` por paleta institucional.
- `WidgetSaldos`: anclar con chip de contexto activo, mostrar top-3 metas críticas.

**Descartar:**
- Rutas `/interno/query-test` y `/interno/sandbox` (ya marcadas TODO T-35/T-36).
- `AccesosRapidos` en dashboard.
- Header "Bienvenido, X" (relleno según §1 principio 8).

**Faltantes a introducir en el rediseño:**
- Store Zustand `contextoInterno` con `añoActivo` (default 2026) y `ccActivo`.
- Componente `TerminoMef` (tooltip para PIM/PIA/Devengado/Meta/Genérica).
- Componente `ChipContexto` (año + CC).
- Breadcrumbs auto desde el router.

**Impacto:** Etapa A pasos 2-4. No afecta a etapas B en adelante.

---

### [2026-07-15] · Filtro de año global en topbar

**Contexto:** pregunta abierta §7 sobre si el año vive en topbar o en cada pantalla.

**Decisión:** el año activo es global, vive en la topbar, persistido en un store Zustand (`contextoInterno.añoActivo`) con default `2026`. Todas las pantallas del interno lo consumen.

**Alternativas descartadas:** filtro por pantalla — obligaría al usuario a repetir la selección en cada módulo y complicaría los cruces entre pantallas.

**Impacto:** `TopbarInterno`, nuevo store `store/contexto-interno.ts`, todos los hooks de dominio (`dashboard`, `pipeline`, `saldos`, `cruce`) deben leer el año del store.

---

### [2026-07-15] · CC activo como chip en topbar

**Contexto:** la guía §1.2 exige que el CC activo esté a la vista siempre. Faltaba decidir dónde y cómo cambiarlo.

**Decisión:** chip en topbar (año + CC), con dropdown al click para cambiar entre los CC visibles del usuario según su rol. Un solo lugar de control.

**Alternativas descartadas:**
- Bloque en sidebar → ocupa área de navegación y duplica el patrón.
- Ambos (topbar + sidebar) → redundante.

**Impacto:** `TopbarInterno` (chip + dropdown), store `contextoInterno.ccActivo`, backend debe exponer endpoint para listar CC visibles al usuario (verificar en el próximo paso; si no existe → anotar en §5).

---

### [2026-07-15] · /auth/me devuelve CC con nombre (no solo códigos)

**Contexto:** el chip de CC activo en la topbar necesitaba mostrar el nombre legible del centro de costo, no solo el código. `MeResponse` devolvía `centros_costo: list[str]`.

**Decisión:** ampliar `MeResponse.centros_costo` a `list[CentroCostoBreve]` con `{codigo, nombre, abreviado}`. El JWT y el resto de servicios siguen consumiendo solo códigos (sin cambios). El enriquecimiento vive únicamente en `obtener_perfil` (nuevo helper `_centros_costo_directos_detalle`).

**Alternativas descartadas:**
- Nuevo endpoint dedicado `/ref/centros-costo/mis-cc` → sumaría un round-trip al arranque del interno.
- Solo mostrar el código → mala UX; el usuario no reconoce "010101" tan rápido como "OF. Presupuesto".

**Impacto:**
- Backend: `schemas/auth.py` (nuevo `CentroCostoBreve`), `services/auth_service.py` (`_centros_costo_directos_detalle`).
- Frontend: `store/auth.ts` (`UserProfile.centros_costo` ahora es `CentroCostoBreve[]`), `store/contexto-interno.ts` nuevo, `components/nav/ChipContexto.tsx` nuevo.

---

### [2026-07-15] · Etapa A · paso 2: Sidebar + Topbar refinados

**Contexto:** cerrar la infraestructura visual del interno antes de rediseñar el dashboard T-44.

**Decisión:** entregables del paso 2:
- Nuevo store persistido `store/contexto-interno.ts` (Zustand + persist) con `añoActivo` (default 2026) y `ccActivo`. Se hidrata al login y en `checkAuth`; se resetea en `resetSession`.
- Nuevo `components/nav/ChipContexto.tsx` con `ChipAñoActivo` y `ChipCentroCostoActivo` (dropdown accesible, `role="listbox"`).
- Nuevo `components/nav/BreadcrumbsAuto.tsx` que lee `useMatches()` y traduce segmentos a etiquetas legibles; el `TopbarInterno` lo usa por defecto (soporta `breadcrumbs` custom por prop).
- `SidebarInterno` añade en el footer chip de rol (`ShieldCheck`) y bloque "Unidad activa" con nombre y código del CC actual.
- `TopbarInterno` incorpora los chips de contexto (visibles ≥ md) y el buscador EXP_SIAF se mueve a lg para no saturar.

**Alternativas descartadas:**
- Selector nativo `<Select>` de shadcn/radix para los chips → aria más complejo, no se integra bien con el estilo redondeado "chip". Se usa un dropdown custom pequeño con la misma pauta que el menú de usuario del topbar.
- CC en sidebar en vez de topbar → contradice la decisión previa.

**Impacto:** todas las páginas del interno ya heredan año + CC activos vía el store. Cuando T-44..T-55 implementen sus hooks, deben leer `useContextoInterno` en vez de pedir el año por prop.

---

### [2026-07-15] · Nuevo endpoint `GET /interno/saldos/resumen` (T-44)

**Contexto:** el dashboard T-44 necesitaba KPIs agregados de saldos (PIM, devengado, saldo disponible, % ejecución, semáforo, top-N metas críticas) para el widget principal. La implementación previa traía las primeras 100 filas de `/interno/saldos` y sumaba en cliente — silenciosamente incorrecto si el usuario tiene >100 metas visibles y duplicaba la lógica del semáforo.

**Decisión:** endpoint dedicado con una sola agregación en SIGA (`SIG_TECHO_PRESUPUESTO`) que devuelve totales + top-3 metas críticas + conteos (`metas_total`, `metas_criticas`). El semáforo se calcula backend usando `sistema.umbrales_alertas` (misma fuente que el resto del sistema).

**Alternativas descartadas:**
- Traer más filas (size=500): sigue frágil ante un CC con muchas metas y desperdicia payload.
- Diferir a T-48: dejaría el widget de saldos como placeholder durante toda la Etapa B; el dashboard perdería su tercer pilar visual y quitaría un motivo de entrada al panel.

**Impacto:**
- Backend: `repositories/saldos_repo.py` (`resumen_saldos`), `services/saldos_service.py` (`resumen_saldos`), `routers/saldos.py` (`GET /resumen`), `schemas/saldos.py` (`SaldosResumenResponse`, `MetaCritica`).
- Frontend: `features/dashboard/api.ts` (`useResumenSaldos`), `features/dashboard/types.ts` (`SaldosResumen`, `MetaCritica`), `WidgetSaldos.tsx`.

---

### [2026-07-15] · Filtro `centro_costo` opcional en endpoints internos (T-44)

**Contexto:** los chips de año + CC del topbar existían desde el paso 2 pero eran cosméticos: cambiarlos no afectaba a ninguna consulta. Rompía §1.3 (contexto siempre visible) y contradecía la decisión previa del chip de CC (§6, 2026-07-15) sobre "un solo lugar de control".

**Decisión:** todos los endpoints internos consumidos por el dashboard aceptan un query param opcional `centro_costo`. Cuando viene, se llama a `permisos_service.restringir_a_subrama(...)` que:
1. Valida que el CC exista y esté activo.
2. Expande su subrama descendiente vía `ltree` (`ruta <@ raiz.ruta`).
3. Intersecta con los `centros_permitidos` del usuario (nunca escala el alcance).
4. Si el CC queda fuera del alcance, devuelve `[]` (no 403) — el filtro pudo ser válido antes; no rompemos la sesión.

Endpoints modificados: `/interno/pipeline/kanban`, `/interno/pedidos`, `/interno/alertas/pedidos-estancados`, `/interno/saldos`, `/interno/saldos/resumen`, `/interno/saldos/metas-rezagadas`. **No aplicado** a `/interno/alertas/contratos-por-vencer` — ver anotación en §5.2.

**Alternativas descartadas:**
- Endpoint dedicado `/me/scope` que resuelva el alcance y todos los demás lo lean: mueve estado del servidor al cliente y agrega latencia a cada consulta.
- Solo permitir el CC exacto (no la subrama): rompe el caso decisor (debe ver toda su gerencia; con "solo exacto" tendría que iterar cada CC hijo).

**Impacto:** todos los hooks del dashboard (`useKanban`, `useResumenSaldos`, `usePedidosEstancados`, `useMetasRezagadas`) incluyen año y CC del store en su `queryKey`, disparando refetch al cambiar los chips del topbar. Este es el patrón a replicar en T-45..T-52.

---

### [2026-07-15] · Rediseño T-44 Dashboard bienvenida (Etapa A · paso 3)

**Contexto:** cerrar la Etapa A del rediseño (§2). El dashboard previo tenía saludo relleno "Bienvenido, X", widgets con datos hardcodeados (`contratos_por_vencer: 0`, `metas_rezagadas: 0`), sumatoria de saldos en cliente sobre las primeras 100 filas, `AccesosRapidos` que duplicaba el sidebar, y `WidgetPipeline` con `var(--chart-*)` (colores categóricos usados en un flujo lineal, semánticamente incorrecto).

**Decisión:** entregables del paso 3:
- `PageHeader` con nombre + rol + CC activo (nombre y código) + año como línea de contexto pegajoso. Se cumple §1.1 principio 3 sin ocupar el widget de saludo.
- Grid 3-columnas: `WidgetAlertas` (pedidos estancados · metas rezagadas · contratos por vencer, cada fila con link a su vista dedicada), `WidgetPipeline` (conteos por etapa con paleta institucional gradada azul→turquesa→gris cerrado), `WidgetSaldos` (KPIs + top-3 metas críticas + semáforo backend).
- `UltimosPedidos` con key compuesta `(ano, nro_pedido, tipo_bien)`, chip de etapa que resalta pedidos estancados con `dias_en_etapa`, y link a `/interno/pedidos/:nro/:tipo` (stub hasta T-46).
- Rutas stub agregadas al router para `/interno/pipeline`, `/interno/pedidos/:nro/:tipo`, `/interno/contratos`, `/interno/cruce`, `/interno/proveedores` — los links del dashboard son navegables aunque las páginas destino sean placeholders hasta T-45..T-53. Consistente con el stub previo `/interno/saldos`.
- `AccesosRapidos` deja de usarse (queda huérfano; se descartará en la limpieza de T-45 junto con la mudanza del feature pipeline).

**Alternativas descartadas:**
- Tres dashboards distintos por rol → ya descartado en decisión previa. Se mantiene un solo `DashboardWidgets` con datos filtrados por el backend.
- `WidgetPipeline` con `var(--chart-1..5)` → los tokens `--chart-*` son categóricos (5 fuentes de financiamiento); el pipeline es un flujo lineal donde la intensidad debe crecer con el avance. Se usa gradación `primary/25 → primary/50 → primary/75 → secondary → muted-foreground/40`.

**Impacto:** cierra la Etapa A. El sistema queda listo para arrancar Etapa B (T-45 Pipeline kanban). El patrón "hooks leen store + queryKey incluye año/CC" es la referencia para el resto del interno.

---

### [2026-07-16] · T-45 Pipeline kanban con 6 macrofases (no 5 columnas)

**Contexto:** el mockup textual de HU-09 propone "5 columnas: Solicitado, Con orden, Conformidad, Devengado, Cerrado" pero el backend/SIGA ya modela el pipeline con **6 macrofases**: solicitud, programacion, certificacion, contratacion, ejecucion, cierre. El widget del dashboard (Etapa A · paso 3) también las usa. Adoptar las "5 columnas" del mockup implicaría duplicar taxonomía y desalinear miniatura vs. pantalla completa.

**Decisión:** el kanban usa **6 columnas correspondientes a las macrofases del SIGA**. Cada columna es expandible a sus etapas (13 servicios / 16 bienes) con un botón "Ver etapas" — respeta §1 principio 5 (jerarquía MEF/SIGA) y §1.1 (densidad progresiva).

**Filtros MVP (AC-09.3 parcial):**
- Tipo B/S (radio group) — implementado.
- Solo estancados (toggle) — implementado, atajo a vista de trabajo urgente.
- Búsqueda por N° pedido — implementado.
- **Diferidos a v2:** rango de fechas y filtro por proveedor (requieren backend/query nuevos que no aportan al día a día del operativo — anotado en §7.1).

**Paginación por columna:** con 1023 pedidos en `cierre` y 782 en `ejecucion`, renderizar todo bloquea el DOM. Cada columna muestra los primeros 20 (estancados primero, luego por días descendente) y ofrece "Cargar 20 más". Es la opción más simple sin introducir virtualización — si en la práctica el usuario se cansa de paginar, escalar a `react-virtual`.

**Estilo:** misma gradación de colores que el `WidgetPipeline` del dashboard (primary/25 → primary → secondary → muted). Semáforo NO se usa (según design-master); estancados se marcan con `border-l-4 border-l-destructive` + `AlertTriangle`, respetando §1.1 "Semáforo con etiqueta, color como refuerzo".

**Alternativas descartadas:**
- 5 columnas literales del mockup HU-09 → contradice taxonomía SIGA canónica y widget dashboard.
- Virtualización con `@tanstack/react-virtual` → complejidad prematura; paginación explícita cubre el caso.
- Filtros avanzados (fecha + proveedor) en MVP → no aportan a lo urgente y complican el estado local; postergado.

**Impacto:**
- Nuevo feature `features/pipeline/` con `PedidoCard`, `KanbanColumn`, `FiltrosPipeline`, `secciones/PipelineKanban`.
- Nueva página `pages/interno/Pipeline.tsx`.
- Router: stub `/interno/pipeline` reemplazado por lazy-load.
- `DashboardWidgets.RESUMEN_VACIO` extendido con `mef: null` (para satisfacer el tipo actualizado en la sesión previa).
- `useKanban()` en `features/dashboard/api.ts` se reutiliza tal cual — cambio del año/CC en topbar dispara refetch automático (patrón del paso 3 de Etapa A confirmado).

---

### [2026-07-15] · Dashboard adaptativo, no tres dashboards

**Contexto:** decidir si operativo/decisor/admin ven layouts distintos o el mismo con datos filtrados.

**Decisión:** un solo `DashboardWidgets` con datos filtrados por el backend según JWT. Los widgets se muestran/expanden según rol (regla §1 principio 11: cero hardcoding de rol en UI, la decisión la resuelve el backend).

**Alternativas descartadas:** tres componentes distintos por rol — divergencia de código, más mantenimiento, y contradice el principio de que el backend resuelve el alcance.

**Impacto:** un único `DashboardWidgets.tsx`, sin ramas por rol. El backend debe devolver datos ya filtrados en `/interno/pipeline/kanban`, `/interno/saldos`, `/interno/alertas/*`.

---

## 7. Preguntas abiertas que deben resolverse pronto

Cosas que necesitan definición del usuario o del backend antes de que bloqueen una pantalla. Se resuelven o se convierten en decisiones (§6) o en issues backend (§5).

- ~~**Filtro global de año en la topbar:** ¿el año se elige una vez por sesión y se aplica a todo, o cada pantalla lo trae en sus filtros?~~ **Resuelto [2026-07-15]:** global en topbar (ver §6).
- **Anotaciones internas de pedido (HU-10):** ¿los operativos pueden ver anotaciones de otros usuarios de su misma unidad, o solo las propias?
- **Alertas "marcar como revisada" (HU-11):** ¿la revisión es por usuario o por unidad? (Impacta el modelo `sistema.alertas_revisadas`.)
- **Exportación desde tabla (HU-15, HU-21):** ¿se exporta la tabla con los filtros aplicados o el dataset completo? (Recomendado: con filtros aplicados, siempre.)
- **Vista consolidada de meta (HU-13):** ¿el acordeón inicia todo colapsado, o con "Presupuesto" y "Órdenes" expandidos por defecto?
- **Configuración de umbrales (HU-18):** ¿los cambios aplican inmediato para todos, o requieren un flujo de aprobación?

### 7.1 Diferido a versiones futuras (v2+)

Se deja constancia de qué funcionalidades avanzadas quedan **fuera del MVP a propósito**, para no meter presión al alcance pero tenerlas anticipadas en la arquitectura (feature aislado por dominio, hooks reutilizables).

- **Comparativo multi-año** (2023 vs 2024 vs 2025 vs 2026) en dashboard y detalle de meta. Backend: query sobre `siaf.ejecucion_presupuestal` con `GROUP BY ANO_EJE`. Frontend: gráfico de líneas + tabla.
- **Proyección de cierre de ejercicio** por meta y por CC (regresión simple sobre devengado mensual). Requiere módulo `analitica/` nuevo.
- **Dashboard ejecutivo** para gerente municipal: 6-8 KPIs de alto nivel, sin drill-down. Complementa HU-22, no la reemplaza.
- **Alertas por email/WhatsApp** (idea-principal §6.3.3). Requiere servicio de notificaciones + preferencias por usuario.
- **Filtros guardados** ("Mis vistas"): que el funcionario guarde combinaciones de filtros con un nombre.
- **Vista mobile del interno.** El MVP prioriza escritorio (el uso real es desde oficina). Mobile queda como responsive de emergencia, no como experiencia diseñada.
- **Integración con SSI del MEF** (idea-principal §6.3.2).
- **Reportes de transparencia estándar** auto-generados (idea-principal §10 backlog).
- **Auditoría visible desde UI** (los `logs.auditoria` existen desde el MVP, pero la pantalla de admin para consultarlos es v2).

Cuando una pantalla del MVP se cruce con algo de esta lista, dejar el "gancho" (prop, sección colapsada, endpoint anticipado) pero no implementar. Anotar en §6 la decisión.

---

## 8. Regla general para todos los chats

- **No inventar datos ni campos.** Si un dato falta, se pregunta o se marca como pendiente en §5.
- **No refactorizar fuera del alcance de la tarea.** Si se ve algo mejorable en otra pantalla, se anota, no se toca.
- **Un commit por tarea.** Aunque tome varios chats terminar una tarea, el commit se hace cuando la tarea está lista y probada.
- **Trunk-based.** Commits directos a `main`, sin feature branches (regla del plan).
- **Mantener esta guía viva.** Al terminar un chat, actualizar §4, §5, §6 según corresponda. Es lo que permite que el próximo chat retome sin perder contexto.

---

*Guía operativa · Frontend interno · Continuación de la Fase 5 · Julio 2026*
