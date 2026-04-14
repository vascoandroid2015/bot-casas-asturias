from typing import Dict, List

from playwright.sync_api import sync_playwright

from config import MAX_RESULTS_PER_RUN
from filters import is_relevant_listing, score_listing
from scrapers import run_all_scrapers
from storage import load_seen, save_seen
from telegram_client import build_message, send_message


def dedupe_by_url(items: List[Dict]) -> List[Dict]:
    seen = set()
    deduped = []
    for item in items:
        url = item.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(item)
    return deduped


def process_items(scraped: List[Dict], history: Dict) -> List[Dict]:
    candidates = []
    for item in dedupe_by_url(scraped):
        if item.get("error"):
            continue
        if not is_relevant_listing(item):
            continue
        item["score"] = score_listing(item)
        prev = history.get(item["url"])
        if not prev:
            item["change_type"] = "new"
            candidates.append(item)
            continue
        prev_price = prev.get("price")
        if prev_price != item.get("price"):
            item["previous_price"] = prev_price
            item["change_type"] = "price_change"
            candidates.append(item)
    return sorted(candidates, key=lambda x: (x.get("change_type") != "price_change", -x.get("score", 0), x.get("price") or 999999))


def update_history(scraped: List[Dict], history: Dict) -> Dict:
    for item in dedupe_by_url(scraped):
        if not item.get("url") or item.get("error"):
            continue
        history[item["url"]] = {
            "title": item.get("title"),
            "price": item.get("price"),
            "source": item.get("source"),
            "location": item.get("location"),
        }
    return history


def main() -> None:
    history = load_seen()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        scraped = run_all_scrapers(browser)
        browser.close()

    to_notify = process_items(scraped, history)[:MAX_RESULTS_PER_RUN]

    if not to_notify:
        send_message("ℹ️ Bot inmobiliario activo, sin novedades que cumplan filtros en esta ejecución.")
    else:
        for item in to_notify:
            previous_price = item.get("previous_price")
            message = build_message(item, previous_price=previous_price)
            send_message(message)

    history = update_history(scraped, history)
    save_seen(history)


if __name__ == "__main__":
    main()
