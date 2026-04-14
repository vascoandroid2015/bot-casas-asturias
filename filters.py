import math
import re
import unicodedata
from typing import Dict, Optional, Tuple

from config import (
    CENTER_COORDS,
    MAX_DISTANCE_KM,
    MAX_PRICE,
    MIN_PRICE,
    MUNICIPALITIES,
    NEGATIVE_TERMS,
    PRIORITY_TERMS,
    SEARCH_TERMS,
)


def normalize_text(text: str) -> str:
    text = text or ""
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def clean_price(text: str) -> Optional[int]:
    if not text:
        return None
    text = text.replace("EUR", "€").replace("euros", "€")
    patterns = [
        r"(\d{1,3}(?:[\.\s]\d{3})+|\d{4,6})\s*€",
        r"€\s*(\d{1,3}(?:[\.\s]\d{3})+|\d{4,6})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(re.sub(r"\D", "", match.group(1)))
    return None


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(h))


def detect_municipality(text: str) -> Tuple[Optional[str], Optional[float]]:
    base = normalize_text(text)
    for municipality, coords in MUNICIPALITIES.items():
        if municipality in base:
            return municipality.title(), round(haversine_km(CENTER_COORDS, coords), 1)
    return None, None


def score_listing(item: Dict) -> int:
    text = normalize_text(" ".join([item.get("title", ""), item.get("description", ""), item.get("location", "")]))
    score = 0
    for term in PRIORITY_TERMS:
        if normalize_text(term) in text:
            score += 2
    if item.get("price") and item["price"] <= 150000:
        score += 2
    if item.get("distance_km") is not None and item["distance_km"] <= 30:
        score += 2
    return score


def is_relevant_listing(item: Dict) -> bool:
    text = normalize_text(" ".join([item.get("title", ""), item.get("description", ""), item.get("location", "")]))
    if any(term in text for term in map(normalize_text, NEGATIVE_TERMS)):
        return False
    if not any(term in text for term in map(normalize_text, SEARCH_TERMS)):
        return False
    price = item.get("price")
    if price is None or not (MIN_PRICE <= price <= MAX_PRICE):
        return False
    municipality, distance = detect_municipality(text)
    item["municipality"] = municipality
    item["distance_km"] = distance
    if distance is not None and distance > MAX_DISTANCE_KM:
        return False
    return True
