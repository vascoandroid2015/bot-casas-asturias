
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

def enviar(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass

def cargar_vistos():
    if not os.path.exists(SEEN_FILE):
        return set()
    return set(json.load(open(SEEN_FILE)))

def guardar_vistos(v):
    json.dump(list(v), open(SEEN_FILE, "w"))

def es_relevante(texto):
    texto = texto.lower()
    return any(k in texto for k in KEYWORDS)

def extraer_precio(texto):
    m = re.search(r'(\d+[\.,]?\d*)\s?€', texto)
    if m:
        return int(m.group(1).replace(".", "").replace(",", ""))
    return 0

def scrap(url, base_url, fuente):
    headers = {"User-Agent": "Mozilla/5.0"}
    resultados = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        enlaces = soup.find_all("a", href=True)

        for e in enlaces:
            texto = e.get_text(" ", strip=True)
            if len(texto) < 20:
                continue
            if not es_relevante(texto):
                continue

            link = e["href"]
            if link.startswith("/"):
                link = base_url + link

            resultados.append({
                "titulo": texto[:200],
                "precio": extraer_precio(texto),
                "link": link,
                "fuente": fuente
            })
    except:
        pass

    return resultados

def main():
    enviar("🚀 BOT INMOBILIARIO ACTIVO")

    vistos = cargar_vistos()

    resultados = []
    resultados += scrap("https://www.idealista.com/venta-viviendas/asturias/", "https://www.idealista.com", "Idealista")
    resultados += scrap("https://www.fotocasa.es/es/comprar/viviendas/asturias-provincia/todas-las-zonas/l", "https://www.fotocasa.es", "Fotocasa")
    resultados += scrap("https://www.milanuncios.com/venta-de-casas-en-asturias/", "https://www.milanuncios.com", "Milanuncios")

    nuevos = []

    for r in resultados:
        if r["link"] in vistos:
            continue
        vistos.add(r["link"])
        nuevos.append(r)

    if not nuevos:
        enviar("⚠️ Sin resultados nuevos")
        return

    for item in nuevos[:15]:
        msg = f"""🏠 PROPIEDAD

{item['titulo']}

💰 {item['precio']:,} €

🌍 {item['fuente']}

{item['link']}"""
        enviar(msg)
        time.sleep(1)

    guardar_vistos(vistos)

if __name__ == "__main__":
    main()
