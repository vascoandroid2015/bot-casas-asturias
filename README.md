# Bot Casas Asturias

Bot de Telegram en Python + Playwright para detectar anuncios de casas, fincas, parcelas y terrenos en Asturias, priorizando inmuebles a un radio aproximado de 50 km desde Oviedo y con precio máximo de 250.000 €.

## Qué hace

- Busca anuncios en Idealista, Milanuncios y Fotocasa.
- Filtra por precio máximo.
- Intenta detectar municipios dentro del radio configurado desde Oviedo.
- Evita duplicados por URL.
- Detecta cambios y bajadas de precio.
- Envía mensajes completos a Telegram.
- Guarda histórico en `seen_ads.json`.

## Estructura

- `main.py`: ejecución principal.
- `scrapers.py`: scrapers Playwright por portal.
- `filters.py`: filtros de texto, precio y distancia.
- `storage.py`: persistencia local JSON.
- `telegram_client.py`: envío y formato del mensaje.
- `config.py`: configuración general.
- `.github/workflows/casas.yml`: ejecución en GitHub Actions.

## Variables necesarias

Configura estos secrets en GitHub:

- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`

## Ejecución local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
python main.py
```

## GitHub Actions

El workflow instala Python, dependencias y Chromium, ejecuta el bot y guarda cambios de `seen_ads.json` en el repo.

## Notas

- Los selectores de scraping pueden cambiar con el tiempo; los portales inmobiliarios cambian su HTML con frecuencia.
- He dejado la configuración preparada para ampliar a más portales y fuentes experimentales como Wallapop o redes sociales, pero desactivadas de serie para no romper la estabilidad de la v1.
