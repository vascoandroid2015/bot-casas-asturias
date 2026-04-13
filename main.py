iimport os
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
            r = requests.get(foto_url, timeout=10)
            if r.status_code == 200:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                    data={"chat_id": CHAT_ID, "caption": msg, "parse_mode": "HTML"},
                    files={"photo": r.content}
                )
                return
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
        )
    except Exception as e:
        print(f"Error al enviar: {e}")

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

# ==================== MILANUNCIOS - Versión mejorada ====================
def milanuncios():
    resultados = []
    vistos = cargar_vistos()
    pagina = 1
    max_paginas = 30

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        while pagina <= max_paginas:
            url = f"https://www.milanuncios.com/venta-de-casas-en-asturias/?p={pagina}"
            try:
                print(f"🔍 Milanuncios - Página {pagina}")
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                time.sleep(random.uniform(5, 8))

                # Scroll para cargar anuncios
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Selectores específicos para Milanuncios 2026
                items = soup.select("article.ma-Ad")
                if not items:
                    items = soup.select("article")  # fallback

                print(f"   → Encontrados {len(items)} anuncios en la página")

                nuevos = 0
                for item in items:
                    texto = item.get_text(" ", strip=True)
                    if len(texto) < 30:
                        continue

                    precio = limpiar_precio(texto)
                    if not precio or not (MIN_PRECIO <= precio <= MAX_PRECIO):
                        continue

                    # Enlace
                    link_tag = item.find("a", href=True)
                    if not link_tag:
                        continue
                    link = "https://www.milanuncios.com" + link_tag["href"]

                    if link in vistos:
                        continue

                    # Foto
                    foto = None
                    img = item.find("img")
                    if img:
                        foto = img.get("src") or img.get("data-src")

                    resultados.append({
                        "titulo": texto[:240],
                        "precio": precio,
                        "link": link,
                        "fuente": "Milanuncios",
                        "foto": foto
                    })
                    vistos.add(link)
                    nuevos += 1

                guardar_vistos(vistos)
                print(f"   → {nuevos} nuevos anuncios válidos añadidos")

                if nuevos == 0 and pagina > 8:
                    print("   Pocas coincidencias → terminando scraping")
                    break

                pagina += 1
                time.sleep(random.uniform(4, 7))
            except Exception as e:
                print(f"❌ Error página {pagina}: {e}")
                break

        browser.close()
    return resultados

# ==================== MAIN ====================
def main():
    print("🚀 Iniciando bot SIMPLIFICADO - Solo Milanuncios (más fiable)")

    todas = milanuncios()

    print(f"\n=== RESUMEN ===\nTotal nuevos anuncios encontrados: {len(todas)}")

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
        enviar_con_foto("❌ Hoy no se encontraron casas nuevas.\n\nRevisa los logs completos en GitHub Actions.")
        print("❌ Sin resultados. Por favor copia aquí los logs detallados.")
    else:
        print(f"✅ Enviadas {enviados} casas nuevas a Telegram")

if __name__ == "__main__":
    main()
