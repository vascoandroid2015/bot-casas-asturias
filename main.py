import os
import json
import time
import requests
import feedparser
import re
import math

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SEEN_FILE = "seen_ads.json"

# 📍 CENTRO: OVIEDO
OVIEDO_LAT = 43.3619
OVIEDO_LON = -5.8494
RADIO_KM = 50

# 🏘️ ZONAS CERCANAS (aprox 50 km)
ZONAS_VALIDAS = [
    "oviedo", "gijon", "aviles", "siero", "langreo",
    "mieres", "llanera", "noreña", "laviana",
    "carreño", "castrillon", "corvera"
]

KEYWORDS_OBJETIVO = ["casa", "terreno", "finca", "parcela", "chalet"]


# ================= TELEGRAM =================
def enviar(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception as e:
        print("Error Telegram:", e)


# ================= VISTOS =================
def cargar_vistos():
    if not os.path.exists(SEEN_FILE):
        return set()
    return set(json.load(open(SEEN_FILE)))


def guardar_vistos(v):
    json.dump(list(v), open(SEEN_FILE, "w"))


# ================= DISTANCIA =================
def distancia_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


# ================= FILTROS =================
def es_relevante(texto):
    texto = texto.lower()
    return any(k in texto for k in KEYWORDS_OBJETIVO)


def dentro_radio(texto):
    texto = texto.lower()
    return any(z in texto for z in ZONAS_VALIDAS)


# ================= PRECIO =================
def extraer_precio(txt):
    m = re.search(r'(\d+[.,]?\d*)\s?€', txt)
    if m:
        return int(m.group(1).replace(".", "").replace(",", ""))
    return 0


# ================= RSS =================
def rss(url, fuente):
    feed = feedparser.parse(url)
    datos = []

    for e in feed.entries:
        if not es_relevante(e.title):
            continue

        if not dentro_radio(e.title):
            continue

        datos.append({
            "titulo": e.title,
            "precio": extraer_precio(e.title),
            "link": e.link,
            "fuente": fuente
        })

    return datos


# ================= PORTALES =================
def buscar_portales():
    headers = {"User-Agent": "Mozilla/5.0"}
    resultados = []

    urls = [
        "https://www.idealista.com/venta-viviendas/asturias/",
        "https://www.fotocasa.es/es/comprar/viviendas/asturias-provincia/todas-las-zonas/l"
    ]

    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            html = r.text.split("\n")

            for linea in html:
                if not es_relevante(linea):
                    continue

                if not dentro_radio(linea):
                    continue

                resultados.append({
                    "titulo": linea.strip()[:120],
                    "precio": extraer_precio(linea),
                    "link": url,
                    "fuente": "Portal"
                })

        except Exception as e:
            print("Error portal:", e)

    return resultados


# ================= MARKETPLACE =================
def buscar_marketplace():
    headers = {"User-Agent": "Mozilla/5.0"}
    resultados = []

    query = "site:facebook.com/marketplace oviedo gijon aviles casa terreno parcela"
    url = f"https://www.google.com/search?q={query}"

    try:
        r = requests.get(url, headers=headers, timeout=10)
        html = r.text

        links = re.findall(r'/url\?q=(https://www.facebook.com/marketplace/[^&]+)', html)

        for l in links[:10]:
            resultados.append({
                "titulo": "Casa o terreno en Facebook Marketplace (zona Oviedo)",
                "precio": 0,
                "link": l,
                "fuente": "Facebook"
            })

    except Exception as e:
        print("Marketplace error:", e)

    return resultados


# ================= BOE =================
def boe():
    return [{
        "titulo": "Subasta inmobiliaria BOE Asturias",
        "precio": 0,
        "link": "https://www.boe.es/",
        "fuente": "BOE"
    }]


# ================= MAIN =================
def main():
    enviar("📍 BOT INMOBILIARIO CON RADIO 50km OVIEDO ACTIVO")

    vistos = cargar_vistos()
    resultados = []

    resultados += buscar_marketplace()
    resultados += buscar_portales()
    resultados += rss("https://www.idealista.com/venta-viviendas/asturias-provincia/rss.xml", "Idealista")
    resultados += rss("https://www.fotocasa.es/es/rss/venta/viviendas/asturias/todas-las-zonas/l", "Fotocasa")
    resultados += boe()

    nuevos = []

    for r in resultados:
        if r["link"] in vistos:
            continue

        vistos.add(r["link"])
        nuevos.append(r)

    if not nuevos:
        enviar("⚠️ Sin resultados en radio 50km")
        return

    nuevos.sort(key=lambda x: x["precio"] if x["precio"] else 999999999)

    for item in nuevos[:15]:
        msg = f"""📍 RESULTADO (<=50km Oviedo)

{item['titulo']}

💰 {item['precio']:,} €

🌍 {item['fuente']}

{item['link']}"""

        enviar(msg)
        time.sleep(1)

    guardar_vistos(vistos)


if __name__ == "__main__":
    main()