# Bitácora de Decisiones del Agente

## T-32 · Cliente API con axios + interceptor de auth
**Fecha:** 2026-07-11
**Estado:** completado

### Decisiones tomadas
- **Almacenamiento del token en memoria** — Se optó por usar una variable en memoria (`let accessToken`) en lugar de `localStorage` para mitigar vulnerabilidades XSS de libro de texto. Sugerido por el supervisor.
- **Lock de Concurrencia (refreshPromise)** — Se implementó un lock basado en promesas para evitar que múltiples requests concurrentes que devuelven `401` disparen múltiples llamadas de refresh simultáneas. Sugerido por el supervisor.
- **Traducción de Errores Pydantic** — Se desarrolló un mapeo manual para traducir los errores técnicos de Pydantic al español llano, manteniendo el tono institucional. *Aclaración:* El diccionario usado (`field required`, `string too short`, etc.) asume los mensajes por defecto de Pydantic v2 genéricos y no está validado contra un esquema custom de FastAPI de T-08 (ya que T-08 aún no se ha examinado). Se validará su estructura final posteriormente. Propuesto por el agente, refinado por el supervisor.

### Preguntas resueltas
- **¿Cuál es el prefijo de la API?** → Se confirmó revisando `main.py` que el prefijo oficial es `/api/v1`. Se actualizó la configuración de `api-client.ts` para usar este prefijo concatenado al `VITE_API_URL`.

### Pendientes / deuda técnica
- Sustituir la redirección rústica `window.location.href = '/login'` en `forceLogout()` por un manejador centralizado del store. Se resolverá en la **T-34 (Zustand)**.

### Verificación realizada
- `npm run build` → **Éxito**. La compilación de TypeScript no arroja errores de tipado (se corrigió un warning menor de verbatimModuleSyntax).
- Test de concurrencia automatizado (`src/lib/api-client.test.ts` con Vitest + axios-mock-adapter) → **Éxito**. 5 requests a una ruta protegida con status 401 generaron exactamente **1** llamada a `/api/v1/auth/refresh`. Al fallar el refresh simulado, redireccionó a `/login` sin entrar en loop.

### Correcciones del supervisor
- **Regla de Proceso (Commits)**: Queda estrictamente prohibido usar `git commit --amend` sobre un commit que ya fue reportado y validado por el supervisor. Cualquier adición (como un test nuevo) debe ir en un commit separado para mantener la trazabilidad.
- Requerir token en memoria en lugar de `localStorage` por seguridad anti-XSS.
- Exigir un lock explícito en el refresco del token para evitar condiciones de carrera y loops infinitos con la ruta de refresh.
- Exigir historial de commits granular por unidad verificable para habilitar un `git bisect` funcional.
- Añadir fallback en español llano para los errores crudos de Pydantic.

### Commits
- T-32: test de camino de éxito — refresh exitoso reintenta con token nuevo (`b690636`) *(Aclaración: El test se sumó al mismo commit de concurrencia original vía `amend` antes de que se estableciera la nueva política restrictiva de git. Se corrige la referencia).*
- T-32: corregir tipado estricto en test de concurrencia (`22597e9`) *(Aclaración: El commit anterior introdujo un indexado agresivo `responses[0].status` en el test de vitest que rompía la compilación de TypeScript por posible valor undefined. En lugar de hacer amend al ya reportado b690636, se creó este commit de fix separado según la regla vigente).*
- T-32: api-errors con parser FastAPI (`c29d123`)
- T-32: lock de refresh + manejo de 401 y reintentos (`d29314d`)
- T-32: api-client base con token en memoria (`77f5007`)
- T-32: instalar axios (`8de2ef4`)

## T-33 · Router + protección de rutas
**Fecha:** 2026-07-11
**Estado:** completado

### Decisiones tomadas
- **Nomenclatura y Rutas:** Se mantuvo `InternoLayout.tsx` y `RequireAuth.tsx`, y se mapeó el panel a `/interno/*` (resolviendo la inconsistencia original del Done-Cuando que decía `/panel/*`).
- **Separación Público vs Interno:** `/` no redirige forzosamente a `/login`. Utiliza un `PublicLayout` abierto, resguardando así el propósito fundamental del portal ciudadano.
- **Manejo de Rehidratación (F5):** `useAuth` retorna `{ isAuthenticated, isLoading }`. Mientras `isLoading` es `true`, `RequireAuth` muestra "Cargando..." y no evalúa redirecciones, evitando expulsiones falsas en refrescos de página.
- **Autorización (RequireRole):** Se creó un stub `RequireRole` que "falla cerrado" comprobando estrictamente una igualdad `===` con el rol actual. Si el rol no existe o no coincide, bloquea el acceso.
- **Destino de Redirección de RequireRole:** Se decidió conscientemente que ante un fallo de autorización (usuario autenticado pero sin rol) se redirija a `/interno` (su dashboard seguro) en lugar de expulsarlo a `/login`, mejorando la UX al no invalidar una sesión activa válida.

