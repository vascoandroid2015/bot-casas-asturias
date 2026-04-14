import os
import re
import json
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import time
import random

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MIN_PRECIO = 5000
MAX_PRECIO = 250000
SEEN_FILE = "seen_ads.json"

def enviar(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ TELEGRAM no configurado")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=15
        )
        print("✅ Enviado a Telegram")
    except Exception as e:
        print(f"❌ Error Telegram: {e}")

def limpiar_precio(texto):
    match = re.search(r'(\d{1,3}(?:\.\d{3})*)\s*€', texto)
    if match:
        return int(match.group(1).replace('.', ''))
    return None

def main():
    print("🤖 BOT CASAS ASTURIAS - DEPURACIÓN MÁXIMA")
    enviar("🧪 Iniciando ejecución del bot...")

    vistos = set()
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                vistos = set(json.load(f))
        except:
            pass

    resultados = []
    pagina = 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.set_viewport_size({"width": 1366, "height": 768})

        while pagina <= 8:   # limitamos a 8 páginas para prueba rápida
            url = f"https://www.milanuncios.com/venta-de-casas-en-asturias/?p={pagina}"
            try:
                print(f"📄 Cargando página {pagina}...")
                page.goto(url, timeout=90000)
                time.sleep(10)   # espera larga

                # Scroll fuerte
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(3)

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Selectores más amplios posibles
                items = soup.select("article, div.ad, div.listing, .ma-Ad")

                print(f"   Encontrados {len(items)} posibles elementos")

                for item in items:
                    texto = item.get_text(" ", strip=True)
                    if len(texto) < 50:
                        continue

                    precio = limpiar_precio(texto)
                    if not precio or not (MIN_PRECIO <= precio <= MAX_PRECIO):
                        continue

                    link_tag = item.find("a", href=True)
                    if not link_tag:
                        continue
                    link = "https://www.milanuncios.com" + link_tag["href"]

                    if link in vistos:
                        continue

                    resultados.append({
                        "titulo": texto[:250],
                        "precio": precio,
                        "link": link,
                        "fuente": "Milanuncios"
                    })
                    vistos.add(link)
                    print(f"   ✅ Encontrado: {precio}€ - {texto[:80]}...")

            except Exception as e:
                print(f"❌ Error página {pagina}: {e}")

            pagina += 1
            time.sleep(6)

        browser.close()

    print(f"\n=== RESUMEN ===\nTotal anuncios válidos encontrados: {len(resultados)}")

    if len(resultados) == 0:
        enviar("❌ No se encontraron casas nuevas hoy.")
    else:
        enviados = 0
        for item in resultados:
            msg = f"""🏠 <b>CASA EN ASTURIAS</b> - {item['fuente']}

{item['titulo']}

💰 <b>{item['precio']:,} €</b>

🔗 {item['link']}
"""
            enviar(msg)
            enviados += 1
            time.sleep(2)

        print(f"✅ Enviados {enviados} anuncios")

    # Guardar vistos
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(vistos), f, ensure_ascii=False)

if __name__ == "__main__":
    main()