from collections import Counter
from datetime import datetime
from typing import Dict, List

from playwright.sync_api import sync_playwright

from config import HEADLESS, MAX_RESULTS_PER_RUN
from filters import classify_listing, score_listing
from scrapers import run_all_scrapers
from storage import load_seen, save_control_report, save_debug, save_seen
from telegram_client import build_message, send_message

def now_iso() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

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

def detect_changes(item: Dict, prev: Dict) -> List[str]:
    changes = []
    if not prev:
        changes.append('new')
        return changes
    if prev.get('last_price') != item.get('price'):
        changes.append('price')
    if (prev.get('title') or '').strip() != (item.get('title') or '').strip():
        changes.append('title')
    prev_loc = (prev.get('location') or '').strip()
    new_loc = (item.get('location') or '').strip()
    if prev_loc != new_loc:
        changes.append('location')
    return changes

def process_items(scraped: List[Dict], history: Dict):
    candidates, flagged = [], []
    for item in dedupe_items(scraped):
        classify_listing(item)
        item['score'] = score_listing(item)
        prev = history.get(item['url'])
        changes = detect_changes(item, prev)
        item['changes'] = changes
        item['previous_price'] = prev.get('last_price') if prev else None
        if 'new' in changes:
            item['change_type'] = 'new'
            candidates.append(item)
        elif changes:
            item['change_type'] = 'updated'
            candidates.append(item)
        else:
            item['change_type'] = 'unchanged'
        if item.get('reject_reasons'):
            flagged.append(item)
    candidates = sorted(candidates, key=lambda x: (-x.get('score', 0), x.get('price') or 999999999))
    return candidates, flagged

def update_history(scraped: List[Dict], history: Dict, notified: List[Dict]) -> Dict:
    timestamp = now_iso()
    notified_urls = {x.get('url') for x in notified if x.get('url')}
    for item in dedupe_items(scraped):
        url = item.get('url')
        if not url:
            continue
        prev = history.get(url, {})
        record = {
            'title': item.get('title'),
            'source': item.get('source'),
            'kind': item.get('kind'),
            'location': item.get('location'),
            'last_price': item.get('price'),
            'first_seen_at': prev.get('first_seen_at', timestamp),
            'last_seen_at': timestamp,
            'first_sent_at': prev.get('first_sent_at'),
            'last_notified_at': prev.get('last_notified_at'),
            'times_seen': int(prev.get('times_seen', 0)) + 1,
            'times_notified': int(prev.get('times_notified', 0)),
            'status': 'active',
        }
        if url in notified_urls:
            record['first_sent_at'] = prev.get('first_sent_at', timestamp)
            record['last_notified_at'] = timestamp
            record['times_notified'] = int(prev.get('times_notified', 0)) + 1
        history[url] = record
    return history

def build_report(scraped: List[Dict], flagged: List[Dict], to_notify: List[Dict], source_stats: List[Dict]) -> Dict:
    reject_counter = Counter()
    change_counter = Counter()
    for item in flagged:
        for reason in item.get('reject_reasons', ['signal']):
            reject_counter[reason] += 1
    for item in to_notify:
        for change in item.get('changes', []):
            change_counter[change] += 1
    for source in source_stats:
        name = source['name']
        source['valid_count'] = sum(1 for x in scraped if x.get('source') == name)
        source['notify_count'] = sum(1 for x in to_notify if x.get('source') == name)
    return {
        'scraped_count': len(scraped),
        'rejected_count': len(flagged),
        'notified_count': len(to_notify),
        'reject_reasons': dict(reject_counter),
        'changes': dict(change_counter),
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
        send_message('ℹ️ Metabuscador inmobiliario activo, sin anuncios nuevos ni cambios detectados en esta ejecución.')
    else:
        for item in to_notify:
            send_message(build_message(item, previous_price=item.get('previous_price')))
    report = build_report(scraped, flagged, to_notify, source_stats)
    save_debug(report)
    history = update_history(scraped, history, to_notify)
    save_seen(history)
    save_control_report(history)

if __name__ == '__main__':
    main()
