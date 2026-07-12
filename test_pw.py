import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        res = await page.goto("http://127.0.0.1:8000/api/v1/publico/ejecucion/resumen")
        print(res.status)
        print(await res.text())
        await browser.close()

asyncio.run(main())
