export type ArticlesDataSourceMode = "mock" | "http";

type ArticlesApiConfig = {
  apiBaseUrl: string;
  dataSourceMode: ArticlesDataSourceMode;
  telegramId: number;
};

function normalizeBaseUrl(value: string) {
  return value.replace(/\/+$/, "");
}

function parseTelegramId(value: string | undefined) {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue : 0;
}

export function getArticlesApiConfig(): ArticlesApiConfig {
  const dataSourceMode =
    import.meta.env.VITE_ARTICLES_DATA_SOURCE === "http" ? "http" : "mock";

  return {
    dataSourceMode,
    apiBaseUrl: normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"),
    telegramId: parseTelegramId(import.meta.env.VITE_API_TELEGRAM_ID),
  };
}
