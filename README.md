# Bot Casas Asturias v4

Versión v4 centrada en diagnóstico explícito en Telegram y GitHub Actions.

## Novedades
- En Telegram informa por portal de URL final, título de página, señales de bloqueo y conteos por selector.
- Guarda HTML y screenshots en `debug/`.
- Sube `debug/` también como artifact del workflow.
- Mantiene extracción en Playwright con capa básica anti-detección.

## Uso local
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install --with-deps chromium
python main.py
```
