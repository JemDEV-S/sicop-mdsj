# Documento maestro de diseño — Frontend

> Municipalidad Distrital de San Jerónimo (Cusco)
> Fase 5 · Frontend por dominio · Guía de rediseño y refactorización
> Julio 2026

---

## 0. Alcance y propósito

Este documento es el **plano conceptual y de implementación** del frontend. Su función es:

1. Consolidar un lenguaje visual único, coherente, **institucional-sobrio**, para todas las pantallas del sistema.
2. Definir la arquitectura de componentes reutilizables **sin acoplamiento excesivo** entre el portal ciudadano y el panel funcionario.
3. Establecer, pantalla por pantalla (T-37 a T-55), qué se ve, qué componentes usa, qué principios respeta.
4. Servir de referencia canónica al refactorizar el código actual (T-37 → T-44 ya implementados) y al construir T-45 en adelante.

**Fuente de verdad visual base:** `.claude/skills/frontend-design-system/SKILL.md`. Este documento **no reemplaza** al skill — lo **operacionaliza**: mientras el skill define reglas (paleta, tono, íconos, checklist), este documento define **estructura de pantallas, patrones repetibles y decisiones concretas**.

**Ámbito de aplicación:** aplica a **toda** pantalla del frontend hasta el cierre del proyecto. Ante conflicto entre este documento y el skill, prevalece el skill (paleta, tono, cero emojis, íconos con texto). Ante conflicto entre este documento y una decisión ad-hoc en código, prevalece este documento — la ad-hoc debe alinearse o justificarse por escrito aquí.

---

## 1. Filosofía del diseño

### 1.1 Un solo sistema, dos audiencias

El sistema atiende dos audiencias muy distintas y no se debe hacer una interfaz híbrida "para los dos":

| Audiencia | Contexto de uso | Prioridad |
|---|---|---|
| **Ciudadano** (portal público) | Navega desde el celular, mayormente. Puede no tener experiencia previa en apps modernas. Quiere **entender** cómo se usan sus impuestos. | Claridad, lenguaje llano, densidad baja, guía visual explícita. |
| **Funcionario** (panel interno) | Usa el sistema como herramienta de trabajo diario en escritorio. Necesita ver mucha información a la vez, filtrar, exportar, cruzar datos. | Densidad alta, atajos, tablas amplias, contexto siempre visible. |

**No se duplica el sistema.** Ambas comparten:
- La **paleta institucional** (blanco, azul `#3484A5`, verde `#2CA792`, amarillo `#F0C84F` + rojo funcional).
- Los **componentes base** (`Button`, `Card`, `Table`, `Input`, `Dialog`, `Semaforo`, `DataTable`, `WrapperGrafico`, `WrapperMapa`).
- Los **formateadores** (moneda, fecha, porcentaje).
- El **cliente API** y los hooks de dominio.

**Lo que se diferencia** son los **layouts**, la **densidad** y el **copy**. Concretamente:

| Aspecto | Ciudadano | Funcionario |
|---|---|---|
| Layout | Header horizontal simple + contenido centrado (`max-w-6xl`) + footer institucional | Sidebar de navegación fija + topbar contextual + contenido `full-width` con `padding` |
| Densidad base | Espaciado `space-y-8`, tarjetas grandes (`p-6` a `p-8`), tipografía `text-base` mínima | Espaciado `space-y-4` a `space-y-6`, tarjetas compactas (`p-4`), tipografía `text-sm` aceptable en tablas y metadata |
| Tono del copy | Explicativo: "Consulta el estado de los proyectos y cómo se usan los recursos" | Operativo: "Pipeline · 87 pedidos activos · 12 estancados" |
| Íconos | Como apoyo visual en la home y en cabeceras de sección; siempre con etiqueta al lado | Funcionales, en botones de acción y widgets; con etiqueta cuando la acción no sea obvia |
| Datos por pantalla | Bajo (1 KPI + 1 gráfico + 1 tabla resumida), progresivo | Alto (varios widgets simultáneos, tablas de N filas, cruces entre secciones) |

### 1.2 No acoplar

**Regla operativa** para evitar acoplamiento excesivo:

1. **Los componentes de `src/components/`** son **agnósticos de dominio**. Un `DataTable` no sabe que existen las obras, ni un `Semaforo` sabe que existen las metas. Reciben `props` y renderizan.
2. **Los componentes de `src/features/<dominio>/`** son **específicos del dominio**. Solo ahí se importan tipos del dominio (`ObraCardResponse`), se llaman hooks del dominio (`useObras`), se aplican formateos particulares.
3. **Las páginas de `src/pages/`** son **componentes de composición**. Reciben parámetros de ruta, orquestan features, y no llevan lógica de negocio en sí — la delegan al feature.
4. **Los layouts de `src/app/layouts/`** son **contenedores estructurales**. No conocen ningún dominio. El sidebar del `InternoLayout` recibe la config de secciones vía `props` o desde un módulo declarativo, no hardcodea rutas de "obras" o "pipeline".
5. **Un componente ciudadano nunca importa uno interno y viceversa.** Si ambos comparten estructura, se **extrae al nivel `src/components/`** (agnóstico) o se **duplica intencionalmente** (dos versiones que evolucionan por separado). Nunca `SomeSharedThing` que se ramifica internamente con `if (esInterno)`.
6. **Cada feature es un módulo aislado**: `api.ts`, `types.ts`, `hooks.ts`, `secciones/*.tsx`. La página lo consume, no interviene en su implementación.

**Prueba de humo:** si se borrara la carpeta `features/pipeline/`, no debería romperse ninguna pantalla del ciudadano. Y viceversa.

### 1.3 Restricciones no negociables (del design system skill)

Repetidas aquí porque son la base y se olvidan:

1. **Solo 4 colores institucionales** + rojo funcional. Prohibido `slate`, `indigo`, `violet`, `emerald`, `amber` de Tailwind salvo el gris de texto muted institucional.
2. **Cero emojis** en cualquier texto de interfaz. Los mockups del doc de HU los usan como shorthand — se traducen a íconos Lucide + etiqueta.
3. **Nada de gradientes, glass, neón, sombras exageradas, animaciones decorativas.** Superficie plana, sobria.
4. **Cada ícono va con texto o alternativa razonable.** Nunca un ícono solo como acción.
5. **Copy en lenguaje llano.** "Descargar" no "Exportar dataset". "Ingresar" no "Login".
6. **El blanco es el 4to color institucional**, no un default. Fondos: blanco puro. Sub-fondos: `--muted` (gris institucional muy claro).

---

## 2. Tokens visuales operacionales

### 2.1 Colores (recordatorio, ver `globals.css`)

Ya cargados como variables CSS. **Usar clases Tailwind, nunca hex.**

| Uso | Clase | Cuándo |
|---|---|---|
| Fondo de página | `bg-background` (blanco) | Siempre |
| Fondo de sección secundaria | `bg-muted` (gris institucional muy claro `hsl(210 16% 95%)`) | Sidebars, sub-secciones, filas alternas de tabla |
| Superficie de tarjeta | `bg-card` (blanco) + `border border-border` | Todas las Cards |
| Texto principal | `text-foreground` | Títulos, contenido principal |
| Texto secundario | `text-muted-foreground` | Metadata, ayudas, descripciones |
| Texto sobre azul/verde | `text-primary-foreground` / `text-secondary-foreground` (blanco) | Botones primarios/secundarios |
| Acción principal (botón, link activo, header) | `bg-primary` / `text-primary` / `border-primary` | Navegación, botón principal, enlaces |
| Acción secundaria / éxito | `bg-secondary` / `text-secondary` | Confirmaciones, "guardado" |
| Aviso / atención | `bg-accent` / `text-accent` | Alertas moderadas, destacar KPI |
| Error / crítico | `bg-destructive` / `text-destructive` | Errores, umbral crítico |
| Semáforo OK | `bg-[var(--semaforo-ok)]` (via `<Semaforo estado="ok" />`) | ≥ umbral verde |
| Semáforo alerta | `bg-[var(--semaforo-alerta)]` | Entre umbrales |
| Semáforo crítico | `bg-[var(--semaforo-critico)]` | < umbral crítico |
| Series de gráficos | `--chart-1` a `--chart-5` (via CSS var) | Recharts, siempre en este orden |

