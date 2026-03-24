import { useDeferredValue, useEffect, useState } from "react";
import "./App.css";
import { ProductCard } from "./components/catalog/ProductCard";
import { AppShell } from "./components/layout/AppShell";
import { BottomNav } from "./components/navigation/BottomNav";
import type { Article } from "./entities/article/model";
import { articleRepository } from "./shared/api";
import { toReadOnlyDataError, type ReadOnlyDataErrorKind } from "./shared/api/errors";
import {
  getCurrentAppRoute,
  navigateToArticle,
  navigateToCatalog,
  navigateToFlow,
  navigateToFlowBarcode,
  navigateToFlowComplete,
  navigateToFlowDetails,
  navigateToFlowFeedback,
  navigateToFlowOrder,
  navigateToProfile,
  subscribeToAppRoute,
  type AppRoute,
} from "./shared/navigation/appRoute";
import { ProductDetailsScreen } from "./screens/article/ProductDetailsScreen";
import { FlowBarcodeScreen } from "./screens/flow/FlowBarcodeScreen";
import { FlowConditionsScreen } from "./screens/flow/FlowConditionsScreen";
import { FlowCompleteScreen } from "./screens/flow/FlowCompleteScreen";
import { FlowDetailsScreen } from "./screens/flow/FlowDetailsScreen";
import { FlowFeedbackScreen } from "./screens/flow/FlowFeedbackScreen";
import { FlowOrderScreen } from "./screens/flow/FlowOrderScreen";
import { ProfileScreen } from "./screens/profile/ProfileScreen";

type CatalogErrorState = {
  description: string;
  kind: ReadOnlyDataErrorKind;
  title: string;
};

function getCatalogErrorState(kind: ReadOnlyDataErrorKind): CatalogErrorState {
  if (kind === "network") {
    return {
      description: "Проверьте соединение и попробуйте открыть каталог ещё раз.",
      kind,
      title: "Нет связи с сервисом",
    };
  }

  if (kind === "unavailable") {
    return {
      description: "Каталог временно недоступен. Обычно это проходит через пару минут.",
      kind,
      title: "Каталог пока не отвечает",
    };
  }

  if (kind === "invalid_response") {
    return {
      description: "Сервис вернул неполные данные. Лучше попробовать ещё раз чуть позже.",
      kind,
      title: "Не удалось показать товары",
    };
  }

  return {
    description: "Попробуйте обновить экран позже. Если проблема повторится, вернитесь чуть позже.",
    kind,
    title: "Не удалось загрузить каталог",
  };
}

