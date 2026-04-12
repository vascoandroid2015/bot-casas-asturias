import os
import re
import json
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MAX_PRECIO = 250000
CENTRO = "oviedo"
RADIO_KM_APROX = 50
SEEN_FILE = "seen_ads.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

ZONAS_VALIDAS = [
    "oviedo", "siero", "llanera", "noreña", "mieres", "grado",
    "langreo", "laviana", "aller", "ribera de arriba", "las regueras",
    "bimenes", "sariego", "nava", "lena", "aller", "proaza",
    "quiros", "quiros", "teverga", "morcin", "tineo", "salas",
    "aviles", "corvera", "castrillon", "soto del barco", "muros de nalon",
    "cudillero", "gijon", "carreño", "villaviciosa", "langreo", "san martin del rey aurelio"
]

TIPOS_VALIDOS = ["casa", "chalet", "piso", "apartamento", "terreno", "finca", "parcela", "solar", "rústica", "rustica", "casa rural", "casería", "caseria"]


def enviar(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=20)
    except Exception:
        pass


def cargar_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def guardar_seen(data):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalizar_link(link, base=None):
    if not link:
        return ""
    link = link.strip()
    if link.startswith("http://") or link.startswith("https://"):
        return link
    if base:
        return base.rstrip("/") + "/" + link.lstrip("/")
    return link


def extraer_precio(texto):
    if not texto:
        return 0
    t = texto.replace("\xa0", " ")
    patrones = [
        r'(\d{1,3}(?:\.\d{3})+(?:,\d{2})?)\s?€',
        r'€\s?(\d{1,3}(?:\.\d{3})+(?:,\d{2})?)',
        r'(\d{2,9})\s?€'
    ]
    for p in patrones:
        m = re.search(p, t)
        if m:
            raw = m.group(1).replace(".", "").replace(",", ".")
            try:
                return int(float(raw))
            except Exception:
                continue
    return 0


def extraer_parcela(texto):
    if not texto:
        return None
    texto = texto.lower()
    patrones = [
        r'(\d{2,6})\s?(?:m2|m²|metros\s?cuadrad[oa]s?)',
        r'parcela\s?(?:de|:)?\s?(\d{2,6})',
        r'finca\s?(?:de|:)?\s?(\d{2,6})',
        r'terreno\s?(?:de|:)?\s?(\d{2,6})',
        r'solar\s?(?:de|:)?\s?(\d{2,6})'
    ]
    for p in patrones:
        m = re.search(p, texto)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
    return None


def cumple_criterios(item):
    texto = " ".join([
        str(item.get("titulo", "")),
        str(item.get("descripcion", "")),
        str(item.get("link", "")),
        str(item.get("fuente", ""))
    ]).lower()

    if not any(z in texto for z in ZONAS_VALIDAS):
        return False

    if not any(t in texto for t in TIPOS_VALIDOS):
        return False

    precio = item.get("precio", 0) or 0
    if precio > MAX_PRECIO:
        return False

    return True


def limpiar_texto(texto):
    return re.sub(r"\s+", " ", (texto or "")).strip()


def idealista(page):
    resultados = []
    urls = [
        "https://www.idealista.com/venta-viviendas/oviedo-asturias/",
        "https://www.idealista.com/venta-terrenos/oviedo-asturias/",
        "https://www.idealista.com/venta-fincas-rusticas/oviedo-asturias/"
    ]
    for url in urls:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)
            cards = page.locator("article").all()
            for card in cards[:30]:
                try:
                    txt = limpiar_texto(card.inner_text())
                    a = card.locator("a").first
                    link = a.get_attribute("href") if a.count() else ""
                    titulo = limpiar_texto(card.locator("a").first.inner_text()) if a.count() else txt[:140]
                    precio = extraer_precio(txt)
                    if link:
                        resultados.append({
                            "fuente": "idealista",
                            "titulo": titulo,
                            "descripcion": txt,
                            "precio": precio,
                            "link": normalizar_link(link, "https://www.idealista.com"),
                            "parcela_m2": extraer_parcela(txt)
                        })
                except Exception:
                    continue
        except Exception:
            continue
    return resultados


def fotocasa(page):
    resultados = []
    urls = [
        "https://www.fotocasa.es/es/comprar/viviendas/oviedo/todas-las-zonas/l",
        "https://www.fotocasa.es/es/comprar/terrenos/oviedo/todas-las-zonas/l",
        "https://www.fotocasa.es/es/comprar/fincas/oviedo/todas-las-zonas/l"
    ]
    for url in urls:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)
            cards = page.locator("article").all()
            for card in cards[:30]:
                try:
                    txt = limpiar_texto(card.inner_text())
                    link = ""
                    loc = card.locator("a")
                    if loc.count():
                        link = loc.first.get_attribute("href") or ""
                    titulo = txt[:140]
                    precio = extraer_precio(txt)
                    resultados.append({
                        "fuente": "fotocasa",
                        "titulo": titulo,
                        "descripcion": txt,
                        "precio": precio,
                        "link": normalizar_link(link, "https://www.fotocasa.es"),
                        "parcela_m2": extraer_parcela(txt)
                    })
                except Exception:
                    continue
        except Exception:
            continue
    return resultados


