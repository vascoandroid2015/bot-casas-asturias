from collections import Counter
from typing import Dict, List

from playwright.sync_api import sync_playwright

from config import HEADLESS, MAX_RESULTS_PER_RUN
from filters import classify_listing, score_listing
from scrapers import run_all_scrapers
from storage import load_seen, save_debug, save_seen
from telegram_client import build_debug_message, build_message, send_message


def dedupe_key(item: Dict):
    return item.get('url') or ''


def dedupe_items(items: List[Dict]) -> List[Dict]:
    seen, deduped = set(), []
    for item in items:
        key = dedupe_key(item)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def process_items(scraped: List[Dict], history: Dict):
    candidates, flagged = [], []
    for item in dedupe_items(scraped):
        classify_listing(item)
        item['score'] = score_listing(item)
        prev = history.get(item['url'])
        if prev and prev.get('price') != item.get('price'):
            item['previous_price'] = prev.get('price')
            item['change_type'] = 'price_change'
        else:
            item['change_type'] = 'all'

        if item.get('reject_reasons'):
            flagged.append(item)
        candidates.append(item)

    candidates = sorted(candidates, key=lambda x: (-x.get('score', 0), x.get('price') or 999999999))
    return candidates, flagged


def update_history(scraped: List[Dict], history: Dict) -> Dict:
    for item in dedupe_items(scraped):
        if not item.get('url'):
            continue
        history[item['url']] = {
            'title': item.get('title'),
            'price': item.get('price'),
            'source': item.get('source'),
            'location': item.get('location'),
        }
    return history


def build_report(scraped: List[Dict], flagged: List[Dict], to_notify: List[Dict], source_stats: List[Dict]) -> Dict:
    reject_counter = Counter()
    for item in flagged:
        for reason in item.get('reject_reasons', ['signal']):
            reject_counter[reason] += 1
    for source in source_stats:
        name = source['name']
        source['valid_count'] = sum(1 for x in scraped if x.get('source') == name)
        source['notify_count'] = sum(1 for x in to_notify if x.get('source') == name)
    return {
        'scraped_count': len(scraped),
        'rejected_count': len(flagged),
        'notified_count': len(to_notify),
        'reject_reasons': dict(reject_counter),
        'sources': source_stats,
        'examples_to_notify': to_notify[:5],
        'examples_rejected': flagged[:5],
    }


def main():
    history = load_seen()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        scraped, source_stats = run_all_scrapers(browser)
        browser.close()

    to_notify, flagged = process_items(scraped, history)
    if MAX_RESULTS_PER_RUN and MAX_RESULTS_PER_RUN > 0:
        to_notify = to_notify[:MAX_RESULTS_PER_RUN]

    if not to_notify:
        send_message('ℹ️ Metabuscador inmobiliario activo, sin anuncios detectados en esta ejecución.')
    else:
        for item in to_notify:
            send_message(build_message(item, previous_price=item.get('previous_price')))

    report = build_report(scraped, flagged, to_notify, source_stats)
    save_debug(report)
    debug_message = build_debug_message(report)
    if debug_message:
        send_message(debug_message)

    history = update_history(scraped, history)
    save_seen(history)


if __name__ == '__main__':
    main()
