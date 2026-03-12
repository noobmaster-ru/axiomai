export type AppRoute =
  | {
      name: "catalog";
    }
  | {
      articleId: number;
      name: "article";
    };

function parseAppRoute(hash: string): AppRoute {
  const normalizedHash = hash.replace(/^#/, "");

  if (!normalizedHash || normalizedHash === "/") {
    return { name: "catalog" };
  }

  const articleMatch = normalizedHash.match(/^\/articles\/(\d+)$/);

  if (articleMatch) {
    return {
      name: "article",
      articleId: Number(articleMatch[1]),
    };
  }

  return { name: "catalog" };
}

export function getCurrentAppRoute(): AppRoute {
  return parseAppRoute(window.location.hash);
}

export function navigateToCatalog() {
  window.location.hash = "/";
}

export function navigateToArticle(articleId: number) {
  window.location.hash = `/articles/${articleId}`;
}

export function subscribeToAppRoute(listener: (route: AppRoute) => void) {
  const handleHashChange = () => {
    listener(getCurrentAppRoute());
  };

  window.addEventListener("hashchange", handleHashChange);

  return () => {
    window.removeEventListener("hashchange", handleHashChange);
  };
}
