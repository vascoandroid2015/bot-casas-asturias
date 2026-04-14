import html
from typing import Dict, Optional
import requests
from config import CENTER_NAME, SEND_DEBUG_SUMMARY, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN

def send_message(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: raise RuntimeError("Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID")
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}, timeout=20)
    r.raise_for_status()

def build_message(item: Dict, previous_price: Optional[int] = None) -> str:
    title = html.escape(item.get("title", "Sin título")); source = html.escape(item.get("source", "Desconocida")); link = item.get("url", "")
    location = html.escape(item.get("location") or item.get("municipality") or "Ubicación no detectada")
    price = item.get("price"); distance = item.get("distance_km"); description = html.escape((item.get("description") or "").strip()[:450])
    header = "🏡 <b>Nueva oportunidad detectada</b>"
    if previous_price and price and previous_price != price: header = "📉 <b>Bajada de precio detectada</b>" if price < previous_price else "🔁 <b>Cambio de precio detectado</b>"
    lines = [header, "", f"<b>{title}</b>"]
    if price: lines.append(f"💰 <b>Precio:</b> {price:,} €".replace(",", "."))
    if previous_price and previous_price != price: lines.append(f"🕓 <b>Antes:</b> {previous_price:,} €".replace(",", "."))
    lines.append(f"🌍 <b>Fuente:</b> {source}"); lines.append(f"📍 <b>Zona:</b> {location}")
    if distance is not None: lines.append(f"🧭 <b>Distancia a {CENTER_NAME}:</b> {distance} km")
    if description: lines.append(f"📝 <b>Resumen:</b> {description}")
    if link: lines.append(f"🔗 <a href="{html.escape(link)}">Ver anuncio</a>")
    return "
".join(lines)

def build_debug_message(report: Dict) -> str:
    if not SEND_DEBUG_SUMMARY: return ""
    lines = ["🛠️ <b>Resumen debug bot casas v3</b>", ""]
    for portal in report.get("portals", []):
        lines.append(f"• <b>{html.escape(portal['name'])}</b>: extraídos={portal['raw_count']}, válidos={portal['valid_count']}, nuevos/cambios={portal['notify_count']}, errores={portal['error_count']}")
        if portal.get("final_url"): lines.append(f"  ↳ URL final: {html.escape(portal['final_url'][:90])}")
        if portal.get("page_title"): lines.append(f"  ↳ Título: {html.escape(portal['page_title'][:90])}")
    lines += ["", f"Total notificados: <b>{report.get('notified_count', 0)}</b>"]
    return "
".join(lines)
