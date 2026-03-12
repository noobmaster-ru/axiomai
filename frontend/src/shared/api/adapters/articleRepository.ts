import type { Article } from "../../../entities/article/model";
import type { ArticleResponseDto, ArticlesDataSource } from "../contracts/articles";
import { toReadOnlyDataError } from "../errors";

type ArticleRepositoryConfig = {
  telegramId: number;
};

export type ArticleRepository = {
  getCatalogArticles: () => Promise<Article[]>;
  getArticleById: (articleId: number) => Promise<Article | null>;
};

function mapArticle(dto: ArticleResponseDto): Article {
  return {
    id: dto.id,
    nmId: dto.nm_id,
    title: dto.title ?? "Товар без названия",
    brandName: dto.brand_name,
    imageUrl: dto.image_url,
    instructionText: dto.instruction_text,
    inStock: dto.in_stock,
    cashbackPercent: dto.cashback_percent,
  };
}

export function createArticleRepository(
  dataSource: ArticlesDataSource,
  config: ArticleRepositoryConfig,
): ArticleRepository {
  return {
    async getCatalogArticles() {
      try {
        const articles = await dataSource.listArticles({ telegramId: config.telegramId });
        return articles.map(mapArticle);
      } catch (error) {
        throw toReadOnlyDataError(error);
      }
    },
    async getArticleById(articleId) {
      try {
        const article = await dataSource.getArticle({ articleId });
        return article ? mapArticle(article) : null;
      } catch (error) {
        throw toReadOnlyDataError(error);
      }
    },
  };
}
