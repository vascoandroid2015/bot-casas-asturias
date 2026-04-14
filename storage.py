import json, os
from typing import Dict
from config import DEBUG_FILE, SEEN_FILE

def ensure_parent(path: str):
    folder = os.path.dirname(path)
    if folder: os.makedirs(folder, exist_ok=True)

def load_seen() -> Dict:
    if not os.path.exists(SEEN_FILE): return {}
    with open(SEEN_FILE, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except json.JSONDecodeError: return {}

def save_seen(data: Dict):
    ensure_parent(SEEN_FILE)
    with open(SEEN_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

def save_debug(report: Dict):
    ensure_parent(DEBUG_FILE)
    with open(DEBUG_FILE, 'w', encoding='utf-8') as f: json.dump(report, f, ensure_ascii=False, indent=2)
