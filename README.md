# Bot Casas Asturias max - control anti-duplicados

Esta versión añade un registro persistente de anuncios enviados a Telegram para no reenviar duplicados y para avisar cuando un anuncio ya conocido cambia.

## Qué hace ahora

- Guarda cada anuncio enviado en `data/sent_ads_registry.json`.
- Genera un documento de control en `data/anuncios_control.md`.
- No vuelve a notificar anuncios idénticos ya enviados.
- Sí notifica cambios en anuncios ya vistos, por ejemplo precio, título o ubicación.
- Si el precio cambia, el mensaje incluye el precio anterior.
- El resumen debug final de Telegram queda desactivado.

## Lógica de notificación

- Anuncio nuevo -> se envía
- Anuncio ya conocido sin cambios -> no se envía
- Anuncio ya conocido con cambios -> se envía indicando cambios detectados

## Uso

```bash
pip install -r requirements.txt
playwright install chromium
export TELEGRAM_TOKEN='tu_token'
export TELEGRAM_CHAT_ID='tu_chat_id'
python main.py
```
