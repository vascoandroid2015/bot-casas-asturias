import json
import re
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
SPECIAL_SOURCE_NAMES = {'Idealista', 'Fotocasa', 'Milanuncios', 'Wallapop'}


def prepare_page(browser: Browser) -> Page:
    context = browser.new_context(
        user_agent=USER_AGENT,
        viewport={'width': 1440, 'height': 2400},
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


def auto_scroll(page: Page, rounds: int = 10, pixels: int = 7000, wait_ms: int = 1800):
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


def try_expand_source(page: Page, source_name: str):
    if source_name == 'Idealista':
        for selector in [
            "button:has-text('Ver más')",
            "button:has-text('Mostrar más')",
            "a:has-text('Siguiente')",
        ]:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=1000):
                    btn.click(timeout=1000)
                    page.wait_for_timeout(1500)
            except Exception:
                pass
    elif source_name in {'Fotocasa', 'Milanuncios', 'Wallapop'}:
        for selector in [
            "button:has-text('Ver más')",
            "button:has-text('Cargar más')",
            "button:has-text('Mostrar más')",
        ]:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=800):
                    btn.click(timeout=1000)
                    page.wait_for_timeout(1200)
            except Exception:
                pass


def normalize_href(href: str, base_url: str) -> str:
    if not href:
        return ''
    href = href.strip()
    if href.startswith('//'):
        return 'https:' + href
    return urljoin(base_url, href)


def build_item(source: Dict, href: str, text: str, title: str = '') -> Dict:
    href = normalize_href(href, source['base_url'])
    clean_text = re.sub(r'\s+', ' ', text or '').strip()
    clean_title = re.sub(r'\s+', ' ', title or '').strip() or clean_text[:170] or 'Sin título'
    return {
        'source': source['name'],
        'kind': source['kind'],
        'title': clean_title[:170],
        'price': clean_price(clean_text),
        'url': href,
        'location': clean_text[:240],
        'description': clean_text[:900],
    }


def extract_generic_items(soup, selectors: List[str], source: Dict) -> List[Dict]:
    results, seen = [], set()
    for selector in selectors:
        for item in soup.select(selector):
            link_tag = item.find('a', href=True)
            text = item.get_text(' ', strip=True)
            if not link_tag or len(text) < 25:
                continue
            href = normalize_href(link_tag.get('href', ''), source['base_url'])
            if not href or href in seen:
                continue
            seen.add(href)
            title = link_tag.get_text(' ', strip=True) or text[:170]
            results.append(build_item(source, href, text, title))
    return results


def extract_idealista(page: Page, source: Dict) -> List[Dict]:
    results, seen = [], set()
    selectors = [
        'article.item',
        'article[data-adid]',
        '[class*="item"]:has(a[href*="/inmueble/"])',
        'a[href*="/inmueble/"]',
    ]
    for selector in selectors:
        try:
            nodes = page.locator(selector).all()
        except Exception:
            nodes = []
        for node in nodes:
            try:
                if 'a[href*="/inmueble/"]' in selector:
                    href = node.get_attribute('href')
                    text = node.text_content() or ''
                    title = text.strip()
                else:
                    link = node.locator('a[href*="/inmueble/"]').first
                    href = link.get_attribute('href')
                    text = node.text_content() or ''
                    title = link.text_content() or ''
                href = normalize_href(href or '', source['base_url'])
                if not href or href in seen or '/inmueble/' not in href:
                    continue
                if len((text or '').strip()) < 20:
                    continue
                seen.add(href)
                results.append(build_item(source, href, text, title))
            except Exception:
                continue
    return results


