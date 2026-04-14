import html
import time
from typing import Dict, Optional
import requests
from config import CENTER_NAME, MAX_TELEGRAM_RETRIES, MESSAGE_DELAY_SECONDS, SEND_DEBUG_SUMMARY, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN

def send_message(text: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError('Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID')
    for _ in range(MAX_TELEGRAM_RETRIES):
        r = requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            data={'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': False},
            timeout=25,
        )
        if r.status_code == 429:
            retry_after = 5
            try:
                retry_after = int(r.json().get('parameters', {}).get('retry_after', 5))
            except Exception:
                retry_after = 5
            time.sleep(retry_after + 1)
            continue
        r.raise_for_status()
        time.sleep(MESSAGE_DELAY_SECONDS)
        return
    raise RuntimeError('Telegram rate limit persistente tras varios reintentos')

def build_message(item: Dict, previous_price: Optional[int] = None) -> str:
    title = html.escape(item.get('title', 'Sin título'))
    source = html.escape(item.get('source', 'Desconocida'))
    kind = html.escape(item.get('kind', 'web'))
    link = item.get('url', '')
    location = html.escape(item.get('location') or item.get('municipality') or 'Ubicación no detectada')
    price = item.get('price')
    distance = item.get('distance_km')
    description = html.escape((item.get('description') or '').strip()[:450])
    header = '🏡 <b>Nueva oportunidad detectada</b>'
    if previous_price and price and previous_price != price:
        header = '📉 <b>Bajada de precio detectada</b>' if price < previous_price else '🔁 <b>Cambio de precio detectado</b>'
    lines = [header, '', f'<b>{title}</b>']
    if price: lines.append(f"💰 <b>Precio:</b> {price:,} €".replace(',', '.'))
    if previous_price and previous_price != price: lines.append(f"🕓 <b>Antes:</b> {previous_price:,} €".replace(',', '.'))
    lines.append(f'🌍 <b>Fuente:</b> {source}')
    lines.append(f'🧩 <b>Tipo fuente:</b> {kind}')
    lines.append(f'📍 <b>Zona:</b> {location}')
    if distance is not None: lines.append(f'🧭 <b>Distancia a {CENTER_NAME}:</b> {distance} km')
    if description: lines.append(f'📝 <b>Resumen:</b> {description}')
    if link: lines.append(f'🔗 <a href="{html.escape(link)}">Ver anuncio</a>')
    return '
'.join(lines)

def build_debug_message(report: Dict) -> str:
    if not SEND_DEBUG_SUMMARY: return ''
    lines = ['🛠️ <b>Resumen debug metabuscador v7</b>', '']
    for portal in report.get('sources', []):
        lines.append(f"• <b>{html.escape(portal['name'])}</b>: kind={portal['kind']}, enabled={portal['enabled']}, extraídos={portal['raw_count']}, válidos={portal['valid_count']}, nuevos/cambios={portal['notify_count']}, errores={portal['error_count']}")
        if portal.get('final_url'): lines.append(f"  ↳ URL final: {html.escape(portal['final_url'][:120])}")
        if portal.get('page_title'): lines.append(f"  ↳ Título: {html.escape(portal['page_title'][:120])}")
        if portal.get('block_signals'): lines.append(f"  ↳ Bloqueos: {html.escape(', '.join(portal['block_signals'][:5]))}")
    return '
'.join(lines + ['', f"Total notificados: <b>{report.get('notified_count', 0)}</b>"])
