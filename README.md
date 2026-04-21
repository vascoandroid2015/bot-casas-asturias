# Bot Casas Asturias portales

Versión ampliada para intentar incluir Fotocasa, Idealista, Milanuncios y Wallapop manteniendo el comportamiento actual del proyecto.

## Qué se ha añadido

- Activación de Fotocasa, Milanuncios y Wallapop en configuración.
- Extractores específicos por portal para Idealista, Fotocasa, Milanuncios y Wallapop.
- Fallback a `application/ld+json` cuando exista listado estructurado.
- Más selectores y scroll más agresivo en portales difíciles.
- Intentos de aceptar cookies y pulsar botones de cargar más.
- Se mantiene el envío de todos los anuncios deduplicados por URL.

## Nota importante

Idealista usa protección anti-bot avanzada y puede bloquear por IP, fingerprint o reputación de red. Esta versión mejora selectores y navegación, pero no garantiza extracción estable sin proxies o infraestructura anti-bot específica.

## Uso

```bash
pip install -r requirements.txt
playwright install chromium
export TELEGRAM_TOKEN='tu_token'
export TELEGRAM_CHAT_ID='tu_chat_id'
python main.py
```

## Recomendación

Si alguno de estos portales sigue dando 0 anuncios en el debug, revisa `debug/html/` y `debug/screenshots/` para ver si hay bloqueo, login, captcha o DOM diferente.
