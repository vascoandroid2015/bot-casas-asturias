import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Browser, Page

from config import DEBUG_HTML_DIR, DEBUG_SCREENSHOT_DIR, WEB_SOURCES
from filters import clean_price

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
COOKIE_SELECTORS = [
    "button:has-text('Aceptar')",
    "button:has-text('Accept')",
    "button:has-text('Consentir')",
    "button:has-text('Entendido')",
    "button:has-text('Continuar')",
    '#didomi-notice-agree-button',
    'button#onetrust-accept-btn-handler',
    '[data-testid="TcfAccept"]',
    '[data-testid="accept-button"]',
]
BLOCK_PATTERNS = [
    'captcha', 'verify you are human', 'access denied', 'robot', 'forbidden',
    'enable javascript', 'ad blocker', 'security check', 'sentimos la interrupción',
    'pardon our interruption', 'datadome'
]


def prepare_page(browser: Browser) -> Page:
    context = browser.new_context(
        user_agent=USER_AGENT,
        viewport={'width': 1440, 'height': 2600},
        locale='es-ES',
        java_script_enabled=True,
    )
    page = context.new_page()
    page.set_default_timeout(45000)
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'platform', {get: () => 'Linux x86_64'});
        Object.defineProperty(navigator, 'language', {get: () => 'es-ES'});
        Object.defineProperty(navigator, 'languages', {get: () => ['es-ES','es','en-US']});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4]});
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
            if locator.is_visible(timeout=1800):
                locator.click(timeout=1800)
                page.wait_for_timeout(1200)
                return True
        except Exception:
            continue
    return False


def detect_blocks(text: str) -> List[str]:
    lower = (text or '').lower()
    return [p for p in BLOCK_PATTERNS if p in lower]


def auto_scroll(page: Page, rounds: int = 12, pixels: int = 7000, wait_ms: int = 1700):
    last_height = 0
    stable_rounds = 0
    for _ in range(rounds):
        page.mouse.wheel(0, pixels)
        page.wait_for_timeout(wait_ms)
        try:
            height = page.evaluate('document.body.scrollHeight')
        except Exception:
            height = 0
        if height == last_height:
            stable_rounds += 1
        else:
            stable_rounds = 0
        last_height = height
        if stable_rounds >= 2:
            break


def normalize_href(href: str, base_url: str) -> str:
    if not href:
        return ''
    href = href.strip()
    if href.startswith('//'):
        return 'https:' + href
    return urljoin(base_url, href)


