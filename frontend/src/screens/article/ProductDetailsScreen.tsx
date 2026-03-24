import { useEffect, useState } from "react";
import type { Article } from "../../entities/article/model";
import { articleRepository } from "../../shared/api";
import { InstructionContent } from "../../shared/ui/InstructionContent";
import { toReadOnlyDataError, type ReadOnlyDataErrorKind } from "../../shared/api/errors";
import "./ProductDetailsScreen.css";

type ProductDetailsScreenProps = {
  articleId: number;
  onBack: () => void;
  onStartFlow?: (articleId: number) => void;
};

type ErrorState = {
  description: string;
  title: string;
};

type ScreenStatus = "loading" | "ready" | "error" | "not-found";

function getProductErrorState(kind: ReadOnlyDataErrorKind): ErrorState {
  if (kind === "network") {
    return {
      description: "Проверьте соединение и попробуйте открыть карточку ещё раз.",
      title: "Нет связи с сервисом",
    };
  }

  if (kind === "unavailable") {
    return {
      description: "Карточка товара временно недоступна. Обычно сервис восстанавливается быстро.",
      title: "Сервис пока не отвечает",
    };
  }

  if (kind === "invalid_response") {
    return {
      description: "Сервис вернул неполные данные по товару. Лучше открыть карточку немного позже.",
      title: "Не удалось показать товар",
    };
  }

  return {
    description: "Попробуйте открыть карточку ещё раз чуть позже.",
    title: "Не удалось загрузить товар",
  };
}

export function ProductDetailsScreen({
  articleId,
  onBack,
  onStartFlow,
}: ProductDetailsScreenProps) {
  const [article, setArticle] = useState<Article | null>(null);
  const [errorState, setErrorState] = useState<ErrorState | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [status, setStatus] = useState<ScreenStatus>("loading");

  useEffect(() => {
    let isMounted = true;

    async function loadArticle() {
      setStatus("loading");
      setArticle(null);
      setErrorState(null);

      try {
        const nextArticle = await articleRepository.getArticleById(articleId);

        if (!isMounted) {
          return;
        }

        if (!nextArticle) {
          setStatus("not-found");
          return;
        }

        setArticle(nextArticle);
        setStatus("ready");
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setErrorState(getProductErrorState(toReadOnlyDataError(error).kind));
        setStatus("error");
      }
    }

    void loadArticle();

    return () => {
      isMounted = false;
    };
  }, [articleId, retryKey]);

  if (status === "loading") {
    return (
      <div className="product-details product-details--loading">
        <div className="product-details__media product-details__media--placeholder" />
        <div className="product-details__card product-details__card--placeholder" />
        <div className="product-details__card product-details__card--placeholder product-details__card--short" />
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="product-details product-details--state">
        <section className="product-details__state-card">
          <h2 className="product-details__state-title">{errorState?.title}</h2>
          <p className="product-details__state-text">{errorState?.description}</p>
          <div className="product-details__state-actions">
            <button className="product-details__secondary-button" type="button" onClick={onBack}>
              Назад в каталог
            </button>
            <button
              className="product-details__primary-button"
              type="button"
              onClick={() => setRetryKey((currentValue) => currentValue + 1)}
            >
              Обновить
            </button>
          </div>
        </section>
      </div>
    );
  }

  if (status === "not-found" || !article) {
    return (
      <div className="product-details product-details--state">
        <section className="product-details__state-card">
          <h2 className="product-details__state-title">Товар не найден</h2>
          <p className="product-details__state-text">
            Возможно, карточка уже недоступна или ссылка устарела.
          </p>
          <button className="product-details__primary-button" type="button" onClick={onBack}>
            Вернуться в каталог
          </button>
        </section>
      </div>
    );
  }

  return (
    <div className="product-details">
      <section className="product-details__hero">
        <div className="product-details__media">
          <img
            className="product-details__image"
            src={article.imageUrl}
            alt={article.title}
            loading="eager"
          />
        </div>

        <div className="product-details__summary">
          <div className="product-details__summary-head">
            <span className="product-details__cashback-badge">{article.cashbackPercent}% кэшбэк</span>
            <span className="product-details__stock-badge">
              {article.inStock ? "Доступно сейчас" : "Недоступно"}
            </span>
          </div>

          <h1 className="product-details__title">{article.title}</h1>

          <div className="product-details__meta-list">
            <p className="product-details__meta-item">Бренд: {article.brandName}</p>
            <p className="product-details__meta-item">Артикул: {article.nmId}</p>
          </div>
        </div>
      </section>

      <section className="product-details__conditions">
        <div className="product-details__section-header">
          <h2 className="product-details__section-title">Условия участия</h2>
          <p className="product-details__section-caption">
            Перед стартом заявки проверьте требования по товару.
          </p>
        </div>

        <div className="product-details__conditions-card">
          <InstructionContent className="product-details__conditions-text" text={article.instructionText} />
        </div>
      </section>

      <section className="product-details__cta-panel">
        <div className="product-details__cta-copy">
          <h2 className="product-details__cta-title">Можно переходить к оформлению</h2>
          <p className="product-details__cta-text">
            На следующем шаге откроется начало заявки и подтверждение участия по товару.
          </p>
        </div>

        <button
          className="product-details__primary-button"
          type="button"
          onClick={() => onStartFlow?.(article.id)}
        >
          Согласен с условиями
        </button>
      </section>
    </div>
  );
}
