# Bot Casas Asturias v3

Versión v3 enfocada en depurar extracción real con Playwright.

## Qué añade
- Guardado de HTML por portal en `debug/html/`
- Capturas completas en `debug/screenshots/`
- Selectores alternativos por portal
- Intento de aceptar cookies
- Capa básica anti-detección (`navigator.webdriver`, idioma, chrome runtime)
- Resumen debug a Telegram

## Objetivo
Validar si el problema es selector roto, muro de cookies o variante anti-bot.

## Uso local
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
python main.py
```