def milanuncios():
    resultados = []
    urls = [
        "https://www.milanuncios.com/venta-de-casas-en-oviedo/",
        "https://www.milanuncios.com/venta-de-terrenos-en-oviedo/",
        "https://www.milanuncios.com/venta-de-fincas-rusticas-en-oviedo/"
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")
            for item in soup.select("article, .aditem, .ma-AdCard")[:30]:
                try:
                    txt = limpiar_texto(item.get_text(" "))
                    a = item.find("a")
                    link = normalizar_link(a.get("href") if a else "", "https://www.milanuncios.com")
                    resultados.append({
                        "fuente": "milanuncios",
                        "titulo": txt[:140],
                        "descripcion": txt,
                        "precio": extraer_precio(txt),
                        "link": link,
                        "parcela_m2": extraer_parcela(txt)
                    })
                except Exception:
                    continue
        except Exception:
            continue
    return resultados


def habitaclia():
    resultados = []
    queries = [
        "https://www.habitaclia.com/comprar-vivienda-en-oviedo.htm",
        "https://www.habitaclia.com/comprar-terreno-en-oviedo.htm",
        "https://www.habitaclia.com/comprar-casa-rustica-en-oviedo.htm"
    ]
    for url in queries:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")
            for item in soup.select("article, .advertisement, .listing-item")[:30]:
                try:
                    txt = limpiar_texto(item.get_text(" "))
                    a = item.find("a")
                    link = normalizar_link(a.get("href") if a else "", "https://www.habitaclia.com")
                    resultados.append({
                        "fuente": "habitaclia",
                        "titulo": txt[:140],
                        "descripcion": txt,
                        "precio": extraer_precio(txt),
                        "link": link,
                        "parcela_m2": extraer_parcela(txt)
                    })
                except Exception:
                    continue
        except Exception:
            continue
    return resultados


def yaencontre():
    resultados = []
    urls = [
        "https://www.yaencontre.com/venta/viviendas/oviedo",
        "https://www.yaencontre.com/venta/terrenos/oviedo",
        "https://www.yaencontre.com/venta/fincas/oviedo"
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")
            for item in soup.select("article, .listing, .card")[:30]:
                try:
                    txt = limpiar_texto(item.get_text(" "))
                    a = item.find("a")
                    link = normalizar_link(a.get("href") if a else "", "https://www.yaencontre.com")
                    resultados.append({
                        "fuente": "yaencontre",
                        "titulo": txt[:140],
                        "descripcion": txt,
                        "precio": extraer_precio(txt),
                        "link": link,
                        "parcela_m2": extraer_parcela(txt)
                    })
                except Exception:
                    continue
        except Exception:
            continue
    return resultados


def pisos_com():
    resultados = []
    urls = [
        "https://www.pisos.com/venta/casas-oviedo/",
        "https://www.pisos.com/venta/terrenos-oviedo/",
        "https://www.pisos.com/venta/fincas-rusticas-oviedo/"
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")
            for item in soup.select("article, .ad-box, .listing"): 
                try:
                    txt = limpiar_texto(item.get_text(" "))
                    a = item.find("a")
                    link = normalizar_link(a.get("href") if a else "", "https://www.pisos.com")
                    resultados.append({
                        "fuente": "pisos.com",
                        "titulo": txt[:140],
                        "descripcion": txt,
                        "precio": extraer_precio(txt),
                        "link": link,
                        "parcela_m2": extraer_parcela(txt)
                    })
                except Exception:
                    continue
        except Exception:
            continue
    return resultados


def bing(query):
    resultados = []
    try:
        r = requests.get(f"https://www.bing.com/search?q={requests.utils.quote(query)}", headers=HEADERS, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")
        for item in soup.select("li.b_algo")[:10]:
            try:
                h2 = item.find("h2")
                a = h2.find("a") if h2 else item.find("a")
                if not a:
                    continue
                titulo = limpiar_texto(h2.get_text(" ")) if h2 else limpiar_texto(a.get_text(" "))
                link = a.get("href") or ""
                snippet = limpiar_texto(item.get_text(" "))
                resultados.append({
                    "fuente": "bing",
                    "titulo": titulo,
                    "descripcion": snippet,
                    "precio": extraer_precio(snippet),
                    "link": link,
                    "parcela_m2": extraer_parcela(snippet)
                })
            except Exception:
                continue
    except Exception:
        pass
    return resultados


def wallapop():
    queries = [
        "site:es.wallapop.com casa oviedo venta",
        "site:es.wallapop.com terreno oviedo venta",
        "site:es.wallapop.com finca oviedo venta"
    ]
    resultados = []
    for q in queries:
        resultados.extend(bing(q))
    return resultados


def redes_sociales():
    queries = [
        'site:facebook.com oviedo casa venta',
        'site:facebook.com oviedo terreno venta',
        'site:facebook.com oviedo finca venta',
        'site:x.com oviedo casa venta',
        'site:x.com oviedo terreno venta'
    ]
    resultados = []
    for q in queries:
        resultados.extend(bing(q))
    return resultados


def otros_portales():
    queries = [
        'site:idealista.com oviedo casa venta',
        'site:fotocasa.es oviedo terreno venta',
        'site:milanuncios.com oviedo finca venta',
        'site:habitaclia.com oviedo casa venta',
        'site:yaencontre.com oviedo terreno venta',
        'site:pisos.com oviedo finca venta'
    ]
    resultados = []
    for q in queries:
        resultados.extend(bing(q))
    return resultados


def boe():
    resultados = []
    urls = [
        'https://www.boe.es/buscar/boe.php?dato=subasta+oviedo',
        'https://www.boe.es/buscar/boe.php?dato=subasta+asturias+inmueble'
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")
            for item in soup.select(".resultado-busqueda, .resultado, li")[:20]:
                try:
                    txt = limpiar_texto(item.get_text(" "))
                    a = item.find("a")
                    link = normalizar_link(a.get("href") if a else "", "https://www.boe.es")
                    resultados.append({
                        "fuente": "boe",
                        "titulo": txt[:160],
                        "descripcion": txt,
                        "precio": 0,
                        "link": link,
                        "parcela_m2": extraer_parcela(txt)
                    })
                except Exception:
                    continue
        except Exception:
            continue
    return resultados


def subastas_boe():
    resultados = []
    urls = [
        'https://subastas.boe.es/subastas_ava.php?campo%5B0%5D=SUBASTA.TITULO&dato%5B0%5D=oviedo',
        'https://subastas.boe.es/subastas_ava.php?campo%5B0%5D=SUBASTA.OBJETO&dato%5B0%5D=vivienda',
        'https://subastas.boe.es/subastas_ava.php?campo%5B0%5D=SUBASTA.OBJETO&dato%5B0%5D=terreno',
        'https://subastas.boe.es/subastas_ava.php?campo%5B0%5D=SUBASTA.OBJETO&dato%5B0%5D=finca'
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")
            for item in soup.select("tr, .resultado, .fila")[:30]:
                try:
                    txt = limpiar_texto(item.get_text(" "))
                    a = item.find("a")
                    link = normalizar_link(a.get("href") if a else "", "https://subastas.boe.es")
                    resultados.append({
                        "fuente": "subastas_boe",
                        "titulo": txt[:160],
                        "descripcion": txt,
                        "precio": 0,
                        "link": link,
                        "parcela_m2": extraer_parcela(txt)
                    })
                except Exception:
                    continue
        except Exception:
            continue
    return resultados


def idealista_directo():
    return []


def recolectar():
    fuentes = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        try:
            fuentes.extend(idealista(page))
            fuentes.extend(fotocasa(page))
        finally:
            browser.close()
    fuentes.extend(milanuncios())
    fuentes.extend(habitaclia())
    fuentes.extend(yaencontre())
    fuentes.extend(pisos_com())
    fuentes.extend(wallapop())
    fuentes.extend(redes_sociales())
    fuentes.extend(otros_portales())
    fuentes.extend(boe())
    fuentes.extend(subastas_boe())
    return fuentes


def main():
    seen = cargar_seen()
    nuevos = []
    fuentes = recolectar()
    for item in fuentes:
        try:
            if not cumple_criterios(item):
                continue
            link = item.get("link", "")
            if not link:
                continue
            key = link
            if key in seen:
                continue
            item["parcela"] = item.get("parcela_m2") or "No especificado"
            seen[key] = {
                "precio": item.get("precio", 0),
                "fuente": item.get("fuente", "")
            }
            nuevos.append(item)
        except Exception:
            continue

    guardar_seen(seen)

    if nuevos:
        for n in nuevos[:15]:
            msg = (
                f"🏠 NUEVO INMUEBLE\n\n"
                f"Fuente: {n.get('fuente', 'desconocida')}\n"
                f"{n.get('titulo', '')}\n\n"
                f"💰 {n.get('precio', 0)}€\n"
                f"🌳 Parcela: {n.get('parcela', 'No especificado')}\n"
                f"📍 Radio aproximado: {RADIO_KM_APROX} km desde {CENTRO.title()}\n\n"
                f"🔗 {n.get('link', '')}"
            )
            enviar(msg)
    else:
        enviar("❌ Sin novedades")


if __name__ == "__main__":
    main()