### Pendientes / deuda técnica
- Sustituir el estado local de `useAuth` por la conexión real con el store en la **T-34 (Zustand)**.
- Sustituir el stub de `RequireRole` para consumir el rol real del usuario desde Zustand.
- Reemplazar los stubs de componentes de React por las páginas verdaderas (T-35, etc.).

### Verificación realizada
- `npm run build` → **Éxito**. Compilación TypeScript impecable tras ajustar un error de tipado estricto (`responses[0]!.status`) en el test de T-32 que rompió el build.
- **Prueba Automatizada de RequireAuth:** Se implementó y ejecutó `RequireAuth.test.tsx` bajo JSDOM comprobando íntegramente las 3 fases del guardia (Cargando..., Redirección a /login, Acceso a Contenido Protegido).

### Correcciones del supervisor
- **Corrección de nomenclatura:** Mantener coherencia en los nombres de archivo y de rutas (usar `/interno` pero los nombres `InternoLayout`).
- **Corrección de arquitectura de rutas:** `/` no debe empujar a `/login`, pues destruye la experiencia del portal ciudadano.
- **Exigencia de automatización de pruebas (RequireAuth):** La prueba del ciclo de `isLoading` de `RequireAuth` (caso F5) no debe ser una instrucción manual de "abrir devtools", sino un test automatizado formal (usando `@testing-library/react`).
- **Exigencia de automatización de pruebas (RequireRole):** Se exigió que todo guard de autorización nuevo esté rigurosamente cubierto por tests desde su nacimiento para prevenir vulnerabilidades silenciosas donde una mala evaluación booleana conceda acceso libre a rutas sensibles (ej: `/admin`).

### Commits
- T-33: test automatizado de RequireRole y hook temporal (`19fa2a4`)
- T-33: integración de enrutamiento principal (router.tsx) (`7d1559b`)
- T-33: test automatizado de RequireAuth (`333c7cd`)
- T-33: guardia de autorización (RequireRole) (`2942c11`)
- T-33: guardia de acceso (RequireAuth) (`4548bdf`)
- T-33: hook de autenticación (useAuth) (`7a8009d`)
- T-33: layouts base (PublicLayout e InternoLayout) (`c1acf60`)
- T-33: dependencias de router y testing-library (`7d97b3c`)

## T-34 · Store de Autenticación (Zustand) + Login Page
**Fecha:** 2026-07-11
**Estado:** completado

### Decisiones tomadas
- **Zustand para Auth:** Se implementó el estado global de la sesión usando Zustand.
- **Evitar Expulsiones a Visitantes Anónimos:** Se dividió la lógica de limpieza de sesión en dos: `resetSession()` (silenciosa, no navega, para fallos de hidratación/401) y `logout()` (explícita, navega a `/login` y avisa al backend).
- **Resolución de Race Condition en Hidratación:** El store usa explícitamente `refreshAuthToken()` al arrancar la app. Si otra petición lanza un 401 concurrentemente, ambas comparten el lock de promesa (`refreshPromise`), evitando loops de red.
- **Orden de Inyección:** La inyección del `setResetSessionCallback` hacia `api-client.ts` se realiza en el momento de carga del módulo `store/auth.ts`, garantizando que esté disponible antes del montaje y evitando dependencias circulares.
- **Garantía de No Regresión:** `useAuth` y `useRole` se refactorizaron para extraer datos de Zustand sin modificar su firma de retorno, manteniendo intactos y pasando a la perfección los tests previos de `RequireAuth` y `RequireRole`.

### Pendientes / deuda técnica
- Ninguno por el momento, la integración de Auth es robusta.

### Verificación realizada
- Test unitario de `auth.test.ts` que valida explícitamente `login()` exitoso (token en memoria), el reseteo silencioso de `checkAuth()` y el ciclo de `logout()` explícito.
- Verificación pasiva de la regresión: los test `RequireAuth.test.tsx` y `RequireRole.test.tsx` siguieron pasando (3/3 casos c/u) intactos.
- Build estricto de TypeScript (`npm run build`) validado.

### Correcciones del supervisor
- **Separación reset/logout:** Se exigió no usar una redirección ruidosa a `/login` para fallos de refresco o hidratación, protegiendo así la UX de visitantes anónimos en rutas públicas.
- **Inyección de Token en Orden:** Se solicitó hacer explícita la inyección del token local en el proceso del `login` justo antes de consultar `/auth/me`.
- **Automatización obligatoria:** Exigencia del test automatizado aislado para el store validando el manejo silencioso, el éxito y el cierre explícito.
