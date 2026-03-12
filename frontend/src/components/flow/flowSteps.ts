export const flowSteps = [
  { key: "conditions", label: "Условия" },
  { key: "order", label: "Покупка" },
  { key: "feedback", label: "Отзыв" },
  { key: "barcode", label: "Штрихкод" },
  { key: "details", label: "Реквизиты" },
  { key: "complete", label: "Готово" },
] as const;

export type FlowStepKey = (typeof flowSteps)[number]["key"];
