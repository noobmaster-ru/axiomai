import "./BottomNav.css";

export type BottomNavKey = "profile" | "requests" | "statuses";

type BottomNavItem = {
  key: BottomNavKey;
  label: string;
};

const bottomNavItems: BottomNavItem[] = [
  { key: "profile", label: "Профиль" },
  { key: "requests", label: "Заявки" },
  { key: "statuses", label: "Статусы" },
];

type BottomNavProps = {
  activeKey: BottomNavKey;
  onSelect?: (key: BottomNavKey) => void;
};

export function BottomNav({ activeKey, onSelect }: BottomNavProps) {
  return (
    <nav className="bottom-nav" aria-label="Основная навигация">
      <div className="bottom-nav__grid">
        {bottomNavItems.map((item) => {
          const isActive = item.key === activeKey;

          return (
            <button
              key={item.key}
              className={`bottom-nav__item${isActive ? " bottom-nav__item--active" : ""}`}
              type="button"
              aria-current={isActive ? "page" : undefined}
              onClick={() => onSelect?.(item.key)}
            >
              <span className="bottom-nav__icon" aria-hidden="true" />
              <span className="bottom-nav__label">{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
