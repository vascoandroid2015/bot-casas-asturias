import os
import re
import json
import requests
from playwright.sync_api import sync_playwright

# ==================== CONFIGURACIÓN ====================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MAX_PRECIO = 250000
MIN_PRECIO = 5000

# Archivo para no repetir exactamente el mismo anuncio en la misma ejecución
SEEN_FILE = "seen_ads.json"

def enviar(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ TELEGRAM_TOKEN o CHAT_ID no configurados")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

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
        num = re.sub(r'[^\d]', '', texto.strip())
        return int(num) if num else None
    except:
        return None

def extraer_parcela(texto):
    texto = texto.lower()
    patrones = [r'(\d{2,5})\s?m2?', r'parcela\s?de?\s?(\d{2,5})', r'finca\s?de?\s?(\d{2,5})', r'terreno\s?(\d{2,5})']
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
        print("🔍 Cargando Idealista...")
        page.goto(url, timeout=90000)
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(8000)

        items = page.locator("article.item, article[data-testid='listing']").all()[:40]
        print(f"   Idealista → {len(items)} anuncios detectados")

        for item in items:
            try:
                titulo = item.inner_text()[:160].strip() or "Casa en Asturias"
                link_elem = item.locator("a").first
                link = link_elem.get_attribute("href")
                if link and not link.startswith("http"):
                    link = "https://www.idealista.com" + link

                precio = limpiar_precio(item.inner_text())
                if precio and MIN_PRECIO <= precio <= MAX_PRECIO:
                    resultados.append({
                        "titulo": titulo,
                        "precio": precio,
                        "link": link,
                        "fuente": "Idealista"
                    })
            except:
                continue
    except Exception as e:
        print(f"❌ Error Idealista: {e}")
    return resultados

def fotocasa(page):
    resultados = []
    url = "https://www.fotocasa.es/es/comprar/viviendas/asturias-provincia/todas-las-zonas/l?sortType=price&sortOrderDesc=false"
    try:
        print("🔍 Cargando Fotocasa...")
        page.goto(url, timeout=90000)
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(8000)

        items = page.locator("article").all()[:40]
        print(f"   Fotocasa → {len(items)} anuncios detectados")

        for item in items:
            try:
                texto = item.inner_text()
                link = item.locator("a").first.get_attribute("href")
                if link and not link.startswith("http"):
                    link = "https://www.fotocasa.es" + link

                precio = limpiar_precio(texto)
                if precio and MIN_PRECIO <= precio <= MAX_PRECIO:
                    resultados.append({
                        "titulo": texto[:150].strip(),
                        "precio": precio,
                        "link": link,
                        "fuente": "Fotocasa"
                    })
            except:
                continue
    except Exception as e:
        print(f"❌ Error Fotocasa: {e}")
    return resultados

def milanuncios(page):
    resultados = []
    url = "https://www.milanuncios.com/venta-de-casas-en-asturias/"
    try:
        print("🔍 Cargando Milanuncios...")
        page.goto(url, timeout=90000)
        page.wait_for_load_state("networkidle", timeout=30000)
        page.wait_for_timeout(6000)

        items = page.locator("article").all()[:50]
        print(f"   Milanuncios → {len(items)} anuncios detectados")

        for item in items:
            try:
                texto = item.inner_text()
                link = item.locator("a").first.get_attribute("href")
                if link and not link.startswith("http"):
                    link = "https://www.milanuncios.com" + link

                precio = limpiar_precio(texto)
                if precio and MIN_PRECIO <= precio <= MAX_PRECIO:
                    resultados.append({
                        "titulo": texto[:160].strip(),
                        "precio": precio,
                        "link": link,
                        "fuente": "Milanuncios"
                    })
            except:
                continue
    except Exception as e:
        print(f"❌ Error Milanuncios: {e}")
    return resultados

# ==================== MAIN ====================

def main():
    seen_today = cargar_seen()   # solo para evitar duplicados exactos en la misma ejecución
    enviados = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            viewport={"width": 1366, "height": 1000},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()

        print("🚀 Iniciando bot - Enviando TODAS las casas baratas encontradas...")

        todas = idealista(page) + fotocasa(page) + milanuncios(page)

        page.screenshot(path="debug_casas_asturias.png", full_page=True)
        print("📸 Captura guardada: debug_casas_asturias.png")

        browser.close()

    print(f"Total de casas con precio válido detectadas: {len(todas)}")

    for item in todas:
        key = item["link"]
        if key in seen_today:
            continue

        msg = f"""🏠 <b>CASA EN ASTURIAS - {item['fuente']}</b>

{item['titulo']}

💰 <b>{item['precio']:,} €</b>
🌳 Parcela: {extraer_parcela(item['titulo'])}
🔗 {item['link']}
"""
        enviar(msg)
        seen_today[key] = item['precio']
        enviados += 1

        if enviados >= 15:   # límite diario para no saturar Telegram
            break

    guardar_seen(seen_today)

    if enviados == 0:
        enviar("❌ Hoy no se detectaron casas baratas válidas (revisa la captura debug_casas_asturias.png)")
        print("❌ No se enviaron casas")
    else:
        print(f"✅ Se enviaron {enviados} casas baratas a Telegram")

if __name__ == "__main__":
    main()