from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import Browser, Page
from config import DEBUG_HTML_DIR, DEBUG_SCREENSHOT_DIR, TARGET_PORTALS
from filters import clean_price

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
COOKIE_SELECTORS = ["button:has-text('Aceptar')", "button:has-text('Accept')", "button:has-text('Consentir')", "#didomi-notice-agree-button", "button#onetrust-accept-btn-handler"]


def prepare_page(browser: Browser) -> Page:
    context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1440, "height": 2200}, locale="es-ES")
    page = context.new_page()
    page.set_default_timeout(45000)
    page.add_init_script("""
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'platform', {get: () => 'Linux x86_64'});
Object.defineProperty(navigator, 'language', {get: () => 'es-ES'});
Object.defineProperty(navigator, 'languages', {get: () => ['es-ES','es','en-US']});
window.chrome = { runtime: {} };
""")
    return page


def save_debug_assets(name: str, page: Page):
    Path(DEBUG_HTML_DIR).mkdir(parents=True, exist_ok=True)
    Path(DEBUG_SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)
    html_path = Path(DEBUG_HTML_DIR) / f"{name.lower()}.html"
    png_path = Path(DEBUG_SCREENSHOT_DIR) / f"{name.lower()}.png"
    html_path.write_text(page.content(), encoding="utf-8")
    page.screenshot(path=str(png_path), full_page=True)


def accept_cookies(page: Page):
    for selector in COOKIE_SELECTORS:
        try:
            el = page.locator(selector).first
            if el.is_visible(timeout=1500):
                el.click(timeout=1500)
                page.wait_for_timeout(1000)
                return True
        except Exception:
            continue
    return False


def _extract_by_selector(soup, selectors: List[str], source: str, base_url: str) -> List[Dict]:
    results = []
    seen = set()
    for selector in selectors:
        for item in soup.select(selector):
            link_tag = item.find('a', href=True)
            text = item.get_text(' ', strip=True)
            if not link_tag or len(text) < 25:
                continue
            href = urljoin(base_url, link_tag['href'])
            if href in seen:
                continue
            seen.add(href)
            title = link_tag.get_text(' ', strip=True) or text[:170]
            results.append({"source": source, "title": title[:170], "price": clean_price(text), "url": href, "location": text[:240], "description": text[:900]})
        if results:
            break
    return results


def collect_portal(page: Page, name: str, url: str, selectors: List[str], base_url: str):
    page.goto(url, wait_until='domcontentloaded')
    page.wait_for_timeout(3500)
    accept_cookies(page)
    for _ in range(3):
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(1800)
    save_debug_assets(name, page)
    soup = BeautifulSoup(page.content(), 'html.parser')
    results = _extract_by_selector(soup, selectors, name, base_url)
    meta = {
        "name": name,
        "raw_count": len(results),
        "error_count": 0,
        "final_url": page.url,
        "page_title": page.title(),
        "selectors_tested": selectors,
    }
    return results, meta


def run_all_scrapers(browser: Browser) -> Tuple[List[Dict], List[Dict]]:
    configs = [
        ("Idealista", next(p['search_url'] for p in TARGET_PORTALS if p['name']=='Idealista'), ['article.item', 'article[data-adid]', '.items-container article', '.listing-items article'], 'https://www.idealista.com'),
        ("Milanuncios", next(p['search_url'] for p in TARGET_PORTALS if p['name']=='Milanuncios'), ['div.ma-AdCard', 'article', '[data-testid="ad-card"]'], 'https://www.milanuncios.com'),
        ("Fotocasa", next(p['search_url'] for p in TARGET_PORTALS if p['name']=='Fotocasa'), ['article', 'div.re-CardPackPremium', 'div.re-CardPack', '[class*="CardPack"]'], 'https://www.fotocasa.es'),
    ]
    collected, report = [], []
    for name, url, selectors, base_url in configs:
        page = prepare_page(browser)
        try:
            items, meta = collect_portal(page, name, url, selectors, base_url)
            collected.extend(items); report.append(meta)
        except Exception as exc:
            report.append({"name": name, "raw_count": 0, "error_count": 1, "final_url": page.url if page else '', "page_title": '', "selectors_tested": selectors, "exception": str(exc)})
        finally:
            page.context.close()
    return collected, report
