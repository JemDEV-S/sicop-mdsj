# Notas Técnicas y E2E Gotchas

Documento vivo de hallazgos y workarounds críticos para el testing End-to-End automatizado (Playwright, Cypress, etc.) en la plataforma institucional.

## 1. Vite Modes vs Environment Variables
`npm run build` o `vite preview` corren en modo `production` por defecto y **ignoran `frontend/.env.development`** silenciosamente si no existe un `.env.production`. Esto provocó que el frontend quedara empaquetado con el fallback por defecto `http://localhost:8000`, disparando bugs de IPv6 que no sucedían en desarrollo.
**Solución/Regla:** Siempre usar `npm run dev` para tests de integración contra un backend local, o asegurar que las variables de entorno se inyectan explícitamente en el pipeline de CI/CD para producción.

## 2. Playwright y Private Network Access (PNA)
Al correr Chromium contra `localhost:5173` y disparar requests fetch a `127.0.0.1:8000`, Chromium bloquea la petición silenciosamente por razones de seguridad (Private Network Access) a menos que Uvicorn emita headers específicos. 
**Solución/Regla:** El workaround oficial para testing E2E rápido es inyectar `--disable-web-security` en el launch de Chromium para evadir la preflight PNA (solo en contextos de testeo aislado).

## 3. Recharts y Animaciones E2E (Barras y Donas Invisibles)
Al usar `requestAnimationFrame`, Playwright headless puede capturar gráficos de Recharts a medio renderizar (barras y donas de tamaño/opacidad 0, generando SVG sin dimensiones).
**Solución/Regla:** Establecer siempre `isAnimationActive={false}` de forma determinista en componentes gráficos (`<Bar>`, `<Pie>`, `<Line>`) para los tests visuales.

## 4. Axios, responseType: 'blob' y Errores JSON
Cuando un endpoint está configurado para descargar archivos (`responseType: 'blob'`), si el servidor devuelve un error HTTP 400/500 con un JSON de detalle, Axios convierte **toda** la respuesta en un `Blob`. Intentar leer `error.response.data.detail` arrojará `undefined`.
**Solución/Regla:** Hay que interceptar el error, verificar si `error.response?.data instanceof Blob`, y leer el contenido asíncronamente con `.text()` antes de parsearlo con `JSON.parse()`. Esto evita fallbacks genéricos de UI cuando el backend envió un mensaje explícito.
