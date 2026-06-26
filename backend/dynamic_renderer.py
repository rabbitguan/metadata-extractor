from __future__ import annotations

from typing import Dict, Optional


def render_url_content(
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    timeout_ms: int = 25000,
    settle_ms: int = 800,
) -> Dict[str, str]:
    """
    Render a page in a real Chromium browser and return the final DOM HTML.

    Playwright is imported lazily so deployments without browser support can
    still run the normal requests-based fetch path.
    """
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-sandbox',
            ],
        )
        try:
            context = browser.new_context(
                user_agent=(headers or {}).get('User-Agent'),
                extra_http_headers={
                    key: value
                    for key, value in (headers or {}).items()
                    if key.lower() not in {'user-agent', 'host', 'content-length'}
                },
                ignore_https_errors=True,
                viewport={'width': 1440, 'height': 1200},
            )
            page = context.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms)
            try:
                page.wait_for_load_state('networkidle', timeout=min(timeout_ms, 10000))
            except PlaywrightTimeoutError:
                pass
            if settle_ms > 0:
                page.wait_for_timeout(settle_ms)
            return {
                'html': page.content() or '',
                'title': page.title() or '',
                'url': page.url or url,
            }
        finally:
            browser.close()
