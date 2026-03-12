import { useEffect, useState } from "react";
import { FlowLayout } from "../../components/flow/FlowLayout";
import type { Article } from "../../entities/article/model";
import { articleRepository } from "../../shared/api";
import "./FlowCompleteScreen.css";

type FlowCompleteScreenProps = {
  articleId: number;
  onBack: () => void;
  onOpenArticle: (articleId: number) => void;
  onReturnHome: () => void;
};

type ScreenStatus = "loading" | "ready" | "error" | "not-found";

export function FlowCompleteScreen({
  articleId,
  onBack,
  onOpenArticle,
  onReturnHome,
}: FlowCompleteScreenProps) {
  const [article, setArticle] = useState<Article | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [status, setStatus] = useState<ScreenStatus>("loading");

  useEffect(() => {
    let isMounted = true;

    async function loadArticle() {
      setStatus("loading");
      setArticle(null);

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
      } catch {
        if (!isMounted) {
          return;
        }

        setStatus("error");
      }
    }

    void loadArticle();

    return () => {
      isMounted = false;
    };
  }, [articleId, retryKey]);

  function renderBody() {
    if (status === "loading") {
      return (
        <div className="flow-complete flow-complete--loading">
          <div className="flow-complete__placeholder flow-complete__placeholder--hero" />
          <div className="flow-complete__placeholder flow-complete__placeholder--summary" />
        </div>
      );
    }

    if (status === "error") {
      return (
        <section className="flow-complete__state-card">
          <h2 className="flow-complete__state-title">Не удалось открыть итог заявки</h2>
          <p className="flow-complete__state-text">
            Попробуйте обновить экран или вернитесь к реквизитам.
          </p>
        </section>
      );
    }

    if (status === "not-found" || !article) {
      return (
        <section className="flow-complete__state-card">
          <h2 className="flow-complete__state-title">Товар недоступен</h2>
          <p className="flow-complete__state-text">
            Карточка больше не найдена. Вернитесь в каталог и выберите другой товар.
          </p>
        </section>
      );
    }

    return (
      <div className="flow-complete">
        <section className="flow-complete__hero-card" aria-live="polite">
          <span className="flow-complete__hero-icon" aria-hidden="true" />

          <div className="flow-complete__hero-copy">
            <h2 className="flow-complete__hero-title">Заявка оформлена</h2>
            <p className="flow-complete__hero-text">
              Мы приняли материалы по товару. Дальше заявка пройдёт проверку, а статус обновится после обработки.
            </p>
          </div>
        </section>

        <section className="flow-complete__summary-card">
          <div className="flow-complete__summary-head">
            <div className="flow-complete__summary-copy">
              <h2 className="flow-complete__summary-title">{article.title}</h2>
              <p className="flow-complete__summary-meta">
                {article.brandName} · Артикул {article.nmId}
              </p>
            </div>

            <span className="flow-complete__summary-badge">{article.cashbackPercent}% кэшбэк</span>
          </div>
        </section>

        <section className="flow-complete__info-card">
          <h3 className="flow-complete__info-title">Что дальше</h3>
          <p className="flow-complete__info-text">
            Если всё заполнено корректно, заявка останется в обработке до завершения модерации. Повторно ничего загружать не нужно.
          </p>
        </section>
      </div>
    );
  }

  function renderActionSlot() {
    if (status === "loading") {
      return (
        <div className="flow-action-group">
          <button className="flow-action-button" type="button" disabled>
            Готовим итог...
          </button>
        </div>
      );
    }

    if (status === "error") {
      return (
        <div className="flow-action-group">
          <button
            className="flow-action-button"
            type="button"
            onClick={() => setRetryKey((currentValue) => currentValue + 1)}
          >
            Повторить
          </button>
          <button className="flow-action-button--secondary" type="button" onClick={onBack}>
            Назад
          </button>
        </div>
      );
    }

    if (status === "not-found" || !article) {
      return (
        <div className="flow-action-group">
          <button className="flow-action-button" type="button" onClick={onReturnHome}>
            На главную
          </button>
        </div>
      );
    }

    return (
      <div className="flow-action-group">
        <button className="flow-action-button" type="button" onClick={onReturnHome}>
          На главную
        </button>
        <button className="flow-action-button--secondary" type="button" onClick={() => onOpenArticle(article.id)}>
          К товару
        </button>
      </div>
    );
  }

  return (
    <FlowLayout
      activeStep="complete"
      title="Заявка готова"
      description="Все шаги сценария заполнены. Ниже итог и понятный выход из заявки."
      onBack={onBack}
      actionSlot={renderActionSlot()}
    >
      {renderBody()}
    </FlowLayout>
  );
}
