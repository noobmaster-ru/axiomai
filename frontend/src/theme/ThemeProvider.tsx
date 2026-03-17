import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  getTelegramColorScheme,
  getTelegramWebApp,
  prepareTelegramWebApp,
  type TelegramColorScheme,
} from "./telegram";

export type ThemeMode = "telegram" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

type ThemeContextValue = {
  mode: ThemeMode;
  resolvedTheme: ResolvedTheme;
  setThemeMode: (mode: ThemeMode) => void;
};

const STORAGE_KEY = "axiomai.theme-mode";

const ThemeContext = createContext<ThemeContextValue | null>(null);

function getSystemTheme(): ResolvedTheme {
  if (typeof window === "undefined") {
    return "light";
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function getStoredThemeMode(): ThemeMode {
  if (typeof window === "undefined") {
    return "light";
  }

  const mode = window.localStorage.getItem(STORAGE_KEY);

  if (mode === "light" || mode === "dark" || mode === "telegram") {
    return mode;
  }

  return "light";
}

function resolveTheme(mode: ThemeMode, telegramTheme: TelegramColorScheme | null, systemTheme: ResolvedTheme): ResolvedTheme {
  if (mode === "light" || mode === "dark") {
    return mode;
  }

  return telegramTheme ?? systemTheme;
}

export function ThemeProvider({ children }: PropsWithChildren) {
  const [mode, setThemeMode] = useState<ThemeMode>(() => getStoredThemeMode());
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>(() => getSystemTheme());
  const [telegramTheme, setTelegramTheme] = useState<TelegramColorScheme | null>(() => getTelegramColorScheme());

  const resolvedTheme = resolveTheme(mode, telegramTheme, systemTheme);

  useEffect(() => {
    prepareTelegramWebApp();

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const webApp = getTelegramWebApp();

    const handleSystemThemeChange = (event: MediaQueryListEvent) => {
      setSystemTheme(event.matches ? "dark" : "light");
    };

    const handleTelegramThemeChange = () => {
      setTelegramTheme(getTelegramColorScheme());
    };

    setTelegramTheme(getTelegramColorScheme());
    setSystemTheme(getSystemTheme());

    mediaQuery.addEventListener("change", handleSystemThemeChange);
    webApp?.onEvent?.("themeChanged", handleTelegramThemeChange);

    return () => {
      mediaQuery.removeEventListener("change", handleSystemThemeChange);
      webApp?.offEvent?.("themeChanged", handleTelegramThemeChange);
    };
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme;
    document.documentElement.dataset.themeMode = mode;
    document.documentElement.style.colorScheme = resolvedTheme;
    window.localStorage.setItem(STORAGE_KEY, mode);
  }, [mode, resolvedTheme]);

  return (
    <ThemeContext.Provider
      value={{
        mode,
        resolvedTheme,
        setThemeMode,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);

  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }

  return context;
}
