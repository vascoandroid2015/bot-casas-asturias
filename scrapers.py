from typing import List, Dict
from playwright.sync_api import sync_playwright


def scrape_example_portal() -> List[Dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://example.com", wait_until="domcontentloaded", timeout=30000)
        title = page.title() or "Example listing"
        browser.close()
    return [{
        "id": "example-com-home",
        "title": title,
        "price": "123000 €",
        "location": "Asturias",
        "url": "https://example.com",
        "source": "Example",
        "maps_url": "https://maps.google.com/?q=Asturias"
    }]
