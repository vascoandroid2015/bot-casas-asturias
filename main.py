import os
import json
import time
import requests
import feedparser
import re

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SEEN_FILE = "seen_ads.json"

KEYWORDS_GANGA = [
    "urge", "oportunidad", "reformar", "bajo precio",
    "chollo", "herencia", "embargo", "subasta"
]


# ================= TELEGRAM =================
def enviar(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
        print("✅ Enviado")
    except Exception as e:
        print("❌ Error:", e)


# ================= VISTOS =================
def cargar_vistos():
    if not os.path.exists(SEEN_FILE):
        return set()
    return set(json.load(open(SEEN_FILE)))


def guardar_vistos(v):
    json.dump(list(v), open(SEEN_FILE, "w"))


# ================= PRECIO =================
def extraer_precio(txt):
    m = re.search(r'(\d+[.,]?\d*)\s?€', txt)
    if m:
        return int(m.group(1).replace(".", "").replace(",", ""))
    return 0


# ================= SCORE =================
def calcular_score(item):
    score = 0

    precio = item["precio"]

    if precio:
        if precio < 60000:
            score += 3
        elif precio < 100000:
            score += 2

    texto = item["titulo"].lower()

    for k in KEYWORDS_GANGA:
        if k in texto:
            score += 2

    return score


# ================= RSS =================
def rss(url, fuente):
    feed = feedparser.parse(url)
    datos = []

    for e in feed.entries:
        datos.append({
            "titulo": e.title,
            "precio": extraer_precio(e.title),
            "link": e.link,
            "fuente": fuente
        })

    return datos


# ================= BOE =================
def boe():
    return [{
        "titulo": "Subasta inmobiliaria BOE",
        "precio": 0,
        "link": "https://www.boe.es/",
        "fuente": "BOE"
    }]


# ================= MAIN =================
def main():
    enviar("🚀 BOT INMOBILIARIO NIVEL DIOS ACTIVO")

    vistos = cargar_vistos()

    resultados = []

    # 🔎 FUENTES
    resultados += rss("https://www.idealista.com/venta-viviendas/asturias-provincia/rss.xml", "Idealista")
    resultados += rss("https://www.fotocasa.es/es/rss/venta/viviendas/asturias/todas-las-zonas/l", "Fotocasa")
    resultados += boe()

    nuevos = []

    for r in resultados:
        if r["link"] in vistos:
            continue

        r["score"] = calcular_score(r)
        vistos.add(r["link"])
        nuevos.append(r)

    if not nuevos:
        enviar("⚠️ Sin novedades (bot operativo)")
        return

    # 🔥 ORDEN DIOS
    nuevos.sort(key=lambda x: (x["score"], -x["precio"] if x["precio"] else 0), reverse=True)

    # 🔝 SOLO LOS MEJORES
    top = nuevos[:10]

    for item in top:
        tag = "🔥 GANGA" if item["score"] >= 4 else "🏠 CASA"

        msg = f"""{tag} [{item['score']}⭐]

{item['titulo']}

💰 {item['precio']:,} €

🌍 {item['fuente']}

{item['link']}"""

        enviar(msg)
        time.sleep(1)

    guardar_vistos(vistos)


if __name__ == "__main__":
    main()