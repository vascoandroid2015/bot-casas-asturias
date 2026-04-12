
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import json
import os
import re

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
    texto = texto.lower()

    patrones = [
        r'(\d{2,5})\s?m2',
        r'(\d{2,5})\s?metros',
        r'parcela\s?de\s?(\d{2,5})',
        r'finca\s?de\s?(\d{2,5})'
    ]

    for p in patrones:
        match = re.search(p, texto)
        if match:
            return match.group(1)

    return None

# ================= IDEALISTA =================

def idealista(page):
    resultados = []
    url = "https://www.idealista.com/venta-viviendas/asturias/"

    page.goto(url)
    page.wait_for_timeout(5000)

    items = page.locator("article").all()

    for item in items[:15]:
        try:
            titulo = item.locator("a.item-link").inner_text()
            link = item.locator("a.item-link").get_attribute("href")
            precio = item.locator(".item-price").inner_text()

            precio_num = int(precio.replace("€", "").replace(".", "").strip())

            if precio_num <= MAX_PRECIO:
                resultados.append({
                    "titulo": titulo,
                    "precio": precio_num,
                    "link": "https://www.idealista.com" + link
                })
        except:
            continue

    return resultados

# ================= FOTOCASA =================

def fotocasa(page):
    resultados = []
    url = "https://www.fotocasa.es/es/comprar/viviendas/asturias/todas-las-zonas/l"

    page.goto(url)
    page.wait_for_timeout(5000)

    items = page.locator("article").all()

    for item in items[:15]:
        try:
            texto = item.inner_text()
            link = item.locator("a").get_attribute("href")

            if "€" in texto:
                precio = int(re.findall(r'(\d{2,3}\.\d{3})', texto)[0].replace(".", ""))

                if precio <= MAX_PRECIO:
                    resultados.append({
                        "titulo": texto[:100],
                        "precio": precio,
                        "link": link
                    })
        except:
            continue

    return resultados

# ================= MILANUNCIOS =================


def extraer_desde_soup(items, source, base_url):
    resultados = []
    for item in items[:150]:
        try:
            txt = limpiar_texto(item.get_text(" "))
            if len(txt) < 5:
                continue
            a = item.find("a")
            link = normalizar_link(a.get("href") if a else "", base_url)
            resultados.append({
                "fuente": source,
                "titulo": txt[:160],
                "descripcion": txt,
                "precio": extraer_precio(txt),
                "link": link,
                "parcela_m2": extraer_parcela(txt)
            })
        except Exception:
            continue
    return resultados


def milanuncios():
    resultados = []
    url = "https://www.milanuncios.com/venta-de-casas-en-asturias/"

    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    items = soup.select("article")

    for item in items[:15]:
        try:
            texto = item.get_text()
            link = item.find("a")["href"]

            if "€" in texto:
                precio = int(re.findall(r'(\d{2,3}\.\d{3})', texto)[0].replace(".", ""))

                if precio <= MAX_PRECIO:
                    resultados.append({
                        "titulo": texto[:100],
                        "precio": precio,
                        "link": link
                    })
        except:
            continue

    return resultados

# ================= BOE =================

def boe():
    resultados = []
    url = "https://www.boe.es/buscar/boe.php?dato=subasta+asturias"

    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    for item in soup.select(".resultado-busqueda")[:10]:
        try:
            titulo = item.get_text(strip=True)
            link = item.find("a")["href"]

            resultados.append({
                "titulo": titulo,
                "precio": 0,
                "link": "https://www.boe.es" + link
            })
        except:
            continue

    return resultados

# ================= SUBASTAS =================

def subastas():
    resultados = []
    url = "https://subastas.boe.es/subastas_ava.php?campo%5B0%5D=SUBASTA.OBJETO&dato%5B0%5D=vivienda+asturias"

    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    for item in soup.select("tr")[:15]:
        try:
            texto = item.get_text()

            if "vivienda" in texto.lower():
                resultados.append({
                    "titulo": texto[:120],
                    "precio": 0,
                    "link": url
                })
        except:
            continue

    return resultados

# ================= BING =================

def bing(query):
    resultados = []
    url = f"https://www.bing.com/search?q={query}"

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

    return resultados

# ================= WALLAPOP =================

def wallapop():
    return bing("casa asturias venta site:wallapop.com")

# ================= REDES =================

def redes_sociales():
    resultados = []

    queries = [
        "vendo casa asturias",
        "casa asturias venta particular",
        "casa rural asturias venta"
    ]

    for q in queries:
        resultados += bing(f"{q} site:twitter.com OR site:facebook.com")

    return resultados

# ================= OTROS =================

def otros_portales():
    resultados = []

    queries = [
        "site:habitaclia.com casa asturias venta",
        "site:yaencontre.com casa asturias",
        "site:pisos.com asturias casa venta"
    ]

    for q in queries:
        resultados += bing(q)

    return resultados

# ================= MAIN =================

def main():
    seen = cargar_seen()
    nuevos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()

        fuentes = (
            idealista(page) +
            fotocasa(page) +
            milanuncios() +
            boe() +
            subastas() +
            wallapop() +
            redes_sociales() +
            otros_portales()
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
        for n in nuevos[:15]:
            msg = f"""🏠 NUEVO INMUEBLE

{n['titulo']}

💰 {n['precio']}€
🌳 Parcela: {n.get('parcela')}

🔗 {n['link']}
"""
            enviar(msg)
    else:
        enviar("❌ Sin novedades")

if __name__ == "__main__":
    main()
