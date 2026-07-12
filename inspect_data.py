import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--disable-web-security"])
        page = await browser.new_page()
        page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        await page.goto("http://localhost:5173/ejecucion", wait_until="networkidle")
        await page.wait_for_selector("text=% Ejecución")
        
        await asyncio.sleep(2)
        
        # Inyectar script que lea el estado interno de React o simplemente mire el DOM
        # Recharts le pone clases a los ejes. ¿Existen ticks en el YAxis?
        y_ticks = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.recharts-yAxis .recharts-cartesian-axis-tick-value tspan')).map(t => t.textContent);
        }''')
        print("YAxis Ticks:", y_ticks)
        
        await browser.close()

asyncio.run(main())
