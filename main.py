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

KEYWORDS_OK = [
    "piedra", "casa de piedra", "casona", "casa rural", "independiente",
    "finca", "parcela", "terreno", "huerta", "hórreo", "horreo"
]
KEYWORDS_BAD = [
    "piso", "apartamento", "ático", "atico", "estudio", "habitación", "habitacion"
]

SEARCH_SOURCES = [
    {
        "name": "Idealista",
        "url": "https://www.idealista.com/venta-viviendas/asturias/con-casas-de-piedra,chalets/?ordenado-por=fecha-publicacion-desc",
        "base": "https://www.idealista.com",
    },
    {
        "name": "Fotocasa",
        "url": "https://www.fotocasa.es/es/comprar/viviendas/asturias-provincia/todas-las-zonas/l",
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
    match = re.search(r"([\d\.]{3,}|\d{2,6})\s*€", text.replace(",", "."))
    if not match:
        match = re.search(r"([\d\.]{3,}|\d{2,6})", text)
    if not match:
        return None
    num = re.sub(r"[^\d]", "", match.group(1))
    if not num:
        return None
    try:
        return int(num)
    except ValueError:
        return None


def parse_parcela(text: str) -> Optional[int]:
    if not text:
        return None
    patterns = [
        r"parcela(?: de)?\s*([\d\.,]+)\s*m[²2]",
        r"finca(?: de)?\s*([\d\.,]+)\s*m[²2]",
        r"terreno(?: de)?\s*([\d\.,]+)\s*m[²2]",
        r"([\d\.,]+)\s*m[²2]\s*de\s*(?:parcela|finca|terreno)",
    ]
    lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            num = re.sub(r"[^\d]", "", match.group(1))
            if num:
                return int(num)
    return None


def contains_good_keywords(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in KEYWORDS_OK)


def contains_bad_keywords(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in KEYWORDS_BAD)


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


def scrape_generic_cards(source: Dict[str, str]) -> List[Listing]:
    listings: List[Listing] = []
    try:
        html = fetch(source["url"])
    except Exception:
        return listings

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article, .item, .listing, .card, li")[:80]
    seen_urls = set()

    for card in cards:
        link = card.select_one("a[href]")
        if not link:
            continue

        url = normalize_url(link.get("href", ""), source["base"])
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        text = clean_text(card.get_text(" ", strip=True))
        title_element = card.select_one("h1, h2, h3, h4")
        title = clean_text(link.get_text(" ", strip=True))
        if not title and title_element:
            title = clean_text(title_element.get_text(" ", strip=True))
        if not title:
            title = text[:120]

        price = parse_price(text)
        parcela = parse_parcela(text)

        location = ""
        location_element = card.select_one('[class*="location"], [class*="district"], address, .item-detail-char, .text-muted')
        if location_element:
            location = clean_text(location_element.get_text(" ", strip=True))
        if not location:
            match = re.search(
                r"(Oviedo|Siero|Noreña|Norena|Llanera|Las Regueras|Ribera de Arriba|Mieres|Langreo|Morcín|Morcin|Sariego|Gijón|Gijon|Avilés|Aviles|Piloña|Pilona)",
                text,
                re.I,
            )
            if match:
                location = match.group(1)

        blob = f"{title} {text} {location}".lower()
        if "asturias" not in blob and not location:
            continue
        if contains_bad_keywords(blob) and not contains_good_keywords(blob):
            continue
        if not contains_good_keywords(blob):
            continue
        if price is None or price > PRECIO_MAXIMO:
            continue
        if parcela is None or parcela < PARCELA_MINIMA:
            continue

        lat, lon = geocode_location(location or title)
        minutes = estimate_drive_minutes(lat, lon)
        if minutes is None or minutes > MAX_MINUTOS_OVIEDO:
            continue

        maps = google_maps_url(lat, lon, f"{location} Asturias")
        listings.append(
            Listing(
                source=source["name"],
                url=url,
                title=title,
                location_text=location or "Asturias",
                price=price,
                parcela_m2=parcela,
                lat=lat,
                lon=lon,
                minutes_to_oviedo=minutes,
                maps_url=maps,
                summary=text[:500],
                seen_at=now_iso(),
            )
        )
        time.sleep(1)

    return listings


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


def build_new_message(listing: Listing) -> str:
    return (
        f"🏡 <b>NUEVO ANUNCIO</b>\n\n"
        f"<b>{escape(listing.title)}</b>\n"
        f"💶 Precio: <b>{fmt_eur(listing.price)}</b>\n"
        f"📐 Parcela: <b>{listing.parcela_m2} m²</b>\n"
        f"📍 Zona: {escape(listing.location_text)}\n"
        f"🚗 Tiempo a {OVIEDO_REF_LABEL}: <b>{listing.minutes_to_oviedo} min</b>\n"
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
        f"📐 Parcela: <b>{listing.parcela_m2} m²</b>\n"
        f"📍 Zona: {escape(listing.location_text)}\n"
        f"🚗 Tiempo a {OVIEDO_REF_LABEL}: <b>{listing.minutes_to_oviedo} min</b>\n"
        f"🗺 <a href=\"{listing.maps_url}\">Ver en Google Maps</a>\n"
        f"🌐 Fuente: {escape(listing.source)}\n"
        f"🔗 <a href=\"{listing.url}\">Ver anuncio</a>"
    )


def dedupe(listings: List[Listing]) -> List[Listing]:
    best: Dict[str, Listing] = {}
    for listing in listings:
        key = listing.url.split("?")[0].rstrip("/")
        if key not in best:
            best[key] = listing
    return list(best.values())


def run() -> None:
    found: List[Listing] = []

    for source in SEARCH_SOURCES:
        print(f"Buscando en {source['name']}...")
        found.extend(scrape_generic_cards(source))

    found = dedupe(found)
    found.sort(key=lambda item: (item.price or 999999999, item.minutes_to_oviedo or 999))

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
    print(f"Anuncios válidos: {len(found)} | avisos enviados: {sent}")


if __name__ == "__main__":
    run()
