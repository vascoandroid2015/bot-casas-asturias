from typing import Dict, List
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


def scrape_idealista(page: Page) -> List[Dict]:
    url = next(p["search_url"] for p in TARGET_PORTALS if p["name"] == "Idealista")
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    page.mouse.wheel(0, 5000)
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
        location = _safe_text(item, ".item-detail-char") or _safe_text(item, ".item-detail-char > span")
        description = _safe_text(item, ".item-description") or item.get_text(" ", strip=True)
        price = clean_price(price_text)
        results.append(
            {
                "source": "Idealista",
                "title": title,
                "price": price,
                "url": urljoin("https://www.idealista.com", href),
                "location": location,
                "description": description,
            }
        )
    return results


def scrape_milanuncios(page: Page) -> List[Dict]:
    url = next(p["search_url"] for p in TARGET_PORTALS if p["name"] == "Milanuncios")
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    page.mouse.wheel(0, 6000)
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
        results.append(
            {
                "source": "Milanuncios",
                "title": text[:160],
                "price": clean_price(text),
                "url": urljoin("https://www.milanuncios.com", href),
                "location": text[:220],
                "description": text[:600],
            }
        )
    return results


def scrape_fotocasa(page: Page) -> List[Dict]:
    url = next(p["search_url"] for p in TARGET_PORTALS if p["name"] == "Fotocasa")
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(5500)
    page.mouse.wheel(0, 5500)
    page.wait_for_timeout(2500)
    soup = BeautifulSoup(page.content(), "html.parser")
    items = soup.select("article, div.re-CardPackPremium, div.re-CardPack")
    results = []
    for item in items:
        link_tag = item.find("a", href=True)
        text = item.get_text(" ", strip=True)
        if not link_tag or len(text) < 30:
            continue
        href = link_tag["href"]
        results.append(
            {
                "source": "Fotocasa",
                "title": text[:160],
                "price": clean_price(text),
                "url": urljoin("https://www.fotocasa.es", href),
                "location": text[:220],
                "description": text[:600],
            }
        )
    return results


def run_all_scrapers(browser: Browser) -> List[Dict]:
    collected = []
    for scraper in (scrape_idealista, scrape_milanuncios, scrape_fotocasa):
        page = prepare_page(browser)
        try:
            collected.extend(scraper(page))
        except Exception as exc:
            collected.append(
                {
                    "source": "Sistema",
                    "title": f"Error en scraper {scraper.__name__}",
                    "price": None,
                    "url": "",
                    "location": "",
                    "description": str(exc),
                    "error": True,
                }
            )
        finally:
            page.context.close()
    return collected
