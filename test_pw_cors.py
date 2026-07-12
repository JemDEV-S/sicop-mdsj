import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("http://localhost:5173")
        res = await page.evaluate('''async () => {
            try {
                const r = await fetch("http://127.0.0.1:8000/api/v1/publico/ejecucion/resumen");
                return r.status;
            } catch (e) {
                return e.message;
            }
        }''')
        print("CORS test result:", res)
        await browser.close()

asyncio.run(main())
