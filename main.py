import json
import math
import os
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from html import escape
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@casaspiedrasenasturias")

PRECIO_MAXIMO = 250000
PARCELA_MINIMA = 600
MAX_MINUTOS_OVIEDO = 15
OVIEDO_REF: Tuple[float, float] = (43.3614, -5.8494)
OVIEDO_REF_LABEL = "Oviedo centro"
SEEN_FILE = "seen_ads.json"
TIMEOUT = 25
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"

KEYWORDS_PRIORITY = [
    "piedra", "casa de piedra", "casona", "casa rural", "independiente",
    "finca", "parcela", "terreno", "huerta", "hórreo", "horreo", "jardín", "jardin"
]
KEYWORDS_EXCLUDE = [
    "piso", "apartamento", "ático", "atico", "estudio", "habitación", "habitacion"
]
OVIEDO_AREA_HINTS = [
    "oviedo", "siero", "noreña", "norena", "llanera", "las regueras", "ribera de arriba",
    "mieres", "langreo", "morcín", "morcin", "sariego"
]

SEARCH_SOURCES = [
    {
        "name": "Fotocasa",
        "url": "https://www.fotocasa.es/es/comprar/chalets/asturias-provincia/todas-las-zonas/l",
        "base": "https://www.fotocasa.es",
    },
    {
        "name": "Pisos.com",
        "url": "https://www.pisos.com/venta/casas-asturias/",
        "base": "https://www.pisos.com",
    },
    {
        "name": "Wallapop",
        "url": "https://es.wallapop.com/inmobiliaria/casas/oviedo",
        "base": "https://es.wallapop.com",
    },
    {
        "name": "Nortecasa",
        "url": "https://www.nortecasa.com/inmuebles/todos/",
        "base": "https://www.nortecasa.com",
    },
    {
        "name": "Aldeasabandonadas",
        "url": "https://www.aldeasabandonadas.com/venta-de-casas-rurales/62-venta-de-casas-rurales-asturias.html",
        "base": "https://www.aldeasabandonadas.com",
    },
    {
        "name": "Idealista",
        "url": "https://www.idealista.com/venta-viviendas/asturias/con-casas-de-piedra,chalets/?ordenado-por=fecha-publicacion-desc",
        "base": "https://www.idealista.com",
    },
]

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "es-ES,es;q=0.9"})


@dataclass
class Listing:
    source: str
    url: str
    title: str
    location_text: str
    price: Optional[int]
    parcela_m2: Optional[int]
    lat: Optional[float]
    lon: Optional[float]
    minutes_to_oviedo: Optional[int]
    maps_url: str
    summary: str
    score: int
    seen_at: str


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def normalize_url(url: str, base: str) -> str:
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("http"):
        return url
    return base.rstrip("/") + "/" + url.lstrip("/")


def parse_price(text: str) -> Optional[int]:
    if not text:
        return None
    for pattern in [r"([\d\.]{3,})\s*€", r"([\d\.,]{3,})\s*euros?", r"precio[: ]+([\d\.]{3,})"]:
        m = re.search(pattern, text.lower())
        if m:
            num = re.sub(r"[^\d]", "", m.group(1))
            if num:
                return int(num)
    return None


def parse_parcela(text: str) -> Optional[int]:
    if not text:
        return None
    low = text.lower()
    patterns = [
        r"parcela(?: de)?\s*([\d\.,]+)\s*m[²2]",
        r"finca(?: de)?\s*([\d\.,]+)\s*m[²2]",
        r"terreno(?: de)?\s*([\d\.,]+)\s*m[²2]",
        r"([\d\.,]+)\s*m[²2]\s*de\s*(?:parcela|finca|terreno)",
        r"solar(?: de)?\s*([\d\.,]+)\s*m[²2]",
        r"huerta(?: de)?\s*([\d\.,]+)\s*m[²2]",
    ]
    for pattern in patterns:
        m = re.search(pattern, low)
        if m:
            num = re.sub(r"[^\d]", "", m.group(1))
            if num:
                return int(num)
    return None


def keyword_score(text: str) -> int:
    low = text.lower()
    score = 0
    for kw in KEYWORDS_PRIORITY:
        if kw in low:
            score += 2
    for kw in OVIEDO_AREA_HINTS:
        if kw in low:
            score += 1
    for kw in KEYWORDS_EXCLUDE:
        if kw in low:
            score -= 3
    return score


def looks_relevant(text: str) -> bool:
    low = text.lower()
    has_positive = any(k in low for k in KEYWORDS_PRIORITY)
    has_oviedo_area = any(k in low for k in OVIEDO_AREA_HINTS)
    return has_positive or has_oviedo_area


