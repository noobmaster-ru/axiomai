export type ArticleResponseDto = {
  id: number;
  nm_id: number;
  title: string | null;
  brand_name: string;
  image_url: string;
  instruction_text: string;
  in_stock: boolean;
  cashback_percent: number;
};

export type ListArticlesRequest = {
  telegramId: number;
};

export type GetArticleRequest = {
  articleId: number;
};

export type ArticlesDataSource = {
  listArticles: (request: ListArticlesRequest) => Promise<ArticleResponseDto[]>;
  getArticle: (request: GetArticleRequest) => Promise<ArticleResponseDto | null>;
};