**Prohibido:** cualquier clase `text-slate-*`, `text-gray-*` (Tailwind default), `bg-blue-500`, `bg-amber-500`, `bg-emerald-500`, `bg-indigo-500`, `bg-violet-500`, `bg-red-50`, `bg-red-200`, etc. Todo debe pasar por las variables institucionales.

**Excepción única:** clases de texto muy neutro donde el token no aplica claramente. En ese caso usar `text-foreground/60` (opacidad) sobre `text-foreground`, o `text-muted-foreground`. Nunca `text-gray-500` directo.

### 2.2 Tipografía

Sans-serif por defecto del sistema (Tailwind: `font-sans` → `ui-sans-serif, system-ui, ...`). No importar fuentes externas.

| Uso | Clase | Notas |
|---|---|---|
| H1 página ciudadana | `text-3xl md:text-4xl font-bold text-foreground` | Encabezado principal |
| H1 página interna | `text-2xl font-bold text-foreground` | Menos declarativo |
| H2 sección | `text-xl font-semibold text-foreground` | Título de sección |
| H3 subsección | `text-lg font-semibold text-foreground` | Título de tarjeta grande |
| Título de widget | `text-sm font-semibold uppercase tracking-wide text-foreground` | Consistente en todos los widgets |
| Body ciudadano | `text-base text-foreground` | Legibilidad para no-expertos |
| Body interno | `text-sm text-foreground` | Densidad de trabajo |
| Metadata / descripción | `text-sm text-muted-foreground` | Ambos |
| KPI grande | `text-3xl font-bold text-foreground` | Números destacados |
| Monospace (CUI, RUC, códigos) | `font-mono text-sm text-muted-foreground` | Códigos técnicos |

**Regla:** Nunca `font-black` (demasiado peso). Nunca `italic` para énfasis (usar `font-semibold`). Nunca `underline` fuera de enlaces.

### 2.3 Espaciado y layout

Se usan los tokens de Tailwind (`space-y-4`, `p-6`, etc.) con esta convención:

| Contexto | Espaciado |
|---|---|
| Entre secciones principales de página ciudadana | `space-y-8` |
| Entre secciones principales de página interna | `space-y-6` |
| Entre bloques dentro de una sección | `space-y-4` |
| Padding interno de tarjeta grande | `p-6` (ciudadano) / `p-5` (interno) |
| Padding interno de tarjeta compacta | `p-4` |
| Gap entre filas de widgets | `gap-4` (interno) / `gap-6` (ciudadano) |
| Ancho máximo de contenido ciudadano | `max-w-6xl mx-auto` |
| Ancho máximo de contenido interno | `max-w-full` con `px-6` en `<main>` |

**Bordes:** `rounded-md` (10 px) para tarjetas y botones. `rounded-lg` (12 px) reservado para contenedores grandes (mapa, gráfico grande). **Nunca `rounded-full`** salvo `Semaforo`, `Avatar`, y los puntos de leyenda.

**Sombras:** solo `shadow-sm` para elevar tarjetas sobre `bg-muted`. `shadow-md` o mayor está prohibido — remite a diseño startup.

### 2.4 Íconos

Librería única: **`lucide-react`** (ya en uso). No mezclar con otras.

**Set canónico** (siempre estos, no cambiar sinónimos):

| Concepto | Ícono | Uso |
|---|---|---|
| Obras públicas | `Building2` | Módulo obras |
| Ejecución presupuestal | `BarChart3` | Módulo ejecución, gráficos generales |
| Proveedores | `Users` | Módulo proveedores |
| Mapa | `MapPin` | Módulo mapa, ubicaciones |
| Pipeline / cadena | `GitBranch` | Módulo pipeline |
| Saldo / dinero | `Wallet` | Widgets de saldo |
| Alerta / atención | `AlertTriangle` | Widgets de alertas, indicadores de estancado |
| Reporte / documento | `FileText` | Documentos, exportaciones (junto con la palabra "Descargar") |
| Búsqueda | `Search` | En input de búsqueda |
| Filtro | `Filter` | Botones de filtro avanzado |
| Cerrar / borrar filtro | `X` | Chip removible |
| Descargar | `Download` | Botón descarga |
| Ver más / navegar | `ArrowRight` | Enlaces "Ver todo" |
| Volver | `ArrowLeft` | Volver a listado |
| Ordenar | `ArrowUpDown` | Encabezado de columna ordenable |
| Configuración | `Settings` | Admin, umbrales |
| Usuarios | `UserCog` | Gestión de usuarios |
| Cerrar sesión | `LogOut` | Topbar |
| Reloj / tiempo | `Clock` | "Última actualización", timeline |

**Reglas:**
- Tamaño estándar: `w-4 h-4` en cuerpo de texto, `w-5 h-5` en cabecera de widget, `w-6 h-6` solo en la home ciudadana (tarjetas grandes de módulos).
- Color: siempre hereda del contenedor (`text-primary`, `text-muted-foreground`, `text-foreground`). **Prohibido** `text-amber-500`, `text-emerald-500`, etc.
- Nunca solo. Siempre acompañan a texto o dentro de un botón cuya `aria-label` explica la acción.

### 2.5 Estados

| Estado | Presentación | Copy |
|---|---|---|
| Cargando (skeleton) | Bloques `bg-muted animate-pulse rounded-md` en la forma del contenido futuro | Sin texto |
| Cargando (spinner) | Nada de spinners salvo en botones tras click | "Guardando..." |
| Vacío (sin datos aún) | Ícono grande (`w-12 h-12 text-muted-foreground`), título, subtítulo explicativo, CTA opcional | "No hay pedidos que mostrar. Ajusta los filtros o prueba otro rango de fechas." |
| Error de red | Tarjeta con `border-destructive` (no `bg-red-50`), ícono `AlertTriangle`, mensaje explicativo, botón "Reintentar" | "No se pudo cargar la información. Verifica tu conexión e intenta de nuevo." |
| Error 404 en detalle | Igual que error de red pero copy específico | "No encontramos la obra con código {codigo}. Es posible que haya sido movida o no exista." |
| Éxito puntual (guardado, subida) | Toast breve con `bg-secondary text-secondary-foreground` | "Cambios guardados." |

**Prohibido:** mensajes tipo "Error 500", "Undefined", "null", códigos HTTP directos. Siempre traducir a lenguaje humano.

---

## 3. Arquitectura de componentes

### 3.1 Capas

