import requests
from playwright.sync_api import sync_playwright
import json
import os
import re
import time

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MAX_PRECIO = 250000
SEEN_FILE = "seen_ads.json"

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
    texto = (item.get("titulo", "")).lower()

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
        r'parcela\s?de\s?(\d{2,5})',
        r'finca\s?de\s?(\d{2,5})'
    ]

    for p in patrones:
        match = re.search(p, texto.lower())
        if match:
            return match.group(1)

    return None

# ================= IDEALISTA (FIABLE) =================

def idealista(page):
    print("Buscando en Idealista...")
    resultados = []

    url = "https://www.idealista.com/venta-viviendas/asturias/"

    page.goto(url)
    page.wait_for_timeout(6000)

    items = page.locator("article")

    count = items.count()
    print(f"Idealista encontrados: {count}")

    for i in range(min(count, 20)):
        try:
            item = items.nth(i)

            titulo = item.locator("a.item-link").inner_text()
            link = item.locator("a.item-link").get_attribute("href")
            precio_txt = item.locator(".item-price").inner_text()

            precio = int(precio_txt.replace("€", "").replace(".", "").strip())

            resultados.append({
                "titulo": titulo,
                "precio": precio,
                "link": "https://www.idealista.com" + link
            })

        except Exception as e:
            continue

    return resultados

# ================= WALLAPOP (PLAYWRIGHT REAL) =================

def wallapop(page):
    print("Buscando en Wallapop...")
    resultados = []

    url = "https://es.wallapop.com/app/search?keywords=casa&latitude=43.3619&longitude=-5.8494"

    page.goto(url)
    page.wait_for_timeout(6000)

    items = page.locator("a")

    for i in range(min(items.count(), 30)):
        try:
            item = items.nth(i)
            texto = item.inner_text()
            link = item.get_attribute("href")

            if not texto or "€" not in texto:
                continue

            precio = int(re.findall(r'\d+', texto.replace(".", ""))[0])

            resultados.append({
                "titulo": texto[:100],
                "precio": precio,
                "link": "https://es.wallapop.com" + link
            })
        except:
            continue

    return resultados

# ================= MILANUNCIOS =================

def milanuncios(page):
    print("Buscando en Milanuncios...")
    resultados = []

    url = "https://www.milanuncios.com/venta-de-casas-en-asturias/"

    page.goto(url)
    page.wait_for_timeout(6000)

    items = page.locator("article")

    for i in range(min(items.count(), 20)):
        try:
            item = items.nth(i)
            texto = item.inner_text()

            if "€" not in texto:
                continue

            precio = int(re.findall(r'\d{2,3}\.\d{3}', texto)[0].replace(".", ""))

            link = item.locator("a").get_attribute("href")

            resultados.append({
                "titulo": texto[:100],
                "precio": precio,
                "link": link
            })
        except:
            continue

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
            wallapop(page) +
            milanuncios(page)
        )

        browser.close()

    print(f"Total encontrados: {len(fuentes)}")

    for item in fuentes:
        if not cumple_criterios(item):
            continue

        key = item["link"]

        if key not in seen:
            parcela = extraer_parcela(item["titulo"])
            item["parcela"] = parcela if parcela else "No especificado"

            seen[key] = item["precio"]
            nuevos.append(item)

    guardar_seen(seen)

    if nuevos:
        for n in nuevos:
            msg = f"""🏠 NUEVA CASA

{n['titulo']}

💰 {n['precio']}€
🌳 Parcela: {n['parcela']}

🔗 {n['link']}
"""
            enviar(msg)
            time.sleep(1)
    else:
        enviar("❌ Sin novedades")

if __name__ == "__main__":
    main()
