import math, re, unicodedata
from typing import Dict, Optional, Tuple
from config import ALLOW_UNKNOWN_LOCATION, CENTER_COORDS, MAX_DISTANCE_KM, MAX_PRICE, MIN_PRICE, MUNICIPALITIES, NEGATIVE_TERMS, PRIORITY_TERMS, SEARCH_TERMS, STRICT_DISTANCE_FILTER

def normalize_text(text: str) -> str:
    text = (text or "").lower().strip(); text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))

def clean_price(text: str) -> Optional[int]:
    if not text: return None
    text = text.replace("EUR", "€").replace("euros", "€")
    for pattern in [r"(\d{1,3}(?:[\.\s]\d{3})+|\d{4,6})\s*€", r"€\s*(\d{1,3}(?:[\.\s]\d{3})+|\d{4,6})"]:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            digits = re.sub(r"\D", "", m.group(1))
            if digits: return int(digits)
    return None

def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a); lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1; dlon = lon2 - lon1
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371.0 * 2 * math.asin(math.sqrt(h))

def detect_municipality(text: str):
    base = normalize_text(text)
    for municipality, coords in MUNICIPALITIES.items():
        if municipality in base: return municipality.title(), round(haversine_km(CENTER_COORDS, coords), 1)
    return None, None

def classify_listing(item: Dict) -> Dict:
    text = normalize_text(" ".join([item.get("title",""), item.get("description",""), item.get("location","")]))
    municipality, distance = detect_municipality(text)
    item["municipality"] = municipality; item["distance_km"] = distance
    reasons = []
    if any(term in text for term in map(normalize_text, NEGATIVE_TERMS)): reasons.append("negative_term")
    if not any(term in text for term in map(normalize_text, SEARCH_TERMS)): reasons.append("missing_search_term")
    price = item.get("price")
    if price is None: reasons.append("missing_price")
    elif not (MIN_PRICE <= price <= MAX_PRICE): reasons.append("price_out_of_range")
    if municipality is None and not ALLOW_UNKNOWN_LOCATION: reasons.append("unknown_location")
    if STRICT_DISTANCE_FILTER and distance is not None and distance > MAX_DISTANCE_KM: reasons.append("outside_radius")
    item["valid"] = not reasons; item["reject_reasons"] = reasons
    return item

def score_listing(item: Dict) -> int:
    text = normalize_text(" ".join([item.get("title",""), item.get("description",""), item.get("location","")]))
    score = sum(2 for term in PRIORITY_TERMS if normalize_text(term) in text)
    if item.get("price") and item["price"] <= 150000: score += 2
    if item.get("distance_km") is not None and item["distance_km"] <= 30: score += 2
    return score
