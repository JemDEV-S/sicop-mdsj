# 03 — Vistas: kanban, detalle y bolsa (completar, no alarmar, dinamizar)

Se apoya en `Docs/frontend-design-master.md` y el skill de diseño del
proyecto. Nada de librerías nuevas salvo lo indicado; todo con shadcn/ui +
Tailwind + TanStack Query ya presentes.

## 1. Kanban (vista principal)

### 1.1 Tarjeta de pedido v2

Hoy: N°, tipo, monto, solicitante, días, borde rojo si estancado.
Cambios:

- **Fila de identificadores**: `N° 232-2026/S · O/S 232 · SIAF 596` (los que
  existan). Cada uno con copy-on-click. Si el puente no está resuelto, la
  orden se muestra como `O/S de bolsa: 132, 155, 802` en tono muted.
- **Fecha de la etapa actual** en la esquina ("en Ejecución desde 12 mar"),
  en vez de solo "N días" — el usuario ve el hecho, no solo el contador.
- **Badges de alerta v2** (02 §4): rojo solo `estancado_real`; ámbar
  `puente_pendiente`/`conflicto`/`sin_consolidar`; gris `cerrado_negativo`.
  Icono + texto corto ("puente por confirmar"), tooltip con la evidencia.
- Pedido con avance de bolsa no atribuido: check verde suave + "bolsa con
  avance" — invita a entrar al detalle, no alarma.

### 1.2 Columnas y dinamismo

- Mantener macrofases colapsables y paginación de 20; añadir **mini-resumen
  por columna**: `12 en plazo · 3 puente pendiente · 2 estancados` (chips
  clicables que filtran la columna).
- **Filtros persistentes** (Zustand): CC, tipo B/S, nivel de puente, con/sin
  alerta, rango de fechas de registro. URL-sync para compartir la vista.
- **Transiciones**: animar entrada/salida de tarjetas al filtrar
  (`transition-all` + `motion-safe:`), skeletons por columna al cargar,
  `placeholderData: keepPreviousData` de TanStack para no parpadear.
- **Frescura**: pie fijo "Datos SIGA al 30/07 08:30 · MEF al 30/06" con punto
  verde/ámbar según el umbral (viene de `sincronizado_hasta`). Botón
  "Actualizar" que invalida queries; nada de fingir tiempo real.
- Densidad: alternar vista tarjetas ↔ tabla compacta (misma data) para
  usuarios operativos que quieren escanear 100 filas.

## 2. Detalle de pedido (completar la vista)

Estructura v2 en 4 bloques:

1. **Cabecera de identificadores** — los 3 IDs grandes con copy, tipo, CC,
   solicitante, monto del pedido (SIGA, informativo) y estado del puente con
   su nivel. Acción "Actualizar desde SIGA" (refresh puntual, 01 §3).
2. **Timeline del pipeline con fechas** — ya existe `Timeline`; se alimenta
   con `fechas` del API v2 (02 §3): un hito por etapa alcanzada con fecha
   exacta, hito actual resaltado, hitos futuros en fantasma. Añadir los
   estados administrativos reales del seguimiento (VB jefe, aprobado por
   USUARIO el FECHA; denegado si aplica) como sub-hitos expandibles —
   fuente `siga.seguimiento_estados`.
3. **Bloque expediente/orden** — cuando hay orden (propia o de bolsa):
   O/S–O/C, fecha, proveedor, EXP SIGA/SIAF, CCP, fecha compromiso,
   conformidades (lista con fecha y `ESTADO_DEVENG`) o movimientos de
   almacén/pecosa para bienes. Aquí va también el devengado MEF de la celda
   (atribución 1:1 o cobertura, 02 §6).
4. **Bolsa y anotaciones** — la vista de bolsa actual (se mantiene, ver §3)
   y las anotaciones existentes.

## 3. Vista de bolsa (se mantiene y se hace gráfica)

Es la preferencia del usuario y la pieza que resuelve el puente. Conservar
las reglas actuales (orden cronológico neutro, nunca sugerir ganador,
validación de candidatos al asociar, revocación). Mejoras:

- **Grafo de dos columnas** (SVG/flex simple, sin librería): pedidos a la
  izquierda, CCMN a la derecha; aristas = asociaciones (verde=manual,
  azul=declarado, gris punteado=candidato sin resolver). Click en un CCMN
  resalta su cadena dura hacia abajo: cotización → cuadro → **O/S** →
  CCP/SIAF → conformidad, con fechas. Así el usuario VE que "el CCMN 2266 ya
  es la O/S 132 conformada el 07-may" antes de asociar.
- Cada tarjeta CCMN muestra su etapa dura y fecha (dato cierto siempre).
- Al asociar: modal de confirmación que enseña la verificación cruzada
  (02 §5) — si el texto de la orden nombra a otro pedido, advertirlo ahí.
- El botón de asociar sigue exigiendo el flujo actual de resoluciones
  (auditoría incluida).

## 4. Diseño visual y accesibilidad (transversal)

- Semántica de color única en todo el módulo: verde=hecho con fecha,
  azul=en curso normal, ámbar=requiere acción del usuario (puente,
  consolidación), rojo=estancado real probado, gris=terminal/negativo.
  Ámbar ≠ verde ya está normado (T-46); extenderlo a estos 5 valores y
  documentarlo en `frontend-design-master.md`.
- Iconografía constante por etapa (mismo icono en kanban, timeline y bolsa).
- `aria-label` con la evidencia de la alerta; foco visible en tarjetas;
  `motion-reduce` respeta animaciones.
- Tooltips informativos en todos los badges: qué significa el estado y de
  qué tabla/fecha sale (genera confianza en el dato).

## 5. Orden de implementación sugerido (sesiones siguientes)

| Paso | Entregable | Depende de |
|---|---|---|
| 1 | Schema `siga.*` + jobs de sync + watermarks (01) | — |
| 2 | Vista materializada de clasificación + API v2 con `fechas`, `identificadores`, `puente.avance_bolsa` (02) | 1 |
| 3 | Kanban leyendo de Postgres + alertas v2 + frescura (03 §1) | 2 |
| 4 | Detalle completo: timeline con fechas + bloque expediente + refresh puntual (03 §2) | 2 |
| 5 | Bolsa gráfica con cadena dura del CCMN (03 §3) | 2 |
| 6 | Cruce MEF por celda en el detalle + `desfase_devengado` (02 §6) | 2 |
| 7 | Retirar `_SQL_KANBAN` y el composite del camino principal; tests de la clasificación nueva | 3–6 |

Smoke test de aceptación del paso 3 (el caso guía): el pedido 232/S debe
mostrarse **sin alerta roja**, con etapa real (ejecución/devengado con fecha
12-mar si el puente se resuelve; o "bolsa con avance — puente por confirmar"
si no), y con O/S y EXP SIAF visibles.
