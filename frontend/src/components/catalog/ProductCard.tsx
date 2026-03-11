import type { Article } from "../../entities/article/model";
import "./ProductCard.css";

type ProductCardProps = {
  article: Article;
  onSelect?: (articleId: number) => void;
};

export function ProductCard({ article, onSelect }: ProductCardProps) {
  const availabilityLabel = article.inStock ? "В наличии" : "Нет в наличии";

  return (
    <button className="product-card" type="button" onClick={() => onSelect?.(article.id)}>
      <img
        className="product-card__image"
        src={article.imageUrl}
        alt={article.title}
        loading="lazy"
      />

      <div className="product-card__content">
        <div className="product-card__head">
          <h3 className="product-card__title">{article.title}</h3>
          <span className="product-card__tag">{availabilityLabel}</span>
        </div>

        <p className="product-card__meta">
          {article.brandName} · Артикул {article.nmId}
        </p>

        <div className="product-card__footer">
          <div className="product-card__cashback">
            <span className="product-card__cashback-label">Кэшбэк</span>
            <strong className="product-card__cashback-value">{article.cashbackPercent}%</strong>
          </div>

          <span className="product-card__cta">Открыть</span>
        </div>
      </div>
    </button>
  );
}
