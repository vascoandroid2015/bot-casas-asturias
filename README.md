# Bot casas Asturias - ZIP nuevo

Incluye una base funcional para:
- detectar anuncios nuevos
- guardar anuncios ya vistos
- enviar cada nueva casa como mensaje individual a Telegram
- evitar errores silenciosos
- manejar 429 Too Many Requests con reintento
- generar debug_report.json

## Variables necesarias
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

## Archivos clave
- main.py
- telegram_client.py
- scrapers.py
- storage.py
- .github/workflows/run-bot.yml

## Importante
El scraper incluido es de ejemplo. Hay que sustituir `scrape_example_portal()` por tus scrapers reales de Idealista/Milanuncios/Fotocasa.
