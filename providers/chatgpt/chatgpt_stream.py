




"""async def run():
    async with async_playwright() as p:
        # Launch Firefox
        browser = await p.firefox.launch(headless=False)
        page = await browser.new_page()

        print("🚀 Listening for SSE streaming responses on ChatGPT...\n")

        # Intercept HTTP response streams
        page.on("response", lambda response: asyncio.create_task(handle_response(response)))

        # Navigate to target
        await page.goto("https://chatgpt.com")

        # Keep browser open to monitor activity
        await asyncio.sleep(120)


if __name__ == "__main__":
    asyncio.run(run())"""