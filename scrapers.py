from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import Browser, Page
from config import DEBUG_HTML_DIR, DEBUG_SCREENSHOT_DIR, SOURCES
from filters import clean_price
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
COOKIE_SELECTORS = ["button:has-text('Aceptar')", "button:has-text('Accept')", "button:has-text('Consentir')", '#didomi-notice-agree-button', 'button#onetrust-accept-btn-handler']
BLOCK_PATTERNS = ['captcha', 'verify you are human', 'access denied', 'robot', 'forbidden', 'enable javascript', 'ad blocker', 'security check', 'sentimos la interrupción', 'pardon our interruption']

def prepare_page(browser: Browser) -> Page:
    context = browser.new_context(user_agent=USER_AGENT, viewport={'width': 1440, 'height': 2200}, locale='es-ES')
    page = context.new_page(); page.set_default_timeout(45000)
    page.add_init_script("""
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'platform', {get: () => 'Linux x86_64'});
Object.defineProperty(navigator, 'language', {get: () => 'es-ES'});
Object.defineProperty(navigator, 'languages', {get: () => ['es-ES','es','en-US']});
window.chrome = { runtime: {} };
""")
    return page

def save_debug_assets(name: str, page: Page):
    Path(DEBUG_HTML_DIR).mkdir(parents=True, exist_ok=True); Path(DEBUG_SCREENSHOT_DIR).mkdir(parents=True, exist_ok=True)
    safe = name.lower().replace(' ', '_').replace('/', '_')
    (Path(DEBUG_HTML_DIR) / f'{safe}.html').write_text(page.content(), encoding='utf-8')
    page.screenshot(path=str(Path(DEBUG_SCREENSHOT_DIR) / f'{safe}.png'), full_page=True)

def accept_cookies(page: Page):
    for selector in COOKIE_SELECTORS:
        try:
            locator = page.locator(selector).first
            if locator.is_visible(timeout=1500):
                locator.click(timeout=1500); page.wait_for_timeout(1000); return True
        except Exception:
            continue
    return False

def detect_blocks(text: str) -> List[str]:
    lower = (text or '').lower()
    return [p for p in BLOCK_PATTERNS if p in lower]

def extract_items(soup, selectors: List[str], source: str, base_url: str) -> List[Dict]:
    results, seen = [], set()
    for selector in selectors:
        for item in soup.select(selector):
            link_tag = item.find('a', href=True)
            text = item.get_text(' ', strip=True)
            if not link_tag or len(text) < 25: continue
            href = urljoin(base_url, link_tag['href'])
            if href in seen: continue
            seen.add(href)
            title = link_tag.get_text(' ', strip=True) or text[:170]
            results.append({'source': source, 'title': title[:170], 'price': clean_price(text), 'url': href, 'location': text[:240], 'description': text[:900]})
        if results: break
    return results

def collect_source(page: Page, source: Dict):
    page.goto(source['url'], wait_until='domcontentloaded')
    page.wait_for_timeout(3500)
    accept_cookies(page)
    for _ in range(2):
        page.mouse.wheel(0, 4000); page.wait_for_timeout(1400)
    html = page.content()
    save_debug_assets(source['name'], page)
    soup = BeautifulSoup(html, 'html.parser')
    results = extract_items(soup, source['selectors'], source['name'], source['base_url'])
    meta = {'name': source['name'], 'enabled': source['enabled'], 'raw_count': len(results), 'error_count': 0, 'final_url': page.url, 'page_title': page.title(), 'block_signals': detect_blocks(soup.get_text(' ', strip=True))}
    return results, meta

def run_all_scrapers(browser: Browser) -> Tuple[List[Dict], List[Dict]]:
    collected, report = [], []
    for source in SOURCES:
        if not source['enabled']:
            report.append({'name': source['name'], 'enabled': False, 'raw_count': 0, 'error_count': 0, 'valid_count': 0, 'notify_count': 0})
            continue
        page = prepare_page(browser)
        try:
            items, meta = collect_source(page, source)
            collected.extend(items); report.append(meta)
        except Exception as exc:
            report.append({'name': source['name'], 'enabled': True, 'raw_count': 0, 'error_count': 1, 'final_url': page.url if page else '', 'page_title': '', 'block_signals': [], 'exception': str(exc)})
        finally:
            page.context.close()
    return collected, report
