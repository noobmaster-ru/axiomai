export type TelegramColorScheme = "light" | "dark";

type TelegramThemeParams = {
  bg_color?: string;
  text_color?: string;
  secondary_bg_color?: string;
  hint_color?: string;
  button_color?: string;
  button_text_color?: string;
};

type TelegramWebAppUser = {
  added_to_attachment_menu?: boolean;
  allows_write_to_pm?: boolean;
  first_name?: string;
  id?: number;
  is_bot?: boolean;
  is_premium?: boolean;
  language_code?: string;
  last_name?: string;
  photo_url?: string;
  username?: string;
};

type TelegramWebApp = {
  colorScheme?: TelegramColorScheme;
  initDataUnsafe?: {
    user?: TelegramWebAppUser;
  };
  themeParams?: TelegramThemeParams;
  ready?: () => void;
  expand?: () => void;
  onEvent?: (eventType: "themeChanged", callback: () => void) => void;
  offEvent?: (eventType: "themeChanged", callback: () => void) => void;
};

export function getTelegramWebApp(): TelegramWebApp | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.Telegram?.WebApp ?? null;
}

export function getTelegramColorScheme(): TelegramColorScheme | null {
  return getTelegramWebApp()?.colorScheme ?? null;
}

export function getTelegramUser(): TelegramWebAppUser | null {
  return getTelegramWebApp()?.initDataUnsafe?.user ?? null;
}

export function prepareTelegramWebApp(): void {
  const webApp = getTelegramWebApp();

  webApp?.ready?.();
  webApp?.expand?.();
}