def geocode_location(location_text: str) -> Tuple[Optional[float], Optional[float]]:
    if not location_text:
        return None, None
    query = f"{location_text}, Asturias, España"
    try:
        response = session.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "jsonv2", "limit": 1},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None, None
    return None, None


def haversine_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    radius = 6371.0
    p1 = math.radians(a_lat)
    p2 = math.radians(b_lat)
    dp = math.radians(b_lat - a_lat)
    dl = math.radians(b_lon - a_lon)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(x), math.sqrt(1 - x))


def estimate_drive_minutes(lat: Optional[float], lon: Optional[float]) -> Optional[int]:
    if lat is None or lon is None:
        return None
    km = haversine_km(OVIEDO_REF[0], OVIEDO_REF[1], lat, lon)
    return round((km * 1.35 / 50) * 60)


def google_maps_url(lat: Optional[float], lon: Optional[float], query: str) -> str:
    if lat is not None and lon is not None:
        return f"https://www.google.com/maps?q={lat},{lon}"
    return f"https://www.google.com/maps/search/?api=1&query={quote(query)}"


def fetch(url: str) -> str:
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text


def extract_location(text: str) -> str:
    m = re.search(
        r"(Oviedo|Siero|Noreña|Norena|Llanera|Las Regueras|Ribera de Arriba|Mieres|Langreo|Morcín|Morcin|Sariego|Gijón|Gijon|Avilés|Aviles|Piloña|Pilona)",
        text,
        re.I,
    )
    return m.group(1) if m else ""


def scrape_listing_detail(url: str, source_name: str) -> Optional[dict]:
    try:
        html = fetch(url)
    except Exception:
        return None
    soup = BeautifulSoup(html, "html.parser")
    text = clean_text(soup.get_text(" ", strip=True))[:15000]
    title = ""
    title_el = soup.select_one("h1") or soup.select_one("title")
    if title_el:
        title = clean_text(title_el.get_text(" ", strip=True))
    location = extract_location(text)
    price = parse_price(text)
    parcela = parse_parcela(text)
    return {
        "title": title,
        "text": text,
        "location": location,
        "price": price,
        "parcela": parcela,
        "source": source_name,
    }


def scrape_candidates(source: Dict[str, str]) -> List[Tuple[str, str, str]]:
    results = []
    try:
        html = fetch(source["url"])
    except Exception:
        return results
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article, .item, .listing, .card, li, .re-CardPack, .property, .result")[:120]
    seen = set()
    for card in cards:
        a = card.select_one("a[href]")
        if not a:
            continue
        url = normalize_url(a.get("href", ""), source["base"])
        if not url or url in seen:
            continue
        seen.add(url)
        text = clean_text(card.get_text(" ", strip=True))
        title = clean_text(a.get_text(" ", strip=True)) or text[:120]
        if not looks_relevant(f"{title} {text}"):
            continue
        results.append((url, title, text))
    return results


def build_listing(source: Dict[str, str], candidate_url: str, candidate_title: str, candidate_text: str) -> Optional[Listing]:
    detail = scrape_listing_detail(candidate_url, source["name"])
    if not detail:
        return None
    merged_text = clean_text(f"{candidate_title} {candidate_text} {detail['title']} {detail['text']}")
    score = keyword_score(merged_text)
    if score < 1:
        return None

    price = detail["price"] or parse_price(candidate_text)
    parcela = detail["parcela"] or parse_parcela(candidate_text)
    location = detail["location"] or extract_location(candidate_text) or extract_location(detail["title"])

    lat, lon = geocode_location(location or detail["title"] or candidate_title)
    minutes = estimate_drive_minutes(lat, lon)

    passes_hard = (
        price is not None and price <= PRECIO_MAXIMO and
        parcela is not None and parcela >= PARCELA_MINIMA and
        minutes is not None and minutes <= MAX_MINUTOS_OVIEDO
    )

    if not passes_hard:
        if score < 4:
            return None
        if price is not None and price > PRECIO_MAXIMO * 1.1:
            return None
        if minutes is not None and minutes > 22:
            return None

    maps = google_maps_url(lat, lon, f"{location or detail['title']} Asturias")
    return Listing(
        source=source["name"],
        url=candidate_url,
        title=detail["title"] or candidate_title,
        location_text=location or "Asturias",
        price=price,
        parcela_m2=parcela,
        lat=lat,
        lon=lon,
        minutes_to_oviedo=minutes,
        maps_url=maps,
        summary=merged_text[:700],
        score=score,
        seen_at=now_iso(),
    )


