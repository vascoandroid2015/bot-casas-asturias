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
        return
    try:
        if foto_url and foto_url.startswith("http"):
            response = requests.get(foto_url, timeout=15)
            if response.status_code == 200:
                files = {'photo': response.content}
                data = {"chat_id": CHAT_ID, "caption": msg, "parse_mode": "HTML"}
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", data=data, files=files)
                return
        # Enviar solo texto
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})
    except Exception as e:
        print(f"Error enviando mensaje: {e}")

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

# ==================== SCRAPING MEJORADO ====================
def scrape_sitio(url_base, fuente, espera_base=7000):
    resultados = []
    vistos = cargar_vistos()
    pagina = 1
    max_paginas = 25

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}
        )
        page = context.new_page()

        while pagina <= max_paginas:
            url = f"{url_base}{'?' if '?' not in url_base else '&'}pagina={pagina}"
            try:
                print(f"🔍 Scraping {fuente} - Página {pagina} ...")
                page.goto(url, timeout=90000, wait_until="domcontentloaded")
                time.sleep(random.uniform(4, 8))  # delay humano

                # Scroll para forzar carga de contenido dinámico
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(random.uniform(1.5, 3))

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Selectores amplios (actualizados 2026)
                items = soup.select("article, div[data-testid], div.re-Card, .item, .listing, .search-result, [class*='card'], [class*='listing']")
                if len(items) < 5:  # fallback si pocos resultados
                    items = soup.find_all(["article", "div"], class_=re.compile(r"card|item|listing|anuncio", re.I))

                print(f"   → Encontrados {len(items)} posibles elementos en la página")

                nuevos = 0
                for item in items:
                    texto = item.get_text(" ", strip=True)
                    if len(texto) < 40:
                        continue

                    precio = limpiar_precio(texto)
                    if not precio or not (MIN_PRECIO <= precio <= MAX_PRECIO):
                        continue

                    # Extraer enlace
                    link_tag = item.find("a", href=True)
                    if not link_tag:
                        continue
                    link = link_tag["href"]
                    if not link.startswith("http"):
                        link = "https://" + fuente.lower() + ".com" + link if "idealista" in fuente.lower() or "fotocasa" in fuente.lower() else "https://www.milanuncios.com" + link

                    if link in vistos:
                        continue

                    # Foto
                    foto = None
                    img = item.find("img")
                    if img:
                        foto = img.get("src") or img.get("data-src") or img.get("data-lazy")

                    resultados.append({
                        "titulo": texto[:240],
                        "precio": precio,
                        "link": link,
                        "fuente": fuente,
                        "foto": foto
                    })
                    vistos.add(link)
                    nuevos += 1

                guardar_vistos(vistos)
                print(f"   → {nuevos} nuevos anuncios válidos en esta página")

                if nuevos == 0 and pagina >= 5:
                    print(f"   Pocas coincidencias en {fuente}. Posible bloqueo o fin.")
                    break

                pagina += 1
                time.sleep(random.uniform(5, 9))
            except Exception as e:
                print(f"❌ Error en {fuente} página {pagina}: {e}")
                break

        browser.close()
    return resultados

# ==================== FUENTES ====================
def milanuncios():
    return scrape_sitio("https://www.milanuncios.com/venta-de-casas-en-asturias/", "Milanuncios", espera_base=6000)

def idealista():
    return scrape_sitio("https://www.idealista.com/venta-viviendas/asturias/", "Idealista", espera_base=10000)

def fotocasa():
    return scrape_sitio("https://www.fotocasa.es/es/comprar/viviendas/asturias/todas-las-zonas/l", "Fotocasa", espera_base=10000)

# ==================== MAIN ====================
def main():
    print("🚀 Iniciando bot mejorado - Buscando casas baratas en Asturias")

    todas = []
    # Prioridad a Milanuncios (más fiable)
    todas.extend(milanuncios())
    todas.extend(idealista())
    todas.extend(fotocasa())

    print(f"\n=== RESUMEN FINAL ===\nTotal nuevos anuncios encontrados: {len(todas)}")

    enviados = 0
    for item in todas:
        msg = f"""🏠 <b>CASA EN ASTURIAS</b> - {item['fuente']}

{item['titulo']}

💰 <b>{item['precio']:,} €</b>
🌳 Parcela: {extraer_parcela(item['titulo'])}

🔗 {item['link']}
"""
        enviar_con_foto(msg, item.get("foto"))
        enviados += 1
        time.sleep(2.0)

    if enviados == 0:
        enviar_con_foto("❌ Hoy no se encontraron casas nuevas.\n\nRevisa los logs de GitHub Actions para ver detalles.")
        print("❌ Sin resultados. Revisa los logs detallados arriba.")
    else:
        print(f"✅ Enviadas {enviados} casas nuevas a Telegram")

if __name__ == "__main__":
    main()
