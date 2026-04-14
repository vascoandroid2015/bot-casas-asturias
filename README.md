# Bot Casas Asturias v2

Versión más abierta y depurable del bot inmobiliario con Playwright para Telegram.

## Mejoras respecto a la v1

- Añade `debug/debug_report.json` con conteos por portal y motivos de descarte.
- No aplica el radio de 50 km de forma estricta al principio (`STRICT_DISTANCE_FILTER = False`).
- Permite anuncios con ubicación no detectada (`ALLOW_UNKNOWN_LOCATION = True`).
- Mantiene precio máximo de 250.000 €.
- Detecta anuncios nuevos y cambios de precio.
- Envía resumen debug al Telegram al final de cada ejecución.

## Objetivo de esta versión

Primero comprobar que el bot realmente extrae anuncios válidos de los portales. Después, cuando veamos resultados en el debug, se puede endurecer de nuevo el filtro de distancia.

## Secrets necesarios

- `TELEGRAM_TOKEN`
- `TELEGRAM_CHAT_ID`

## Uso local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
python main.py
```

## Ficheros clave

- `debug/debug_report.json`: resumen por portal, descartes y ejemplos.
- `seen_ads.json`: histórico de anuncios vistos y último precio.

## Ajustes rápidos

En `config.py` puedes cambiar:

- `STRICT_DISTANCE_FILTER = False` a `True`
- `ALLOW_UNKNOWN_LOCATION = True` a `False`
- `MAX_RESULTS_PER_RUN`
- portales activos
