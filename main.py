import json
from pathlib import Path
from scrapers import scrape_example_portal
from storage import load_seen, save_seen
from telegram_client import build_message, build_debug_message, send_message

MAX_PRICE = 250000
DEBUG_PATH = Path("debug_report.json")


def parse_price(value: str) -> int:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else 0


def normalize_item(item: dict) -> dict:
    item = dict(item)
    item["price_num"] = parse_price(item.get("price", 0))
    return item


def is_valid(item: dict) -> bool:
    return item.get("price_num", 0) <= MAX_PRICE


def main():
    seen = load_seen()
    stats = {"total_found": 0, "total_new": 0, "total_sent": 0, "sources": {}}
    all_items = []
    sources = {"Example": scrape_example_portal}

    for source_name, fn in sources.items():
        source_stats = {"found": 0, "valid": 0, "new": 0, "errors": 0}
        try:
            items = [normalize_item(x) for x in fn()]
            source_stats["found"] = len(items)
            stats["total_found"] += len(items)
            for item in items:
                if is_valid(item):
                    source_stats["valid"] += 1
                    all_items.append(item)
        except Exception:
            source_stats["errors"] += 1
        stats["sources"][source_name] = source_stats

    new_items = []
    for item in all_items:
        key = item.get("id") or item.get("url")
        fingerprint = f"{item.get('price')}|{item.get('title')}|{item.get('location')}"
        if seen.get(key) != fingerprint:
            new_items.append(item)
            seen[key] = fingerprint

    stats["total_new"] = len(new_items)

    for item in new_items:
        send_message(build_message(item))
        stats["total_sent"] += 1
        src = item.get("source", "unknown")
        if src in stats["sources"]:
            stats["sources"][src]["new"] += 1

    if not new_items:
        send_message("ℹ️ Bot inmobiliario activo, sin novedades notificables en esta ejecución.")

    DEBUG_PATH.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    save_seen(seen)
    send_message(build_debug_message(stats))


if __name__ == "__main__":
    main()
