import { FlowUploadStepScreen } from "./FlowUploadStepScreen";

type FlowBarcodeScreenProps = {
  articleId: number;
  onBack: () => void;
  onContinue?: (articleId: number) => void;
};

export function FlowBarcodeScreen({
  articleId,
  onBack,
  onContinue,
}: FlowBarcodeScreenProps) {
  return (
    <FlowUploadStepScreen
      activeStep="barcode"
      articleId={articleId}
      title="Фото штрихкода"
      description="Теперь загрузите фото разрезанного штрихкода, чтобы подтвердить выполнение условий."
      sectionTitle="Загрузите фото разрезанного штрихкода"
      sectionCaption="На фото должен быть хорошо виден разрезанный штрихкод от товара."
      uploadLabel="Добавить фото штрихкода"
      uploadDescription="Подойдёт снимок с камеры телефона или изображение из галереи."
      uploadSubmitLabel="Загрузить фото"
      idleActionLabel="Выберите фото штрихкода"
      errorTitle="Не удалось открыть шаг штрихкода"
      errorText="Попробуйте обновить шаг или вернитесь к загрузке скрина отзыва."
      errorBackLabel="Назад"
      notFoundBackLabel="Вернуться к отзыву"
      successTitle="Фото штрихкода загружено"
      successBodyText="Фото сохранено для этого шага. Дальше можно будет перейти к заполнению реквизитов."
      onBack={onBack}
      onContinue={onContinue}
      successActionLabel="Продолжить"
      successFallbackLabel="Фото штрихкода загружено"
    />
  );
}
