# Bot Casas Portales Pro

Versión enfocada solo en Idealista, Fotocasa, Milanuncios y Wallapop.

## Enfoque

- Solo 4 portales.
- Extractores dedicados por portal.
- Scroll largo y segundo scroll corto.
- Intento de aceptar cookies y de pulsar botones de cargar más.
- Fallback a `application/ld+json` si la página publica listados estructurados.
- Mantiene tu flujo actual: deduplicación por URL, envío por Telegram y debug.

## URLs base usadas

- Idealista Asturias: https://www.idealista.com/venta-viviendas/asturias/
- Fotocasa Asturias: https://www.fotocasa.es/es/comprar/viviendas/asturias-provincia/todas-las-zonas/l
- Milanuncios Asturias: https://www.milanuncios.com/venta-de-casas-en-asturias/
- Wallapop inmobiliaria Salas: https://es.wallapop.com/inmobiliaria/salas

## Instalación

```bash
pip install -r requirements.txt
playwright install chromium
export TELEGRAM_TOKEN='tu_token'
export TELEGRAM_CHAT_ID='tu_chat_id'
python main.py
```

## Nota seria

Fotocasa y Wallapop publican URLs y listados accesibles desde buscador público. Idealista también muestra listados públicos en Asturias, pero puede activar medidas anti-bot y devolver menos resultados o bloquear sesiones. Wallapop además puede variar mucho por municipio o búsqueda. [web:26][web:31][web:32][web:34]

## Revisión de fallos

Si uno da 0 resultados, revisa:

- `debug/html/<portal>.html`
- `debug/screenshots/<portal>.png`
- `debug/debug_report.json`
