import { createArticleRepository } from "./adapters/articleRepository";
import { mockArticlesDataSource } from "./mocks/mockArticlesDataSource";

const MOCK_TELEGRAM_ID = 0;

export const articleRepository = createArticleRepository(mockArticlesDataSource, {
  telegramId: MOCK_TELEGRAM_ID,
});
