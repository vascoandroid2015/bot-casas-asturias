
# Bot Inmobiliario Asturias

Busca casas en Asturias en múltiples fuentes:

- Idealista
- Fotocasa
- Milanuncios
- BOE
- Subastas
- Wallapop (indirecto)
- Redes sociales
- Otros portales

## Uso

Configura en GitHub Secrets:

- TELEGRAM_TOKEN
- TELEGRAM_CHAT_ID

## Importante

Añadir en GitHub Actions:

```yaml
- name: Install Playwright
  run: playwright install
```
