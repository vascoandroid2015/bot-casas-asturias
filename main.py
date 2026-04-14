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

print(f"🔧 TELEGRAM_TOKEN existe: {'SÍ' if TELEGRAM_TOKEN else 'NO'}")
print(f"🔧 CHAT_ID existe: {'SÍ' if CHAT_ID else 'NO'}")

def enviar(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ TELEGRAM no configurado")
        return
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=20
        )
        print(f"📤 Telegram respuesta: {r.status_code}")
        if r.status_code == 200:
            print("✅ MENSAJE ENVIADO A TELEGRAM")
        else:
            print(f"❌ Telegram error: {r.text[:300]}")
    except Exception as e:
        print(f"❌ Excepción Telegram: {e}")

# Test inmediato al empezar
enviar("🧪 Test del bot - Iniciando ejecución...")

def cargar_vistos():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def guardar_vistos(vistos):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(vistos), f, ensure_ascii=False)

def limpiar_precio(texto):
    match = re.search(r'(\d{1,3}(?:\.\d{3})*)\s*€', texto)
    if match:
        return int(match.group(1).replace('.', ''))
    return None

# ==================== MILANUNCIOS CON PLAYWRIGHT (máxima depuración) ====================
def milanuncios_scraper():
    resultados = []
    vistos = cargar_vistos()
    pagina = 1

    print("🚀 Iniciando Playwright para Milanuncios...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 800})

        while pagina <= 10:
            url = f"https://www.milanuncios.com/venta-de-casas-en-asturias/?p={pagina}"
            try:
                print(f"📄 Cargando página {pagina}...")
                page.goto(url, timeout=90000)
                time.sleep(8)

                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(5)

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                items = soup.select("article")

                print(f"   Encontrados {len(items)} elementos <article>")

                for item in items:
                    texto = item.get_text(" ", strip=True)
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
                    print(f"   ✅ Nuevo anuncio válido: {precio}€")

                pagina += 1
                time.sleep(6)

            except Exception as e:
                print(f"❌ Error página {pagina}: {e}")
                break

        browser.close()

    print(f"Total anuncios válidos encontrados: {len(resultados)}")
    return resultados

# ==================== MAIN ====================
def main():
    print("🤖 BOT CASAS ASTURIAS - VERSIÓN DEPURACIÓN MÁXIMA")
    
    todas = milanuncios_scraper()

    if len(todas) == 0:
        enviar("❌ No se encontraron casas nuevas hoy.")
        print("❌ No se encontraron anuncios válidos")
    else:
        enviados = 0
        for item in todas:
            msg = f"""🏠 <b>CASA EN ASTURIAS</b> - {item['fuente']}

{item['titulo']}

💰 <b>{item['precio']:,} €</b>

🔗 {item['link']}
"""
            enviar(msg)
            enviados += 1
            time.sleep(2)

        print(f"✅ Se enviaron {enviados} anuncios")

if __name__ == "__main__":
    main()