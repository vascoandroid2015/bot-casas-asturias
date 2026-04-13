import os
import re
import json
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import time

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MIN_PRECIO = 5000
MAX_PRECIO = 250000

SEEN_FILE = "seen_ads.json"

def cargar_vistos():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def guardar_vistos(vistos):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(vistos), f, ensure_ascii=False)

def enviar_con_foto(msg, foto_url=None):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ TELEGRAM no configurado")
        return False
    try:
        if foto_url:
            response = requests.get(foto_url, timeout=10)
            if response.status_code == 200:
                files = {'photo': response.content}
                data = {"chat_id": CHAT_ID, "caption": msg, "parse_mode": "HTML"}
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", data=data, files=files)
                return True
        # Si no hay foto o falla, envía solo texto
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
        return True
    except:
        return False

def limpiar_precio(texto):
    match = re.search(r'(\d{1,3}(?:\.\d{3})*)\s*€', texto)
    if match:
        return int(match.group(1).replace('.', ''))
    return None

def extraer_parcela(texto):
    texto = texto.lower()
    patrones = [r'(\d{2,5})\s?m2?', r'parcela\s?de?\s?(\d{2,5})', r'finca\s?de?\s?(\d{2,5})', r'(\d{3,5})\s*m²']
    for p in patrones:
        m = re.search(p, texto)
        if m:
            return m.group(1) + " m²"
    return "No especificado"

# ==================== SCRAPING CON PLAYWRIGHT (versión más resistente) ====================
def scrape_sitio(url_base, fuente, espera=8000):
    resultados = []
    vistos = cargar_vistos()
    pagina = 1
    max_paginas = 30  # seguridad para no scrapear eternamente

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        while pagina <= max_paginas:
            url = f"{url_base}{'?' if '?' not in url_base else '&'}pagina={pagina}"
            try:
                print(f"🔍 {fuente} → Página {pagina}")
                page.goto(url, timeout=90000, wait_until="networkidle")
                page.wait_for_timeout(espera)

                # Scroll para cargar más contenido dinámico
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(3000)

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Selectores actualizados 2026 (más genéricos + fallback)
                items = soup.select("article, div[data-testid*='listing'], div.re-Card, .item, .listing-card")
                if not items:
                    items = soup.find_all("a", href=True)  # fallback muy amplio

                print(f"   Encontrados {len(items)} posibles anuncios")

                nuevos_en_pagina = 0
                for item in items:
                    texto = item.get_text(" ", strip=True)
                    if len(texto) < 30:
                        continue

                    precio = limpiar_precio(texto)
                    if not precio or not (MIN_PRECIO <= precio <= MAX_PRECIO):
                        continue

                    # Extraer link
                    link_tag = item.find("a", href=True)
                    link = link_tag["href"] if link_tag else ""
                    if not link:
                        continue
                    if not link.startswith("http"):
                        link = "https://www." + fuente.lower() + ".com" + link if fuente.lower() in ["idealista", "fotocasa"] else link

                    if link in vistos:
                        continue

                    # Foto (mejorado)
                    foto = None
                    img = item.find("img")
                    if img and img.get("src"):
                        foto = img["src"]
                    elif img and img.get("data-src"):
                        foto = img["data-src"]

                    resultados.append({
                        "titulo": texto[:240],
                        "precio": precio,
                        "link": link,
                        "fuente": fuente,
                        "foto": foto
                    })
                    vistos.add(link)
                    nuevos_en_pagina += 1

                guardar_vistos(vistos)
                print(f"   → {nuevos_en_pagina} nuevos válidos en esta página")

                if nuevos_en_pagina == 0 and pagina > 3:
                    print(f"   Pocas coincidencias → posiblemente fin o bloqueo")
                    break

                pagina += 1
                time.sleep(5)
            except Exception as e:
                print(f"❌ Error {fuente} página {pagina}: {e}")
                break

        browser.close()
    return resultados

# ==================== FUENTES ====================
def milanuncios():
    return scrape_sitio("https://www.milanuncios.com/venta-de-casas-en-asturias/", "Milanuncios", espera=6000)

def idealista():
    return scrape_sitio("https://www.idealista.com/venta-viviendas/asturias/", "Idealista", espera=10000)

def fotocasa():
    return scrape_sitio("https://www.fotocasa.es/es/comprar/viviendas/asturias/todas-las-zonas/l", "Fotocasa", espera=10000)

# ==================== MAIN ====================
def main():
    print("🚀 Iniciando bot mejorado - Buscando casas en Asturias (sin límites)")

    todas = []
    todas.extend(milanuncios())
    todas.extend(idealista())
    todas.extend(fotocasa())

    print(f"\nTotal nuevos anuncios encontrados: {len(todas)}")

    enviados = 0
    for item in todas:
        msg = f"""🏠 <b>CASA EN ASTURIAS</b> - {item['fuente']}

{item['titulo']}

💰 <b>{item['precio']:,} €</b>
🌳 Parcela: {extraer_parcela(item['titulo'])}

🔗 {item['link']}
"""
        if enviar_con_foto(msg, item.get("foto")):
            enviados += 1
            time.sleep(2.2)  # evitar flood

    if enviados == 0:
        enviar_con_foto("❌ Hoy no se encontraron casas nuevas en el rango 5.000-250.000 €.\nPosible bloqueo temporal o cambio en las webs.")
        print("❌ Sin resultados nuevos (revisa logs)")
    else:
        print(f"✅ Enviadas {enviados} casas NUEVAS a Telegram")

if __name__ == "__main__":
    main()
