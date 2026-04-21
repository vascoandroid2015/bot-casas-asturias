import os
from typing import Dict, List, Tuple

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

MIN_PRICE = 0
MAX_PRICE = 99999999
MAX_RESULTS_PER_RUN = 9999
MESSAGE_DELAY_SECONDS = 1.5
MAX_TELEGRAM_RETRIES = 4
TELEGRAM_SAFE_CHARS = 3500

SEEN_FILE = 'seen_ads.json'
DEBUG_FILE = 'debug/debug_report.json'
DEBUG_HTML_DIR = 'debug/html'
DEBUG_SCREENSHOT_DIR = 'debug/screenshots'

CENTER_NAME = 'Oviedo'
CENTER_COORDS: Tuple[float, float] = (43.3614, -5.8494)
MAX_DISTANCE_KM = 60
STRICT_DISTANCE_FILTER = False
ALLOW_UNKNOWN_LOCATION = True
SEND_DEBUG_SUMMARY = True
HEADLESS = True

PRIORITY_TERMS: List[str] = [
    'piedra', 'finca', 'parcela', 'terreno', 'rustica', 'rústica', 'independiente', 'aldea'
]
NEGATIVE_TERMS: List[str] = [
    'alquiler', 'alquilar', 'habitacion', 'habitación', 'traspaso', 'parking',
    'garaje', 'oficina', 'local', 'nave', 'compartir'
]

MUNICIPALITIES: Dict[str, Tuple[float, float]] = {
    'oviedo': (43.3614, -5.8494), 'siero': (43.3929, -5.6634), 'llanera': (43.4619, -5.8507),
    'noreña': (43.3950, -5.7061), 'mieres': (43.2503, -5.7757), 'langreo': (43.2957, -5.6826),
    'laviana': (43.2358, -5.5628), 'aller': (43.1262, -5.6236), 'morcín': (43.2830, -5.8919),
    'ribera de arriba': (43.3081, -5.8750), 'las regueras': (43.4139, -5.9706), 'grado': (43.3888, -6.0685),
    'candamo': (43.4465, -6.0580), 'proaza': (43.2515, -6.0167), 'santo adriano': (43.2981, -5.9724),
    'quirós': (43.1581, -5.9732), 'teverga': (43.1634, -6.1011), 'avilés': (43.5569, -5.9248),
    'castrillón': (43.5493, -5.9938), 'corvera': (43.5292, -5.8690), 'carreño': (43.5454, -5.7898),
    'gijón': (43.5322, -5.6611), 'villaviciosa': (43.4815, -5.4357), 'nava': (43.3580, -5.5073),
    'sariego': (43.4093, -5.5588), 'cabranes': (43.4185, -5.4064), 'piloña': (43.3477, -5.3647),
    'bimenes': (43.3338, -5.5642), 'gozón': (43.6166, -5.7902), 'pravia': (43.4904, -6.1118),
    'soto del barco': (43.5339, -6.0694), 'cudillero': (43.5639, -6.1459), 'salas': (43.4098, -6.2604)
}

WEB_SOURCES = [
    {'name': 'Idealista', 'enabled': True, 'kind': 'portal', 'url': 'https://www.idealista.com/venta-viviendas/asturias/', 'base_url': 'https://www.idealista.com'},
    {'name': 'Fotocasa', 'enabled': True, 'kind': 'portal', 'url': 'https://www.fotocasa.es/es/comprar/viviendas/asturias-provincia/todas-las-zonas/l', 'base_url': 'https://www.fotocasa.es'},
    {'name': 'Milanuncios', 'enabled': True, 'kind': 'classifieds', 'url': 'https://www.milanuncios.com/venta-de-casas-en-asturias/', 'base_url': 'https://www.milanuncios.com'},
    {'name': 'Wallapop', 'enabled': True, 'kind': 'classifieds', 'url': 'https://es.wallapop.com/inmobiliaria/salas', 'base_url': 'https://es.wallapop.com'},
]
