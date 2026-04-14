from collections import Counter
from typing import Dict, List

from playwright.sync_api import sync_playwright

from config import MAX_RESULTS_PER_RUN
from filters import classify_listing, score_listing
from scrapers import run_all_scrapers
from storage import load_seen, save_debug, save_seen
from telegram_client import build_debug_message, build_message, send_message


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


def process_items(scraped: List[Dict], history: Dict):
    candidates = []
    rejected = []
    for item in dedupe_by_url(scraped):
        if item.get("error"):
            rejected.append(item)
            continue
        classify_listing(item)
        if not item.get("valid"):
            rejected.append(item)
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
    candidates = sorted(candidates, key=lambda x: (x.get("change_type") != "price_change", -x.get("score", 0), x.get("price") or 999999))
    return candidates, rejected


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


def build_report(scraped: List[Dict], rejected: List[Dict], to_notify: List[Dict], portal_stats: List[Dict]) -> Dict:
    reject_counter = Counter()
    for item in rejected:
        for reason in item.get("reject_reasons", ["error"]):
            reject_counter[reason] += 1
    for portal in portal_stats:
        portal_name = portal["name"]
        portal["valid_count"] = sum(1 for x in scraped if x.get("source") == portal_name and not x.get("error") and x.get("valid"))
        portal["notify_count"] = sum(1 for x in to_notify if x.get("source") == portal_name)
    return {
        "scraped_count": len(scraped),
        "rejected_count": len(rejected),
        "notified_count": len(to_notify),
        "reject_reasons": dict(reject_counter),
        "portals": portal_stats,
        "examples_to_notify": to_notify[:5],
        "examples_rejected": rejected[:5],
    }


def main() -> None:
    history = load_seen()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        scraped, portal_stats = run_all_scrapers(browser)
        browser.close()

    to_notify, rejected = process_items(scraped, history)
    to_notify = to_notify[:MAX_RESULTS_PER_RUN]

    if not to_notify:
        send_message("ℹ️ Bot inmobiliario activo, sin novedades notificables en esta ejecución. Revisa el debug_report.json para ver cuántos anuncios se extrajeron y por qué se descartaron.")
    else:
        for item in to_notify:
            send_message(build_message(item, previous_price=item.get("previous_price")))

    report = build_report(scraped, rejected, to_notify, portal_stats)
    save_debug(report)
    debug_message = build_debug_message(report)
    if debug_message:
        send_message(debug_message)

    history = update_history(scraped, history)
    save_seen(history)


if __name__ == "__main__":
    main()
