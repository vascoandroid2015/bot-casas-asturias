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


# ================= TELEGRAM =================
def enviar(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ Telegram no configurado")
        return

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=20
        )

        if response.status_code != 200:
            print("❌ Error Telegram:", response.text)
        else:
            print("✅ Enviado a Telegram")

    except Exception as e:
        print("❌ Error Telegram:", e)


# ================= VISTOS =================
def cargar_vistos():
    if not os.path.exists(SEEN_FILE):
        return set()

    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(data)
    except Exception as e:
        print("Error leyendo vistos:", e)

    return set()


def guardar_vistos(vistos):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(list(vistos), f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Error guardando vistos:", e)


# ================= MAIN =================
def main():
    print("🚀 BOT INICIADO")

    enviar("🤖 Bot activo y ejecutándose...")

    vistos = cargar_vistos()

    nuevos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()

        print("🔎 Buscando en Milanuncios...")
        milanuncios = scrap_milanuncios(page)
        print(f"➡️ Milanuncios encontrados: {len(milanuncios)}")

        print("🔎 Buscando en Idealista...")
        idealista = scrap_idealista(page)
        print(f"➡️ Idealista encontrados: {len(idealista)}")

        browser.close()

    print("🔎 Buscando en BOE...")
    boe = scrap_boe()
    print(f"➡️ BOE encontrados: {len(boe)}")

    nuevos += milanuncios + idealista + boe

    # ================= FILTRAR DUPLICADOS =================
    filtrados = []

    for item in nuevos:
        if item["link"] in vistos:
            continue

        vistos.add(item["link"])
        filtrados.append(item)

    print(f"📊 Total nuevos sin duplicados: {len(filtrados)}")

    if not filtrados:
        enviar("⚠️ Bot funcionando pero no encontró anuncios nuevos")
        return

    # ================= ORDENAR =================
    filtrados.sort(key=lambda x: x["precio"] if x["precio"] else 999999999)

    # ================= ENVIAR =================
    enviados = 0

    for item in filtrados:
        ganga = es_ganga(item["precio"], item["titulo"])

        tag = "🔥 GANGA" if ganga else "🏠 CASA"

        mensaje = f"""<b>{tag} - {item['fuente']}</b>

{item['titulo']}

💰 <b>{item['precio']:,} €</b>

🔗 {item['link']}
"""

        enviar(mensaje)
        enviados += 1
        time.sleep(1.5)

    print(f"✅ Total enviados: {enviados}")

    guardar_vistos(vistos)


# ================= RUN =================
if __name__ == "__main__":
    main()