def collapse_ws(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


def build_item(source: Dict, href: str, text: str, title: str = '') -> Dict:
    clean_text = collapse_ws(text)
    clean_title = collapse_ws(title) or clean_text[:170] or 'Sin título'
    return {
        'source': source['name'],
        'kind': source['kind'],
        'title': clean_title[:170],
        'price': clean_price(clean_text),
        'url': normalize_href(href, source['base_url']),
        'location': clean_text[:240],
        'description': clean_text[:900],
    }


def dedupe_results(items: List[Dict]) -> List[Dict]:
    out, seen = [], set()
    for item in items:
        url = item.get('url')
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(item)
    return out


def extract_from_json_ld(soup: BeautifulSoup, source: Dict) -> List[Dict]:
    results = []
    for tag in soup.select('script[type="application/ld+json"]'):
        raw = tag.string or tag.get_text(strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        blocks = data if isinstance(data, list) else [data]
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get('@type') == 'ItemList' and isinstance(block.get('itemListElement'), list):
                for entry in block['itemListElement']:
                    if isinstance(entry, dict):
                        entry = entry.get('item') or entry
                    if not isinstance(entry, dict):
                        continue
                    href = entry.get('url', '')
                    title = entry.get('name', '')
                    text = ' '.join(str(entry.get(k, '')) for k in ['name', 'description'])
                    if href:
                        results.append(build_item(source, href, text, title))
    return dedupe_results(results)


def extract_idealista(page: Page, source: Dict) -> List[Dict]:
    results = []
    selectors = [
        'article.item',
        'article[data-adid]',
        'a[href*="/inmueble/"]',
    ]
    for selector in selectors:
        try:
            nodes = page.locator(selector).all()
        except Exception:
            nodes = []
        for node in nodes:
            try:
                if selector.startswith('a['):
                    href = node.get_attribute('href') or ''
                    title = node.text_content() or ''
                    text = title
                else:
                    link = node.locator('a[href*="/inmueble/"]').first
                    href = link.get_attribute('href') or ''
                    title = link.text_content() or ''
                    text = node.text_content() or ''
                href = normalize_href(href, source['base_url'])
                if '/inmueble/' not in href:
                    continue
                if len(collapse_ws(text)) < 20:
                    continue
                results.append(build_item(source, href, text, title))
            except Exception:
                continue
    return dedupe_results(results)


def extract_fotocasa(page: Page, source: Dict) -> List[Dict]:
    results = []
    selectors = [
        'a[href*="/es/comprar/vivienda/"]',
        'a[href*="/es/comprar/casa/"]',
        'a[href*="/es/comprar/piso/"]',
    ]
    for selector in selectors:
        try:
            links = page.locator(selector).all()
        except Exception:
            links = []
        for link in links:
            try:
                href = normalize_href(link.get_attribute('href') or '', source['base_url'])
                if '/es/comprar/' not in href:
                    continue
                container = link.locator('xpath=ancestor-or-self::*[self::article or contains(@class, "Card") or contains(@class, "card")][1]').first
                text = (container.text_content() if container.count() else link.text_content()) or ''
                title = (link.text_content() or text).strip()
                if len(collapse_ws(text)) < 20:
                    continue
                results.append(build_item(source, href, text, title))
            except Exception:
                continue
    return dedupe_results(results)


def extract_milanuncios(page: Page, source: Dict) -> List[Dict]:
    results = []
    selectors = [
        'a[href*="/venta-de-casas/"]',
        'a[href*="/inmuebles/"]',
        '[data-testid="ad-card"] a[href]',
        'div.ma-AdCard a[href]',
    ]
    for selector in selectors:
        try:
            links = page.locator(selector).all()
        except Exception:
            links = []
        for link in links:
            try:
                href = normalize_href(link.get_attribute('href') or '', source['base_url'])
                if 'milanuncios.com' not in href:
                    continue
                container = link.locator('xpath=ancestor-or-self::*[self::article or contains(@class, "AdCard") or contains(@class, "ad-card")][1]').first
                text = (container.text_content() if container.count() else link.text_content()) or ''
                title = (link.text_content() or text).strip()
                if len(collapse_ws(text)) < 20:
                    continue
                results.append(build_item(source, href, text, title))
            except Exception:
                continue
    return dedupe_results(results)


def extract_wallapop(page: Page, source: Dict) -> List[Dict]:
    results = []
    selectors = [
        'a[href*="/item/"]',
        '[data-testid="item-card"] a[href]',
        'article a[href*="/item/"]',
    ]
    for selector in selectors:
        try:
            links = page.locator(selector).all()
        except Exception:
            links = []
        for link in links:
            try:
                href = normalize_href(link.get_attribute('href') or '', source['base_url'])
                if '/item/' not in href:
                    continue
                container = link.locator('xpath=ancestor-or-self::*[self::article or contains(@data-testid, "item-card") or contains(@class, "card")][1]').first
                text = (container.text_content() if container.count() else link.text_content()) or ''
                title = (link.text_content() or text).strip()
                if len(collapse_ws(text)) < 10:
                    continue
                results.append(build_item(source, href, text, title))
            except Exception:
                continue
    return dedupe_results(results)


def click_load_more(page: Page):
    selectors = [
        "button:has-text('Ver más')",
        "button:has-text('Cargar más')",
        "button:has-text('Mostrar más')",
        "a:has-text('Siguiente')",
    ]
    for selector in selectors:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=800):
                btn.click(timeout=1000)
                page.wait_for_timeout(1200)
        except Exception:
            pass


def extract_items(page: Page, soup: BeautifulSoup, source: Dict) -> List[Dict]:
    name = source['name']
    if name == 'Idealista':
        items = extract_idealista(page, source)
    elif name == 'Fotocasa':
        items = extract_fotocasa(page, source)
    elif name == 'Milanuncios':
        items = extract_milanuncios(page, source)
    elif name == 'Wallapop':
        items = extract_wallapop(page, source)
    else:
        items = []
    if not items:
        items = extract_from_json_ld(soup, source)
    return dedupe_results(items)


def collect_source(page: Page, source: Dict):
    page.goto(source['url'], wait_until='domcontentloaded')
    page.wait_for_timeout(5000)
    accept_cookies(page)
    auto_scroll(page)
    click_load_more(page)
    auto_scroll(page, rounds=6, pixels=5000, wait_ms=1300)
    page.wait_for_timeout(1000)
    html = page.content()
    save_debug_assets(source['name'], page)
    soup = BeautifulSoup(html, 'html.parser')
    results = extract_items(page, soup, source)
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
    return collected, report
