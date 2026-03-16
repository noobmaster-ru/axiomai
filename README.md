# AxiomAI

## Environment

1. Скопировать шаблон:

```bash
cp .env.dist .env
```

2. Заполнить значения в `.env`.

Минимально проверить:
- `POSTGRES_*`
- `REDIS_*`
- `BOT_TOKEN`
- `SERVICE_ACCOUNT_AXIOMAI`
- `SERVICE_ACCOUNT_AXIOMAI_EMAIL`
- `OPENAI_TOKEN`
- `SUPERBANKING_*`

Для production дополнительно:
- `APP_DOMAIN`
- `ACME_EMAIL`
- `CORS_ALLOWED_ORIGINS`

## Development

Запуск:

```bash
docker compose up --build
```

Миграции:

```bash
docker compose run --rm postgres_migration
```

## Production

На сервере должен быть заполнен `.env`.

Запуск:

```bash
make up-prod
```

### Запуск Grafana (мониторинг)

Запуск стека мониторинга:

```bash
make grafana
```

Grafana доступна по адресу: http://localhost:3001