```
src/
├── app/
│   ├── App.tsx                    # Providers globales
│   ├── router.tsx                 # Definición de rutas
│   └── layouts/
│       ├── PublicLayout.tsx       # Portal ciudadano (header + main + footer)
│       └── InternoLayout.tsx      # Panel funcionario (sidebar + topbar + main)
│
├── components/                    # AGNÓSTICOS de dominio. Reutilizables por AMBAS audiencias.
│   ├── ui/                        # shadcn/ui base (Button, Card, Input, Table, Dialog, Badge)
│   ├── Semaforo.tsx               # Badge color + texto (ya existe)
│   ├── tabla/DataTable.tsx        # Tabla con orden/filtro/paginación (ya existe)
│   ├── grafico/WrapperGrafico.tsx # Wrapper Recharts con paleta institucional
│   ├── mapa/WrapperMapa.tsx       # Wrapper Leaflet con marcadores color-semáforo
│   ├── layout/                    # NUEVOS componentes de layout
│   │   ├── PageHeader.tsx         # H1 + descripción + acciones (ambos)
│   │   ├── EmptyState.tsx         # Estado vacío estandarizado
│   │   ├── ErrorState.tsx         # Estado de error con reintento
│   │   ├── LoadingSkeleton.tsx    # Skeletons por forma (card, table, grafico)
│   │   └── SectionCard.tsx        # Card contenedor de sección con título opcional
│   ├── forms/                     # Wrappers de campos con label + error
│   │   ├── FormField.tsx
│   │   └── FiltroChips.tsx        # Chips de filtros activos removibles
│   └── nav/                       # NUEVOS componentes de navegación
│       ├── HeaderPublico.tsx      # Header del portal ciudadano
│       ├── FooterPublico.tsx      # Footer institucional
│       ├── SidebarInterno.tsx     # Sidebar del panel funcionario
│       └── TopbarInterno.tsx      # Topbar (breadcrumbs, usuario, logout)
│
├── features/                      # ESPECÍFICOS de dominio. Un módulo por dominio.
│   ├── auth/
│   ├── obras/
│   ├── ejecucion/
│   ├── proveedores/
│   ├── pipeline/                  # NUEVO
│   ├── saldos/                    # NUEVO
│   ├── cruce/                     # NUEVO
│   ├── dashboard/                 # widgets del dashboard interno
│   └── alertas/                   # NUEVO (widget compartido de alertas)
│
├── pages/                         # COMPOSICIONES. Una página = una ruta.
│   ├── publico/
│   │   ├── Home.tsx
│   │   ├── ObrasListado.tsx
│   │   ├── Obra.tsx
│   │   ├── EjecucionDashboard.tsx
│   │   ├── EjecucionDetalle.tsx
│   │   ├── DirectorioProveedores.tsx
│   │   └── Mapa.tsx
│   ├── auth/Login.tsx
│   ├── interno/
│   │   ├── Dashboard.tsx
│   │   ├── Pipeline.tsx
│   │   ├── Pedido.tsx
│   │   ├── Saldos.tsx
│   │   ├── CruceExpediente.tsx
│   │   ├── MetaConsolidada.tsx
│   │   ├── Proveedores.tsx
│   │   ├── Proveedor.tsx
│   │   ├── ObraEditar.tsx
│   │   └── ObservacionesCiudadanas.tsx
│   └── admin/
│       ├── Usuarios.tsx
│       └── Configuracion.tsx
│
├── lib/                           # utilidades transversales
├── store/                         # Zustand stores
└── styles/globals.css             # tokens CSS
```

**Regla operativa:** todo componente que se use en más de un dominio y no dependa de tipos de dominio → `src/components/`. Todo lo que dependa de tipos o hooks de un dominio → `src/features/<dominio>/`.

### 3.2 Componentes nuevos a construir (prerrequisito de la refactorización)

Antes de rediseñar cada pantalla, hay que crear estos componentes reutilizables. Sin ellos, cada pantalla vuelve a inventar la rueda y se rompe la coherencia.

#### 3.2.1 `components/layout/PageHeader.tsx`

Cabecera de página estándar. Reemplaza los múltiples patrones de "H1 + descripción + botón" que hoy están duplicados en cada página.

```tsx
interface PageHeaderProps {
  titulo: string;
  descripcion?: string;
  acciones?: React.ReactNode;   // botones a la derecha
  breadcrumbs?: React.ReactNode; // opcional
}
```

Estructura visual:
```
[Breadcrumbs opcionales]
[Título grande]                          [Acciones alineadas a la derecha]
[Descripción en muted-foreground]
─────────────────────────────────────── (border-b border-border)
```

Uso en ciudadano: `text-3xl md:text-4xl font-bold`. En interno: `text-2xl font-bold`. Detecta el layout activo vía prop `densidad="publico" | "interno"` (default `"interno"`).

#### 3.2.2 `components/layout/SectionCard.tsx`

Contenedor de sección con título y contenido. Reemplaza los `<div className="bg-white rounded-lg border border-slate-200 p-5">` esparcidos.

```tsx
interface SectionCardProps {
  titulo?: string;
  icono?: LucideIcon;
  accion?: React.ReactNode;    // link "Ver todo →" a la derecha
  children: React.ReactNode;
  padding?: 'sm' | 'md' | 'lg'; // p-4 / p-5 / p-6
}
```

Siempre `bg-card border border-border rounded-md`. El título va con `text-sm font-semibold uppercase tracking-wide text-foreground` + ícono opcional a la izquierda con `text-primary` (no colores random).

#### 3.2.3 `components/layout/EmptyState.tsx`

Estado vacío estandarizado.

```tsx
interface EmptyStateProps {
  icono?: LucideIcon;
  titulo: string;
  descripcion?: string;
  accion?: { label: string; onClick?: () => void; href?: string };
}
```

#### 3.2.4 `components/layout/ErrorState.tsx`

Estado de error con reintento.

```tsx
interface ErrorStateProps {
  titulo?: string;              // default "No se pudo cargar la información"
  descripcion?: string;         // default explicativo
  onReintentar?: () => void;    // muestra botón "Reintentar" si se pasa
}
```

Usa `border-destructive` (borde), **no** `bg-destructive` (llena) — un fondo rojo intenso en pantalla completa es agresivo. Ícono `AlertTriangle` en `text-destructive`.

#### 3.2.5 `components/layout/LoadingSkeleton.tsx`

Exporta variantes por forma:
- `<SkeletonCard />` — bloque de tarjeta
- `<SkeletonTable rows={5} cols={4} />` — bloque de tabla
- `<SkeletonKPI />` — bloque de KPI
- `<SkeletonGrafico />` — bloque de gráfico

Todos usan `bg-muted animate-pulse rounded-md`. Cero colores custom.

#### 3.2.6 `components/nav/HeaderPublico.tsx`

Header horizontal del portal ciudadano. Estructura:

```
┌────────────────────────────────────────────────────────────────────┐
│ [Escudo][Municipalidad de San Jerónimo · Portal de Transparencia] │
│         [Obras] [Ejecución] [Proveedores] [Mapa]  [Ingresar]      │
└────────────────────────────────────────────────────────────────────┘
```

- Fondo `bg-primary` con `text-primary-foreground` (blanco sobre azul institucional).
- Alto fijo `h-16`. Sticky en `top-0`.
- Logo/escudo del lado izquierdo (por ahora, placeholder de texto "MDSJ" en un cuadrado blanco con azul). El asset se pondrá cuando la muni lo entregue.
- Enlaces principales centrados o alineados a la izquierda del logo, con estado activo `border-b-2 border-accent` (subrayado amarillo) en la ruta actual.
- Botón "Ingresar" a la derecha, variante `outline` sobre fondo azul → borde blanco, texto blanco.
- En móvil (`md:` no aplica): menú hamburguesa clásico con drawer.

#### 3.2.7 `components/nav/FooterPublico.tsx`

Footer institucional.

```
┌────────────────────────────────────────────────────────────────────┐
│ Municipalidad Distrital de San Jerónimo · Cusco                   │
│ Portal de Transparencia · Última actualización: DD/MM/YYYY        │
│                                                                    │
│ [Contacto] [Sobre este portal] [Ley de Transparencia]             │
│                                                                    │
│ Fuente de datos: SIAF (MEF), SIGA, Invierte.pe                    │
└────────────────────────────────────────────────────────────────────┘
```

- Fondo `bg-muted` con `text-muted-foreground`. Alto orgánico según contenido.
- Padding generoso (`py-8 md:py-12`).
- Enlaces subrayados en hover.

#### 3.2.8 `components/nav/SidebarInterno.tsx`

Sidebar fija del panel funcionario. Estructura:

