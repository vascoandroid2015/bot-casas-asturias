from typing import List, Dict
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def scrape_example_portal() -> List[Dict]:
    url = "https://example.com"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    title = (soup.title.text or "Example listing").strip() if soup.title else "Example listing"
    return [{
        "id": "example-com-home",
        "title": title,
        "price": "123000 €",
        "location": "Asturias",
        "url": url,
        "source": "Example",
        "maps_url": "https://maps.google.com/?q=Asturias"
    }]
