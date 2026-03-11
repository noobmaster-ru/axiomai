import "./ProductCard.css";

type ProductCardProps = {
  cashbackAmount: number;
  imageUrl: string;
  nmId: number;
  onSelect?: (nmId: number) => void;
  title: string;
  buyoutPercent: number;
};

export function ProductCard({
  cashbackAmount,
  imageUrl,
  nmId,
  onSelect,
  title,
  buyoutPercent,
}: ProductCardProps) {
  return (
    <button className="product-card" type="button" onClick={() => onSelect?.(nmId)}>
      <img className="product-card__image" src={imageUrl} alt={title} loading="lazy" />

      <div className="product-card__content">
        <div className="product-card__head">
          <h3 className="product-card__title">{title}</h3>
          <span className="product-card__tag">{buyoutPercent}% выкуп</span>
        </div>

        <p className="product-card__meta">Артикул {nmId}</p>

        <div className="product-card__footer">
          <div className="product-card__cashback">
            <span className="product-card__cashback-label">Кэшбэк</span>
            <strong className="product-card__cashback-value">{cashbackAmount} ₽</strong>
          </div>

          <span className="product-card__cta">Открыть</span>
        </div>
      </div>
    </button>
  );
}
