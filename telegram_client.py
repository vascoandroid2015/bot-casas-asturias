import html
import re
import time
from typing import Dict, List, Optional

import requests

from config import (
    CENTER_NAME,
    MAX_TELEGRAM_RETRIES,
    MESSAGE_DELAY_SECONDS,
    SEND_DEBUG_SUMMARY,
    TELEGRAM_CHAT_ID,
    TELEGRAM_SAFE_CHARS,
    TELEGRAM_TOKEN,
)


def strip_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text or '')


def chunk_text(text: str, limit: int) -> List[str]:
    if len(text) <= limit:
        return [text]

    parts: List[str] = []
    current: List[str] = []
    current_len = 0

    for line in text.split('\n'):
        extra = len(line) + 1
        if current and current_len + extra > limit:
            parts.append('\n'.join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += extra

    if current:
        parts.append('\n'.join(current))

    return parts


def _post_message(text: str, parse_mode: Optional[str] = 'HTML'):
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'disable_web_page_preview': False,
    }
    if parse_mode:
        payload['parse_mode'] = parse_mode
    return requests.post(
        f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
        data=payload,
        timeout=25,
    )


def send_message(text: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError('Faltan TELEGRAM_TOKEN o TELEGRAM_CHAT_ID')

    parts = chunk_text(text, TELEGRAM_SAFE_CHARS)
    for part in parts:
        sent = False
        for _ in range(MAX_TELEGRAM_RETRIES):
            r = _post_message(part, parse_mode='HTML')
            if r.status_code == 429:
                retry_after = 5
                try:
                    retry_after = int(r.json().get('parameters', {}).get('retry_after', 5))
                except Exception:
                    retry_after = 5
                time.sleep(retry_after + 1)
                continue

            if r.status_code == 400:
                plain = strip_html(part)
                r2 = _post_message(plain, parse_mode=None)
                if r2.status_code == 429:
                    retry_after = 5
                    try:
                        retry_after = int(r2.json().get('parameters', {}).get('retry_after', 5))
                    except Exception:
                        retry_after = 5
                    time.sleep(retry_after + 1)
                    continue
                r2.raise_for_status()
                time.sleep(MESSAGE_DELAY_SECONDS)
                sent = True
                break

            r.raise_for_status()
            time.sleep(MESSAGE_DELAY_SECONDS)
            sent = True
            break

        if not sent:
            raise RuntimeError('No se pudo enviar un bloque a Telegram tras varios reintentos')


def build_message(item: Dict, previous_price: Optional[int] = None) -> str:
    title = html.escape(item.get('title', 'Sin título')[:180])
    source = html.escape(item.get('source', 'Desconocida'))
    kind = html.escape(item.get('kind', 'web'))
    link = item.get('url', '')
    location = html.escape((item.get('location') or item.get('municipality') or 'Ubicación no detectada')[:160])
    price = item.get('price')
    distance = item.get('distance_km')
    description = html.escape((item.get('description') or '').strip()[:320])

    header = '🏡 <b>Nueva oportunidad detectada</b>'
    if previous_price and price and previous_price != price:
        header = '📉 <b>Bajada de precio detectada</b>' if price < previous_price else '🔁 <b>Cambio de precio detectado</b>'

    lines = [header, '', f'<b>{title}</b>']
    if price:
        lines.append(f"💰 <b>Precio:</b> {price:,} €".replace(',', '.'))
    if previous_price and previous_price != price:
        lines.append(f"🕓 <b>Antes:</b> {previous_price:,} €".replace(',', '.'))
    lines.append(f'🌍 <b>Fuente:</b> {source}')
    lines.append(f'🧩 <b>Tipo fuente:</b> {kind}')
    lines.append(f'📍 <b>Zona:</b> {location}')
    if distance is not None:
        lines.append(f'🧭 <b>Distancia a {CENTER_NAME}:</b> {distance} km')
    if description:
        lines.append(f'📝 <b>Resumen:</b> {description}')
    if link:
        lines.append(f'🔗 <a href="{html.escape(link)}">Ver anuncio</a>')
    return '\n'.join(lines)


def build_debug_message(report: Dict) -> str:
    if not SEND_DEBUG_SUMMARY:
        return ''

    lines = [
        '🛠️ <b>Resumen debug metabuscador v8</b>',
        f"Total extraídos: <b>{report.get('scraped_count', 0)}</b>",
        f"Total rechazados: <b>{report.get('rejected_count', 0)}</b>",
        f"Total notificados: <b>{report.get('notified_count', 0)}</b>",
        '',
    ]

    for portal in report.get('sources', []):
        line = (
            f"• <b>{html.escape(portal['name'])}</b> | {portal['kind']} | "
            f"on={portal['enabled']} | ext={portal['raw_count']} | val={portal['valid_count']} | new={portal['notify_count']} | err={portal['error_count']}"
        )
        lines.append(line)
        if portal.get('block_signals'):
            lines.append(f"  ↳ bloqueos: {html.escape(', '.join(portal['block_signals'][:3]))}")

    if report.get('reject_reasons'):
        top_reasons = ', '.join(f"{k}:{v}" for k, v in list(report['reject_reasons'].items())[:6])
        lines += ['', f"Rechazos: {html.escape(top_reasons)}"]

    return '\n'.join(lines)
