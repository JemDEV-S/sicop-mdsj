---
name: frontend-design-system
description: Sistema de diseño institucional de este proyecto (paleta de color, tono, uso de iconos, accesibilidad). CONSULTAR SIEMPRE que se vaya a crear o modificar cualquier componente visual, página, o estilo del frontend — no solo en Fase 4, sino en cualquier fase del proyecto hasta que termine. Se activa ante: nuevos componentes de UI, nuevas páginas, ajustes de estilo/color, decisiones de tono/copy, uso de iconos o cualquier elemento gráfico. Si el agente está por elegir un color, un ícono, un emoji, o el tono de un texto de interfaz y no tiene certeza de que respeta este sistema, debe leer este archivo antes de escribir código.
---

# Sistema de diseño — Proyecto institucional

Este documento es la fuente de verdad visual del proyecto. Se aplica a **toda**
pantalla, componente o texto de interfaz que se construya, en cualquier fase
del pipeline descrito en el README de orquestación de skills (no es exclusivo
de Fase 4 "Fundaciones frontend"). Cada vez que `codebase-design`, `tdd`, o
cualquier tarea de `to-issues` toque el frontend, este documento tiene
prioridad sobre gustos genéricos o defaults de librería.

## 1. Paleta de color institucional

| Rol | Hex | RGB | CMYK | Pantone | Variable CSS |
|---|---|---|---|---|---|
| Blanco | `#FFFFFF` | 255, 255, 255 | 0, 0, 0, 0 | — | `--background` |
| Primario (azul) | `#3484A5` | 52, 132, 165 | 77, 34, 23, 6 | 6797 C | `--primary` |
| Secundario (verde/turquesa) | `#2CA792` | 44, 167, 146 | 75, 8, 51, 0 | 7473 C | `--secondary` |
| Acento (amarillo) | `#F0C84F` | 240, 200, 79 | 7, 21, 77, 0 | 141 C | `--accent` |

**Reglas de uso:**
- El **blanco** no es "el fondo por defecto que trae la librería" — es el
  cuarto color institucional, elegido deliberadamente como base de la
  interfaz. Domina el espacio negativo: fondo principal de página, fondo de
  `Card`, fondo de inputs. Es lo que le da el aire "gubernamental, sobrio"
  al conjunto — nunca reemplazarlo por un gris cálido, crema, o cualquier
  fondo "de diseño" que no sea blanco puro.
- El **azul** es el color dominante de las 3 tintas: navegación, encabezados,
  acciones principales (`Button` variant `default`), enlaces, estado activo.
- El **verde/turquesa** es secundario: confirmaciones, estados positivos,
  acciones secundarias. Coincide con `--semaforo-ok`.
- El **amarillo** es acento/aviso: úsalo con moderación (destacar, advertir,
  llamar la atención puntual), nunca como color de fondo dominante de una
  pantalla completa. Coincide con `--semaforo-alerta`.
- El **rojo funcional** (`--destructive` / `--semaforo-critico`) **no** es
  parte de la paleta institucional pero se mantiene para error/peligro/
  crítico, porque romper esa convención universal perjudicaría la
  comprensión, no la mejoraría. Es la única excepción deliberada.
- No introducir colores fuera de estos 4 (blanco, azul, verde, amarillo) más
  la excepción del rojo funcional — ni variantes de tinte/sombra que no
  estén ya definidas en `globals.css` — sin volver a este documento y
  actualizarlo primero. Si una pantalla nueva "necesita" un color nuevo, es
  señal de que hay que resolverlo con tono/contraste de los 4 colores
  existentes, no agregar un quinto.
- **Nota sobre modo oscuro:** el `.dark` que ya existe en `globals.css` es
  soporte técnico estándar, no una prioridad de este proyecto. El modo claro
  (blanco como base) es el estado por defecto y el que representa la
  identidad institucional — no diseñar pensando "primero dark mode".
- Los valores de la tabla ya están cargados como variables CSS en
  `src/styles/globals.css` (Tailwind v4, formato CSS-first: `:root` +
  `@theme inline`, sin `tailwind.config.ts`) y expuestos como
  `--primary`, `--secondary`, `--accent`, `--semaforo-*`. Usar siempre las
  clases Tailwind (`bg-primary`, `text-secondary-foreground`, etc.), nunca
  hardcodear el hex en un componente.

## 2. Tono e identidad visual

