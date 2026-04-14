import os
import json
import time
import requests
import feedparser
import re
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SEEN_FILE = "seen_ads.json"

KEYWORDS = ["casa", "terreno", "finca", "parcela", "chalet"]


# ================= TELEGRAM =================
def enviar(msg):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg},
        timeout=10
    )


# ================= VISTOS =================
def cargar_vistos():
    if not os.path.exists(SEEN_FILE):
        return set()
    return set(json.load(open(SEEN_FILE)))


def guardar_vistos(v):
    json.dump(list(v), open(SEEN_FILE, "w"))


# ================= FILTRO =================
def es_relevante(texto):
    texto = texto.lower()
    return any(k in texto for k in KEYWORDS)


# ================= PRECIO =================
def extraer_precio(texto):
    m = re.search(r'(\d+[\.\,]?\d*)\s?€', texto)
    if m:
        return int(m.group(1).replace(".", "").replace(",", ""))
    return 0


# ================= IDEALISTA REAL =================
def idealista():
    url = "https://www.idealista.com/venta-viviendas/asturias/"
    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    resultados = []

    anuncios = soup.select("article")

    for a in anuncios:
        titulo = a.get_text(" ", strip=True)

        if not es_relevante(titulo):
            continue

        link_tag = a.find("a", href=True)
        link = "https://www.idealista.com" + link_tag["href"] if link_tag else url

        precio = extraer_precio(titulo)

        resultados.append({
            "titulo": titulo[:200],
            "precio": precio,
            "link": link,
            "fuente": "Idealista"
        })

    return resultados


# ================= RSS =================
def rss():
    feed = feedparser.parse("https://www.idealista.com/venta-viviendas/asturias-provincia/rss.xml")
    datos = []

    for e in feed.entries:
        if not es_relevante(e.title):
            continue

        datos.append({
            "titulo": e.title,
            "precio": extraer_precio(e.title),
            "link": e.link,
            "fuente": "RSS"
        })

    return datos


# ================= MARKETPLACE =================
def marketplace():
    headers = {"User-Agent": "Mozilla/5.0"}
    resultados = []

    query = "site:facebook.com/marketplace asturias casa terreno"
    url = f"https://www.google.com/search?q={query}"

    r = requests.get(url, headers=headers)

    links = re.findall(r'/url\\?q=(https://www.facebook.com/marketplace/[^&]+)', r.text)

    for l in links[:5]:
        resultados.append({
            "titulo": "Posible casa en Marketplace",
            "precio": 0,
            "link": l,
            "fuente": "Facebook"
        })

    return resultados


# ================= MAIN =================
def main():
    enviar("🚀 BOT INMOBILIARIO ACTIVO (RESULTADOS REALES)")

    vistos = cargar_vistos()

    resultados = []
    resultados += idealista()
    resultados += rss()
    resultados += marketplace()

    nuevos = []

    for r in resultados:
        if r["link"] in vistos:
            continue

        vistos.add(r["link"])
        nuevos.append(r)

    if not nuevos:
        enviar("⚠️ Sin anuncios nuevos (pero el bot funciona)")
        return

    nuevos.sort(key=lambda x: x["precio"] if x["precio"] else 999999999)

    for item in nuevos:
        msg = f"""🏠 NUEVA PROPIEDAD

{item['titulo']}

💰 {item['precio']:,} €

🌍 {item['fuente']}

{item['link']}"""

        enviar(msg)
        time.sleep(2)

    guardar_vistos(vistos)


if __name__ == "__main__":
    main()