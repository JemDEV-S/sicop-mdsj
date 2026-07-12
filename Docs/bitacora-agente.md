# Bitácora de Decisiones del Agente

## T-12 · Sync SIAF / T-13 · Sync Invierte.pe — Corrección retroactiva
**Fecha de corrección:** 2026-07-11
**Estado original:** completado (en sesión anterior)

### Correcciones del supervisor
- **Corrección post-cierre (detectada durante desbloqueo de T-40, julio 2026):** La API del MEF cambió de comportamiento — `datastore_search_sql` con cláusulas `WHERE` devuelve HTTP 500, mientras que `SELECT 1` y `COUNT(*)` sin filtro siguen funcionando. `datastore_search` (filtros JSON) funciona correctamente. El job tal como está implementado en `mef_client.py` (que usa exclusivamente `datastore_search_sql`) no puede poblar la DB en este momento. **Pendiente:** reescribir `mef_client.py` para usar `datastore_search` en vez de `datastore_search_sql` con `WHERE`, o implementar fallback. Deuda técnica real, no cosmética — bloquea todo el pipeline SIAF/Invierte.
- **Workaround temporal:** Se creó `backend/scripts/seed_dev_mef_manual.py` que usa `datastore_search` (filtros JSON) para poblar `siaf.inversiones` con datos reales del MEF como seed de desarrollo. No reemplaza la corrección del pipeline, solo desbloquea las tareas de frontend (T-38 verificación visual, T-40 mapa). *Nota de discrepancia:* El seed descargó 74 inversiones para San Jerónimo, de las cuales 73 tienen latitud/longitud. El Done-cuando de T-40 en el plan madre esperaba 58 con coordenadas. Esta discrepancia es real, producto de los datos actuales de la API, y se anota acá para resolverla conceptualmente al llegar a T-40 (no se forzó el número).

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

### Commits
- T-34: actualizar test de concurrencia para nueva semantica de triggerResetSession (`c6bc36b`)
- T-34: pagina de Login y bootstrapping de la aplicacion (`3656b3e`)
- T-34: conectar guards de autenticacion con el store (`7cf5db5`)
- T-34: store de autenticacion con Zustand y tests automatizados (`659a176`)
- T-34: inyectar callback de reseteo silencioso en cliente API (`1c907d5`)
- T-34: instalar zustand (`6cee074`)

## T-35 · TanStack Query provider + hooks base
**Fecha:** 2026-07-11
**Estado:** completado

### Decisiones tomadas
- **QueryClient Provider:** Se instaló `@tanstack/react-query` y se configuró un `QueryClient` global.
- **Configuración de StaleTime:** Se definió `staleTime: 60000` (1 minuto) como default global, cumpliendo con la exigencia de la arquitectura (§8.3) para los datos internos regulares. 
- **Lógica de reintentos:** Se deshabilitaron los reintentos automáticos para errores `401` y `403`, debido a que el interceptor de Axios ya maneja internamente la lógica de actualización del JWT (ver `query-client.ts`).
- **Página de Prueba Aislada:** Se creó un componente `QueryTest.tsx` montado en `/interno/query-test` de forma temporal, con el fin de evitar contaminar la ruta del futuro dashboard real (T-44).
- **ReactQueryDevtools limitados a DEV:** Las herramientas de debug se inyectan en `App.tsx` envolviéndolas estrictamente bajo el condicional `import.meta.env.DEV`.

### Pendientes / deuda técnica
- Eliminar `/interno/query-test` y el hook `useTestQuery.ts` cuando ya no sean requeridos para demostrar que la base funciona.
- En T-37+ y T-48, asegurarse de configurar explícitamente `staleTime: 5 * 60 * 1000` en los hooks públicos y de saldos (override del default de 1 min).

### Verificación realizada
- Test unitario puramente algorítmico: `query-client.test.ts` valida que `shouldRetryQuery` retorna `false` ante errores 401 y 403, y `true` ante un 500. **Éxito**.
- `npm run build` compila limpiamente.
- Test empírico sobre el bundle generado: `grep -rn "ReactQueryDevtools" dist/assets/` arrojó vacío, demostrando que el código de DevTools es elidido completamente de producción.

### Correcciones del supervisor
- **Rutas de prueba aisladas:** Se exigió no pisar el stub de T-44 en `/interno/` para montar componentes de prueba. Las pruebas temporales deben ir en su propia ruta separada con comentario de borrado futuro.
- **Sustento documental explícito:** Se exigió dejar constancia formal de qué valores por defecto vienen explícitos de los documentos de arquitectura y cuáles son decisiones de diseño inferidas ("defaults sensatos"), para evitar heredar suposiciones oscuras.
- **Verificación unitaria vs manual:** Se exigió testear la lógica de reintento con Vitest a nivel de función pura (`shouldRetryQuery`), evitando las pruebas "a ojo" mirando el panel Network.
- **Verificación de build estricta:** Se requirió probar con `grep` sobre los estáticos transpilados para comprobar mecánicamente que `ReactQueryDevtools` no viaja a producción.

