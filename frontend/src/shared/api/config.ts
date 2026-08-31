export type ArticlesDataSourceMode = "mock" | "http";

type ArticlesApiConfig = {
  apiBaseUrl: string;
  dataSourceMode: ArticlesDataSourceMode;
};

function normalizeBaseUrl(value: string) {
  return value.replace(/\/+$/, "");
}

export function getArticlesApiConfig(): ArticlesApiConfig {
  const dataSourceMode =
    import.meta.env.VITE_ARTICLES_DATA_SOURCE === "http" ? "http" : "mock";

  return {
    dataSourceMode,
    apiBaseUrl: normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"),
  };
}
