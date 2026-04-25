export {};

declare global {
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

  interface Window {
    Telegram?: {
      WebApp?: {
        colorScheme?: "light" | "dark";
        initDataUnsafe?: {
          user?: TelegramWebAppUser;
        };
        ready?: () => void;
        expand?: () => void;
        onEvent?: (eventType: "themeChanged", callback: () => void) => void;
        offEvent?: (eventType: "themeChanged", callback: () => void) => void;
      };
    };
  }
}
