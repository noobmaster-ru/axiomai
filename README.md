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

Тестовые статьи:

```bash
cmd /c "docker compose exec -T postgres psql -U axiomai -d axiomai_db < scripts\dev_seed_articles.sql"
```

## Production

На сервере должен быть заполнен `.env`.

Миграции:

```bash
docker compose -f docker-compose.prod.yaml run --rm postgres_migration
```

Запуск:

```bash
docker compose -f docker-compose.prod.yaml pull
docker compose -f docker-compose.prod.yaml up -d
```
