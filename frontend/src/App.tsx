import { useDeferredValue, useEffect, useState } from "react";
import "./App.css";
import { ProductCard } from "./components/catalog/ProductCard";
import { AppShell } from "./components/layout/AppShell";
import { BottomNav } from "./components/navigation/BottomNav";
import type { Article } from "./entities/article/model";
import { articleRepository } from "./shared/api";
import {
  getCurrentAppRoute,
  navigateToArticle,
  navigateToCatalog,
  navigateToFlow,
  navigateToFlowBarcode,
  navigateToFlowFeedback,
  navigateToFlowOrder,
  subscribeToAppRoute,
  type AppRoute,
} from "./shared/navigation/appRoute";
import { ProductDetailsScreen } from "./screens/article/ProductDetailsScreen";
import { FlowBarcodeScreen } from "./screens/flow/FlowBarcodeScreen";
import { FlowConditionsScreen } from "./screens/flow/FlowConditionsScreen";
import { FlowFeedbackScreen } from "./screens/flow/FlowFeedbackScreen";
import { FlowOrderScreen } from "./screens/flow/FlowOrderScreen";

export default function App() {
  const [route, setRoute] = useState<AppRoute>(() => getCurrentAppRoute());
  const [articles, setArticles] = useState<Article[]>([]);
  const [isLoadingArticles, setIsLoadingArticles] = useState(true);
  const [articlesError, setArticlesError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const deferredQuery = useDeferredValue(searchQuery);
  const normalizedQuery = deferredQuery.trim().toLowerCase();

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
      setArticlesError("");

      try {
        const nextArticles = await articleRepository.getCatalogArticles();

        if (!isMounted) {
          return;
        }

        setArticles(nextArticles);
      } catch {
        if (!isMounted) {
          return;
        }

        setArticlesError("Не удалось загрузить каталог. Попробуйте обновить экран позже.");
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
  }, [route.name]);

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
        bottomSlot={<BottomNav activeKey="requests" />}
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
    if (route.step === "barcode") {
      return (
        <AppShell>
          <FlowBarcodeScreen
            articleId={route.articleId}
            onBack={() => navigateToFlowFeedback(route.articleId)}
          />
        </AppShell>
      );
    }

    if (route.step === "feedback") {
      return (
        <AppShell>
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
        <AppShell>
          <FlowOrderScreen
            articleId={route.articleId}
            onBack={() => navigateToFlow(route.articleId)}
            onContinue={navigateToFlowFeedback}
          />
        </AppShell>
      );
    }

    return (
      <AppShell>
        <FlowConditionsScreen
          articleId={route.articleId}
          onBack={() => navigateToArticle(route.articleId)}
          onStart={navigateToFlowOrder}
        />
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

          <button className="app-header__action" type="button">
            Профиль
          </button>
        </div>
      }
      bottomSlot={<BottomNav activeKey="requests" />}
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
              {isLoadingArticles ? "..." : filteredArticles.length}
            </span>
          </div>

          {articlesError ? (
            <div className="catalog-empty">{articlesError}</div>
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
          ) : (
            <div className="catalog-empty">По вашему запросу пока ничего не найдено.</div>
          )}
        </section>
      </div>
    </AppShell>
  );
}
