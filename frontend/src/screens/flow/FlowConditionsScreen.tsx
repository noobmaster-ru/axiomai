import { useEffect, useState } from "react";
import { FlowLayout } from "../../components/flow/FlowLayout";
import type { Article } from "../../entities/article/model";
import { articleRepository } from "../../shared/api";
import { InstructionContent } from "../../shared/ui/InstructionContent";
import "./FlowConditionsScreen.css";

type FlowConditionsScreenProps = {
  articleId: number;
  onBack: () => void;
  onStart?: (articleId: number) => void;
};

type ScreenStatus = "loading" | "ready" | "error" | "not-found";

export function FlowConditionsScreen({
  articleId,
  onBack,
  onStart,
}: FlowConditionsScreenProps) {
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
        <div className="flow-conditions flow-conditions--loading">
          <div className="flow-conditions__placeholder flow-conditions__placeholder--summary" />
          <div className="flow-conditions__placeholder flow-conditions__placeholder--text" />
        </div>
      );
    }

    if (status === "error") {
      return (
        <section className="flow-conditions__state-card">
          <h2 className="flow-conditions__state-title">Не удалось открыть условия</h2>
          <p className="flow-conditions__state-text">
            Попробуйте ещё раз. Если проблема повторится, вернитесь к карточке товара.
          </p>
        </section>
      );
    }

    if (status === "not-found" || !article) {
      return (
        <section className="flow-conditions__state-card">
          <h2 className="flow-conditions__state-title">Товар недоступен</h2>
          <p className="flow-conditions__state-text">
            Карточка больше не найдена. Вернитесь назад и выберите другой товар.
          </p>
        </section>
      );
    }

    return (
      <div className="flow-conditions">
        <section className="flow-conditions__article-card">
          <div className="flow-conditions__article-head">
            <div className="flow-conditions__article-copy">
              <h2 className="flow-conditions__article-title">{article.title}</h2>
              <p className="flow-conditions__article-meta">
                {article.brandName} · Артикул {article.nmId}
              </p>
            </div>

            <span className="flow-conditions__article-badge">{article.cashbackPercent}% кэшбэк</span>
          </div>
        </section>

        <section className="flow-conditions__section">
          <div className="flow-conditions__section-header">
            <h2 className="flow-conditions__section-title">Проверьте условия перед стартом</h2>
            <p className="flow-conditions__section-caption">
              После подтверждения откроется следующий шаг сценария.
            </p>
          </div>

          <div className="flow-conditions__content-card">
            <InstructionContent className="flow-conditions__content-text" text={article.instructionText} />
          </div>
        </section>
      </div>
    );
  }

  function renderActionSlot() {
    if (status === "loading") {
      return (
        <div className="flow-action-group">
          <button className="flow-action-button" type="button" disabled>
            Загружаем...
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
            К товару
          </button>
        </div>
      );
    }

    if (status === "not-found" || !article) {
      return (
        <div className="flow-action-group">
          <button className="flow-action-button" type="button" onClick={onBack}>
            Вернуться к товару
          </button>
        </div>
      );
    }

    return (
      <div className="flow-action-group">
        <button
          className="flow-action-button"
          type="button"
          onClick={() => onStart?.(article.id)}
          disabled={!onStart}
        >
          Начать
        </button>
      </div>
    );
  }

  return (
    <FlowLayout
      activeStep="conditions"
      title="Условия участия"
      description="Сначала проверьте требования по товару. После подтверждения начнётся пошаговое оформление."
      onBack={onBack}
      actionSlot={renderActionSlot()}
    >
      {renderBody()}
    </FlowLayout>
  );
}
