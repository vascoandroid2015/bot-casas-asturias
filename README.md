# Bot casas Asturias - ZIP corregido con Playwright

Cambios incluidos:
- añadido playwright a requirements.txt
- workflow GitHub Actions corregido para Python
- uso de `python -m playwright install --with-deps chromium`
- envío Telegram con control anti-429
- persistencia de anuncios vistos
- debug_report.json al final de cada ejecución

## Variables necesarias
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

## Nota
El scraper incluido sigue siendo de ejemplo con Playwright. Sustituye `scrape_example_portal()` por tus scrapers reales.
