# Documento de control de anuncios enviados

Este proyecto mantiene un registro persistente de anuncios para evitar duplicados y detectar cambios relevantes.

## Archivos de control

- `data/sent_ads_registry.json`: base maestra de anuncios ya vistos y notificados
- `data/anuncios_control.md`: documento legible con el historial resumido

## Reglas

1. Si la URL no existe en el registro, el anuncio se considera nuevo y se envía
2. Si la URL ya existe y no cambia nada relevante, no se reenvía
3. Si cambia el precio, se reenvía e incluye el precio anterior
4. Si cambia el título o la ubicación, también se reenvía como anuncio actualizado
5. El resumen debug ya no se envía a Telegram