export default function App() {
  const [route, setRoute] = useState<AppRoute>(() => getCurrentAppRoute());
  const [articles, setArticles] = useState<Article[]>([]);
  const [isLoadingArticles, setIsLoadingArticles] = useState(true);
  const [articlesError, setArticlesError] = useState<CatalogErrorState | null>(null);
  const [catalogRetryKey, setCatalogRetryKey] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const deferredQuery = useDeferredValue(searchQuery);
  const normalizedQuery = deferredQuery.trim().toLowerCase();

  function handleBottomNavSelect(key: "profile" | "requests" | "statuses") {
    if (key === "profile") {
      navigateToProfile();
      return;
    }

    if (key === "requests") {
      navigateToCatalog();
      return;
    }
  }

  useEffect(() => {
    return subscribeToAppRoute(setRoute);
  }, []);

  useEffect(() => {
    if (route.name !== "catalog") {
      return;
    }

    let isMounted = true;

    async function loadArticles() {
      setIsLoadingArticles(true);
      setArticlesError(null);

      try {
        const nextArticles = await articleRepository.getCatalogArticles();

        if (!isMounted) {
          return;
        }

        setArticles(nextArticles);
      } catch (error) {
        if (!isMounted) {
          return;
        }

        setArticlesError(getCatalogErrorState(toReadOnlyDataError(error).kind));
      } finally {
        if (isMounted) {
          setIsLoadingArticles(false);
        }
      }
    }

    void loadArticles();

    return () => {
      isMounted = false;
    };
  }, [catalogRetryKey, route.name]);

  const filteredArticles = articles.filter((article) => {
    if (!normalizedQuery) {
      return true;
    }

    return (
      article.title.toLowerCase().includes(normalizedQuery) ||
      article.brandName.toLowerCase().includes(normalizedQuery) ||
      String(article.nmId).includes(normalizedQuery)
    );
  });

  if (route.name === "article") {
    return (
      <AppShell
        topSlot={
          <div className="app-header app-header--compact">
            <button className="app-header__back" type="button" onClick={navigateToCatalog}>
              Назад
            </button>

            <div className="app-header__meta">
              <p className="app-header__eyebrow">AxiomAI Cashback</p>
              <h1 className="app-header__title app-header__title--compact">Карточка товара</h1>
            </div>
          </div>
        }
        bottomSlot={<BottomNav activeKey="requests" onSelect={handleBottomNavSelect} />}
      >
        <ProductDetailsScreen
          articleId={route.articleId}
          onBack={navigateToCatalog}
          onStartFlow={navigateToFlow}
        />
      </AppShell>
    );
  }

  if (route.name === "flow") {
    if (route.step === "complete") {
      return (
        <AppShell mode="flow">
          <FlowCompleteScreen
            articleId={route.articleId}
            onBack={() => navigateToFlowDetails(route.articleId)}
            onReturnHome={navigateToCatalog}
            onOpenArticle={navigateToArticle}
          />
        </AppShell>
      );
    }

    if (route.step === "details") {
      return (
        <AppShell mode="flow">
          <FlowDetailsScreen
            articleId={route.articleId}
            onBack={() => navigateToFlowBarcode(route.articleId)}
            onContinue={navigateToFlowComplete}
          />
        </AppShell>
      );
    }

    if (route.step === "barcode") {
      return (
        <AppShell mode="flow">
          <FlowBarcodeScreen
            articleId={route.articleId}
            onBack={() => navigateToFlowFeedback(route.articleId)}
            onContinue={navigateToFlowDetails}
          />
        </AppShell>
      );
    }

    if (route.step === "feedback") {
      return (
        <AppShell mode="flow">
          <FlowFeedbackScreen
            articleId={route.articleId}
            onBack={() => navigateToFlowOrder(route.articleId)}
            onContinue={navigateToFlowBarcode}
          />
        </AppShell>
      );
    }

    if (route.step === "order") {
      return (
        <AppShell mode="flow">
          <FlowOrderScreen
            articleId={route.articleId}
            onBack={() => navigateToFlow(route.articleId)}
            onContinue={navigateToFlowFeedback}
          />
        </AppShell>
      );
    }

    return (
      <AppShell mode="flow">
        <FlowConditionsScreen
          articleId={route.articleId}
          onBack={() => navigateToArticle(route.articleId)}
          onStart={navigateToFlowOrder}
        />
      </AppShell>
    );
  }

  if (route.name === "profile") {
    return (
      <AppShell
        topSlot={
          <div className="app-header">
            <div className="app-header__meta">
              <p className="app-header__eyebrow">AxiomAI Cashback</p>
              <h1 className="app-header__title">Профиль</h1>
            </div>
          </div>
        }
        bottomSlot={<BottomNav activeKey="profile" onSelect={handleBottomNavSelect} />}
      >
        <ProfileScreen />
      </AppShell>
    );
  }

  return (
    <AppShell
      topSlot={
        <div className="app-header">
          <div className="app-header__meta">
            <p className="app-header__eyebrow">AxiomAI Cashback</p>
            <h1 className="app-header__title">Каталог</h1>
            <p className="app-header__subtitle">Выберите товар и начните оформление кэшбэка</p>
          </div>
        </div>
      }
      bottomSlot={<BottomNav activeKey="requests" onSelect={handleBottomNavSelect} />}
    >
      <div className="home-screen">
        <section className="home-screen__intro">
          <h2 className="home-screen__title">Товары для выкупа</h2>
          <p className="home-screen__description">
            Найдите артикул, откройте карточку товара и пройдите шаги проверки внутри заявки.
          </p>
        </section>

        <label className="search-panel">
          <span className="search-panel__label">Поиск по названию или артикулу</span>
          <input
            className="search-panel__field"
            placeholder="Например, кроссовки или 128934"
            type="text"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </label>

        <section className="catalog-section">
          <div className="catalog-section__header">
            <h2 className="catalog-section__title">Доступные товары</h2>
            <span className="catalog-section__meta">
              {isLoadingArticles ? "..." : articlesError ? "—" : filteredArticles.length}
            </span>
          </div>

          {articlesError ? (
            <div className="catalog-empty catalog-empty--state">
              <h3 className="catalog-empty__title">{articlesError.title}</h3>
              <p className="catalog-empty__text">{articlesError.description}</p>
              <button
                className="catalog-empty__button"
                type="button"
                onClick={() => setCatalogRetryKey((currentValue) => currentValue + 1)}
              >
                Попробовать ещё раз
              </button>
            </div>
          ) : isLoadingArticles ? (
            <div className="catalog-empty">Загружаем товары...</div>
          ) : filteredArticles.length ? (
            <div className="catalog-list">
              {filteredArticles.map((article) => (
                <ProductCard
                  key={article.id}
                  article={article}
                  onSelect={navigateToArticle}
                />
              ))}
            </div>
          ) : articles.length === 0 ? (
            <div className="catalog-empty">
              Сейчас в каталоге нет доступных товаров. Проверьте список немного позже.
            </div>
          ) : (
            <div className="catalog-empty">По вашему запросу пока ничего не найдено.</div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
