import { createArticleRepository } from "./adapters/articleRepository";
import { getArticlesApiConfig } from "./config";
import { createHttpArticlesDataSource } from "./http/httpArticlesDataSource";
import { mockArticlesDataSource } from "./mocks/mockArticlesDataSource";

const apiConfig = getArticlesApiConfig();

const articlesDataSource =
  apiConfig.dataSourceMode === "http"
    ? createHttpArticlesDataSource({ baseUrl: apiConfig.apiBaseUrl })
    : mockArticlesDataSource;

export const articleRepository = createArticleRepository(articlesDataSource, {
  telegramId: apiConfig.telegramId,
});
