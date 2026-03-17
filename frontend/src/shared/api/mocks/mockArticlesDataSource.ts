import type { ArticleResponseDto, ArticlesDataSource } from "../contracts/articles";

const mockArticles: ArticleResponseDto[] = [
  {
    id: 101,
    nm_id: 128934,
    title: "Кроссовки женские спортивные",
    brand_name: "Mizari",
    image_url: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=320&q=80",
    instruction_text: "Закажите товар, дождитесь получения и затем загрузите подтверждающие скриншоты.",
    in_stock: true,
    cashback_percent: 12,
  },
  {
    id: 102,
    nm_id: 459321,
    title: "Набор контейнеров для хранения",
    brand_name: "Home Vita",
    image_url: "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&w=320&q=80",
    instruction_text: "Сделайте заказ на нужный артикул и пройдите все шаги оформления заявки в приложении.",
    in_stock: true,
    cashback_percent: 8,
  },
  {
    id: 103,
    nm_id: 771552,
    title: "Платье миди с коротким рукавом",
    brand_name: "Liora",
    image_url: "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?auto=format&fit=crop&w=320&q=80",
    instruction_text: "После получения товара оставьте отзыв и загрузите подтверждение в заявку.",
    in_stock: true,
    cashback_percent: 15,
  },
  {
    id: 104,
    nm_id: 884210,
    title: "Увлажняющая сыворотка для лица",
    brand_name: "Derma Glow",
    image_url: "https://images.unsplash.com/photo-1585386959984-a4155224a1ad?auto=format&fit=crop&w=320&q=80",
    instruction_text: "Проверьте условия по товару, затем оформите заказ и загрузите нужные материалы.",
    in_stock: true,
    cashback_percent: 10,
  },
];

const MOCK_NETWORK_DELAY_MS = 120;

function wait(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export const mockArticlesDataSource: ArticlesDataSource = {
  async listArticles() {
    await wait(MOCK_NETWORK_DELAY_MS);
    return mockArticles.filter((article) => article.in_stock);
  },
  async getArticle({ articleId }) {
    await wait(MOCK_NETWORK_DELAY_MS);
    return mockArticles.find((article) => article.id === articleId) ?? null;
  },
};
