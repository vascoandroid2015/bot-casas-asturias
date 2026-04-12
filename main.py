import os
import re
import json
import requests
from playwright.sync_api import sync_playwright

# ==================== CONFIGURACIÓN ====================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MAX_PRECIO = 250000
SEEN_FILE = "seen_ads.json"

def enviar(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ TELEGRAM_TOKEN o CHAT_ID no configurados")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    })

def cargar_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_seen(data):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def limpiar_precio(texto):
    if not texto:
        return None
    try:
        num = re.sub(r'[^\d]', '', texto)
        return int(num) if num else None
    except:
        return None

def extraer_parcela(texto):
    texto = texto.lower()
    patrones = [
        r'(\d{2,5})\s?m2?',
        r'parcela\s?de?\s?(\d{2,5})',
        r'finca\s?de?\s?(\d{2,5})',
        r'terreno\s?(\d{2,5})'
    ]
    for p in patrones:
        m = re.search(p, texto)
        if m:
            return m.group(1) + " m²"
    return "No especificado"

# ==================== SCRAPERS ====================

def idealista(page):
    resultados = []
    url = "https://www.idealista.com/venta-viviendas/asturias/?ordenado-por=precios-asc"
    try:
        print("🔍 Buscando en Idealista...")
        page.goto(url, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(6000)

        items = page.locator("article.item").all()[:25]
        print(f"   → {len(items)} anuncios encontrados en Idealista")

        for item in items:
            try:
                titulo = item.locator("a.item-link").inner_text().strip()
                link = "https://www.idealista.com" + item.locator("a.item-link").get_attribute("href")
                precio_txt = item.locator(".item-price, .price-row, span[data-testid='price']").inner_text()
                precio = limpiar_precio(precio_txt)

                if precio and 15000 <= precio <= MAX_PRECIO:
                    resultados.append({
                        "titulo": titulo,
                        "precio": precio,
                        "link": link,
                        "fuente": "Idealista"
                    })
            except:
                continue
    except Exception as e:
        print(f"❌ Error en Idealista: {e}")
    return resultados

def fotocasa(page):
    resultados = []
    url = "https://www.fotocasa.es/es/comprar/viviendas/asturias-provincia/todas-las-zonas/l?sortType=priceAsc"
    try:
        print("🔍 Buscando en Fotocasa...")
        page.goto(url, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(7000)

        items = page.locator("article").all()[:25]
        print(f"   → {len(items)} anuncios encontrados en Fotocasa")

        for item in items:
            try:
                texto_completo = item.inner_text()
                link_elem = item.locator("a").first
                link = link_elem.get_attribute("href")
                if link and not link.startswith("http"):
                    link = "https://www.fotocasa.es" + link

                precio = limpiar_precio(texto_completo)
                if precio and 15000 <= precio <= MAX_PRECIO:
                    resultados.append({
                        "titulo": texto_completo[:130].strip(),
                        "precio": precio,
                        "link": link,
                        "fuente": "Fotocasa"
                    })
            except:
                continue
    except Exception as e:
        print(f"❌ Error en Fotocasa: {e}")
    return resultados

def milanuncios(page):
    resultados = []
    url = "https://www.milanuncios.com/venta-de-casas-en-asturias/"
    try:
        print("🔍 Buscando en Milanuncios...")
        page.goto(url, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(5000)

        items = page.locator("article").all()[:30]
        print(f"   → {len(items)} anuncios encontrados en Milanuncios")

        for item in items:
            try:
                texto = item.inner_text()
                link_elem = item.locator("a").first
                link = link_elem.get_attribute("href")
                if link and not link.startswith("http"):
                    link = "https://www.milanuncios.com" + link

                precio = limpiar_precio(texto)
                if precio and 15000 <= precio <= MAX_PRECIO:
                    resultados.append({
                        "titulo": texto[:140].strip(),
                        "precio": precio,
                        "link": link,
                        "fuente": "Milanuncios"
                    })
            except:
                continue
    except Exception as e:
        print(f"❌ Error en Milanuncios: {e}")
    return resultados

# ==================== MAIN ====================

def main():
    seen = cargar_seen()
    nuevos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("🚀 Iniciando Bot Inmobiliario Asturias...")

        todas = idealista(page) + fotocasa(page) + milanuncios(page)

        # Captura para depuración
        page.screenshot(path="ultima_pagina.png", full_page=True)
        print("📸 Captura de pantalla guardada: ultima_pagina.png")

        browser.close()

    # Filtrar y guardar nuevos
    for item in todas:
        key = item["link"]
        if key in seen:
            continue

        if not (15000 <= item["precio"] <= MAX_PRECIO):
            continue

        parcela = extraer_parcela(item["titulo"])
        item["parcela"] = parcela

        seen[key] = item["precio"]
        nuevos.append(item)

    guardar_seen(seen)

    if nuevos:
        print(f"✅ Encontrados {len(nuevos)} nuevos inmuebles válidos")
        for n in nuevos[:8]:   # límite para evitar spam
            msg = f"""🏠 <b>NUEVA CASA EN ASTURIAS</b>

{n['titulo']}

💰 <b>{n['precio']:,} €</b>
🌳 Parcela: {n.get('parcela')}
📍 Fuente: {n.get('fuente')}

🔗 {n['link']}
"""
            enviar(msg)
            print(f"   → Enviado: {n['titulo'][:60]}...")
    else:
        enviar("❌ No hay nuevas casas interesantes por debajo de 250.000€ hoy.")
        print("❌ Sin novedades hoy.")

if __name__ == "__main__":
    main()
