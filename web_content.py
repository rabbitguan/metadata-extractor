from playwright.sync_api import sync_playwright

url = "https://www.ncdc.ac.cn/portal/metadata/55a9ae01-da93-438d-9594-3a6095fc7bc9"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(url, wait_until="networkidle")

    html = page.content()

    with open("page.html", "w", encoding="utf-8") as f:
        f.write(html)

    browser.close()