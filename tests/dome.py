import asyncio

from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as playwright:
        # Launch a browser context.
        chromium = playwright.chromium
        browser = await chromium.launch(headless=False)  # type: ignore
        browser_context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
        )
        p = await browser_context.new_page()
        await p.goto("https://www.baidu.com")
        # await p.close()
        # await browser_context.close()
        await browser.close()
        await asyncio.sleep(10)


if __name__ == '__main__':
    asyncio.run(main())