```
┌──────────────────┐
│ MDSJ · Panel     │  ← branding compacto, fondo bg-primary
│ Interno          │
├──────────────────┤
│ ○ Dashboard      │
│ ○ Pipeline       │
│ ○ Saldos         │  ← items con ícono a la izquierda + label
│ ○ Cruce SIAF     │     estado activo: bg-primary/10 border-l-4 border-primary
│ ○ Reportes       │     hover: bg-muted
│ ○ Proveedores    │
├──────────────────┤
│ Administración   │  ← sección plegable si el usuario es Admin
│ ○ Usuarios       │
│ ○ Configuración  │
└──────────────────┘
```

- Ancho fijo `w-64` en desktop. Colapsable a `w-16` (solo íconos) en tablet.
- Fondo `bg-card` con `border-r border-border`.
- Cabecera con `bg-primary text-primary-foreground` (branding).
- Items de nav configurados desde un array `secciones: NavSection[]` recibido por prop — **no hardcodear rutas dentro** del sidebar. La config está en `src/app/nav-config.ts` (nuevo archivo).
- Filtra items según rol del usuario (usa `useAuthStore` o recibe rol por prop).

#### 3.2.9 `components/nav/TopbarInterno.tsx`

Topbar del panel funcionario.

```
┌─────────────────────────────────────────────────────────────────┐
│ Panel Interno / Pipeline / Pedido N° 199-2026                   │
│                          [Buscar EXP_SIAF...🔍]  [Nombre ▼]     │
└─────────────────────────────────────────────────────────────────┘
```

- Alto fijo `h-14`. Sticky en `top-0`. Fondo `bg-card border-b border-border`.
- Breadcrumbs a la izquierda usando `Breadcrumbs.tsx` (que se crea en T-52; hasta entonces, texto simple).
- Buscador global de EXP_SIAF a la derecha (envía a `/interno/cruce/expediente-siaf/{val}`).
- Menú de usuario con dropdown: nombre + rol + acciones (Cambiar contraseña, Cerrar sesión).

#### 3.2.10 `components/forms/FiltroChips.tsx`

Muestra los filtros activos como chips removibles debajo de la barra de filtros. Coherente en todas las listas (obras, saldos, pipeline, proveedores).

```
Filtros activos: [Función: Salud ×] [Año: 2026 ×] [Estancado ×]   Limpiar todos
```

- Chip: `bg-muted text-foreground text-sm px-3 py-1 rounded-md border border-border`.
- Botón "Limpiar todos" solo `text-primary underline` al hover.

#### 3.2.11 `components/grafico/WrapperGrafico.tsx` (revisión)

Ya existe. Auditar que:
- Serie 1 use `var(--chart-1)` (azul), serie 2 `var(--chart-2)` (turquesa medio), etc.
- Tooltips con `bg-card border border-border text-foreground` (nunca fondo negro tipo dark tooltip default).
- Ejes con `stroke-muted-foreground` y texto `text-xs fill-muted-foreground`.
- Grid con `stroke-border` sutil, no gris oscuro.

#### 3.2.12 `components/mapa/WrapperMapa.tsx` (revisión)

Ya existe. Auditar que:
- Marcadores usan color de `Semaforo` (verde/amarillo/rojo) según avance.
- Popup con estilos alineados a Card: `bg-card`, `text-foreground`, `border border-border`.
- Tiles: OpenStreetMap estándar (evitar tiles satelitales para respetar el tono sobrio; el mapa es funcional, no decorativo).

### 3.3 Convenciones de código UI (para el refactor)

1. **Nunca** crear tokens de color inline. Usar clases Tailwind sobre variables CSS ya definidas.
2. **Nunca** usar `style={{ ... }}` para colores/espaciado. Solo para valores dinámicos (ej. `width: ${porcentaje}%`).
3. **Nunca** usar clases legacy: `text-slate-*`, `bg-red-50`, `bg-blue-50`, `text-primary-600`, `text-primary-700`. Solo tokens institucionales.
4. **Siempre** encapsular pantalla en `PageHeader` + secciones en `SectionCard`. No pintar directamente H1 en la página.
5. **Siempre** manejar los 3 estados: `isLoading` → `LoadingSkeleton`; `isError` → `ErrorState`; `data.length === 0` → `EmptyState`.
6. **Siempre** usar `formatearMoneda`, `formatFecha`, `formatPorcentaje` de `lib/formatters.ts`. Nunca `${valor}` crudo para dinero.
7. **Nunca** más de un `H1` por página. Nunca `H3` sin `H2` que lo preceda.
8. **Nunca** enlaces sin `hover:` visible y `focus-visible:` accesible (ring institucional).

---

## 4. Diseño conceptual de cada pantalla

Para cada tarea T-XX se define:
- **Objetivo del usuario** (qué viene a hacer aquí).
- **Anatomía** (secciones de la pantalla).
- **Estados** (loading, error, vacío, éxito).
- **Componentes** (cuáles del sistema usa).
- **Refactor pendiente** (qué está mal hoy).

---

### T-37 · Home ciudadana

**Objetivo del usuario:** entender qué puede hacer aquí y encontrar rápidamente lo que busca (una obra en particular, cómo se gasta el presupuesto, un proveedor).

**Anatomía:**

```
┌────────────────────────────────────────────────────────────────────┐
│ [HEADER PÚBLICO — HeaderPublico]                                   │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│              PORTAL DE TRANSPARENCIA                               │
│              Municipalidad de San Jerónimo                         │
│                                                                     │
│  Consulta las obras públicas y la ejecución del presupuesto        │
│  distrital. Datos actualizados diariamente desde SIAF y SIGA.      │
│                                                                     │
│           [Ver obras públicas]   [Ver presupuesto]                 │
│                                                                     │
├────────────────────────────────────────────────────────────────────┤
│  ¿Qué información encontrarás aquí?                                │
│                                                                     │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐       │
│  │ [Building2]     │  │ [BarChart3]     │  │ [Users]         │       │
│  │ Obras Públicas │  │ Ejecución       │  │ Proveedores    │       │
│  │                │  │ Presupuestal    │  │                │       │
│  │ 70 proyectos   │  │ S/ XX millones  │  │ 2,645 empresas │       │
│  │ activos en     │  │ ejecutados en   │  │ registradas    │       │
│  │ el distrito.   │  │ el año 2026.    │  │ en la entidad. │       │
│  │                │  │                 │  │                │       │
│  │ Ver todas →    │  │ Ver detalle →   │  │ Ver directorio→│       │
│  └────────────────┘  └────────────────┘  └────────────────┘       │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ [MapPin]  Mapa del distrito                                 │   │
│  │                                                              │   │
│  │ Ubica visualmente las obras en curso a lo largo             │   │
│  │ de San Jerónimo.                                             │   │
│  │                                                              │   │
│  │ Ver mapa →                                                   │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
├────────────────────────────────────────────────────────────────────┤
│  Última actualización de datos: 12 de julio de 2026, 03:15         │
├────────────────────────────────────────────────────────────────────┤
│ [FOOTER PÚBLICO — FooterPublico]                                   │
└────────────────────────────────────────────────────────────────────┘
```

**Estados:**
- Loading: no aplica (contenido estático + KPIs con skeleton mientras cargan).
- Error de KPIs: fallback silencioso (no romper la home).

**Componentes:** `HeaderPublico`, `FooterPublico`, `SectionCard`, `Button`.

**Refactor pendiente sobre el código actual:**
- Reemplazar `bg-gray-50`, `border-gray-200`, `text-gray-900`, `text-gray-600`, `bg-blue-50`, `text-primary` inline por tokens institucionales (`bg-background`, `border-border`, `text-foreground`, `text-muted-foreground`, `bg-primary/10`, `text-primary`).
- Cambiar hero de "texto centrado" a título institucional con datos concretos (número de proyectos, monto ejecutado).
- Agregar KPIs dinámicos en las 3 tarjetas de módulo (llamada a `/publico/ejecucion/resumen`).
- Agregar sello "Última actualización" en el pie del contenido (antes del footer).
- Eliminar el "call to action secundario" del footer inline (el enlace "¿Eres funcionario? Ingresa" va en el `HeaderPublico` como botón outline).

