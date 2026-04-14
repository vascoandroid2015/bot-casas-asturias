import re
import html
from bs4 import BeautifulSoup

MIN_PRECIO = 5000
MAX_PRECIO = 250000

def limpiar_precio(texto):
    match = re.search(r'(\d{1,3}(?:\.\d{3})*)\s*€', texto)
    if match:
        return int(match.group(1).replace('.', ''))
    return None

def scrap_milanuncios(page):
    resultados = []
    for pagina in range(1, 3):
        url = f"https://www.milanuncios.com/venta-de-casas-en-asturias/?p={pagina}"
        page.goto(url, timeout=60000)
        page.wait_for_timeout(4000)

        soup = BeautifulSoup(page.content(), "html.parser")
        links = soup.select("a[href*='/venta-de-casas/']")

        for a in links:
            texto = a.get_text(" ", strip=True)
            precio = limpiar_precio(texto)

            if not precio or not (MIN_PRECIO <= precio <= MAX_PRECIO):
                continue

            link = a.get("href")
            if not link.startswith("http"):
                link = "https://www.milanuncios.com" + link

            resultados.append({
                "titulo": html.escape(texto[:200]),
                "precio": precio,
                "link": link,
                "fuente": "Milanuncios"
            })
    return resultados

def scrap_idealista(page):
    resultados = []
    url = "https://www.idealista.com/venta-viviendas/asturias/"
    page.goto(url, timeout=60000)
    page.wait_for_timeout(5000)

    soup = BeautifulSoup(page.content(), "html.parser")
    items = soup.select("article")

    for item in items:
        texto = item.get_text(" ", strip=True)
        precio = limpiar_precio(texto)
        if not precio or not (MIN_PRECIO <= precio <= MAX_PRECIO):
            continue

        link_tag = item.find("a", href=True)
        if not link_tag:
            continue

        link = link_tag["href"]
        if not link.startswith("http"):
            link = "https://www.idealista.com" + link

        resultados.append({
            "titulo": html.escape(texto[:200]),
            "precio": precio,
            "link": link,
            "fuente": "Idealista"
        })
    return resultados

def scrap_boe():
    import requests
    resultados = []
    url = "https://www.boe.es/diario_boe/xml.php?id=BOE-B-2024"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and "subasta" in r.text.lower():
            resultados.append({
                "titulo": "Subasta BOE detectada",
                "precio": 0,
                "link": url,
                "fuente": "BOE"
            })
    except:
        pass
    return resultados
