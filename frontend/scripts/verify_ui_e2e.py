import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
        page.on("requestfailed", lambda req: print(f"Request failed: {req.url} - {req.failure}"))
        await page.goto('http://localhost:5173/obras', wait_until='networkidle')
        await page.wait_for_timeout(5000)
        content = await page.content()
        with open("page_output.html", "w") as f:
            f.write(content)
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
