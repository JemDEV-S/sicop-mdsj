from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--disable-web-security'])
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        
        print("Cargando pagina Ejecucion Detalle...")
        page.goto("http://localhost:5173/ejecucion/detalle")
        
        page.wait_for_selector("table", timeout=15000)
        time.sleep(2)
        
        print("Clic en exportar para forzar error 400...")
        page.route("**/api/v1/publico/exportar/excel*", lambda route: route.fulfill(
            status=400,
            json={"detail": "La consulta supera el limite de 5000 registros para exportacion publica. Por favor, refine sus filtros (por ejemplo, seleccionando una Funcion o Fuente especifica)."}
        ))
        
        page.click("button:has-text('Exportar a Excel')")
        
        # Just wait for the toast to appear without strict selector
        time.sleep(2)
        
        print("Tomando captura del error (detalle_export_error.png)...")
        page.screenshot(path="Docs/evidencia/T-42/detalle_export_error.png")
        
        browser.close()

if __name__ == "__main__":
    run()