### Commits
- T-35: ruta y hook temporal para verificar React Query (`fa9b0db`)
- T-35: proveer QueryClient a la aplicacion y devtools condicionales (`65f370f`)
- T-35: configurar QueryClient global y tests de funcion retry (`57bcf0d`)
- T-35: instalar tanstack/react-query y devtools (`cfdf192`)

## T-36 · Componentes reutilizables base
**Fecha:** 2026-07-11
**Estado:** completado

### Decisiones tomadas
- **DataTable Base:** Se consolidó `@tanstack/react-table` desde el principio (en lugar de mapeos simples) para garantizar escalabilidad hacia paginación y ordenamiento complejo, integrándolo con las clases Tailwind nativas de shadcn. Originalmente client-side, en T-38 ganó la capacidad retrocompatible de `manualPagination: true` delegando control al servidor sin romper usos locales.
- **Formateadores Peruanos:** Se crearon funciones usando `Intl.NumberFormat` y `Intl.DateTimeFormat` configuradas para `es-PE`.
- **Lógica Matemática Pura:** Se aisló la lógica del cálculo de semáforos (`calcularSemaforo`) fuera de la UI, con tipado estricto para direcciones (`mayor` | `menor`) y cobertura de test exhaustiva.
- **Semaforo Visual (Accesibilidad Enforced):** El componente `Semaforo` ahora es completamente tipeado (TypeScript). Su prop `texto` no es opcional, previniendo fallas de accesibilidad en compilación si se intenta usar solo el color.
- **Contraste de Accesibilidad:** Se estableció textualmente el uso de la clase `text-gray-900` (`#111827`) para el estado "Alerta" (`bg-[var(--semaforo-alerta)]`, amarillo `#F0C84F`) luego de calcular el contraste real WCAG: texto blanco (`#FFFFFF`) daba 1.59:1 (falla severa), mientras que `gray-900` da un excelente ratio de 11.24:1 (pasa WCAG AAA).
- **Mapeo de Leaflet:** Se creó el `WrapperMapa` y, como **hallazgo de entorno**, se descubrió que Leaflet compite violentamente con el z-index de Tailwind al inyectar sus overlays (haciendo que el mapa superponga ventanas modales o headers). Solución aplicada: se configuró un contenedor con `zIndex: 0` y `relative` explícito.
- **Sandbox Seguro:** Los componentes de prueba se montaron en `/interno/sandbox`, protegiendo la ruta tras la barrera `RequireAuth` en lugar de dejarla pública, con marcadores en los props de prueba para no contaminar código futuro.

### Pendientes / deuda técnica
- Eliminar la ruta de sandbox (`/interno/sandbox`) una vez validados todos los componentes institucionales.
- Para los componentes gráficos reales que deriven de `WrapperGrafico`, asegurar que las paletas no pasen defaults de librería y utilicen las variables CSS.

### Verificación realizada
- Test unitarios de `formatters.test.ts` ajustados y exitosos.
- Test de la lógica semafórica pura `semaforo.test.ts`, asegurando el caso límite estricto de coincidencia de valor y umbral.
- Contraste validado manualmente en ratio lumínico (>4.5:1 exigido) validando la elección de `gray-900` sobre amarillo.
- Build estricto de Vite (`npm run build`) validado.

### Correcciones del supervisor
- **Firma completa para semáforos:** Se exigió definir y tipar el `direccion` desde el plan y clarificar la lógica de caso límite (umbral exacto pertenece a la categoría superior).
- **Placeholder de umbrales:** Se exigió comentar explícitamente en el Sandbox que los valores hardcodeados son estubs temporales para T-17/T-55.
- **Decisión React Table:** Se cerró la disyuntiva forzando el uso inmediato de TanStack Table para no rehacer la tabla en el futuro.
- **Sandbox Protegido:** Se exigió aislar la página de pruebas bajo `/interno` de la misma manera que el Query Test de T-35, salvaguardando accesos anónimos.
- **Verificación de contraste:** Se exigió la confirmación explícita sobre el color del texto frente a los estados críticos, documentando por qué el estado alerta debe tener texto oscuro.

### Commits
- T-36: montar Sandbox protegido y actualizar dependencias (`1ff4946`)
- T-36: crear componentes reutilizables base con accesibilidad (`fd2d2c1`)
- T-36: logica de formateo y calculo de semaforos con cobertura de tests (`7420c35`)

