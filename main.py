import os
import re
import json
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import time
import html

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MIN_PRECIO = 5000
MAX_PRECIO = 250000
SEEN_FILE = "seen_ads.json"


# ===================== TELEGRAM =====================
def enviar(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ TELEGRAM no configurado")
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=15
        )
        print("✅ Enviado a Telegram")

    except Exception as e:
        print(f"❌ Error Telegram: {e}")


# ===================== UTILIDADES =====================
def limpiar_precio(texto):
    match = re.search(r'(\d{1,3}(?:\.\d{3})*)\s*€', texto)
    if match:
        return int(match.group(1).replace('.', ''))
    return None


def cargar_vistos():
    if not os.path.exists(SEEN_FILE):
        return set()

    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(data)
            return set()
    except:
        return set()


def guardar_vistos(vistos):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(vistos), f, ensure_ascii=False, indent=2)


# ===================== SCRAPER =====================
def scrap_milanuncios(page, vistos):
    resultados = []

    for pagina in range(1, 6):  # más estable
        url = f"https://www.milanuncios.com/venta-de-casas-en-asturias/?p={pagina}"

        try:
            print(f"📄 Página {pagina}")
            page.goto(url, timeout=60000)

            # Espera real (mejor que sleep)
            page.wait_for_timeout(4000)

            html_content = page.content()
            soup = BeautifulSoup(html_content, "html.parser")

            items = soup.select("article.ma-AdCard")

            print(f"   🔎 Detectados: {len(items)} anuncios")

            for item in items:
                texto = item.get_text(" ", strip=True)

                precio = limpiar_precio(texto)
                if not precio or not (MIN_PRECIO <= precio <= MAX_PRECIO):
                    continue

                link_tag = item.find("a", href=True)
                if not link_tag:
                    continue

                link = link_tag["href"]
                if not link.startswith("http"):
                    link = "https://www.milanuncios.com" + link

                if link in vistos:
                    continue

                titulo = html.escape(texto[:200])

                resultados.append({
                    "titulo": titulo,
                    "precio": precio,
                    "link": link
                })

                vistos.add(link)
                print(f"   ✅ {precio}€")

        except Exception as e:
            print(f"❌ Error página {pagina}: {e}")

        time.sleep(2)

    return resultados


# ===================== MAIN =====================
def main():
    print("🤖 BOT CASAS ASTURIAS - VERSION ESTABLE")

    enviar("🚀 Bot iniciado correctamente")

    vistos = cargar_vistos()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()

        resultados = scrap_milanuncios(page, vistos)

        browser.close()

    print(f"📊 Total nuevos: {len(resultados)}")

    if not resultados:
        enviar("❌ No hay anuncios nuevos.")
    else:
        for item in resultados:
            msg = f"""🏠 <b>CASA EN ASTURIAS</b>

{item['titulo']}

💰 <b>{item['precio']:,} €</b>

🔗 {item['link']}
"""
            enviar(msg)
            time.sleep(1.5)

    guardar_vistos(vistos)


if __name__ == "__main__":
    main()