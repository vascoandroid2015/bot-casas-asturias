import json
import os
from datetime import datetime
from typing import Dict

from config import CONTROL_REPORT_FILE, DEBUG_FILE, SEEN_FILE

def ensure_parent(path: str):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

def load_seen() -> Dict:
    if not os.path.exists(SEEN_FILE):
        return {}
    with open(SEEN_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_seen(data: Dict):
    ensure_parent(SEEN_FILE)
    with open(SEEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_debug(report: Dict):
    ensure_parent(DEBUG_FILE)
    with open(DEBUG_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

def save_control_report(history: Dict):
    ensure_parent(CONTROL_REPORT_FILE)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    rows = []
    for url, item in sorted(history.items(), key=lambda kv: kv[1].get('last_seen_at', ''), reverse=True):
        rows.append(
            f"| {item.get('title','Sin título').replace('|','-')[:120]} | {item.get('source','')} | {item.get('first_sent_at','')} | {item.get('last_seen_at','')} | {item.get('last_notified_at','')} | {item.get('times_seen',0)} | {item.get('times_notified',0)} | {item.get('last_price','')} | {item.get('status','active')} | {url} |"
        )
    md = [
        '# Control de anuncios enviados',
        '',
        f'Generado: {now}',
        '',
        'Este documento registra los anuncios ya enviados a Telegram para evitar duplicados y conservar cambios detectados.',
        '',
        '| Título | Fuente | Primer envío | Última vez visto | Última notificación | Veces visto | Veces notificado | Último precio | Estado | URL |',
        '|---|---|---|---|---|---:|---:|---:|---|---|',
    ]
    md.extend(rows or ['| Sin anuncios |  |  |  |  | 0 | 0 |  |  |  |'])
    Path(CONTROL_REPORT_FILE).write_text('\n'.join(md), encoding='utf-8')
