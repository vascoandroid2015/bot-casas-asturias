from typing import Dict, List, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Browser, Page

from config import TARGET_PORTALS
from filters import clean_price

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def prepare_page(browser: Browser) -> Page:
    context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1440, "height": 2200})
    page = context.new_page()
    page.set_default_timeout(45000)
    return page


def _safe_text(node, selector: str) -> str:
    found = node.select_one(selector)
    return found.get_text(" ", strip=True) if found else ""


def _collect_idealista(page: Page) -> List[Dict]:
    url = next(p["search_url"] for p in TARGET_PORTALS if p["name"] == "Idealista")
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    page.mouse.wheel(0, 7000)
    page.wait_for_timeout(2500)
    soup = BeautifulSoup(page.content(), "html.parser")
    items = soup.select("article.item")
    results = []
    for item in items:
        title_tag = item.select_one("a.item-link")
        if not title_tag:
            continue
        href = title_tag.get("href", "")
        title = title_tag.get_text(" ", strip=True)
        price_text = _safe_text(item, ".item-price") or item.get_text(" ", strip=True)
        location = _safe_text(item, ".item-detail-char") or item.get_text(" ", strip=True)
        description = _safe_text(item, ".item-description") or item.get_text(" ", strip=True)
        results.append({
            "source": "Idealista",
            "title": title,
            "price": clean_price(price_text),
            "url": urljoin("https://www.idealista.com", href),
            "location": location[:220],
            "description": description[:700],
        })
    return results


def _collect_milanuncios(page: Page) -> List[Dict]:
    url = next(p["search_url"] for p in TARGET_PORTALS if p["name"] == "Milanuncios")
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(4500)
    page.mouse.wheel(0, 8000)
    page.wait_for_timeout(2500)
    soup = BeautifulSoup(page.content(), "html.parser")
    items = soup.select("div.ma-AdCard, article")
    results = []
    for item in items:
        link_tag = item.find("a", href=True)
        text = item.get_text(" ", strip=True)
        if not link_tag or len(text) < 30:
            continue
        href = link_tag["href"]
        results.append({
            "source": "Milanuncios",
            "title": text[:170],
            "price": clean_price(text),
            "url": urljoin("https://www.milanuncios.com", href),
            "location": text[:240],
            "description": text[:700],
        })
    return results


def _collect_fotocasa(page: Page) -> List[Dict]:
    url = next(p["search_url"] for p in TARGET_PORTALS if p["name"] == "Fotocasa")
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(5500)
    page.mouse.wheel(0, 9000)
    page.wait_for_timeout(3000)
    soup = BeautifulSoup(page.content(), "html.parser")
    items = soup.select("article, div.re-CardPackPremium, div.re-CardPack")
    results = []
    for item in items:
        link_tag = item.find("a", href=True)
        text = item.get_text(" ", strip=True)
        if not link_tag or len(text) < 30:
            continue
        href = link_tag["href"]
        results.append({
            "source": "Fotocasa",
            "title": text[:170],
            "price": clean_price(text),
            "url": urljoin("https://www.fotocasa.es", href),
            "location": text[:240],
            "description": text[:700],
        })
    return results


def run_all_scrapers(browser: Browser) -> Tuple[List[Dict], List[Dict]]:
    collected = []
    report = []
    scrapers = [
        ("Idealista", _collect_idealista),
        ("Milanuncios", _collect_milanuncios),
        ("Fotocasa", _collect_fotocasa),
    ]
    for name, scraper in scrapers:
        page = prepare_page(browser)
        raw_items = []
        errors = 0
        try:
            raw_items = scraper(page)
            collected.extend(raw_items)
        except Exception as exc:
            errors = 1
            collected.append({
                "source": name,
                "title": f"Error scraper {name}",
                "price": None,
                "url": "",
                "location": "",
                "description": str(exc),
                "error": True,
            })
        finally:
            page.context.close()
        report.append({"name": name, "raw_count": len(raw_items), "error_count": errors})
    return collected, report
