import asyncio
from playwright.async_api import async_playwright
import pathlib

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page(
            viewport={"width": 390, "height": 844},
            is_mobile=True, has_touch=True
        )
        print("Navigating...")
        await page.goto("http://127.0.0.1:8080", wait_until="networkidle", timeout=60000)
        print("Waiting for React hydration...")
        await page.wait_for_timeout(10000)
        
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(2000)
        
        html = await page.content()
        pathlib.Path("index_hydrated.html").write_text(html, encoding="utf-8")
        print("Captured", len(html)//1024, "KB")
        await browser.close()

asyncio.run(main())
