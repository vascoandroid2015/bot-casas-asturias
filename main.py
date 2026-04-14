import os
import json
import time
import requests
from playwright.sync_api import sync_playwright

from scrapers import scrap_milanuncios, scrap_idealista, scrap_boe
from inteligencia import es_ganga

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SEEN_FILE = "seen_ads.json"

def enviar(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Telegram no configurado")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": msg,
                "parse_mode": "HTML"
            },
            timeout=15
        )
    except Exception as e:
        print("Error Telegram:", e)

def cargar_vistos():
    if not os.path.exists(SEEN_FILE):
        return set()
    try:
        with open(SEEN_FILE) as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(data)
    except:
        pass
    return set()

def guardar_vistos(vistos):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(vistos), f, indent=2)

def main():
    enviar("BOT INICIADO")

    vistos = cargar_vistos()
    nuevos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()

        nuevos += scrap_milanuncios(page)
        nuevos += scrap_idealista(page)

        browser.close()

    nuevos += scrap_boe()

    filtrados = []

    for item in nuevos:
        if item["link"] in vistos:
            continue
        vistos.add(item["link"])
        filtrados.append(item)

    if not filtrados:
        enviar("Sin resultados nuevos")
        return

    filtrados.sort(key=lambda x: x["precio"])

    for item in filtrados:
        ganga = es_ganga(item["precio"], item["titulo"])
        tag = "GANGA" if ganga else "CASA"

        msg = f"{tag} - {item['fuente']}\n\n{item['titulo']}\n\nPrecio: {item['precio']:,} EUR\n\n{item['link']}"

        enviar(msg)
        time.sleep(1.5)

    guardar_vistos(vistos)

if __name__ == "__main__":
    main()
