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
        return
    if foto_url:
        files = {'photo': requests.get(foto_url, stream=True).raw}
        data = {"chat_id": CHAT_ID, "caption": msg, "parse_mode": "HTML"}
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", data=data, files=files)
    else:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def limpiar_precio(texto):
    match = re.search(r'(\d{1,3}(?:\.\d{3})*)\s*€', texto)
    if match:
        return int(match.group(1).replace('.', ''))
    return None

def extraer_parcela(texto):
    texto = texto.lower()
    patrones = [r'(\d{2,5})\s?m2?', r'parcela\s?de?\s?(\d{2,5})', r'finca\s?de?\s?(\d{2,5})']
    for p in patrones:
        m = re.search(p, texto)
        if m:
            return m.group(1) + " m²"
    return "No especificado"

# ==================== FUNCIÓN GENÉRICA PARA SCRAPEAR CON PLAYWRIGHT ====================
def scrape_con_playwright(base_url, fuente, select_anuncios, get_link, get_precio_texto, get_foto=None):
    resultados = []
    vistos = cargar_vistos()
    pagina = 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 800})

        while True:
            url = f"{base_url}?pagina={pagina}" if "?" not in base_url else f"{base_url}&pagina={pagina}"
            try:
                print(f"🔍 {fuente} → Página {pagina}")
                page.goto(url, timeout=90000)
                page.wait_for_timeout(7000)  # espera JS y carga dinámica

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                items = soup.select(select_anuncios)

                if not items:
                    print(f"   {fuente} → No hay más anuncios (página {pagina})")
                    break

                print(f"   {fuente} → {len(items)} anuncios encontrados")

                for item in items:
                    texto_completo = item.get_text(" ", strip=True)
                    precio = limpiar_precio(texto_completo)
                    if not precio or not (MIN_PRECIO <= precio <= MAX_PRECIO):
                        continue

                    link = get_link(item)
                    if not link or link in vistos:
                        continue

                    foto_url = get_foto(item) if get_foto else None

                    resultados.append({
                        "titulo": texto_completo[:250],
                        "precio": precio,
                        "link": link,
                        "fuente": fuente,
                        "foto": foto_url
                    })
                    vistos.add(link)

                guardar_vistos(vistos)
                pagina += 1
                time.sleep(4)  # anti-bloqueo
            except Exception as e:
                print(f"❌ Error en {fuente} página {pagina}: {e}")
                break

        browser.close()
    return resultados

# ==================== MILANUNCIOS (rápido con requests + fallback) ====================
def milanuncios_requests():
    # ... (puedes mantener la versión anterior con requests si prefieres velocidad)
    # Por simplicidad aquí uso también Playwright para unificar, pero si quieres la versión requests avísame
    return scrape_con_playwright(
        "https://www.milanuncios.com/venta-de-casas-en-asturias",
        "Milanuncios",
        "article",
        lambda item: "https://www.milanuncios.com" + (item.find("a", href=True)["href"] if item.find("a", href=True) else ""),
        lambda item: item.get_text(" ", strip=True),
        lambda item: None  # Milanuncios suele no mostrar foto en listado fácilmente
    )

# ==================== IDEALISTA ====================
def idealista():
    return scrape_con_playwright(
        "https://www.idealista.com/venta-viviendas/asturias/",
        "Idealista",
        "article.item",
        lambda item: "https://www.idealista.com" + (item.find("a", href=True)["href"] if item.find("a", href=True) else ""),
        lambda item: item.get_text(" ", strip=True),
        lambda item: item.find("img")["src"] if item.find("img") and item.find("img").get("src") else None
    )

# ==================== FOTOCASA ====================
def fotocasa():
    return scrape_con_playwright(
        "https://www.fotocasa.es/es/comprar/viviendas/asturias/todas-las-zonas/l",
        "Fotocasa",
        "div.re-Card",
        lambda item: item.find("a", href=True)["href"] if item.find("a", href=True) else "",
        lambda item: item.get_text(" ", strip=True),
        lambda item: item.find("img")["src"] if item.find("img") and item.find("img").get("src") else None
    )

# ==================== MAIN ====================
def main():
    print("🚀 Iniciando bot completo - Milanuncios + Idealista + Fotocasa (sin límites)")

    todas = []
    todas.extend(milanuncios_requests())
    todas.extend(idealista())
    todas.extend(fotocasa())

    print(f"Total nuevos anuncios encontrados: {len(todas)}")

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
        time.sleep(2.0)  # evita flood en Telegram

    if enviados == 0:
        enviar_con_foto("❌ Hoy no hay casas nuevas en el rango de precio.")
    else:
        print(f"✅ Enviadas {enviados} casas NUEVAS con foto a Telegram")

if __name__ == "__main__":
    main()