def load_seen() -> Dict[str, dict]:
    if not os.path.exists(SEEN_FILE):
        return {}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def save_seen(data: Dict[str, dict]) -> None:
    with open(SEEN_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def send_telegram(message: str) -> None:
    if not TELEGRAM_TOKEN:
        print("Falta TELEGRAM_TOKEN")
        return
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=TIMEOUT,
    )


def fmt_eur(value: Optional[int]) -> str:
    if value is None:
        return "N/D"
    return f"{value:,.0f} €".replace(",", ".")


def fmt_m2(value: Optional[int]) -> str:
    return f"{value} m²" if value is not None else "N/D"


def fmt_min(value: Optional[int]) -> str:
    return f"{value} min" if value is not None else "N/D"


def build_new_message(listing: Listing) -> str:
    return (
        f"🏡 <b>NUEVA OPORTUNIDAD</b>\n\n"
        f"<b>{escape(listing.title)}</b>\n"
        f"💶 Precio: <b>{fmt_eur(listing.price)}</b>\n"
        f"📐 Parcela: <b>{fmt_m2(listing.parcela_m2)}</b>\n"
        f"📍 Zona: {escape(listing.location_text)}\n"
        f"🚗 Tiempo a {OVIEDO_REF_LABEL}: <b>{fmt_min(listing.minutes_to_oviedo)}</b>\n"
        f"⭐ Relevancia: <b>{listing.score}</b>\n"
        f"🗺 <a href=\"{listing.maps_url}\">Ver en Google Maps</a>\n"
        f"🌐 Fuente: {escape(listing.source)}\n"
        f"🔗 <a href=\"{listing.url}\">Ver anuncio</a>"
    )


def build_price_change_message(listing: Listing, old_price: int) -> str:
    is_drop = listing.price is not None and listing.price < old_price
    icon = "💸" if is_drop else "📈"
    label = "BAJADA DE PRECIO" if is_drop else "CAMBIO DE PRECIO"
    diff = "N/D" if listing.price is None else fmt_eur(abs(listing.price - old_price))
    return (
        f"{icon} <b>{label}</b>\n\n"
        f"<b>{escape(listing.title)}</b>\n"
        f"💶 Antes: <s>{fmt_eur(old_price)}</s>\n"
        f"💶 Ahora: <b>{fmt_eur(listing.price)}</b>\n"
        f"↕ Diferencia: <b>{diff}</b>\n"
        f"📐 Parcela: <b>{fmt_m2(listing.parcela_m2)}</b>\n"
        f"📍 Zona: {escape(listing.location_text)}\n"
        f"🚗 Tiempo a {OVIEDO_REF_LABEL}: <b>{fmt_min(listing.minutes_to_oviedo)}</b>\n"
        f"⭐ Relevancia: <b>{listing.score}</b>\n"
        f"🗺 <a href=\"{listing.maps_url}\">Ver en Google Maps</a>\n"
        f"🌐 Fuente: {escape(listing.source)}\n"
        f"🔗 <a href=\"{listing.url}\">Ver anuncio</a>"
    )


def dedupe(listings: List[Listing]) -> List[Listing]:
    best: Dict[str, Listing] = {}
    for listing in listings:
        key = listing.url.split("?")[0].rstrip("/")
        if key not in best or listing.score > best[key].score:
            best[key] = listing
    return list(best.values())


def run() -> None:
    found: List[Listing] = []
    for source in SEARCH_SOURCES:
        print(f"Buscando candidatos en {source['name']}...")
        candidates = scrape_candidates(source)[:20]
        print(f"  candidatos: {len(candidates)}")
        for url, title, text in candidates:
            listing = build_listing(source, url, title, text)
            if listing:
                found.append(listing)
            time.sleep(0.6)

    found = dedupe(found)
    found.sort(key=lambda item: (-(item.score or 0), item.price or 999999999))
    found = found[:15]

    seen = load_seen()
    updated = dict(seen)
    sent = 0

    for listing in found:
        key = listing.url.split("?")[0].rstrip("/")
        previous = seen.get(key)

        if previous is None:
            send_telegram(build_new_message(listing))
            sent += 1
        else:
            old_price = previous.get("price")
            if old_price != listing.price:
                send_telegram(build_price_change_message(listing, old_price or 0))
                sent += 1

        updated[key] = asdict(listing)

    save_seen(updated)
    print(f"Anuncios candidatos finales: {len(found)} | avisos enviados: {sent}")


if __name__ == "__main__":
    run()
