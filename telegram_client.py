import html
from typing import Dict, Optional

import requests

from config import CENTER_NAME, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN


def send_message(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID en variables de entorno")
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=20,
    )
    response.raise_for_status()


def build_message(item: Dict, previous_price: Optional[int] = None) -> str:
    title = html.escape(item.get("title", "Sin título"))
    source = html.escape(item.get("source", "Desconocida"))
    link = item.get("url", "")
    location = html.escape(item.get("location") or item.get("municipality") or "Ubicación no detectada")
    price = item.get("price")
    distance = item.get("distance_km")
    description = html.escape((item.get("description") or "").strip()[:500])

    header = "🏡 <b>Nueva oportunidad detectada</b>"
    if previous_price and price and previous_price != price:
        if price < previous_price:
            header = "📉 <b>Bajada de precio detectada</b>"
        else:
            header = "🔁 <b>Cambio de precio detectado</b>"

    lines = [header, "", f"<b>{title}</b>"]
    if price:
        lines.append(f"💰 <b>Precio:</b> {price:,} €".replace(",", "."))
    if previous_price and previous_price != price:
        lines.append(f"🕓 <b>Antes:</b> {previous_price:,} €".replace(",", "."))
    lines.append(f"🌍 <b>Fuente:</b> {source}")
    lines.append(f"📍 <b>Zona:</b> {location}")
    if distance is not None:
        lines.append(f"🧭 <b>Distancia a {CENTER_NAME}:</b> {distance} km")
    if description:
        lines.append(f"📝 <b>Resumen:</b> {description}")
    if link:
        lines.append(f"🔗 <a href=\"{html.escape(link)}\">Ver anuncio</a>")
    return "\n".join(lines)
