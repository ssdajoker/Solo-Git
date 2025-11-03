import time
from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # Retry logic to wait for the server to start
    for _ in range(30):
        try:
            page.goto("http://localhost:5173/")
            break
        except Exception:
            time.sleep(1)

    # Verify that the main content is visible
    main_content = page.locator('div#root')
    expect(main_content).to_be_visible()

    page.screenshot(path="jules-scratch/verification/verification.png")
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