---

### T-38 · Portal de obras — listado (HU-01)

**Objetivo del usuario:** encontrar una obra que le interesa (por nombre, por barrio, por función). Ver su semáforo de avance sin abrir el detalle.

**Anatomía:**

```
[HEADER PÚBLICO]

[PageHeader]
  Directorio de Obras Públicas
  70 proyectos activos · Consulta el avance y presupuesto de cada uno.

[SectionCard — Filtros]
  ┌────────────────────────────────────────────────────────────────┐
  │ Buscar: [_____________ 🔍]                                     │
  │ Función: [Todas ▼]   Tipología: [Todas ▼]  Avance: [Todos ▼]   │
  │ [Chips de filtros activos]                                     │
  └────────────────────────────────────────────────────────────────┘

Vista alternante (toggle discreto arriba a la derecha):
  ● Tarjetas  ○ Tabla

[Modo Tarjetas — grid 1 col móvil / 2 col md / 3 col lg]
  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
  │ [Ícono función]  │ │                  │ │                  │
  │ CUI: 2453117     │ │ ...              │ │ ...              │
  │ Movilidad Urbana │ │                  │ │                  │
  │ Cantaritos       │ │                  │ │                  │
  │                  │ │                  │ │                  │
  │ Presupuesto:     │ │                  │ │                  │
  │ S/ 2,340,000     │ │                  │ │                  │
  │                  │ │                  │ │                  │
  │ Avance físico:   │ │                  │ │                  │
  │ [🟢 68%]         │ │                  │ │                  │
  │                  │ │                  │ │                  │
  │ Ver ficha →      │ │                  │ │                  │
  └──────────────────┘ └──────────────────┘ └──────────────────┘
  [< 1 · 2 · 3 ... >]

[Modo Tabla — DataTable]
  CUI | Proyecto | Presupuesto | Avance físico | Estado | Acciones
```

**Estados:**
- Loading: `SkeletonCard` × 9 en grid.
- Error: `ErrorState`.
- Vacío (sin resultados de filtro): `EmptyState` con CTA "Limpiar filtros".

**Componentes:** `PageHeader`, `SectionCard`, `FiltroChips`, `Semaforo`, `DataTable` (modo tabla), `ObraCard` nueva (modo tarjetas).

**Nueva: `features/obras/ObraCard.tsx`** — ficha compacta con imagen (o placeholder), datos clave y CTA.

**Refactor pendiente:**
- Reemplazar `bg-gray-50`, `bg-white`, `text-gray-900`, `border-gray-300`, `rounded-none`, `focus:ring-primary`, `focus:border-primary` por tokens institucionales.
- Agregar modo tarjetas (más ciudadano-friendly) además del modo tabla.
- El input actual usa `rounded-none` (agresivo). Cambiar a `rounded-md`.
- Agregar `FiltroChips` con los filtros activos.
- Migrar el select nativo a `<Select>` de shadcn (consistente con proveedores).

---

### T-39 · Portal de obras — ficha detallada (HU-02)

**Objetivo del usuario:** conocer todo sobre una obra específica: qué es, cuánto avance tiene, cuánto se ha gastado, quién la ejecuta, dónde está.

**Anatomía:**

```
[HEADER PÚBLICO]

← Volver al directorio

[SectionCard — Identificación · destacada]
  CUI: 2453117
  MOVILIDAD URBANA DE LA COMUNIDAD DE CANTARITOS
  Función: Transporte · Tipología: Vías vecinales
  Etapa: En ejecución

[Grid 2 col md]
  [SectionCard — Avance físico]     [SectionCard — Presupuesto]
    Avance: 68%                        PIM 2026: S/ 2,340,000
    [barra progreso grande]            Devengado: S/ 1,590,000 (68%)
    [🟢 Al día]                        Saldo disp: S/ 750,000
                                       [barra ejecución]

[SectionCard — Cronograma]
  Inicio programado: 01/03/2026
  Fin programado: 30/11/2026
  Días transcurridos: 133 / 275
  [timeline horizontal con hitos]

[SectionCard — Ubicación]
  [Mini-mapa Leaflet · marker semáforo]
  Coordenadas: -13.5401, -71.9450
  Barrio: Cantaritos

[SectionCard — Contratista y ejecución]  (mostrar cuando el API lo soporte)
  Contratista: CONSTRUCTORA XYZ SAC
  RUC: 20xxxxxxxxx
  Contrato N°: xxxx-2026
  Ver ficha del proveedor →

[SectionCard — Documentos y fotos]
  Grid de miniaturas de fotos + lista de PDFs con nombre + fecha + tamaño

[SectionCard — Deja tu observación]  (HU-24, cuando esté implementado T-57)
  [formulario con captcha]

[FOOTER PÚBLICO]
```

**Estados:** loading (skeleton por sección), error 404 específico ("No encontramos la obra {codigo}"), sin contratista/docs (no mostrar la sección hasta que haya datos).

**Componentes:** `PageHeader` (sin H1 porque el título va en la SectionCard destacada de Identificación), `SectionCard`, `Semaforo`, `WrapperMapa`, `LoadingSkeleton`, `ErrorState`.

**Refactor pendiente:**
- Reemplazar `bg-red-50 text-red-700 border-red-200` (en error) por `ErrorState`.
- Reemplazar `text-primary-600 hover:text-primary-700` (variantes que no existen en el sistema) por `text-primary hover:underline`.
- Estandarizar el skeleton con `<SkeletonCard />` en vez de `bg-gray-200` inline.
- Envolver todas las secciones en `SectionCard` en vez de estilar cada una a mano.

---

### T-40 · Mapa de obras (HU-04)

**Objetivo del usuario:** ver dónde están las obras en el distrito y saber cuáles van bien o mal.

**Anatomía:**

```
[HEADER PÚBLICO]

[PageHeader]
  Mapa de Obras Públicas
  Ubicación y estado de los proyectos de inversión en San Jerónimo.

[Layout de 2 columnas · lg]
  ┌──────────────────────────────────┐  ┌──────────────────────┐
  │                                  │  │ Filtros              │
  │                                  │  │ Función [▼]          │
  │       [MAPA — 60vh de alto]      │  │ Estado  [▼]          │
  │       marcadores color-semaforo  │  │ Avance  [▼]          │
  │       popup con datos            │  │                      │
  │                                  │  │ Leyenda              │
  │                                  │  │ 🟢 Avance ≥ 70%      │
  │                                  │  │ 🟡 40% – 70%         │
  │                                  │  │ 🔴 < 40%             │
  │                                  │  │                      │
  │                                  │  │ Obras sin coords (12)│
  └──────────────────────────────────┘  │ Cantaritos           │
                                        │ Villa María          │
                                        │ ...                  │
                                        └──────────────────────┘
```

**Estados:** loading (mapa con overlay "Cargando obras..."), error (tarjeta sobre el mapa).

**Componentes:** `PageHeader`, `WrapperMapa`, `SectionCard` (panel lateral), `Semaforo` (leyenda).

**Refactor pendiente:** revisar que `WrapperMapa` use la paleta institucional para marcadores (verde `--semaforo-ok`, amarillo `--semaforo-alerta`, rojo `--semaforo-critico`) y no defaults de Leaflet.

---

### T-41 · Dashboard público de ejecución (HU-05)

**Objetivo del usuario:** ver de un vistazo cuánto presupuesto tiene el distrito y cuánto se ha gastado.

**Anatomía:**

