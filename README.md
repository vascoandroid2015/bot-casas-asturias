# Bot Casas Asturias max

Versión corregida para maximizar anuncios siguiendo 3 mejoras prácticas:

- Fase 1: quitar el corte por primer selector, subir scrolls y eliminar filtros agresivos.
- Fase 2: enviar todo lo deduplicado por URL, no solo novedades.
- Fase 3: dejar la base preparada para crear scrapers específicos por portal en una siguiente iteración.

## Cambios aplicados

- Ya no se rompe la extracción al primer selector con resultados.
- Se hace autoscroll más largo para cargar más tarjetas.
- Los anuncios no se invalidan por texto, precio o ubicación desconocida; solo se marcan con señales informativas.
- Se deduplica por URL.
- Se envían todos los anuncios encontrados en cada ejecución.
- El límite de resultados se ha subido a 9999.
- Se corrigieron errores de sintaxis en `telegram_client.py`.

## Uso

```bash
pip install -r requirements.txt
playwright install chromium
export TELEGRAM_TOKEN='tu_token'
export TELEGRAM_CHAT_ID='tu_chat_id'
python main.py
```

## Siguiente mejora recomendada

La fase 3 real consiste en sustituir selectores genéricos por extractores específicos para los 5-8 portales que más anuncios aporten.
