from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Browser, Page

from config import DEBUG_HTML_DIR, DEBUG_SCREENSHOT_DIR, SOCIAL_SOURCES, WEB_SOURCES
from filters import clean_price

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
COOKIE_SELECTORS = [
    "button:has-text('Aceptar')",
    "button:has-text('Accept')",
    "button:has-text('Consentir')",
    '#didomi-notice-agree-button',
    'button#onetrust-accept-btn-handler',
]
BLOCK_PATTERNS = [
    'captcha', 'verify you are human', 'access denied', 'robot', 'forbidden',
    'enable javascript', 'ad blocker', 'security check', 'sentimos la interrupción',
    'pardon our interruption'
]


def prepare_page(browser: Browser) -> Page:
    context = browser.new_context(
        user_agent=USER_AGENT,
        viewport={'width': 1440, 'height': 2200},
        locale='es-ES',
    )
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
    safe = name.lower().replace(' ', '_').replace('/', '_')
    (Path(DEBUG_HTML_DIR) / f'{safe}.html').write_text(page.content(), encoding='utf-8')
    page.screenshot(path=str(Path(DEBUG_SCREENSHOT_DIR) / f'{safe}.png'), full_page=True)


def accept_cookies(page: Page):
    for selector in COOKIE_SELECTORS:
        try:
            locator = page.locator(selector).first
            if locator.is_visible(timeout=1500):
                locator.click(timeout=1500)
                page.wait_for_timeout(1000)
                return True
        except Exception:
            continue
    return False


def detect_blocks(text: str) -> List[str]:
    lower = (text or '').lower()
    return [p for p in BLOCK_PATTERNS if p in lower]


def extract_items(soup, selectors: List[str], source: Dict) -> List[Dict]:
    results, seen = [], set()
    for selector in selectors:
        for item in soup.select(selector):
            link_tag = item.find('a', href=True)
            text = item.get_text(' ', strip=True)
            if not link_tag or len(text) < 25:
                continue
            href = urljoin(source['base_url'], link_tag['href'])
            if not href or href in seen:
                continue
            seen.add(href)
            title = link_tag.get_text(' ', strip=True) or text[:170]
            results.append({
                'source': source['name'],
                'kind': source['kind'],
                'title': title[:170],
                'price': clean_price(text),
                'url': href,
                'location': text[:240],
                'description': text[:900],
            })
    return results


def auto_scroll(page: Page, rounds: int = 8, pixels: int = 6000, wait_ms: int = 1800):
    last_height = 0
    stable_rounds = 0
    for _ in range(rounds):
        page.mouse.wheel(0, pixels)
        page.wait_for_timeout(wait_ms)
        try:
            height = page.evaluate("document.body.scrollHeight")
        except Exception:
            height = 0
        if height == last_height:
            stable_rounds += 1
        else:
            stable_rounds = 0
        last_height = height
        if stable_rounds >= 2:
            break


def collect_source(page: Page, source: Dict):
    page.goto(source['url'], wait_until='domcontentloaded')
    page.wait_for_timeout(5000)
    accept_cookies(page)
    auto_scroll(page)
    html = page.content()
    save_debug_assets(source['name'], page)
    soup = BeautifulSoup(html, 'html.parser')
    results = extract_items(soup, source['selectors'], source)
    meta = {
        'name': source['name'],
        'kind': source['kind'],
        'enabled': source['enabled'],
        'raw_count': len(results),
        'error_count': 0,
        'final_url': page.url,
        'page_title': page.title(),
        'block_signals': detect_blocks(soup.get_text(' ', strip=True)),
    }
    return results, meta


def run_all_scrapers(browser: Browser) -> Tuple[List[Dict], List[Dict]]:
    collected, report = [], []
    for source in WEB_SOURCES:
        if not source['enabled']:
            report.append({
                'name': source['name'], 'kind': source['kind'], 'enabled': False,
                'raw_count': 0, 'error_count': 0, 'valid_count': 0, 'notify_count': 0,
            })
            continue
        page = prepare_page(browser)
        try:
            items, meta = collect_source(page, source)
            collected.extend(items)
            report.append(meta)
        except Exception as exc:
            report.append({
                'name': source['name'], 'kind': source['kind'], 'enabled': True,
                'raw_count': 0, 'error_count': 1,
                'final_url': page.url if page else '', 'page_title': '',
                'block_signals': [], 'exception': str(exc),
            })
        finally:
            page.context.close()

    for source in SOCIAL_SOURCES:
        report.append({
            'name': source['name'], 'kind': source['kind'], 'enabled': source['enabled'],
            'raw_count': 0, 'error_count': 0, 'valid_count': 0, 'notify_count': 0,
            'note': source.get('note', ''),
        })
    return collected, report
