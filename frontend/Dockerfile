FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY index.html ./
COPY tsconfig.json ./
COPY tsconfig.app.json ./
COPY vite.config.ts ./
COPY src ./src

ARG VITE_API_BASE_URL=/api
ARG VITE_ARTICLES_DATA_SOURCE=http
ARG VITE_API_TELEGRAM_ID=0

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_ARTICLES_DATA_SOURCE=${VITE_ARTICLES_DATA_SOURCE}
ENV VITE_API_TELEGRAM_ID=${VITE_API_TELEGRAM_ID}

RUN npm run build

FROM caddy:2.10-alpine

COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=builder /app/dist /srv
