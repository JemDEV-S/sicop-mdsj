import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--disable-web-security"])
        page = await browser.new_page()
        await page.goto("http://localhost:5173/ejecucion", wait_until="networkidle")
        await page.wait_for_selector("text=% Ejecución")
        await asyncio.sleep(2)
        
        # Check computed styles for rect and path
        bar_fills = await page.evaluate('''() => {
            const rects = document.querySelectorAll(".recharts-bar-rectangle rect");
            return Array.from(rects).map(r => window.getComputedStyle(r).fill);
        }''')
        
        pie_fills = await page.evaluate('''() => {
            const sectors = document.querySelectorAll(".recharts-pie-sector path");
            return Array.from(sectors).map(p => window.getComputedStyle(p).fill);
        }''')
        
        print("Bar computed fills:", bar_fills)
        print("Pie computed fills:", pie_fills)
        
        # Extraer TODO los rects de recharts para ver si están
        all_rects = await page.evaluate('''() => {
            const rects = document.querySelectorAll("rect");
            return Array.from(rects).map(r => ({
                class: r.className.baseVal,
                fill: r.getAttribute("fill"),
                width: r.getAttribute("width")
            }));
        }''')
        print("All rects:", all_rects)
        
        await browser.close()

asyncio.run(main())
