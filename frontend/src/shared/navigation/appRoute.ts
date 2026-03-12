export type FlowRouteStep = "conditions" | "order" | "feedback" | "barcode";

export type AppRoute =
  | {
      name: "catalog";
    }
  | {
      articleId: number;
      name: "article";
    }
  | {
      articleId: number;
      name: "flow";
      step: FlowRouteStep;
    };

function parseAppRoute(hash: string): AppRoute {
  const normalizedHash = hash.replace(/^#/, "");

  if (!normalizedHash || normalizedHash === "/") {
    return { name: "catalog" };
  }

  const articleMatch = normalizedHash.match(/^\/articles\/(\d+)$/);
  const flowMatch = normalizedHash.match(/^\/flow\/(\d+)$/);
  const flowOrderMatch = normalizedHash.match(/^\/flow\/(\d+)\/order$/);
  const flowFeedbackMatch = normalizedHash.match(/^\/flow\/(\d+)\/feedback$/);
  const flowBarcodeMatch = normalizedHash.match(/^\/flow\/(\d+)\/barcode$/);

  if (articleMatch) {
    return {
      name: "article",
      articleId: Number(articleMatch[1]),
    };
  }

  if (flowOrderMatch) {
    return {
      name: "flow",
      articleId: Number(flowOrderMatch[1]),
      step: "order",
    };
  }

  if (flowFeedbackMatch) {
    return {
      name: "flow",
      articleId: Number(flowFeedbackMatch[1]),
      step: "feedback",
    };
  }

  if (flowBarcodeMatch) {
    return {
      name: "flow",
      articleId: Number(flowBarcodeMatch[1]),
      step: "barcode",
    };
  }

  if (flowMatch) {
    return {
      name: "flow",
      articleId: Number(flowMatch[1]),
      step: "conditions",
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

export function navigateToFlow(articleId: number) {
  window.location.hash = `/flow/${articleId}`;
}

export function navigateToFlowOrder(articleId: number) {
  window.location.hash = `/flow/${articleId}/order`;
}

export function navigateToFlowFeedback(articleId: number) {
  window.location.hash = `/flow/${articleId}/feedback`;
}

export function navigateToFlowBarcode(articleId: number) {
  window.location.hash = `/flow/${articleId}/barcode`;
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
