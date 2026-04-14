import os
import re
import json
import time
import random
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MIN_PRECIO = 5000
MAX_PRECIO = 250000
SEEN_FILE = "seen_ads.json"

def cargar_vistos():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def guardar_vistos(vistos):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(vistos), f, ensure_ascii=False)

def enviar(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ TELEGRAM no configurado")
        return
    try:
        requests.post(   # Necesitas importar requests abajo
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
    match = re.search(r'\b(\d{4,6})\b', texto)
    if match:
        num = int(match.group(1))
        if MIN_PRECIO <= num <= MAX_PRECIO:
            return num
    return None

def extraer_parcela(texto):
    texto = texto.lower()
    patrones = [r'(\d{2,5})\s?m2?', r'parcela\s?de?\s?(\d{2,5})', r'finca\s?de?\s?(\d{2,5})', r'(\d{3,5})\s*m²']
    for p in patrones:
        m = re.search(p, texto)
        if m:
            return m.group(1) + " m²"
    return "No especificado"

# ==================== SCRAPING CON PLAYWRIGHT (anti-bloqueo) ====================
def milanuncios_scraper():
    resultados = []
    vistos = cargar_vistos()
    pagina = 1

    print("🚀 Iniciando scraping con Playwright (anti-403)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        while True:
            url = f"https://www.milanuncios.com/venta-de-casas-en-asturias/?p={pagina}"
            try:
                print(f"📄 Cargando página {pagina} con Playwright...")
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                time.sleep(random.uniform(4, 7))

                # Scroll para cargar contenido dinámico
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                items = soup.select("article")

                if not items or len(items) < 5:
                    print(f"   Fin de anuncios en página {pagina}")
                    break

                print(f"   → {len(items)} anuncios encontrados")

                nuevos = 0
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
                        "titulo": texto[:280],
                        "precio": precio,
                        "link": link,
                        "fuente": "Milanuncios"
                    })
                    vistos.add(link)
                    nuevos += 1

                guardar_vistos(vistos)
                print(f"   → {nuevos} nuevos anuncios válidos añadidos")

                if nuevos == 0 and pagina > 8:
                    break

                pagina += 1
                time.sleep(random.uniform(5, 8))

            except Exception as e:
                print(f"❌ Error página {pagina}: {e}")
                break

        browser.close()
    return resultados

# ==================== MAIN ====================
def main():
    print("="*65)
    print("🤖 BOT CASAS ASTURIAS - Versión anti-403 con Playwright")
    print("="*65)

    todas = milanuncios_scraper()

    print(f"\nTotal nuevos anuncios encontrados: {len(todas)}")

    enviados = 0
    for item in todas:
        msg = f"""🏠 <b>CASA EN ASTURIAS</b> - {item['fuente']}

{item['titulo']}

💰 <b>{item['precio']:,} €</b>
🌳 Parcela: {extraer_parcela(item['titulo'])}

🔗 {item['link']}
"""
        enviar(msg)
        enviados += 1
        time.sleep(1.8)

    if enviados == 0:
        enviar("❌ Hoy no se encontraron casas nuevas (rango 5.000 - 250.000 €).")
        print("❌ No se enviaron anuncios")
    else:
        print(f"✅ Se enviaron {enviados} casas NUEVAS a Telegram")

if __name__ == "__main__":
    main()