```
[HEADER PÚBLICO]

[PageHeader]
  Ejecución Presupuestal
  Cómo se distribuye y ejecuta el presupuesto del distrito.
  Acciones: [Año 2026 ▼] [Descargar]

[Grid 4 col — KPIs]
  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ PIA      │ │ PIM      │ │ Devengado│ │ Ejecución│
  │ S/ XX M  │ │ S/ XX M  │ │ S/ XX M  │ │   68%    │
  │          │ │          │ │          │ │ [semáforo]│
  └──────────┘ └──────────┘ └──────────┘ └──────────┘

[Grid 2 col lg]
  [SectionCard — Ejecución por función]     [SectionCard — Por fuente]
    [barras horizontales]                     [dona 5 series]

[SectionCard — Ejecución mensual]
  [línea o barras]

[SectionCard — Detalle de metas]
  Enlace/botón: Ver tabla detallada →

[FOOTER PÚBLICO]
```

**Estados:** loading (skeletons por widget), error (por widget, no global — si falla el gráfico de fuente no rompe los KPIs).

**Componentes:** `PageHeader`, `SectionCard`, KPI card (nuevo), `WrapperGrafico`.

**Nuevo: `components/KpiCard.tsx`** — tarjeta con label, valor grande, delta opcional, semáforo opcional.

**Refactor pendiente:**
- Reemplazar `bg-card border rounded-lg` (parcialmente correcto) por `SectionCard`.
- El selector de año inline debe migrarse a `<Select>` shadcn en el `PageHeader.acciones`.
- Botón "Tabla Detallada (HU-06)" `disabled` con texto entre paréntesis → cambiar copy a "Ver detalle por meta" y habilitar el enlace real.
- KPIs no existen aún visualmente en el actual `ResumenKpis` — auditar y estandarizar.
- Colores de gráficos: usar `--chart-1` a `--chart-5` (verificar).

---

### T-42 · Tabla detallada de ejecución (HU-06)

**Objetivo del usuario:** ver la tabla completa de metas y sus montos, poder filtrar y descargar.

**Anatomía:**

```
[HEADER PÚBLICO]

← Volver al dashboard

[PageHeader]
  Detalle de ejecución por meta
  Todas las metas del año {ano} con sus montos.
  Acciones: [Año ▼] [Descargar Excel] [Descargar PDF]

[SectionCard — Filtros]
  Buscar, función, fuente, rango de ejecución.
  [FiltroChips]

[SectionCard — Tabla]
  DataTable con columnas: meta, descripción, PIA, PIM, Certificado, Devengado, Ejecución %, [Semáforo]
  Paginación abajo.
```

**Componentes:** `PageHeader`, `SectionCard`, `FiltroChips`, `DataTable`, `Semaforo`, botón `Download`.

**Refactor pendiente:** cuando se implemente, seguir el mismo patrón que Proveedores.

---

### T-43 · Directorio público de proveedores (HU-07)

**Objetivo del usuario:** ver la lista de proveedores registrados (sin exponer contacto).

**Anatomía:**

```
[HEADER PÚBLICO]

[PageHeader]
  Directorio de Proveedores
  Empresas y personas que brindan bienes y servicios a la entidad.

[SectionCard — Filtros]
  Buscar (RUC o razón social) · Año

[SectionCard — Tabla]
  DataTable: RUC, Razón social, N° órdenes, Monto acumulado
```

**Estados:** ya bien manejados en el código actual (loading, error, tabla).

**Refactor pendiente:**
- Envolver la tabla en `SectionCard`.
- Reemplazar `bg-destructive/15` (variante shadcn no estándar) por `ErrorState`.
- Pasar el `<PageHeader>` en vez del H1 inline actual.
- Está mejor alineado que otras páginas — es la referencia.

---

### T-44 · Dashboard interno de bienvenida (HU-22)

**Objetivo del usuario:** al entrar, saber qué necesita atender hoy.

**Anatomía:**

```
[SIDEBAR INTERNO]     [TOPBAR INTERNO]
                      [Contenido]

┌─────────────────────────────────────────────────────────────┐
│ Bienvenido, José Pérez                                       │
│ Sub. Obras Públicas · Operativo                              │
└─────────────────────────────────────────────────────────────┘

[Grid 3 col lg — Widgets]
  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
  │ [AlertTri.]   │ │ [GitBranch]   │ │ [Wallet]      │
  │ ALERTAS       │ │ PIPELINE      │ │ SALDO DE MI   │
  │               │ │               │ │ UNIDAD        │
  │ 3 pedidos     │ │ 87 pedidos    │ │ S/ 87,540     │
  │ estancados    │ │ activos       │ │               │
  │               │ │               │ │ Ejecución 42% │
  │ 2 contratos   │ │ [barra segm.] │ │ [🟡 Atención] │
  │ por vencer    │ │               │ │               │
  │               │ │ Solicitados 8 │ │               │
  │ Ver alertas → │ │ Con orden 15  │ │ Ver saldos →  │
  │               │ │ Conformidad 12│ │               │
  │               │ │ Devengado 40  │ │               │
  │               │ │ Cerrado 12    │ │               │
  └───────────────┘ └───────────────┘ └───────────────┘

[SectionCard — Últimos pedidos]
  Tabla compacta con 5 filas: N° | Descripción | Monto | Etapa | Fecha

[SectionCard — Accesos rápidos]
  [Pipeline] [Saldos] [Cruce SIAF] [Reportes] [Proveedores]
```

**Estados:** loading (widgets skeleton), error (por widget), vacío (widget dice "Sin alertas pendientes").

**Refactor pendiente (importante — el actual usa muchos colores no institucionales):**
- **Widget Alertas:** `text-amber-500`, `text-amber-600`, `text-orange-600`, `text-red-600` → todo pasa por `text-destructive` o `text-accent-foreground` según severidad. El ícono siempre `text-accent` (amarillo institucional).
- **Widget Pipeline:** las 5 clases `bg-blue-500`, `bg-indigo-500`, `bg-violet-500`, `bg-emerald-500`, `bg-slate-400` → usar `var(--chart-1)` a `var(--chart-5)` para las series (mismos colores que gráficos).
- **Widget Saldos:** `text-emerald-500` (ícono) → `text-secondary` (verde institucional).
- **Fondo tarjetas:** `bg-white rounded-lg border border-slate-200` → `bg-card rounded-md border border-border` vía `SectionCard`.
- **Tabla pedidos:** `border-slate-200`, `hover:bg-slate-50`, `text-slate-500` → `border-border`, `hover:bg-muted`, `text-muted-foreground`.
- **Estado "Sin alertas pendientes":** migrar a `EmptyState`.
- **Widget Error:** `border-red-200` → `border-destructive` con `ErrorState`.
- Extraer widgets a `features/dashboard/widgets/WidgetAlertas.tsx`, `WidgetPipeline.tsx`, `WidgetSaldos.tsx` (hoy están todos en `DashboardWidgets.tsx` — demasiado acoplados).
- Extraer `TablaPedidos` a `features/dashboard/widgets/UltimosPedidos.tsx`.
- Extraer `AccesosRapidos` a `components/nav/AccesosRapidos.tsx` (agnóstico — recibe items por prop).

---

### T-45 · Pipeline kanban (HU-09)

**Objetivo del usuario:** ver de un vistazo todos los pedidos, en qué etapa están, cuáles están estancados.

**Anatomía:**

