import os
import re
import json
import requests
from bs4 import BeautifulSoup
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
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=20
        )
        if response.status_code == 200:
            print("✅ Mensaje enviado a Telegram")
            return True
        else:
            print(f"❌ Error Telegram: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Excepción al enviar: {e}")
        return False

def limpiar_precio(texto):
    # Busca precios como "95.000 €", "95000 €", etc.
    match = re.search(r'(\d{1,3}(?:\.\d{3})*)\s*€', texto)
    if match:
        return int(match.group(1).replace('.', ''))
    # Fallback: cualquier número entre 4 y 6 dígitos
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

# ==================== SCRAPING COMPLETO ====================
def milanuncios_scraper():
    resultados = []
    vistos = cargar_vistos()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    pagina = 1
    print("🚀 Iniciando scraping completo de Milanuncios...")

    while True:
        url = f"https://www.milanuncios.com/venta-de-casas-en-asturias/?p={pagina}"
        try:
            print(f"📄 Página {pagina} → Solicitando...")
            r = requests.get(url, headers=headers, timeout=40)

            if r.status_code != 200:
                print(f"   Bloqueado o fin (código {r.status_code})")
                break

            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.select("article")

            if not items or len(items) < 5:
                print(f"   No hay más anuncios en página {pagina}. Fin.")
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
            print(f"   → {nuevos} nuevos anuncios válidos en esta página")

            if nuevos == 0 and pagina > 10:
                break

            pagina += 1
            time.sleep(random.uniform(2.8, 5.0))

        except Exception as e:
            print(f"❌ Error página {pagina}: {e}")
            break

    return resultados

# ==================== MAIN ====================
def main():
    print("=" * 60)
    print("🤖 BOT CASAS ASTURIAS - Versión de depuración")
    print("=" * 60)

    todas = milanuncios_scraper()

    print(f"\n=== RESUMEN FINAL ===\nTotal nuevos anuncios encontrados: {len(todas)}")

    enviados = 0
    for item in todas:
        msg = f"""🏠 <b>CASA EN ASTURIAS</b> - {item['fuente']}

{item['titulo']}

💰 <b>{item['precio']:,} €</b>
🌳 Parcela: {extraer_parcela(item['titulo'])}

🔗 {item['link']}
"""
        if enviar(msg):
            enviados += 1
        time.sleep(1.8)

    if enviados == 0:
        enviar("❌ Hoy no se encontraron casas nuevas en el rango 5.000 - 250.000 €.")
        print("❌ No se enviaron anuncios")
    else:
        print(f"✅ Se enviaron {enviados} casas NUEVAS a Telegram")

if __name__ == "__main__":
    main()