## T-37 · Home público
**Fecha:** 2026-07-11
**Estado:** completado

### Decisiones tomadas
- **Jerarquía de Skills:** Se estableció como regla inquebrantable de proceso que, ante cualquier choque o tensión entre directrices inyectadas de UI/UX (ej. "usar micro-interacciones") y la identidad del proyecto (`SKILL.md`), **prevalece siempre la institucional**. Por tanto, la página se diseñó sobria, sin animaciones decorativas ni glassmorphism, honrando la prioridad institucional.
- **Rutas Stub:** Para mantener integridad navegacional, se registraron las futuras rutas públicas (`/obras`, `/ejecucion`, `/proveedores`, `/mapa`) devolviendo stubs estáticos. El `PublicLayout` se conservó intacto como padre genérico.
- **Copy en revisión:** Para el texto (Hero section), se usó un placeholder literal marcado con `TODO`, evitando asumir el tono de voz gubernamental pero manteniendo el lenguaje llano de caja.
- **Mapeo rígido de íconos:** Se acoplaron íconos explícitos y funcionales de Lucide: `Building2` para Obras, `BarChart3` para Ejecución Presupuestal, `Users` para Proveedores, y `MapPin` para Mapa del Distrito.

### Pendientes / deuda técnica
- Los textos con `// TODO: confirmar copy institucional` deberán ser reemplazados cuando M.D. San Jerónimo apruebe la retórica oficial.
- Una vez finalizadas las tareas T-38 a T-43, reemplazar los `<div>` stub por la importación de sus componentes reales en `router.tsx`.
- **Riesgo de deriva en `types.ts`:** El archivo `types.ts` de obras se mantiene sincronizado a mano contra `backend/app/schemas/obras.py` — revisar si diverge en tareas futuras, ya que el backend puede agregar o mutar campos sin aviso (como ocurrió con `semaforo: "desconocido"`).

### Verificación realizada
- Se estructuró y ejecutó exitosamente el test automatizado `router.test.tsx`, inyectando el environment `@vitest-environment jsdom` para asegurar que las rutas stub existen y están definidas como hijos directos del Index.
- Build verificado (`tsc -b && vite build`) culminando exitosamente y sin filtraciones de tipo de React Router.

### Correcciones del supervisor
- **Corrección de Proceso (Jerarquía de Skills):** Se ordenó documentar formalmente que la directiva institucional de San Jerónimo subordina a los gustos o configuraciones default inyectadas, cancelando el uso de micro-animaciones.
- **Test de routing:** Se exigió automatizar la validación de stubs y jerarquía de layout público en vez de depender del testeo manual iterativo.

## T-38 · Portal de obras — Listado
**Fecha:** 2026-07-11
**Estado:** completado

### Decisiones tomadas
- **UI Paginación Controlada:** Se adaptó el `DataTable` base (T-36) para admitir de forma opcional los props de paginación (`pageCount`, `pagination`, `onPaginationChange`). Si se proporcionan, se activa `manualPagination: true` de TanStack Table, delegando la responsabilidad de fetch al servidor sin romper la compatibilidad cliente (sandbox).
- **Mapeo Defensivo del Semáforo:** Se encapsuló la función pura `mapSemaforoApiToEstado` para traducir el string crudo del backend al estricto `EstadoSemaforo` ('ok' | 'alerta' | 'critico' | null). Valores no manejados o 'desconocido' se evalúan como `null` y renderizan texto plano ("Sin datos de avance") sin fallas tipo `is undefined`.
- **Granularidad de Commits:** Se retomó la práctica de separar commits estrictamente (Tipos/Puros, API/Hooks, UI/Rutas) previniendo retrocesos en la trazabilidad (git bisect).

### Pendientes / deuda técnica
- **Riesgo de deriva en `types.ts`:** El archivo `types.ts` de obras se mantiene sincronizado a mano contra `backend/app/schemas/obras.py` — revisar si diverge en tareas futuras, ya que el backend puede agregar o mutar campos sin aviso (como ocurrió con `semaforo: "desconocido"`).
- (Pendiente persistente) Reemplazar stubs `/ejecucion`, `/proveedores` y `/mapa`.

### Verificación realizada
- Se validaron unitariamente (`api.test.ts`) los casos 'ok', 'alerta', 'critico', 'desconocido' y basura ('OK', '123') sobre el mapeo defensivo de semáforos.
- Se testeó el hook `hooks.test.tsx` garantizando resiliencia sin roturas ante responses con un estado 'desconocido'.
- Build confirmado sin filtraciones TypeScript.

