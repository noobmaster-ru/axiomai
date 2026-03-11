import { useDeferredValue, useState } from "react";
import "./App.css";
import { ProductCard } from "./components/catalog/ProductCard";
import { AppShell } from "./components/layout/AppShell";
import { BottomNav } from "./components/navigation/BottomNav";
import { mockProducts } from "./data/mockProducts";

export default function App() {
  const [searchQuery, setSearchQuery] = useState("");
  const deferredQuery = useDeferredValue(searchQuery);
  const normalizedQuery = deferredQuery.trim().toLowerCase();

  const filteredProducts = mockProducts.filter((product) => {
    if (!normalizedQuery) {
      return true;
    }

    return (
      product.title.toLowerCase().includes(normalizedQuery) ||
      String(product.nmId).includes(normalizedQuery)
    );
  });

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
      bottomSlot={
        <BottomNav activeKey="requests" />
      }
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
            <span className="catalog-section__meta">{filteredProducts.length}</span>
          </div>

          {filteredProducts.length ? (
            <div className="catalog-list">
              {filteredProducts.map((product) => (
                <ProductCard key={product.nmId} {...product} />
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
