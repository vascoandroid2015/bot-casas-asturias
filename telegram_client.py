import os
import time
import html
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _escape(text: str) -> str:
    return html.escape(str(text or ""), quote=False)


def chunk_text(text: str, limit: int = 3500):
    text = text or ""
    if len(text) <= limit:
        return [text]
    chunks = []
    current = []
    size = 0
    for line in text.split("\n"):
        extra = len(line) + (1 if current else 0)
        if size + extra > limit:
            chunks.append("\n".join(current))
            current = [line]
            size = len(line)
        else:
            current.append(line)
            size += extra
    if current:
        chunks.append("\n".join(current))
    return chunks


def build_message(item: dict) -> str:
    title = _escape(item.get("title", "Sin título"))
    price = _escape(item.get("price", "Precio desconocido"))
    location = _escape(item.get("location", "Ubicación desconocida"))
    source = _escape(item.get("source", "fuente"))
    url = item.get("url", "")
    lines = [
        "🏡 <b>Nueva casa detectada</b>",
        f"<b>{title}</b>",
        f"💶 {price}",
        f"📍 {location}",
        f"🌐 {source}",
    ]
    if url:
        safe_url = _escape(url)
        lines.append(f'🔗 <a href="{safe_url}">Ver anuncio</a>')
    if item.get("maps_url"):
        safe_maps = _escape(item["maps_url"])
        lines.append(f'🗺️ <a href="{safe_maps}">Google Maps</a>')
    return "\n".join(lines)


def build_debug_message(stats: dict) -> str:
    total_found = stats.get("total_found", 0)
    total_new = stats.get("total_new", 0)
    total_sent = stats.get("total_sent", 0)
    lines = [
        "ℹ️ <b>Resumen debug bot casas</b>",
        "",
        f"• Extraídos: {total_found}",
        f"• Nuevos/cambios: {total_new}",
        f"• Notificados: {total_sent}",
    ]
    for source, data in (stats.get("sources") or {}).items():
        lines.append(
            f"• {source}: extraídos={data.get('found', 0)}, válidos={data.get('valid', 0)}, nuevos={data.get('new', 0)}, errores={data.get('errors', 0)}"
        )
    return "\n".join(lines)


def send_message(text: str, parse_mode: str = "HTML", retries: int = 3, pause: float = 1.2):
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en variables de entorno")

    url = f"{API_URL}/sendMessage"
    sent = 0
    for chunk in chunk_text(text):
        payload = {
            "chat_id": CHAT_ID,
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False,
        }
        last_error = None
        for attempt in range(retries + 1):
            try:
                r = requests.post(url, json=payload, timeout=30)
                if r.status_code == 429:
                    data = r.json()
                    retry_after = ((data.get("parameters") or {}).get("retry_after", 3))
                    time.sleep(float(retry_after) + 1)
                    continue
                r.raise_for_status()
                data = r.json()
                if not data.get("ok"):
                    raise RuntimeError(f"Telegram API error: {data}")
                sent += 1
                time.sleep(pause)
                break
            except Exception as e:
                last_error = e
                if attempt >= retries:
                    raise RuntimeError(f"Error enviando a Telegram: {repr(last_error)}")
                time.sleep(2 + attempt)
    return sent
