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

SEEN_FILE = 'data/sent_ads_registry.json'
DEBUG_FILE = 'debug/debug_report.json'
CONTROL_REPORT_FILE = 'data/anuncios_control.md'
DEBUG_HTML_DIR = 'debug/html'
DEBUG_SCREENSHOT_DIR = 'debug/screenshots'

CENTER_NAME = 'Oviedo'
CENTER_COORDS: Tuple[float, float] = (43.3614, -5.8494)
MAX_DISTANCE_KM = 60
STRICT_DISTANCE_FILTER = False
ALLOW_UNKNOWN_LOCATION = True
SEND_DEBUG_SUMMARY = False
HEADLESS = True

SEARCH_TERMS: List[str] = [
    'casa', 'casas', 'chalet', 'chalets', 'finca', 'fincas', 'parcela', 'parcelas',
    'terreno', 'terrenos', 'solar', 'solares', 'casona', 'aldea', 'rural', 'piedra'
]

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
    'soto del barco': (43.5339, -6.0694), 'cudillero': (43.5639, -6.1459)
}

WEB_SOURCES = [
    {'name': 'Idealista', 'enabled': True, 'kind': 'portal', 'url': 'https://www.idealista.com/venta-viviendas/asturias/', 'base_url': 'https://www.idealista.com', 'selectors': ['article.item', 'article[data-adid]', '.items-container article', '.listing-items article']},
    {'name': 'CASASAPO', 'enabled': True, 'kind': 'portal', 'url': 'https://casasapo.es/comprar-viviendas-casas/distrito.asturias/', 'base_url': 'https://casasapo.es', 'selectors': ['article', '.property', '.search-results article', '.listings article']},
    {'name': 'Fincas Asturias', 'enabled': True, 'kind': 'agency', 'url': 'https://www.fincasasasturias.com/search-form-top.php?pagina=1', 'base_url': 'https://www.fincasasasturias.com', 'selectors': ['article', '.property', '.item', '.resultado']},
    {'name': 'CASAL Inmobiliaria', 'enabled': True, 'kind': 'agency', 'url': 'https://www.inmocasal.es', 'base_url': 'https://www.inmocasal.es', 'selectors': ['article', '.property', '.inmueble', '.item']},
    {'name': 'Inmobiliaria Asturias', 'enabled': True, 'kind': 'agency', 'url': 'https://www.inmobiliariaasturias.es', 'base_url': 'https://www.inmobiliariaasturias.es', 'selectors': ['article', '.property', '.listing', '.item']},
    {'name': 'Agencia Asturias', 'enabled': True, 'kind': 'agency', 'url': 'https://agencia-asturias.com/tipo/casa/', 'base_url': 'https://agencia-asturias.com', 'selectors': ['article', '.property', '.entry', '.item']},
    {'name': 'Inmobiliaria María', 'enabled': True, 'kind': 'agency', 'url': 'https://inmobiliariamaria.es', 'base_url': 'https://inmobiliariamaria.es', 'selectors': ['article', '.property', '.inmueble', '.item']},
    {'name': 'Grupo Duarte', 'enabled': True, 'kind': 'agency', 'url': 'https://www.grupoduarte.es/propiedades-venta/', 'base_url': 'https://www.grupoduarte.es', 'selectors': ['article', '.property', '.item', '.listing']},
    {'name': 'REMAX Asturias', 'enabled': True, 'kind': 'portal', 'url': 'https://www.remax.es/buscador-de-inmuebles/venta/casa/asturias/', 'base_url': 'https://www.remax.es', 'selectors': ['article', '.property', '.item', '.listing']},
    {'name': 'Facilitea Casa', 'enabled': True, 'kind': 'portal', 'url': 'https://faciliteacasa.com/viviendas/comprar/Asturias', 'base_url': 'https://faciliteacasa.com', 'selectors': ['article', '.property', '.item', '.listing']},
    {'name': 'e-viviendas', 'enabled': True, 'kind': 'portal', 'url': 'https://www.e-viviendas.es/inmuebles/venta_asturias', 'base_url': 'https://www.e-viviendas.es', 'selectors': ['article', '.property', '.item', '.listing']},
    {'name': 'Arxus Inmobiliaria', 'enabled': True, 'kind': 'agency', 'url': 'https://arxus.es/casas-en-venta-en-asturias/', 'base_url': 'https://arxus.es', 'selectors': ['article', '.property', '.item', '.listing']},
    {'name': 'Hunosa Inmobiliario', 'enabled': True, 'kind': 'institutional', 'url': 'https://hunosainmobiliario.es', 'base_url': 'https://hunosainmobiliario.es', 'selectors': ['article', '.property', '.item', '.listing']},
    {'name': 'Solvia', 'enabled': True, 'kind': 'servicer', 'url': 'https://www.solvia.es/es/comprar/viviendas/asturias', 'base_url': 'https://www.solvia.es', 'selectors': ['article', '.property', '.item', '.listing']},
    {'name': 'Altamira', 'enabled': True, 'kind': 'servicer', 'url': 'https://www.altamirainmuebles.com/venta-viviendas/asturias', 'base_url': 'https://www.altamirainmuebles.com', 'selectors': ['article', '.property', '.item', '.listing']},
    {'name': 'Green-Acres', 'enabled': True, 'kind': 'portal', 'url': 'https://www.green-acres.es/property-for-sale/asturias-province', 'base_url': 'https://www.green-acres.es', 'selectors': ['article', '.property', '.item', '.listing']},
    {'name': 'Properstar', 'enabled': True, 'kind': 'portal', 'url': 'https://www.properstar.com/spain/asturias/buy', 'base_url': 'https://www.properstar.com', 'selectors': ['article', '.property', '.listing', "[data-testid='property-card']"]},
    {'name': 'Engel & Völkers Asturias', 'enabled': True, 'kind': 'agency', 'url': 'https://www.engelvoelkers.com/es/en/properties/res/sale/real-estate/asturias', 'base_url': 'https://www.engelvoelkers.com', 'selectors': ['article', '.property', '.listing', "[data-testid='property-card']"]},
    {'name': 'Sellmi', 'enabled': True, 'kind': 'agency', 'url': 'https://www.sellmi.es/inmuebles-venta/', 'base_url': 'https://www.sellmi.es', 'selectors': ['article', '.property', '.listing', '.item']},
    {'name': 'Asturias Property', 'enabled': True, 'kind': 'portal', 'url': 'https://asturiasproperty.com', 'base_url': 'https://asturiasproperty.com', 'selectors': ['article', '.property', '.listing', '.item']},
    {'name': 'Indomio', 'enabled': True, 'kind': 'portal', 'url': 'https://www.indomio.es/en/venta-casas/asturias-provincia/', 'base_url': 'https://www.indomio.es', 'selectors': ['article', '.property', '.listing', '.item']},
    {'name': 'Fotocasa', 'enabled': False, 'kind': 'portal', 'url': 'https://www.fotocasa.es/es/comprar/viviendas/asturias-provincia/todas-las-zonas/l', 'base_url': 'https://www.fotocasa.es', 'selectors': ['article', 'div.re-CardPackPremium', 'div.re-CardPack', "[class*='CardPack']"]},
    {'name': 'Milanuncios', 'enabled': False, 'kind': 'classifieds', 'url': 'https://www.milanuncios.com/venta-de-casas-en-asturias/', 'base_url': 'https://www.milanuncios.com', 'selectors': ['div.ma-AdCard', 'article', "[data-testid='ad-card']"]},
]

SOCIAL_SOURCES = [
    {'name': 'Telegram channels', 'enabled': False, 'kind': 'social', 'note': 'Preparado para futuras integraciones'},
    {'name': 'Facebook groups', 'enabled': False, 'kind': 'social', 'note': 'Usar solo para descubrimiento o ingesta manual'},
    {'name': 'Facebook Marketplace', 'enabled': False, 'kind': 'social', 'note': 'Opcional y sensible a bloqueos'},
    {'name': 'Instagram discovery', 'enabled': False, 'kind': 'social', 'note': 'Mejor como descubrimiento de agencias'},
]