```
[SIDEBAR] [TOPBAR]

[PageHeader]
  Pipeline de Pedidos
  Vista general de todos los pedidos activos por etapa.
  Acciones: [Filtros] [Descargar]

[Barra filtros horizontal — SectionCard]
  Tipo: [B/S] · Fechas · Área · Proveedor · [FiltroChips]

[Grid 5 col — columnas kanban]
  ┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐
  │ SOLICITADO   ││ CON ORDEN    ││ CONFORMIDAD  ││ DEVENGADO    ││ CERRADO      │
  │ 23           ││ 41           ││ 12           ││ 28           ││ 15           │
  │              ││              ││              ││              ││              │
  │ [card ped.]  ││ [card ped.]  ││ [card ped.]  ││ [card ped.]  ││ [card ped.]  │
  │ [card ped.]  ││ [card ped.  ]││ [card ped.]  ││ [card ped.]  ││ [card ped.]  │
  │ ...          ││ ...          ││ ...          ││ ...          ││ ...          │
  └──────────────┘└──────────────┘└──────────────┘└──────────────┘└──────────────┘

Card pedido:
  N° 199-2026 · Bien
  S/ 25,400
  Sub. Obras Públicas
  Hace 21 días · [AlertTriangle si estancado con borde-l-4 border-destructive]
```

**Nota móvil:** las 5 columnas se apilan verticalmente en pantalla chica (scroll vertical con títulos sticky).

**Componentes:** `PageHeader`, `SectionCard` (barra filtros), `KanbanColumn` (nuevo, en `features/pipeline/`), `PedidoCard` (nuevo). Semáforo NO se usa aquí — el indicador de estancado es un `AlertTriangle` + borde izquierdo destructive.

**Copy:** títulos de columna en `text-sm font-semibold uppercase tracking-wide text-foreground`. Contador de columna a la derecha en `text-muted-foreground`.

---

### T-46 · Detalle de pedido/orden (HU-10)

**Objetivo del usuario:** entender todo del pedido — items, orden asociada, timeline, poder anotar.

**Anatomía:**

```
[SIDEBAR] [TOPBAR con breadcrumbs: Pipeline / Pedido N° 199]

← Volver al pipeline

[SectionCard destacada — Cabecera]
  N° 199-2026 · BIEN
  Solicitante: Sub. Obras Públicas
  Estado actual: Con orden emitida · Hace 21 días [AlertTriangle si estancado]

[Grid 2 col lg]
  [SectionCard — Pedido]         [SectionCard — Orden]
    Fecha pedido, aprobado          N° 187-2026 B
    Meta                            Estado SIAF, Proveedor, EXP_SIAF
    Tabla items                     Monto
                                    [Ver ejecución SIAF →]

[SectionCard — Timeline]
  Lista vertical con puntos:
    [•] 2026-06-15 · Solicitado
    [•] 2026-06-18 · Aprobado
    [•] 2026-06-30 · Orden emitida
    [○] Esperando conformidad...

[SectionCard — Observaciones internas]
  [+ Nueva observación]
  Lista de observaciones anteriores con autor y fecha
```

**Componentes:** `PageHeader`, `SectionCard`, `Table`, `Timeline` (nuevo), `Button`.

**Nuevo: `components/Timeline.tsx`** — lista vertical con puntos (rellenos si completados, vacíos si pendientes), líneas conectoras, fecha y descripción.

---

### T-47 · Alertas de pedidos estancados (HU-11)

**Objetivo del usuario:** ver la lista de sus alertas, marcarlas como revisadas.

**Anatomía:** panel dedicado + widget en dashboard.

```
[SIDEBAR] [TOPBAR]

[PageHeader]
  Pedidos estancados
  Pedidos que superan el umbral de días sin avance en su etapa.
  Acciones: [Umbral: 15 días]

[SectionCard]
  DataTable con: N° pedido | Etapa | Días | Solicitante | Acciones (Ver, Marcar como revisada)
```

**Componente widget:** `features/alertas/WidgetPedidosEstancados.tsx` para el dashboard. En la página completa, `DataTable`.

**Refactor:** cuando se implemente, seguir patrón de `SectionCard` + `DataTable`.

---

### T-48 · Saldos presupuestales (HU-15)

**Objetivo del usuario:** ver saldos disponibles por meta, con semáforo, exportar.

**Anatomía:**

```
[SIDEBAR] [TOPBAR]

[PageHeader]
  Saldos presupuestales
  Consulta el saldo disponible de cada meta.
  Acciones: [Año] [Descargar Excel] [Descargar PDF]

[SectionCard — Filtros]
  Centro de costo · Fuente · Estado semáforo · [FiltroChips]

[Grid 3 col — KPIs de resumen]
  PIM total · Devengado total · Saldo disponible

[SectionCard — Tabla]
  DataTable con: Meta | Descripción | PIM | Certificado | Devengado | Saldo | [Semáforo]
```

**Componentes:** `PageHeader`, `SectionCard`, `KpiCard`, `DataTable`, `Semaforo`, `FiltroChips`.

---

### T-49 · Alertas de metas rezagadas (HU-16)

**Objetivo del usuario:** ver metas con devengado bajo el umbral, poder navegar al detalle.

**Anatomía:** widget en dashboard + panel dedicado, análogo a T-47.

---

### T-50 · Buscador por EXP_SIAF (HU-12)

**Objetivo del usuario:** pegar un EXP_SIAF y ver todo el cruce.

**Anatomía:**

```
[SIDEBAR] [TOPBAR]

[PageHeader]
  Cruce SIAF ↔ SIGA por expediente
  Ingresa el N° de expediente SIAF para consultar la meta, órdenes, pedidos y conformidad asociados.

[SectionCard — Input central]
  Buscar por EXP_SIAF: [_____________ 🔍]
  Sin resultados aún — copy explicativo.

[Cuando hay resultado:]

[SectionCard destacada — Resumen]
  EXP_SIAF: 456789
  Meta: 00121 · Movilidad Urbana Cantaritos
  Proveedor: Constructora ABC (RUC ...)
  Monto: S/ 25,400

[Grid 2 col — Detalles]
  [SectionCard — Ejecución SIAF]      [SectionCard — Órdenes SIGA]
    PIA, PIM, Certificado, Devengado    N° orden, fecha, estado, monto

[SectionCard — Pedido origen]
  Enlace al pedido N° 199-2026 →

[SectionCard — Conformidad]
  Fecha, monto, observaciones
```

**Estados:** vacío al entrar (invitación a buscar); "No se encontró el EXP_SIAF" con `EmptyState`.

---

### T-51 · Vista consolidada por meta (HU-13)

**Objetivo del usuario:** ver todo lo que se ha hecho contra una meta.

**Anatomía:**

```
[SIDEBAR] [TOPBAR con breadcrumbs]

[PageHeader]
  Meta 00121 · Movilidad Urbana Cantaritos
  Consolidado de presupuesto, órdenes, pedidos y conformidades.
  Acciones: [Descargar]

[Grid 3 col — KPIs]
  PIA | PIM | Devengado

[Acordeón vertical]
  ▸ Presupuesto (SIGA y SIAF)
  ▸ Órdenes de adquisición (N filas)
  ▸ Certificaciones (N filas)
  ▸ Conformidades (N filas)
  ▸ Pedidos asociados (N filas)

Cada sección al expandirse muestra tabla o detalle.
```

**Componente nuevo:** `components/Accordion.tsx` (o usar el de shadcn). Cada panel = `SectionCard` interno.

---

### T-52 · Drill-down con breadcrumbs (HU-14)

**Componente reutilizable:** `components/Breadcrumbs.tsx`.

```
Panel Interno / Cruce / Meta 00121 / Orden 187-2026
```

- Estilo: `text-sm text-muted-foreground`, separadores `/`, último ítem sin enlace.
- Se muestra en el `TopbarInterno` para páginas de cruce (T-50, T-51).

---

### T-53 · Directorio interno de proveedores + contratos por vencer (HU-19, HU-20)

**Objetivo del usuario:** ver proveedores con contacto, entrar a un perfil detallado, ver contratos por vencer.

**Anatomía del directorio interno:** igual que el público pero con columnas extra (email, teléfono, N° contratos activos).

**Perfil de proveedor:**

