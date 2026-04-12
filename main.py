import requests
from playwright.sync_api import sync_playwright
import json
import os
import re
import time

# ================= CONFIG =================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MAX_PRECIO = 250000
SEEN_FILE = "seen_ads.json"

ZONAS = [
    "oviedo", "morcín", "riosa", "proaza", "quirós",
    "mieres", "langreo", "san martin", "gijon", "aviles"
]

KEYWORDS_OK = ["casa", "chalet", "finca", "parcela", "terreno"]
KEYWORDS_BAD = ["piso", "apartamento", "habitacion", "estudio"]

KEYWORDS_INVERSOR = [
    "reformar", "ruina", "oportunidad",
    "negociable", "urge", "inversion"
]

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ================= TELEGRAM =================

def enviar(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ================= STORAGE =================

def cargar_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return json.load(f)
    return {}

def guardar_seen(data):
    with open(SEEN_FILE, "w") as f:
        json.dump(data, f)

# ================= FILTRO =================

def cumple_criterios(item):
    texto = (item.get("titulo", "") + item.get("link", "")).lower()

    if not any(k in texto for k in KEYWORDS_OK):
        return False

    if any(k in texto for k in KEYWORDS_BAD):
        return False

    if not any(z in texto for z in ZONAS):
        return False

    precio = item.get("precio", 0)
    if precio and precio > MAX_PRECIO:
        return False

    return True

# ================= INVERSIÓN =================

def es_inversion(item):
    texto = item.get("titulo", "").lower()
    return any(k in texto for k in KEYWORDS_INVERSOR)

# ================= PARCELA =================

def extraer_parcela(texto):
    patrones = [
        r'(\d{2,5})\s?m2',
        r'parcela\s?de\s?(\d{2,5})',
        r'finca\s?de\s?(\d{2,5})'
    ]

    for p in patrones:
        match = re.search(p, texto.lower())
        if match:
            return match.group(1)
    return None

# ================= SCRAPER PLAYWRIGHT =================

def scrap(page, url):
    resultados = []

    try:
        page.goto(url)
        page.wait_for_timeout(6000)

        items = page.locator("article")

        for i in range(min(items.count(), 25)):
            try:
                item = items.nth(i)
                texto = item.inner_text()

                if "€" not in texto:
                    continue

                precio_match = re.findall(r'\d{2,3}\.\d{3}', texto)
                precio = int(precio_match[0].replace(".", "")) if precio_match else 0

                link = item.locator("a").get_attribute("href")

                resultados.append({
                    "titulo": texto[:120],
                    "precio": precio,
                    "link": link if link.startswith("http") else url
                })

            except:
                continue
    except:
        pass

    return resultados

# ================= BUSCADOR (BING) =================

def buscador(query):
    resultados = []
    url = f"https://www.bing.com/search?q={query}"

    try:
        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select("li.b_algo")[:10]:
            try:
                titulo = item.find("h2").get_text()
                link = item.find("a")["href"]

                resultados.append({
                    "titulo": titulo,
                    "precio": 0,
                    "link": link
                })
            except:
                continue
    except:
        pass

    return resultados

# ================= FUENTES =================

def inmobiliarias(page):
    return (
        scrap(page, "https://www.idealista.com/venta-viviendas/asturias/") +
        scrap(page, "https://www.fotocasa.es/es/comprar/viviendas/asturias/todas-las-zonas/l") +
        scrap(page, "https://www.habitaclia.com/viviendas-asturias.htm") +
        scrap(page, "https://www.yaencontre.com/venta/viviendas/asturias") +
        scrap(page, "https://www.pisos.com/venta/viviendas-asturias/")
    )

def buscadores():
    queries = [
        "casa asturias venta oviedo",
        "terreno asturias venta cerca oviedo",
        "finca asturias barata"
    ]

    resultados = []
    for q in queries:
        resultados += buscador(q)

    return resultados

def redes():
    queries = [
        "vendo casa asturias",
        "vendo finca asturias",
        "terreno asturias venta"
    ]

    resultados = []
    for q in queries:
        resultados += buscador(f"{q} site:twitter.com OR site:facebook.com OR site:reddit.com")

    return resultados

def particulares():
    return (
        buscador("site:wallapop.com casa asturias") +
        buscador("site:milanuncios.com casa asturias")
    )

# ================= MAIN =================

def main():
    seen = cargar_seen()
    nuevos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()

        fuentes = (
            inmobiliarias(page) +
            buscadores() +
            redes() +
            particulares()
        )

        browser.close()

    print(f"Total encontrados: {len(fuentes)}")

    for item in fuentes:
        if not cumple_criterios(item):
            continue

        key = item["link"]

        if key not in seen:
            texto = item["titulo"]

            parcela = extraer_parcela(texto)
            inversion = es_inversion(item)

            item["parcela"] = parcela if parcela else "No especificado"
            item["inversion"] = "🔥 OPORTUNIDAD" if inversion else "Normal"

            seen[key] = item["precio"]
            nuevos.append(item)

    guardar_seen(seen)

    if nuevos:
        for n in nuevos[:20]:
            msg = f"""🏠 INMUEBLE DETECTADO

{n['titulo']}

💰 {n['precio']}€
🌳 Parcela: {n['parcela']}
📊 {n['inversion']}

🔗 {n['link']}
"""
            enviar(msg)
            time.sleep(1)
    else:
        enviar("❌ Sin novedades")

if __name__ == "__main__":
    main()