**Gubernamental / institucional, no futurista.** Esto es la restricción de
diseño más importante del proyecto y anula cualquier instinto de "modernizar"
la interfaz:

- Nada de gradientes llamativos, glassmorphism, efectos neón, sombras
  exageradas, ni animaciones decorativas. La superficie es plana, sobria,
  legible.
- Tipografía: sans-serif del sistema o una humanista simple (Inter, Source
  Sans, o la que ya traiga el proyecto vía Tailwind por defecto). Sin
  displays decorativos ni fuentes "tech".
- Bordes con radio moderado (`--radius: 0.5rem`, ya configurado) — ni
  completamente cuadrado (se ve rígido/frío) ni muy redondeado (se ve
  infantil/startup).
- Jerarquía por tamaño y peso tipográfico y por color institucional, no por
  efectos visuales.
- Densidad de información: priorizar que se entienda rápido sobre que se vea
  minimalista. Es preferible una tabla con encabezados claros y datos
  visibles a una interfaz "limpia" que esconde información en tooltips o
  pasos extra.

## 3. Íconos y símbolos

- **Cero emojis**, en ningún texto de interfaz, notificación, email
  transaccional, ni copy del sistema.
- Los íconos están permitidos como apoyo funcional (ej. una lupa en un campo
  de búsqueda, una flecha de orden en una columna de tabla) pero **se
  prefiere activamente la menor cantidad posible de íconos**. Ante la duda
  entre un ícono y una palabra ("Guardar" vs. un ícono de disquete), usar la
  palabra.
- Nunca un ícono como único indicador de una acción o estado sin
  acompañarlo de texto (por accesibilidad y porque el público objetivo no
  necesariamente decodifica convenciones de iconografía de apps consumer).
- El `Semaforo` (T-36) es la excepción ya prevista: ahí el color + texto de
  estado (no solo color) comunican la condición — nunca color solo, para
  quienes tienen dificultades de percepción de color.

## 4. Para el usuario final

Los usuarios de este sistema no son necesariamente personas con experiencia
en apps modernas. Esto condiciona todo el copy y la estructura:

- Lenguaje llano, sin jerga técnica ni anglicismos innecesarios ("Descargar",
  no "Exportar dataset"; "Ingresar", no "Login").
- Cada acción dice exactamente qué hace ("Guardar cambios", no "Confirmar").
- Los mensajes de error explican qué pasó y qué hacer, nunca solo un código
  o un texto genérico ("No se pudo guardar. Verificá tu conexión e intentá
  de nuevo" en vez de "Error 500").
- Evitar dar por sentado que el usuario sabe navegar por convención tácita
  (ej. que un ícono de tres puntos abre un menú). Si hace falta, la palabra
  "Más opciones" al lado del ícono no sobra.

## 5. Checklist antes de dar por cerrada una pantalla o componente nuevo

1. ¿Usa solo los 4 colores institucionales (blanco, azul, verde, amarillo)
   + el rojo funcional de error/crítico? (nada de colores nuevos sin
   actualizar este doc)
2. ¿Evita gradientes, sombras exageradas, glass, neón, animaciones
   decorativas?
3. ¿Tiene cero emojis?
4. ¿Cada ícono usado tiene una alternativa razonable en texto, o texto que
   lo acompañe?
5. ¿El copy usa lenguaje llano y dice literalmente qué va a pasar al
   interactuar?
6. ¿Un usuario sin experiencia previa en el sistema podría usar esta
   pantalla sin ayuda?

Si alguna respuesta es "no", corregir antes de considerar la tarea (T-XX)
terminada — esto aplica al mismo nivel que los criterios de "Done cuando"
de cada issue.

## 6. Dónde viven los tokens en código

- `frontend/src/styles/globals.css` — variables CSS (`:root`, `.dark`,
  `@theme inline`). Tailwind v4 CSS-first: no hay `tailwind.config.ts`.
- `frontend/vite.config.ts` — plugin `@tailwindcss/vite`.
- Componentes base ya alineados: `src/components/ui/button.tsx`, `card.tsx`,
  `input.tsx`, `table.tsx`, `dialog.tsx` (estilo "new-york").

Si se agrega una librería de gráficos (Recharts, T-36) o mapas (Leaflet), sus
colores de series/capas deben derivarse de esta paleta (blanco como fondo,
variaciones de luminosidad de azul/verde/amarillo para las series), no de la
paleta por defecto de la librería.
