# Bot Casas Asturias v8

Versión recomendada con mejoras de robustez para Telegram y metabuscador ampliado.

## Mejoras principales
- Anti-429 con reintentos usando `retry_after`.
- Anti-400 con fallback automático sin HTML si Telegram rechaza el parseo.
- Troceo automático de mensajes largos para no superar límites seguros.
- Resumen debug compacto para evitar errores por longitud.
- Truncado de campos largos en anuncios.
- Catálogo amplio de portales, agencias, servicers e institucionales.
- Preparación para fuentes sociales opcionales.

## Recomendación
Usa esta versión como base estable para seguir afinando selectores fuente por fuente.
