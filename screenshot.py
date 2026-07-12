from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--disable-web-security'])
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        
        # Mock API calls to render table
        page.route("**/api/v1/publico/ejecucion/detalle*", lambda route: route.fulfill(
            status=200,
            json={"items": [{"sec_func": 1, "meta_nombre": "META", "producto_proyecto": "PROYECTO", "pim": 100, "devengado": 50, "porcentaje_ejecucion": 50.0}], "total": 1, "page": 1, "size": 25}
        ))
        
        page.route("**/api/v1/publico/ejecucion/resumen*", lambda route: route.fulfill(
            status=200, json={"pim_total": 100, "devengado_total": 50, "porcentaje_ejecucion_total": 50.0}
        ))
        page.route("**/api/v1/publico/ejecucion/por-funcion*", lambda route: route.fulfill(status=200, json=[]))
        page.route("**/api/v1/publico/ejecucion/por-fuente*", lambda route: route.fulfill(status=200, json=[]))
        page.route("**/api/v1/publico/ejecucion/mensual*", lambda route: route.fulfill(status=200, json=[]))
        
        print("Cargando pagina Ejecucion Detalle...")
        page.goto("http://localhost:5173/ejecucion/detalle")
        page.wait_for_selector("table", timeout=15000)
        time.sleep(1)
        
        print("Clic en exportar para forzar error 400...")
        page.route("**/api/v1/publico/exportar/excel*", lambda route: route.fulfill(
            status=400,
            headers={"Content-Type": "application/json"},
            json={"detail": "La consulta supera el límite de 5000 registros para exportación pública. Por favor, refine sus filtros (por ejemplo, seleccionando una Función o Fuente específica)."}
        ))
        
        page.click("button:has-text('Exportar a Excel')")
        time.sleep(1) # wait for toast
        
        print("Tomando captura del error...")
        page.screenshot(path="/home/jeanpier/.gemini/antigravity-ide/brain/aefa8ec0-df35-446a-8732-c8ddd936cab7/detalle_export_error.png")
        browser.close()

if __name__ == "__main__":
    run()
