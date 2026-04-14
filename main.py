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

# ==================== FUNCIÓN GENÉRICA (para todos los portales) ====================
def scrape_portal(nombre, base_url, selector_anuncios, get_link_func, espera=7000):
    resultados = []
    vistos = cargar_vistos()
    pagina = 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        while True:
            # Construcción de URL según el portal
            if "milanuncios" in base_url.lower():
                url = f"{base_url}?p={pagina}"
            else:
                url = f"{base_url}{'?' if '?' not in base_url else '&'}pagina={pagina}"

            try:
                print(f"🔍 {nombre} → Página {pagina}")
                page.goto(url, timeout=90000, wait_until="domcontentloaded")
                time.sleep(random.uniform(5, 8))
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(4)

                soup = BeautifulSoup(page.content(), "html.parser")
                items = soup.select(selector_anuncios)

                if not items or len(items) < 4:
                    print(f"   {nombre} → Fin de anuncios (página {pagina})")
                    break

                print(f"   → {len(items)} anuncios encontrados")

                nuevos = 0
                for item in items:
                    texto = item.get_text(" ", strip=True)
                    precio = limpiar_precio(texto)
                    if not precio or not (MIN_PRECIO <= precio <= MAX_PRECIO):
                        continue

                    link = get_link_func(item)
                    if not link or link in vistos:
                        continue

                    resultados.append({
                        "titulo": texto[:280],
                        "precio": precio,
                        "link": link,
                        "fuente": nombre
                    })
                    vistos.add(link)
                    nuevos += 1

                guardar_vistos(vistos)
                print(f"   → {nuevos} nuevos válidos en {nombre}")

                if nuevos == 0 and pagina > 6:
                    break

                pagina += 1
                time.sleep(random.uniform(6, 10))
            except Exception as e:
                print(f"❌ Error en {nombre} página {pagina}: {e}")
                break

        browser.close()
    return resultados

# ==================== TODOS LOS PORTALES ====================
def milanuncios():
    return scrape_portal(
        "Milanuncios",
        "https://www.milanuncios.com/venta-de-casas-en-asturias/",
        "article",
        lambda item: "https://www.milanuncios.com" + (item.find("a", href=True)["href"] if item.find("a", href=True) else "")
    )

def idealista():
    return scrape_portal(
        "Idealista",
        "https://www.idealista.com/venta-viviendas/asturias/",
        "article.item",
        lambda item: "https://www.idealista.com" + (item.find("a", href=True)["href"] if item.find("a", href=True) else "")
    )

def fotocasa():
    return scrape_portal(
        "Fotocasa",
        "https://www.fotocasa.es/es/comprar/viviendas/asturias/todas-las-zonas/l",
        "div.re-Card, article",
        lambda item: item.find("a", href=True)["href"] if item.find("a", href=True) else ""
    )

def habitaclia():
    return scrape_portal(
        "Habitaclia",
        "https://www.habitaclia.com/venta-casas-asturias",
        "div.list-element, article",
        lambda item: "https://www.habitaclia.com" + (item.find("a", href=True)["href"] if item.find("a", href=True) else "")
    )

def pisos_com():
    return scrape_portal(
        "Pisos.com",
        "https://www.pisos.com/venta-pisos/asturias/",
        "div.ad",
        lambda item: "https://www.pisos.com" + (item.find("a", href=True)["href"] if item.find("a", href=True) else "")
    )

def yaencontre():
    return scrape_portal(
        "Yaencontre",
        "https://www.yaencontre.com/venta-viviendas/asturias",
        "div.listing-item, article",
        lambda item: "https://www.yaencontre.com" + (item.find("a", href=True)["href"] if item.find("a", href=True) else "")
    )

def spainhouses():
    return scrape_portal(
        "SpainHouses",
        "https://www.spainhouses.net/es/venta-casas-asturias",
        "div.property-item, article",
        lambda item: "https://www.spainhouses.net" + (item.find("a", href=True)["href"] if item.find("a", href=True) else "")
    )

# ==================== MAIN ====================
def main():
    print("🚀 INICIANDO BOT MULTI-PORTAL (máxima cobertura)")
    print("Portales activos: Milanuncios, Idealista, Fotocasa, Habitaclia, Pisos.com, Yaencontre, SpainHouses")

    todas = []
    todas.extend(milanuncios())
    todas.extend(idealista())
    todas.extend(fotocasa())
    todas.extend(habitaclia())
    todas.extend(pisos_com())
    todas.extend(yaencontre())
    todas.extend(spainhouses())

    print(f"\n=== RESUMEN FINAL ===\nTotal nuevos anuncios encontrados en TODOS los portales: {len(todas)}")

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
        time.sleep(2.0)

    if enviados == 0:
        enviar("❌ Hoy no se encontraron casas nuevas en el rango 5.000 - 250.000 €.")
    else:
        print(f"✅ Enviadas {enviados} casas NUEVAS a Telegram")

if __name__ == "__main__":
    main()