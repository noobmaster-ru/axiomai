import type { ArticleResponseDto, ArticlesDataSource } from "../contracts/articles";
import { ReadOnlyDataError } from "../errors";

type HttpArticlesDataSourceConfig = {
  baseUrl: string;
  fetchFn?: typeof fetch;
};

function createApiUrl(baseUrl: string, path: string) {
  return new URL(path.replace(/^\/+/, ""), `${baseUrl}/`);
}

async function readJson<T>(response: Response): Promise<T> {
  try {
    return (await response.json()) as T;
  } catch {
    throw new ReadOnlyDataError("API returned an invalid JSON response.", {
      kind: "invalid_response",
      status: response.status,
    });
  }
}

function isArticleResponseDto(value: unknown): value is ArticleResponseDto {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;

  return (
    typeof candidate.id === "number" &&
    typeof candidate.nm_id === "number" &&
    (typeof candidate.title === "string" || candidate.title === null) &&
    typeof candidate.brand_name === "string" &&
    typeof candidate.image_url === "string" &&
    typeof candidate.instruction_text === "string" &&
    typeof candidate.in_stock === "boolean" &&
    typeof candidate.cashback_percent === "number"
  );
}

function assertArticleResponseDto(value: unknown): ArticleResponseDto {
  if (!isArticleResponseDto(value)) {
    throw new ReadOnlyDataError("API returned an unexpected article shape.", {
      kind: "invalid_response",
    });
  }

  return value;
}

function assertArticlesListResponse(value: unknown): ArticleResponseDto[] {
  if (!Array.isArray(value)) {
    throw new ReadOnlyDataError("API returned an unexpected articles list shape.", {
      kind: "invalid_response",
    });
  }

  return value.map(assertArticleResponseDto);
}

function normalizeHttpError(response: Response, message: string) {
  if (response.status >= 500 || response.status === 429) {
    return new ReadOnlyDataError(message, {
      kind: "unavailable",
      status: response.status,
    });
  }

  return new ReadOnlyDataError(message, {
    kind: "unknown",
    status: response.status,
  });
}

export function createHttpArticlesDataSource({
  baseUrl,
  fetchFn = fetch,
}: HttpArticlesDataSourceConfig): ArticlesDataSource {
  return {
    async listArticles({ telegramId }) {
      const url = createApiUrl(baseUrl, "articles");
      url.searchParams.set("telegram_id", String(telegramId));

      let response: Response;

      try {
        response = await fetchFn(url.toString(), {
          headers: {
            Accept: "application/json",
          },
          method: "GET",
        });
      } catch (error) {
        throw new ReadOnlyDataError("Failed to load articles.", {
          cause: error,
          kind: "network",
        });
      }

      if (!response.ok) {
        throw normalizeHttpError(
          response,
          `Failed to load articles: ${response.status} ${response.statusText}`,
        );
      }

      const json = await readJson<unknown>(response);
      return assertArticlesListResponse(json);
    },

    async getArticle({ articleId }) {
      const url = createApiUrl(baseUrl, `articles/${articleId}`);

      let response: Response;

      try {
        response = await fetchFn(url.toString(), {
          headers: {
            Accept: "application/json",
          },
          method: "GET",
        });
      } catch (error) {
        throw new ReadOnlyDataError("Failed to load article.", {
          cause: error,
          kind: "network",
        });
      }

      if (response.status === 404) {
        return null;
      }

      if (!response.ok) {
        throw normalizeHttpError(
          response,
          `Failed to load article: ${response.status} ${response.statusText}`,
        );
      }

      const json = await readJson<unknown>(response);
      return assertArticleResponseDto(json);
    },
  };
}
