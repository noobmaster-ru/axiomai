export {};

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        initData?: string;
        colorScheme?: "light" | "dark";
        ready?: () => void;
        expand?: () => void;
        onEvent?: (eventType: "themeChanged", callback: () => void) => void;
        offEvent?: (eventType: "themeChanged", callback: () => void) => void;
      };
    };
  }
}
