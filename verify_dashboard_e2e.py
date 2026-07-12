import asyncio
import subprocess
import time
import os
from playwright.async_api import async_playwright

async def main():
    print("Iniciando Vite dev server...")
    
    vite_process = subprocess.Popen(["npm", "run", "dev"], cwd="frontend", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Esperar a que Vite levante
    time.sleep(5)
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                args=["--disable-web-security"]
            )
            
            print("1. Probando Desktop con datos reales...")
            context_desktop = await browser.new_context(viewport={'width': 1280, 'height': 800})
            page = await context_desktop.new_page()
            
            # Iniciar captura de request para verificar refetch por año
            requests_made = []
            page.on("request", lambda request: print(f"FETCH: {request.url}") if "publico/ejecucion" in request.url else None)
            page.on("requestfailed", lambda request: print(f"FAILED: {request.url} -> {request.failure.error_text}") if "publico/ejecucion" in request.url else None)
            page.on("request", lambda request: requests_made.append(request.url) if "publico/ejecucion" in request.url else None)

            await page.goto("http://localhost:5173/ejecucion", wait_until="networkidle")
            await page.wait_for_selector("text=Ejecución Presupuestal")
            
            # Esperar a que termine de cargar el gráfico o KPI (asegurarnos de que no esté en skeleton)
            # Buscamos el texto '% Ejecución' que es el título de la última tarjeta KPI
            print("Esperando a que los KPIs terminen de cargar (conectando al backend real)...")
            await page.wait_for_selector("text=% Ejecución")
            await asyncio.sleep(2) # Esperar a que Recharts termine su animación
            
            # Verificar botón "Próximamente"
            btn = page.locator("button:has-text('Tabla Detallada')")
            is_disabled = await btn.is_disabled()
            title = await btn.get_attribute("title")
            print(f"Botón Tabla Detallada -> disabled: {is_disabled}, title: {title}")
            
            await page.screenshot(path="dashboard_desktop.png", full_page=True)
            print("Captura Desktop: dashboard_desktop.png")

            # Cambiar de año
            print("Cambiando año en el selector a 2025...")
            
            # Iniciar captura de request/response para verificar refetch por año
            requests_2025 = []
            responses_2025 = []
            page.on("request", lambda request: requests_2025.append(request.url) if "publico/ejecucion" in request.url and "2025" in request.url else None)
            
            async def log_response(response):
                if "publico/ejecucion" in response.url and "2025" in response.url:
                    try:
                        body = await response.json()
                        responses_2025.append(f"{response.url} -> {response.status} | Body: {body}")
                    except Exception:
                        responses_2025.append(f"{response.url} -> {response.status} | Body: no JSON")
            
            page.on("response", log_response)

            await page.evaluate("() => { const select = document.querySelector('select'); const option = document.createElement('option'); option.value = '2025'; option.text = '2025'; select.appendChild(option); select.value = '2025'; select.dispatchEvent(new Event('change', { bubbles: true })); }")
            
            # Esperar 2 segundos para que React Query dispare la petición y terminen de resolverse
            await asyncio.sleep(2)
            
            print("Respuestas capturadas tras cambiar a 2025:")
            for res in responses_2025:
                print(" -", res)

            # Tomar screenshot del estado vacío (2025)
            await page.screenshot(path="dashboard_2025.png", full_page=True)
            print("Captura 2025 Vacío: dashboard_2025.png")

            await context_desktop.close()

            print("\n2. Probando Mobile (Responsive)...")
            context_mobile = await browser.new_context(
                viewport={'width': 375, 'height': 812},
                is_mobile=True
            )
            page_mobile = await context_mobile.new_page()
            await page_mobile.goto("http://localhost:5173/ejecucion", wait_until="networkidle")
            await page_mobile.wait_for_selector("text=% Ejecución")
            await asyncio.sleep(2)
            await page_mobile.screenshot(path="dashboard_mobile.png", full_page=True)
            print("Captura Mobile: dashboard_mobile.png")
            await context_mobile.close()

            print("\n3. Probando caso sintético de NULLs (Mocking de API)...")
            context_mock = await browser.new_context(viewport={'width': 1280, 'height': 800})
            page_mock = await context_mock.new_page()

            # Interceptar para devolver nulls
            async def handle_route(route):
                url = route.request.url
                if "resumen" in url:
                    await route.fulfill(json={
                        "pia": "1000", "pim": "1000", "certificado": "500",
                        "comprometido_anual": "400", "devengado": "300", "girado": "200",
                        "metas": 10, "porcentaje_ejecucion": null  # Simular KPI en null
                    })
                elif "por-funcion" in url:
                    await route.fulfill(json=[
                        {"funcion_codigo": "01", "funcion_nombre": "Normal", "pim": "1000", "certificado": "500", "devengado": "300", "girado": "200"},
                        {"funcion_codigo": "02", "funcion_nombre": "Con PIM NULL (No debe verse)", "pim": null, "certificado": "500", "devengado": "300", "girado": "200"}
                    ])
                elif "por-fuente" in url:
                    await route.fulfill(json=[
                        {"fuente_codigo": "01", "fuente_nombre": "Normal", "pim": "1000", "devengado": "300"},
                        {"fuente_codigo": "02", "fuente_nombre": "Con PIM NULL (No debe verse)", "pim": null, "devengado": "300"}
                    ])
                elif "mensual" in url:
                    await route.fulfill(json=[
                        {"mes_eje": 1, "pim": "1000", "certificado": "500", "devengado": "100", "girado": "100"},
                        {"mes_eje": 2, "pim": null, "certificado": null, "devengado": null, "girado": null}, # GAP
                        {"mes_eje": 3, "pim": "1000", "certificado": "600", "devengado": "300", "girado": "200"}
                    ])
                else:
                    await route.continue_()

            # Usar null en python requiere json.dumps, re-escribimos el fulfill:
            import json
            async def handle_route_json(route):
                url = route.request.url
                headers = {"Content-Type": "application/json"}
                if "resumen" in url:
                    await route.fulfill(headers=headers, body=json.dumps({
                        "pia": "1000", "pim": "1000", "certificado": "500",
                        "comprometido_anual": "400", "devengado": "300", "girado": "200",
                        "metas": 10, "porcentaje_ejecucion": None
                    }))
                elif "por-funcion" in url:
                    await route.fulfill(headers=headers, body=json.dumps([
                        {"funcion_codigo": "01", "funcion_nombre": "Normal", "pim": "1000", "certificado": "500", "devengado": "300", "girado": "200"},
                        {"funcion_codigo": "02", "funcion_nombre": "Con PIM NULL (No debe verse)", "pim": None, "certificado": "500", "devengado": "300", "girado": "200"}
                    ]))
                elif "por-fuente" in url:
                    await route.fulfill(headers=headers, body=json.dumps([
                        {"fuente_codigo": "01", "fuente_nombre": "Normal", "pim": "1000", "devengado": "300"},
                        {"fuente_codigo": "02", "fuente_nombre": "Con PIM NULL (No debe verse)", "pim": None, "devengado": "300"}
                    ]))
                elif "mensual" in url:
                    await route.fulfill(headers=headers, body=json.dumps([
                        {"mes_eje": 1, "pim": "1000", "certificado": "500", "devengado": "100", "girado": "100"},
                        {"mes_eje": 2, "pim": None, "certificado": None, "devengado": None, "girado": None},
                        {"mes_eje": 3, "pim": "1000", "certificado": "600", "devengado": "300", "girado": "200"}
                    ]))
                else:
                    await route.continue_()

            await page_mock.route("**/publico/ejecucion/*", handle_route_json)
            await page_mock.goto("http://localhost:5173/ejecucion", wait_until="networkidle")
            await page_mock.wait_for_selector("text=% Ejecución")
            await asyncio.sleep(2)
            await page_mock.screenshot(path="dashboard_nulls.png", full_page=True)
            print("Captura Mock Nulls: dashboard_nulls.png")
            await context_mock.close()

            await browser.close()
    finally:
        print("Cerrando Vite dev server...")
        vite_process.terminate()
        vite_process.wait()

if __name__ == "__main__":
    asyncio.run(main())
