import { FlowUploadStepScreen } from "./FlowUploadStepScreen";

type FlowOrderScreenProps = {
  articleId: number;
  onBack: () => void;
  onContinue?: (articleId: number) => void;
};

export function FlowOrderScreen({ articleId, onBack, onContinue }: FlowOrderScreenProps) {
  return (
    <FlowUploadStepScreen
      activeStep="order"
      articleId={articleId}
      title="Скрин заказа"
      description="Подтвердите покупку, чтобы перейти к следующему шагу сценария."
      sectionTitle="Загрузите скрин заказа"
      sectionCaption="Нужен читаемый скрин с подтверждением покупки по выбранному товару."
      uploadLabel="Добавить скрин заказа"
      uploadDescription="Подойдёт изображение из галереи или новый снимок из телефона."
      uploadSubmitLabel="Загрузить скрин"
      idleActionLabel="Выберите скрин заказа"
      errorTitle="Не удалось открыть шаг покупки"
      errorText="Попробуйте обновить шаг или вернитесь к условиям по товару."
      errorBackLabel="Назад"
      notFoundBackLabel="Вернуться к условиям"
      onBack={onBack}
      onContinue={onContinue}
      successActionLabel="Продолжить"
      successFallbackLabel="Скрин загружен"
    />
  );
}
