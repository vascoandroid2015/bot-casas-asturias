# Bot Casas Asturias v6

Versión v6 con control anti-429 para Telegram.

## Mejoras
- Cada anuncio sigue siendo un mensaje independiente.
- Pausa entre mensajes (`MESSAGE_DELAY_SECONDS`).
- Reintentos automáticos si Telegram responde 429 usando `retry_after`.
- Límite por ejecución (`MAX_RESULTS_PER_RUN = 10`).
- Mantiene debug por fuente y artefactos HTML/capturas.
