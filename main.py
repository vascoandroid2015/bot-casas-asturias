import os
import re
import json
import time
import requests
from playwright.sync_api import sync_playwright

# ==================== CONFIGURACIÓN ====================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MAX_PRECIO = 250000
MIN_PRECIO = 5000

def enviar(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ TELEGRAM no configurado")
        return
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    )

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
    patrones = [r'(\d{2,5})\s?m2?', r'parcela\s?de?\s?(\d{2,5})', r'finca\s?de?\s?(\d{2,5})']
    for p in patrones:
        m = re.search(p, texto)
        if m:
            return m.group(1) + " m²"
    return "No especificado"

# ==================== STEALTH + HUMAN BEHAVIOR ====================

def stealth_browser():
    p = sync_playwright().start()
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-extensions"
        ]
    )
    context = browser.new_context(
        viewport={"width": 1366, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        locale="es-ES"
    )
    # Extra stealth
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
    """)
    page = context.new_page()
    return p, browser, page

# ==================== SCRAPERS ====================

def idealista(page):
    resultados = []
    url = "https://www.idealista.com/venta-viviendas/asturias/?ordenado-por=precios-asc"
    try:
        print("🔍 Intentando Idealista con stealth...")
        page.goto(url, timeout=90000, wait_until="domcontentloaded")
        time.sleep(8)

        # Scroll para forzar carga de anuncios
        for _ in range(4):
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(2)

        # Selectores más amplios y actuales
        items = page.locator("article.item, article[data-testid], div[class*='item'], div[class*='listing']").all()[:50]
        print(f"   Idealista → {len(items)} elementos detectados")

        for item in items:
            try:
                full_text = item.inner_text()
                if len(full_text) < 30:
                    continue
                link = item.locator("a").first.get_attribute("href")
                if link and not link.startswith("http"):
                    link = "https://www.idealista.com" + link

                precio = limpiar_precio(full_text)
                if precio and MIN_PRECIO <= precio <= MAX_PRECIO:
                    resultados.append({
                        "titulo": full_text[:160].strip(),
                        "precio": precio,
                        "link": link,
                        "fuente": "Idealista"
                    })
            except:
                continue
    except Exception as e:
        print(f"❌ Idealista falló: {e}")
    return resultados

def fotocasa(page):
    resultados = []
    url = "https://www.fotocasa.es/es/comprar/viviendas/asturias-provincia/todas-las-zonas/l?sortType=price&sortOrderDesc=false"
    try:
        print("🔍 Intentando Fotocasa...")
        page.goto(url, timeout=90000)
        time.sleep(10)

        page.evaluate("window.scrollBy(0, 1000)")
        time.sleep(4)

        items = page.locator("article").all()[:50]
        print(f"   Fotocasa → {len(items)} elementos detectados")

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
        print(f"❌ Fotocasa falló: {e}")
    return resultados

def milanuncios(page):
    resultados = []
    url = "https://www.milanuncios.com/venta-de-casas-en-asturias/"
    try:
        print("🔍 Intentando Milanuncios...")
        page.goto(url, timeout=90000)
        time.sleep(7)

        items = page.locator("article").all()[:60]
        print(f"   Milanuncios → {len(items)} elementos detectados")

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
        print(f"❌ Milanuncios falló: {e}")
    return resultados

# ==================== MAIN ====================

def main():
    p, browser, page = stealth_browser()

    print("🚀 Iniciando bot con stealth mejorado...")

    todas = idealista(page) + fotocasa(page) + milanuncios(page)

    page.screenshot(path="debug_casas_asturias.png", full_page=True)
    print("📸 Captura guardada → debug_casas_asturias.png")

    browser.close()
    p.stop()

    print(f"\nTotal anuncios con precio válido: {len(todas)}")

    enviados = 0
    for item in todas[:20]:   # máximo 20 por ejecución
        msg = f"""🏠 <b>CASA EN ASTURIAS</b> - {item['fuente']}

{item['titulo']}

💰 <b>{item['precio']:,} €</b>
🌳 Parcela: {extraer_parcela(item['titulo'])}

🔗 {item['link']}
"""
        enviar(msg)
        enviados += 1
        time.sleep(1)  # evitar flood

    if enviados == 0:
        enviar("❌ No se detectaron casas baratas hoy.\nRevisa la captura debug_casas_asturias.png")
        print("❌ No se enviaron casas")
    else:
        print(f"✅ Se enviaron {enviados} casas a Telegram")

if __name__ == "__main__":
    main()