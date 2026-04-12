import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import json
import os
import re
import time

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MAX_PRECIO = 250000
SEEN_FILE = "seen_ads.json"

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
    texto = (item.get("titulo", "") + " " + item.get("link", "")).lower()

    if "asturias" not in texto:
        return False

    if "casa" not in texto:
        return False

    precio = item.get("precio", 0)
    if precio and precio > MAX_PRECIO:
        return False

    return True

# ================= PARCELA =================

def extraer_parcela(texto):
    patrones = [
        r'(\d{2,5})\s?m2',
        r'(\d{2,5})\s?metros',
        r'parcela\s?de\s?(\d{2,5})',
        r'finca\s?de\s?(\d{2,5})'
    ]

    for p in patrones:
        match = re.search(p, texto.lower())
        if match:
            return match.group(1)

    return None

# ================= SCRAPERS =================

def scrap_generico(url):
    resultados = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.find_all("a", href=True):
            texto = a.get_text(" ", strip=True)
            link = a["href"]

            if not texto or len(texto) < 20:
                continue

            if "€" in texto:
                precio_match = re.findall(r'(\d{2,3}\.\d{3})', texto)
                precio = int(precio_match[0].replace(".", "")) if precio_match else 0
            else:
                precio = 0

            resultados.append({
                "titulo": texto[:120],
                "precio": precio,
                "link": link if link.startswith("http") else url
            })
    except:
        pass

    return resultados

# ================= IDEALISTA =================

def idealista(page):
    resultados = []
    url = "https://www.idealista.com/venta-viviendas/asturias/"

    page.goto(url)
    page.wait_for_timeout(5000)

    items = page.locator("article").all()

    for item in items[:20]:
        try:
            titulo = item.locator("a.item-link").inner_text()
            link = item.locator("a.item-link").get_attribute("href")
            precio = item.locator(".item-price").inner_text()

            precio_num = int(precio.replace("€", "").replace(".", "").strip())

            resultados.append({
                "titulo": titulo,
                "precio": precio_num,
                "link": "https://www.idealista.com" + link
            })
        except:
            continue

    return resultados

# ================= BÚSQUEDA INTELIGENTE =================

def buscador(query):
    resultados = []
    url = f"https://www.bing.com/search?q={query}"

    try:
        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")

        for item in soup.select("li.b_algo")[:15]:
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

# ================= PORTALES MASIVOS =================

def portales_extra():
    queries = [
        "casa asturias venta",
        "casa rural asturias barata",
        "vendo casa asturias particular",
        "casa con terreno asturias",
    ]

    resultados = []

    for q in queries:
        resultados += buscador(q)

    # sitios específicos
    sites = [
        "habitaclia.com",
        "yaencontre.com",
        "pisos.com",
        "tucasa.com",
        "indomio.es",
        "globaliza.com"
    ]

    for site in sites:
        resultados += buscador(f"site:{site} casa asturias venta")

    return resultados

# ================= WALLAPOP =================

def wallapop():
    return buscador("site:wallapop.com casa asturias venta")

# ================= MILANUNCIOS =================

def milanuncios():
    return buscador("site:milanuncios.com casa asturias")

# ================= REDES SOCIALES =================

def redes():
    queries = [
        "vendo casa asturias",
        "vendo casa rural asturias",
        "casa asturias particular venta"
    ]

    resultados = []

    for q in queries:
        resultados += buscador(f"{q} site:twitter.com OR site:facebook.com OR site:reddit.com")

    return resultados

# ================= BOE Y SUBASTAS =================

def boe():
    return buscador("site:boe.es subasta vivienda asturias")

def subastas():
    return buscador("subasta vivienda asturias")

# ================= MAIN =================

def main():
    seen = cargar_seen()
    nuevos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()

        fuentes = (
            idealista(page) +
            portales_extra() +
            wallapop() +
            milanuncios() +
            redes() +
            boe() +
            subastas()
        )

        browser.close()

    for item in fuentes:
        if not cumple_criterios(item):
            continue

        key = item["link"]

        if key not in seen:
            texto_total = item.get("titulo", "") + " " + item.get("link", "")
            parcela = extraer_parcela(texto_total)

            item["parcela"] = parcela if parcela else "No especificado"

            seen[key] = item["precio"]
            nuevos.append(item)

    guardar_seen(seen)

    if nuevos:
        for n in nuevos[:20]:
            msg = f"""🏠 NUEVA OPORTUNIDAD

{n['titulo']}

💰 {n['precio']}€
🌳 Parcela: {n.get('parcela')}

🔗 {n['link']}
"""
            enviar(msg)
            time.sleep(1)
    else:
        enviar("❌ Sin novedades")

if __name__ == "__main__":
    main()
