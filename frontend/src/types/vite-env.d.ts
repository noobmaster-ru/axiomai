/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_TELEGRAM_ID?: string;
  readonly VITE_ARTICLES_DATA_SOURCE?: "mock" | "http";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
