import type { ArticleResponseDto, ArticlesDataSource } from "../contracts/articles";

type HttpArticlesDataSourceConfig = {
  baseUrl: string;
  fetchFn?: typeof fetch;
};

class HttpArticlesDataSourceError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "HttpArticlesDataSourceError";
  }
}

async function readJson<T>(response: Response): Promise<T> {
  try {
    return (await response.json()) as T;
  } catch {
    throw new HttpArticlesDataSourceError("API returned an invalid JSON response.");
  }
}

export function createHttpArticlesDataSource({
  baseUrl,
  fetchFn = fetch,
}: HttpArticlesDataSourceConfig): ArticlesDataSource {
  return {
    async listArticles({ telegramId }) {
      const url = new URL("/articles", baseUrl);
      url.searchParams.set("telegram_id", String(telegramId));

      const response = await fetchFn(url.toString(), {
        headers: {
          Accept: "application/json",
        },
        method: "GET",
      });

      if (!response.ok) {
        throw new HttpArticlesDataSourceError(
          `Failed to load articles: ${response.status} ${response.statusText}`,
        );
      }

      return readJson<ArticleResponseDto[]>(response);
    },

    async getArticle({ articleId }) {
      const url = new URL(`/articles/${articleId}`, baseUrl);

      const response = await fetchFn(url.toString(), {
        headers: {
          Accept: "application/json",
        },
        method: "GET",
      });

      if (response.status === 404) {
        return null;
      }

      if (!response.ok) {
        throw new HttpArticlesDataSourceError(
          `Failed to load article: ${response.status} ${response.statusText}`,
        );
      }

      return readJson<ArticleResponseDto>(response);
    },
  };
}
