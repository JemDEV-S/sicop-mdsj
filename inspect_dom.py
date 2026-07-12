import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--disable-web-security"])
        page = await browser.new_page()
        await page.goto("http://localhost:5173/ejecucion", wait_until="networkidle")
        await page.wait_for_selector("text=% Ejecución")
        await asyncio.sleep(2)
        
        # Obtener el HTML de la BarChart (el tercer card o el que diga "Ejecución por Función")
        html = await page.evaluate('''() => {
            const h3 = Array.from(document.querySelectorAll('h3')).find(el => el.textContent.includes('Ejecución por Función'));
            if (!h3) return "No h3";
            const svg = h3.parentElement.querySelector('svg');
            if (!svg) return "No svg";
            return svg.outerHTML;
        }''')
        print(html)
        await browser.close()

asyncio.run(main())
