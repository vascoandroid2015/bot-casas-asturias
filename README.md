# Bot Casas Asturias max - versión corregida final

Esta versión incluye:

- control persistente de anuncios ya enviados a Telegram
- prevención de duplicados por URL
- detección de cambios en precio, título y ubicación
- documento de control legible en `data/anuncios_control.md`
- almacenamiento del registro maestro en `data/sent_ads_registry.json`
- eliminación del mensaje final de Telegram llamado resumen debug

## Comportamiento

- Anuncio nuevo: se envía
- Anuncio ya conocido sin cambios: no se envía
- Anuncio con cambios: se vuelve a enviar indicando los cambios
- Si cambia el precio: se muestra también el precio anterior

## Uso

```bash
pip install -r requirements.txt
playwright install chromium
export TELEGRAM_TOKEN='tu_token'
export TELEGRAM_CHAT_ID='tu_chat_id'
python main.py
```
