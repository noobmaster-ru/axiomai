import { FlowUploadStepScreen } from "./FlowUploadStepScreen";

type FlowFeedbackScreenProps = {
  articleId: number;
  onBack: () => void;
  onContinue?: (articleId: number) => void;
};

export function FlowFeedbackScreen({
  articleId,
  onBack,
  onContinue,
}: FlowFeedbackScreenProps) {
  return (
    <FlowUploadStepScreen
      activeStep="feedback"
      articleId={articleId}
      title="Скрин отзыва"
      description="После покупки загрузите подтверждение опубликованного отзыва по товару."
      sectionTitle="Загрузите скриншот отзыва"
      sectionCaption="На изображении должны быть видны сам отзыв и привязка к нужному товару."
      uploadLabel="Добавить скрин отзыва"
      uploadDescription="Подойдёт скрин из приложения маркетплейса или снимок экрана с телефона."
      uploadSubmitLabel="Загрузить отзыв"
      idleActionLabel="Выберите скрин отзыва"
      errorTitle="Не удалось открыть шаг отзыва"
      errorText="Попробуйте обновить шаг или вернитесь к загрузке скрина заказа."
      errorBackLabel="Назад"
      notFoundBackLabel="Вернуться к покупке"
      onBack={onBack}
      onContinue={onContinue}
      successActionLabel="Продолжить"
      successFallbackLabel="Скрин отзыва загружен"
    />
  );
}