def extract_fotocasa(page: Page, source: Dict) -> List[Dict]:
    results, seen = [], set()
    selectors = [
        'a[href*="/es/comprar/vivienda/"]',
        'a[href*="/es/comprar/casa/"]',
        '[class*="re-Card"] a[href]',
        '[class*="CardPack"] a[href]',
    ]
    for selector in selectors:
        try:
            links = page.locator(selector).all()
        except Exception:
            links = []
        for link in links:
            try:
                href = normalize_href(link.get_attribute('href') or '', source['base_url'])
                if not href or href in seen:
                    continue
                if '/es/comprar/' not in href:
                    continue
                container = link.locator('xpath=ancestor-or-self::*[self::article or contains(@class, "Card") or contains(@class, "card")][1]').first
                text = (container.text_content() if container.count() else link.text_content()) or ''
                title = (link.text_content() or text).strip()
                if len(text.strip()) < 20:
                    continue
                seen.add(href)
                results.append(build_item(source, href, text, title))
            except Exception:
                continue
    return results


def extract_milanuncios(page: Page, source: Dict) -> List[Dict]:
    results, seen = [], set()
    selectors = [
        'a[href*="/inmuebles/"]',
        'a[href*="/venta-de-casas/"]',
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
                if not href or href in seen:
                    continue
                if 'milanuncios.com' not in href:
                    continue
                container = link.locator('xpath=ancestor-or-self::*[self::article or contains(@class, "AdCard") or contains(@class, "ad-card")][1]').first
                text = (container.text_content() if container.count() else link.text_content()) or ''
                title = (link.text_content() or text).strip()
                if len(text.strip()) < 20:
                    continue
                seen.add(href)
                results.append(build_item(source, href, text, title))
            except Exception:
                continue
    return results


def extract_wallapop(page: Page, source: Dict) -> List[Dict]:
    results, seen = [], set()
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
                if not href or href in seen:
                    continue
                if '/item/' not in href:
                    continue
                container = link.locator('xpath=ancestor-or-self::*[self::article or contains(@data-testid, "item-card") or contains(@class, "card")][1]').first
                text = (container.text_content() if container.count() else link.text_content()) or ''
                title = (link.text_content() or text).strip()
                if len(text.strip()) < 10:
                    continue
                seen.add(href)
                results.append(build_item(source, href, text, title))
            except Exception:
                continue
    return results


def extract_from_json_ld(soup: BeautifulSoup, source: Dict) -> List[Dict]:
    results, seen = [], set()
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
            item_list = block.get('itemListElement') if block.get('@type') == 'ItemList' else None
            if not item_list:
                continue
            for entry in item_list:
                if isinstance(entry, dict):
                    entry = entry.get('item') or entry
                if not isinstance(entry, dict):
                    continue
                href = normalize_href(entry.get('url', ''), source['base_url'])
                title = entry.get('name', '')
                text = ' '.join(str(entry.get(k, '')) for k in ['name', 'description'])
                if not href or href in seen:
                    continue
                seen.add(href)
                results.append(build_item(source, href, text, title))
    return results


def extract_items(page: Page, soup: BeautifulSoup, selectors: List[str], source: Dict) -> List[Dict]:
    if source['name'] == 'Idealista':
        results = extract_idealista(page, source)
    elif source['name'] == 'Fotocasa':
        results = extract_fotocasa(page, source)
    elif source['name'] == 'Milanuncios':
        results = extract_milanuncios(page, source)
    elif source['name'] == 'Wallapop':
        results = extract_wallapop(page, source)
    else:
        results = extract_generic_items(soup, selectors, source)

    if not results:
        results = extract_from_json_ld(soup, source)

    if not results:
        results = extract_generic_items(soup, selectors, source)

    unique = []
    seen = set()
    for item in results:
        url = item.get('url')
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(item)
    return unique


def collect_source(page: Page, source: Dict):
    page.goto(source['url'], wait_until='domcontentloaded')
    page.wait_for_timeout(5000)
    accept_cookies(page)
    auto_scroll(page, rounds=12 if source['name'] in SPECIAL_SOURCE_NAMES else 10)
    try_expand_source(page, source['name'])
    page.wait_for_timeout(1200)
    html = page.content()
    save_debug_assets(source['name'], page)
    soup = BeautifulSoup(html, 'html.parser')
    results = extract_items(page, soup, source['selectors'], source)
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
