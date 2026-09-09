FROM python:3.13-slim AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_PATH="/app"

ENV VIRTUAL_ENV="$APP_PATH/.venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR $APP_PATH

FROM python-base AS builder-base

# Версия совпадает с CI (astral-sh/setup-uv), чтобы образ резолвил тот же набор зависимостей
RUN pip install --no-cache-dir uv==0.11.12

COPY ./pyproject.toml ./uv.lock ./

RUN uv venv \
    && uv sync --frozen --no-install-project

COPY ./alembic.ini ./
COPY ./axiomai ./axiomai

FROM python-base

RUN addgroup --system --gid 1000 app \
    && adduser --system --uid 1000 --ingroup app app

COPY --from=builder-base --chown=app:app $APP_PATH $APP_PATH

USER app