```
[PageHeader]
  CONSTRUCTORA ABC SAC
  RUC: 20xxxxxxxxx
  Contacto: xxx@xxx.pe · 999-999-999

[Grid 2 col]
  [SectionCard — KPIs]                [SectionCard — Contratos activos]
    Total contratado                    tabla
    Órdenes totales
    Última orden

[SectionCard — Historial de órdenes]
  DataTable con filtros
```

**Widget dashboard:** `features/alertas/WidgetContratosPorVencer.tsx`.

---

### T-54 · Gestión de usuarios (HU-17)

**Objetivo del usuario (Admin):** CRUD de usuarios, asignar rol y centros de costo.

**Anatomía:**

```
[SIDEBAR (con sección Admin)] [TOPBAR]

[PageHeader]
  Gestión de usuarios
  Acciones: [Nuevo usuario]

[SectionCard — Filtros]
  Buscar · Rol · Estado (activo/inactivo)

[SectionCard — Tabla]
  DataTable con: Nombre | Email | Rol | CC asignados | Estado | Acciones (Editar, Desactivar)

[Dialog — Editar usuario]
  Nombre completo, email, rol (Select), centros de costo (multi-select), estado, reset password
```

**Componentes:** `PageHeader`, `SectionCard`, `DataTable`, `Dialog` (shadcn), `FormField`.

---

### T-55 · Configuración de umbrales (HU-18)

**Objetivo del usuario:** ajustar umbrales de semáforo y alertas por módulo.

**Anatomía:**

```
[SIDEBAR] [TOPBAR]

[PageHeader]
  Configuración de umbrales
  Define los rangos de semáforo y las condiciones de alerta.

[Tabs — por módulo]
  [Semáforos] [Alertas]

  Panel Semáforos:
    [SectionCard — Ejecución presupuestal]
      Umbral verde ≥: [___] %     Umbral rojo <: [___] %
      [Guardar]

    [SectionCard — Avance físico]
      ...

  Panel Alertas:
    [SectionCard — Pedidos estancados]
      Días máximos en estado: [___]
      [Guardar]

    [SectionCard — Contratos por vencer]
      Días antes del vencimiento para alertar: [___]
      [Guardar]
```

**Componentes:** `Tabs` (shadcn), `SectionCard`, `FormField`, `Button`.

---

## 5. Plan de refactorización recomendado

Este orden minimiza rework y desbloquea cada tarea siguiente:

### Paso 1 · Fundaciones visuales (prerrequisito)

Crear los componentes nuevos que todas las pantallas van a usar:

1. `components/layout/PageHeader.tsx`
2. `components/layout/SectionCard.tsx`
3. `components/layout/EmptyState.tsx`
4. `components/layout/ErrorState.tsx`
5. `components/layout/LoadingSkeleton.tsx`
6. `components/forms/FiltroChips.tsx`
7. `components/KpiCard.tsx`

**Criterio de done:** todos con story de ejemplo funcionando en `Sandbox.tsx`.

### Paso 2 · Navegación institucional

8. `components/nav/HeaderPublico.tsx`
9. `components/nav/FooterPublico.tsx`
10. `components/nav/SidebarInterno.tsx`
11. `components/nav/TopbarInterno.tsx`
12. `app/nav-config.ts` (config declarativa de secciones)
13. Refactor de `app/layouts/PublicLayout.tsx` para usar Header + Footer.
14. Refactor de `app/layouts/InternoLayout.tsx` para usar Sidebar + Topbar.

**Criterio de done:** al recorrer la app (home, obras, dashboard interno), la navegación es visible, consistente, con la paleta institucional.

### Paso 3 · Refactor de pantallas T-37 a T-44 (una por una)

En este orden, para validar el sistema antes de avanzar:

15. **T-37 Home** — más simple, pruebas de header/footer.
16. **T-43 Directorio Proveedores** — ya cerca del estándar, primera aplicación de `PageHeader` + `SectionCard`.
17. **T-38 Obras Listado** — introduce `FiltroChips` y modo tarjetas.
18. **T-39 Obra ficha** — introduce `SectionCard` en grid, `ErrorState`, `LoadingSkeleton`.
19. **T-41 Ejecución Dashboard** — introduce `KpiCard` y validación de paleta en Recharts.
20. **T-40 Mapa** — valida `WrapperMapa` con colores institucionales.
21. **T-44 Dashboard interno** — extrae widgets a `features/dashboard/widgets/*`, aplica tokens institucionales, migra AccesosRapidos.

Cada uno con smoke test manual (arrancar dev server, verificar visualmente).

### Paso 4 · Pantallas nuevas T-45 en adelante

Ya con el sistema consolidado, T-45 a T-55 se construyen directamente sobre él sin necesidad de refactor posterior.

---

## 6. Checklist antes de dar por cerrada cualquier pantalla

Extiende el checklist del skill `frontend-design-system`:

1. ¿Usa **solo tokens institucionales** (paleta + tokens de `globals.css`)? Cero `slate/gray/blue-500/amber/emerald/indigo/violet`.
2. ¿Envuelve el contenido en `PageHeader` + `SectionCard` en vez de estilar cada bloque a mano?
3. ¿Maneja los 3 estados (loading con `LoadingSkeleton`, error con `ErrorState`, vacío con `EmptyState`)?
4. ¿Los filtros activos se ven vía `FiltroChips` en vez de solo estar en los selects?
5. ¿Los íconos siempre acompañan a texto o al menos tienen `aria-label` claro?
6. ¿Cero emojis en el JSX final (los mockups del doc de HU los usan, pero se traducen a íconos Lucide)?
7. ¿Los enlaces son navegables por teclado con `focus-visible:` visible?
8. ¿La densidad respeta la audiencia (`space-y-8` ciudadano vs `space-y-6` interno)?
9. ¿El copy es lenguaje llano ("Descargar" no "Exportar", "Ingresar" no "Login")?
10. ¿La página se puede recorrer con lector de pantalla (encabezados jerárquicos, roles, labels en inputs)?

Si alguna respuesta es "no", corregir antes de considerar la tarea terminada.

---

## 7. Preguntas abiertas / decisiones pendientes

- **Escudo de la Municipalidad:** placeholder por ahora; el asset final se integra cuando la muni lo provea. Ubicación: `frontend/public/logo-mdsj.svg`.
- **Fuente tipográfica:** por ahora `font-sans` del sistema. Si la muni tiene tipografía institucional (Inter, Source Sans, etc.), se integra vía `<link>` en `index.html` sin cambios en tokens.
- **Modo oscuro:** soportado técnicamente en `globals.css` pero no priorizado como identidad. Ninguna pantalla se diseña "dark-first".
- **Idioma:** todo en español peruano. No i18n en el MVP.
- **Toast/Notificaciones:** decidir librería (sonner viene con shadcn) y ubicación estándar (arriba a la derecha).
- **Confirmaciones destructivas:** definir componente `ConfirmDialog` reutilizable cuando aparezca el primer caso (probablemente T-54, desactivar usuario).

---

## 8. Cierre

Este documento se **mantiene vivo** durante el resto de la Fase 5. Cada vez que aparezca una decisión de diseño no cubierta acá (por ejemplo, cómo se ve una alerta de contrato por vencer, o qué patrón sigue una tabla con expandable rows), se añade la sección correspondiente en vez de resolverlo ad-hoc en el código.

**Referencias cruzadas:**
- `CLAUDE.md` — contexto de proyecto y reglas de negocio.
- `.claude/skills/frontend-design-system/SKILL.md` — paleta y tono.
- `Docs/actividad-2-requerimientos-funcionales.md` — HUs y mockups textuales originales.
- `Docs/actividad-3-arquitectura-tecnica.md` §8 — arquitectura frontend.
- `Docs/actividad-5-plan-desarrollo.md` — T-37 a T-55 con dependencias.

*Documento maestro de diseño · Frontend · Fase 5 · Julio 2026*
