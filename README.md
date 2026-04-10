# Bot de casas de piedra en Asturias para Telegram

Este bot busca anuncios inmobiliarios en varios portales y manda avisos a Telegram cuando detecta inmuebles que cumplan estos filtros:

- Precio máximo: 250.000 €
- Parcela/finca mínima: 600 m²
- Zona: Asturias
- Tiempo estimado a Oviedo centro: 15 min o menos
- Si el anuncio ya existía, solo avisa de nuevo si cambia el precio

## Archivos

- `main.py`: lógica principal
- `seen_ads.json`: histórico de anuncios ya vistos
- `.github/workflows/casas.yml`: ejecución automática en GitHub Actions
- `requirements.txt`: dependencias Python

## Secrets necesarios en GitHub

Crea estos secretos en el repositorio:

- `TELEGRAM_TOKEN`: token del bot creado con BotFather
- `TELEGRAM_CHAT_ID`: por ejemplo `@casaspiedrasenasturias`

## Importante

Esta versión está pensada como base funcional y mantenible. Muchos portales cambian HTML, limitan scraping o usan JavaScript/captcha. Por eso el scraper usa un enfoque genérico y habrá que ajustar selectores por portal según veas resultados reales.

## Mejoras futuras recomendadas

- Añadir Playwright para fuentes que cargan contenido dinámico
- Ajustar scraper específico por cada portal
- Sustituir el tiempo estimado por una API real de rutas
- Añadir aviso de anuncio desaparecido
- Añadir filtro por concejos concretos
