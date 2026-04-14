import os
import time
import json
import math
import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ================= CONFIG =================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SEEN_FILE = "seen.json"

OVIEDO_LAT = 43.3619
OVIEDO_LON = -5.8494
MAX_KM = 50

KEYWORDS = ["casa", "terreno", "finca", "parcela", "chalet"]


# ================= TELEGRAM =================
def enviar(msg):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg}
    )


# ================= VISTOS =================
def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    return set(json.load(open(SEEN_FILE)))


def save_seen(s):
    json.dump(list(s), open(SEEN_FILE, "w"))


# ================= DISTANCIA =================
def distancia_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


# ================= GEO =================
def geocode(direccion):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={direccion}&format=json"
        r = requests.get(url, headers={"User-Agent": "bot"})
        data = r.json()

        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except:
        pass

    return None, None


# ================= SELENIUM =================
def navegador():
    opt = Options()
    opt.add_argument("--headless")
    opt.add_argument("--no-sandbox")
    opt.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=opt)
    return driver


# ================= SCRAPER =================
def scrap_selenium(url, fuente):
    driver = navegador()
    driver.get(url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    resultados = []

    for a in soup.find_all("a", href=True):
        txt = a.get_text(" ", strip=True)

        if len(txt) < 20:
            continue

        if not any(k in txt.lower() for k in KEYWORDS):
            continue

        link = a["href"]
        if link.startswith("/"):
            link = url.split(".com")[0] + ".com" + link

        resultados.append({
            "titulo": txt,
            "link": link,
            "fuente": fuente
        })

    return resultados


# ================= FILTRO GEO =================
def filtrar_geo(items):
    buenos = []

    for i in items:
        lat, lon = geocode(i["titulo"])

        if not lat:
            continue

        d = distancia_km(OVIEDO_LAT, OVIEDO_LON, lat, lon)

        if d <= MAX_KM:
            i["distancia"] = round(d, 1)
            buenos.append(i)

    return buenos


# ================= MAIN =================
def main():
    enviar("🚀 BOT NIVEL DIOS (GEO + SELENIUM)")

    vistos = load_seen()

    resultados = []
    resultados += scrap_selenium("https://www.idealista.com/venta-viviendas/asturias/", "Idealista")
    resultados += scrap_selenium("https://www.fotocasa.es/es/comprar/viviendas/asturias/", "Fotocasa")
    resultados += scrap_selenium("https://www.milanuncios.com/venta-de-casas-en-asturias/", "Milanuncios")

    resultados = filtrar_geo(resultados)

    nuevos = []

    for r in resultados:
        if r["link"] in vistos:
            continue

        vistos.add(r["link"])
        nuevos.append(r)

    if not nuevos:
        enviar("⚠️ Sin resultados en radio 50km")
        return

    for item in nuevos[:15]:
        msg = f"""🏠 PROPIEDAD CERCA DE OVIEDO

{item['titulo']}

📍 Distancia: {item['distancia']} km

🌍 {item['fuente']}

{item['link']}"""

        enviar(msg)
        time.sleep(2)

    save_seen(vistos)


if __name__ == "__main__":
    main()