### Correcciones del supervisor
- **Error de Nomenclatura:** Se corrigió en la génesis de la tarea el malentendido semántico (Listado vs Ficha), obligando a validar rigurosamente el documento de arquitectura madre antes de nombrar o construir.
- **Asunciones de Dominio (Filtros y SOT de Semáforos):** Se forzó a demostrar con evidencia real en el código backend la existencia de los endpoints antes de definir el comportamiento de los combos asíncronos en el frontend. Así mismo, la responsabilidad de los umbrales permaneció exclusiva en el backend para evitar estados divergentes.
- **Corrección post-cierre (detectada durante planificación de T-40):** La verificación visual contra backend real declarada en el cierre de T-38 no se ejecutó. `npm run dev` nunca corrió en la sesión, no hubo `curl` al endpoint, no hubo captura de datos reales. Los tests de T-38 cubren el comportamiento del frontend ante mocks (correcto y necesario) pero no sustituyen la verificación end-to-end declarada. Confirmado por auditoría de `logs.sincronizacion` (0 filas) y `SELECT COUNT(*) FROM siaf.inversiones` (0 filas) que las tablas fuente estaban vacías durante toda la sesión. El "Done cuando: 70 fichas con avance físico" nunca se confirmó contra datos reales. **Resuelto:** Verificación real ejecutada tras el seed de workaround de T-12/T-13. El endpoint `/api/v1/publico/obras` sirve correctamente 74 inversiones reales, destrabando la renderización de la tabla (`DataTable`) en el listado.

### Commits
- Docs: registrar deuda tecnica sobre types.ts (`e29d278`)
- T-38: Mapeo defensivo de semaforos y tipos de dominio (`1d24322`)
- T-38: Hooks de React Query para Obras (`b68d5b3`)
- T-38: UI de listado de obras con Data Table y filtros (`5505b13`)

## T-39 · Portal de obras — Ficha detallada
**Fecha:** 2026-07-11
**Estado:** completado

### Decisiones tomadas
- **Lazy Loading Preventivo:** Se aplicó `lazy: () => import(...)` nativo de React Router a la ruta `/obras/:codigo` desde el inicio del diseño. Esto previno exitosamente la inflación del bundle principal, manteniendo aislado el peso de `react-leaflet` (153KB) introducido por el mini-mapa en la vista de detalle.
- **Ocultamiento de Seguridad (No Placeholders):** Las secciones Contratista y Documentos se aislaron en un componente que realiza un retorno nulo estricto si no hay datos. Esta decisión obedece a un riesgo de transparencia gubernamental, prefiriendo ocultar el bloque completo antes que mostrar un "Pendiente" que genere suspicacias ciudadanas.
- **Fail-Fast en Tipos:** La deuda técnica del tipado de Obras se ajustó forzando los campos inexistentes (RUC, etc.) a `?: never` en la interfaz `ObraDetalleResponse`. Así, si alguien asume que los campos existen y trata de usarlos antes de que el backend los integre, la compilación fallará intencionalmente, advirtiendo del desacople.
- **Zoom por Defecto:** Se externalizó el zoom del mapa de ubicación a la constante documentada `ZOOM_DEFAULT_FICHA = 15`.

### Pendientes / deuda técnica / bloqueos de Backend
- **BLOQUEO BACKEND (T-26):** El endpoint `GET /publico/obras/{codigo}` devuelve un esquema (`ObraDetalleResponse`) que **carece** de los datos del contratista (RUC, Razón Social, Monto Contratado - AC-02.3) y no expone las URLs directas o listados de descarga de documentos (AC-02.4), solo enviando flags de existencia (`tiene_f8`). Este es un bloqueo real que requiere que el backend (T-26 o su equivalente) asigne, obtenga e incluya estos campos antes de que puedan ser renderizados en el frontend (donde ya esperan bajo un condicional oculto con `// TODO T-XX`).
- Continúa el riesgo de deriva manual de `types.ts`.

### Verificación realizada
- Test unitario (`ContratistaDocumentos.test.tsx`) creado para validar estructuralmente mediante Vitest+JsDom que los componentes de sección ocultos devuelven el contenedor en blanco (vaciado real del DOM, cero huecos o títulos huérfanos) cuando falta la data.
- Test de rutas expandido para probar la inyección `lazy` de `/obras/:codigo`.
- Comprobación manual del tamaño final del bundle, constatando que el archivo `index.js` permaneció ligero (~367 KB).

### Commits
- T-39: tipos y capa de datos para ficha detallada (`a643d03`)
- T-39: componentes de secciones de la ficha detallada, test de ocultamiento y Leaflet aislado (`e2dabfe`)
- T-39: implementar página Obra y agregar al router (`99b3bd9`)
