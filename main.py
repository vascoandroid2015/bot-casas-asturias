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
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass


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


def extraer_precio(texto):
    m = re.search(r'(\d+[\.\,]?\d*)\s?€', texto)
    if m:
        return int(m.group(1).replace(".", "").replace(",", ""))
    return 0


# ================= SCRAPER BASE =================
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

    except Exception as e:
        print("Error en", fuente, e)

    return resultados


# ================= PORTALES =================
def idealista():
    return scrap(
        "https://www.idealista.com/venta-viviendas/asturias/",
        "https://www.idealista.com",
        "Idealista"
    )


def fotocasa():
    return scrap(
        "https://www.fotocasa.es/es/comprar/viviendas/asturias-provincia/todas-las-zonas/l",
        "https://www.fotocasa.es",
        "Fotocasa"
    )


def milanuncios():
    return scrap(
        "https://www.milanuncios.com/venta-de-casas-en-asturias/",
        "https://www.milanuncios.com",
        "Milanuncios"
    )


def wallapop():
    return scrap(
        "https://es.wallapop.com/app/search?keywords=casa&latitude=43.36&longitude=-5.84",
        "https://es.wallapop.com",
        "Wallapop"
    )


def yaencontre():
    return scrap(
        "https://www.yaencontre.com/venta/viviendas/asturias",
        "https://www.yaencontre.com",
        "Yaencontre"
    )


def pisos():
    return scrap(
        "https://www.pisos.com/venta/viviendas-asturias/",
        "https://www.pisos.com",
        "Pisos.com"
    )


# ================= GOOGLE EXTRA =================
def google_extra():
    headers = {"User-Agent": "Mozilla/5.0"}
    resultados = []

    query = "casa terreno asturias venta"
    url = f"https://www.google.com/search?q={query}"

    try:
        r = requests.get(url, headers=headers)
        links = re.findall(r'/url\\?q=(https://[^&]+)', r.text)

        for l in links[:10]:
            resultados.append({
                "titulo": "Resultado externo inmobiliario",
                "precio": 0,
                "link": l,
                "fuente": "Google"
            })

    except:
        pass

    return resultados


# ================= MAIN =================
def main():
    enviar("🚀 BOT MULTIPORTAL INMOBILIARIO ACTIVO")

    vistos = cargar_vistos()

    resultados = []
    resultados += idealista()
    resultados += fotocasa()
    resultados += milanuncios()
    resultados += wallapop()
    resultados += yaencontre()
    resultados += pisos()
    resultados += google_extra()

    nuevos = []

    for r in resultados:
        if r["link"] in vistos:
            continue

        vistos.add(r["link"])
        nuevos.append(r)

    if not nuevos:
        enviar("⚠️ Sin resultados nuevos (pero el bot funciona)")
        return

    nuevos.sort(key=lambda x: x["precio"] if x["precio"] else 999999999)

    for item in nuevos[:20]:
        msg = f"""🏠 PROPIEDAD DETECTADA

{item['titulo']}

💰 {item['precio']:,} €

🌍 {item['fuente']}

{item['link']}"""

        enviar(msg)
        time.sleep(2)

    guardar_vistos(vistos)


if __name__ == "__main__":
    main()