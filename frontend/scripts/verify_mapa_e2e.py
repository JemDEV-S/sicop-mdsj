import asyncio
from playwright.async_api import async_playwright

async def run():
    print("Iniciando prueba e2e visual de Mapa de Obras (T-40)...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
        page.on("requestfailed", lambda req: print(f"Request failed: {req.url} - {req.failure}"))
        
        print("Navegando a /mapa...")
        await page.goto("http://localhost:5173/mapa", wait_until='networkidle')
        
        # Esperar un poco a que cargue React y la data
        await page.wait_for_timeout(5000)
        
        # Contar marcadores renderizados
        marcadores = await page.locator(".custom-leaflet-icon").all()
        print(f"Éxito: Se renderizaron {len(marcadores)} marcadores en el mapa.")
        
        # Verificar el panel lateral
        texto_panel = await page.locator("h3:has-text('Sin Coordenadas o Inválidas')").inner_text()
        print(f"Panel Lateral extraído: {texto_panel}")
        
        # Extraer las clases de color inyectadas por Tailwind
        clases = []
        for m in marcadores:
            # Buscamos el elemento div interno que lleva el fondo
            div_interno = m.locator("div.rounded-full").first
            css_class = await div_interno.get_attribute("class")
            if css_class:
                # Extraemos el prefijo bg-semaforo-* o bg-muted
                clases_list = css_class.split()
                bg_class = next((c for c in clases_list if c.startswith('bg-')), "unknown")
                clases.append(bg_class)
        
        # Reportar variedad de colores
        from collections import Counter
        conteo_colores = Counter(clases)
        print("Colores de semáforo inyectados en el DOM:")
        for color, cantidad in conteo_colores.items():
            print(f"  - {color}: {cantidad} pines")
            
        print("Probando interacción con Popup y Link...")
        # Hacer click en el primer marcador
        await marcadores[0].click()
        
        # Esperar a que se abra el popup de leaflet (.leaflet-popup)
        popup = await page.wait_for_selector(".leaflet-popup", timeout=5000)
        
        if popup:
            # Buscar el link dentro del popup
            link = await popup.query_selector("a")
            href = await link.get_attribute("href")
            print(f"Éxito: Se abrió el popup. El enlace apunta a: {href}")
            if href.startswith("/obras/"):
                print("El enlace tiene el formato correcto a la ficha (/obras/:codigo).")
            else:
                print("Advertencia: El formato del enlace no parece correcto.")
        else:
            print("Error: No se encontró el popup tras el clic.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
