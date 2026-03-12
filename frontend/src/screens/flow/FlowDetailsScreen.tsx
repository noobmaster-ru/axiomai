import { useEffect, useMemo, useRef, useState } from "react";
import { FlowLayout } from "../../components/flow/FlowLayout";
import type { Article } from "../../entities/article/model";
import { articleRepository } from "../../shared/api";
import "./FlowDetailsScreen.css";

type FlowDetailsScreenProps = {
  articleId: number;
  onBack: () => void;
  onContinue?: (articleId: number) => void;
};

type ScreenStatus = "loading" | "ready" | "error" | "not-found";
type SubmitStatus = "idle" | "submitting" | "success";

type DetailsFormValues = {
  amount: string;
  bank: string;
  phone: string;
};

type DetailsFormErrors = Partial<Record<keyof DetailsFormValues, string>>;

const suggestedBanks = [
  "СберБанк",
  "Т-Банк",
  "Альфа-Банк",
  "ВТБ",
  "Ozon Банк",
];

function getPhoneDigits(value: string) {
  return value.replace(/\D/g, "");
}

function formatPhoneInput(value: string) {
  const digits = getPhoneDigits(value).slice(0, 11);

  if (!digits) {
    return "";
  }

  const normalized = digits.startsWith("8")
    ? `7${digits.slice(1)}`
    : digits.startsWith("7")
      ? digits
      : `7${digits}`;

  const parts = [
    normalized.slice(0, 1),
    normalized.slice(1, 4),
    normalized.slice(4, 7),
    normalized.slice(7, 9),
    normalized.slice(9, 11),
  ].filter(Boolean);

  if (parts.length === 1) {
    return `+${parts[0]}`;
  }

  return `+${parts[0]} ${parts[1]}${parts[2] ? ` ${parts[2]}` : ""}${parts[3] ? `-${parts[3]}` : ""}${parts[4] ? `-${parts[4]}` : ""}`;
}

function validateDetailsForm(values: DetailsFormValues): DetailsFormErrors {
  const errors: DetailsFormErrors = {};

  if (!values.bank.trim()) {
    errors.bank = "Укажите банк для выплаты.";
  }

  const phoneDigits = getPhoneDigits(values.phone);

  if (!phoneDigits) {
    errors.phone = "Укажите номер телефона.";
  } else if (phoneDigits.length !== 11) {
    errors.phone = "Введите номер в формате +7 999 123-45-67.";
  }

  if (values.amount.trim()) {
    const normalizedAmount = Number(values.amount.replace(",", "."));

    if (!Number.isFinite(normalizedAmount) || normalizedAmount <= 0) {
      errors.amount = "Сумма должна быть больше нуля.";
    }
  }

  return errors;
}

export function FlowDetailsScreen({
  articleId,
  onBack,
  onContinue,
}: FlowDetailsScreenProps) {
  const [article, setArticle] = useState<Article | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [status, setStatus] = useState<ScreenStatus>("loading");
  const [submitStatus, setSubmitStatus] = useState<SubmitStatus>("idle");
  const [formValues, setFormValues] = useState<DetailsFormValues>({
    bank: "",
    phone: "",
    amount: "",
  });
  const [fieldErrors, setFieldErrors] = useState<DetailsFormErrors>({});
  const submitTimerRef = useRef<number | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadArticle() {
      setStatus("loading");
      setArticle(null);

      try {
        const nextArticle = await articleRepository.getArticleById(articleId);

        if (!isMounted) {
          return;
        }

        if (!nextArticle) {
          setStatus("not-found");
          return;
        }

        setArticle(nextArticle);
        setStatus("ready");
      } catch {
        if (!isMounted) {
          return;
        }

        setStatus("error");
      }
    }

    void loadArticle();

    return () => {
      isMounted = false;
    };
  }, [articleId, retryKey]);

  useEffect(() => {
    return () => {
      if (submitTimerRef.current) {
        window.clearTimeout(submitTimerRef.current);
      }
    };
  }, []);

  const formErrors = useMemo(() => validateDetailsForm(formValues), [formValues]);
  const isFormValid = Object.keys(formErrors).length === 0;

  function handleFieldChange<K extends keyof DetailsFormValues>(field: K, value: DetailsFormValues[K]) {
    setFormValues((currentValues) => {
      const nextValues = { ...currentValues, [field]: value };
      return nextValues;
    });

    setSubmitStatus("idle");

    if (fieldErrors[field]) {
      const nextValues = { ...formValues, [field]: value };
      setFieldErrors(validateDetailsForm(nextValues));
    }
  }

  function handleBankSuggestion(bank: string) {
    handleFieldChange("bank", bank);
  }

  function handleSubmit() {
    const nextErrors = validateDetailsForm(formValues);
    setFieldErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setSubmitStatus("submitting");

    submitTimerRef.current = window.setTimeout(() => {
      setSubmitStatus("success");
    }, 1100);
  }

  function resetSubmittedState() {
    setSubmitStatus("idle");
  }

  function renderBody() {
    if (status === "loading") {
      return (
        <div className="flow-details flow-details--loading">
          <div className="flow-details__placeholder flow-details__placeholder--summary" />
          <div className="flow-details__placeholder flow-details__placeholder--form" />
        </div>
      );
    }

    if (status === "error") {
      return (
        <section className="flow-details__state-card">
          <h2 className="flow-details__state-title">Не удалось открыть реквизиты</h2>
          <p className="flow-details__state-text">
            Попробуйте обновить шаг или вернитесь к загрузке фото штрихкода.
          </p>
        </section>
      );
    }

    if (status === "not-found" || !article) {
      return (
        <section className="flow-details__state-card">
          <h2 className="flow-details__state-title">Товар недоступен</h2>
          <p className="flow-details__state-text">
            Карточка больше не найдена. Вернитесь назад и выберите другой товар.
          </p>
        </section>
      );
    }

    return (
      <div className="flow-details">
        <section className="flow-details__summary-card">
          <div className="flow-details__summary-head">
            <div className="flow-details__summary-copy">
              <h2 className="flow-details__summary-title">{article.title}</h2>
              <p className="flow-details__summary-meta">
                {article.brandName} · Артикул {article.nmId}
              </p>
            </div>

            <span className="flow-details__summary-badge">{article.cashbackPercent}% кэшбэк</span>
          </div>
        </section>

        <section className="flow-details__section">
          <div className="flow-details__section-header">
            <h2 className="flow-details__section-title">Куда перевести выплату</h2>
            <p className="flow-details__section-caption">
              Укажите реквизиты для перевода. Эти данные понадобятся после проверки заявки.
            </p>
          </div>

          {submitStatus === "success" ? (
            <section className="flow-details__success-card" aria-live="polite">
              <span className="flow-details__success-icon" aria-hidden="true" />

              <div className="flow-details__success-copy">
                <h3 className="flow-details__success-title">Реквизиты сохранены</h3>
                <p className="flow-details__success-text">
                  Данные заполнены. Следующим шагом можно будет завершить заявку и показать итоговый статус.
                </p>
              </div>

              <div className="flow-details__success-values">
                <p className="flow-details__success-item">
                  <span>Банк</span>
                  <strong>{formValues.bank}</strong>
                </p>
                <p className="flow-details__success-item">
                  <span>Телефон</span>
                  <strong>{formValues.phone}</strong>
                </p>
                {formValues.amount.trim() ? (
                  <p className="flow-details__success-item">
                    <span>Сумма</span>
                    <strong>{formValues.amount} ₽</strong>
                  </p>
                ) : null}
              </div>
            </section>
          ) : (
            <div className="flow-details__form">
              <label className="flow-details__field">
                <span className="flow-details__field-label">Банк</span>
                <input
                  className={`flow-details__input${fieldErrors.bank ? " flow-details__input--error" : ""}`}
                  type="text"
                  placeholder="Например, СберБанк"
                  value={formValues.bank}
                  onChange={(event) => handleFieldChange("bank", event.target.value)}
                />
                {fieldErrors.bank ? (
                  <span className="flow-details__field-error">{fieldErrors.bank}</span>
                ) : (
                  <span className="flow-details__field-help">Можно ввести вручную или выбрать популярный банк ниже.</span>
                )}
              </label>

              <div className="flow-details__suggestions" role="list" aria-label="Популярные банки">
                {suggestedBanks.map((bank) => (
                  <button
                    key={bank}
                    className={`flow-details__suggestion${formValues.bank === bank ? " flow-details__suggestion--active" : ""}`}
                    type="button"
                    onClick={() => handleBankSuggestion(bank)}
                  >
                    {bank}
                  </button>
                ))}
              </div>

              <label className="flow-details__field">
                <span className="flow-details__field-label">Номер телефона</span>
                <input
                  className={`flow-details__input${fieldErrors.phone ? " flow-details__input--error" : ""}`}
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="+7 999 123-45-67"
                  value={formValues.phone}
                  onChange={(event) => handleFieldChange("phone", formatPhoneInput(event.target.value))}
                />
                {fieldErrors.phone ? (
                  <span className="flow-details__field-error">{fieldErrors.phone}</span>
                ) : (
                  <span className="flow-details__field-help">На этот номер будет оформлена выплата.</span>
                )}
              </label>

              <label className="flow-details__field">
                <span className="flow-details__field-label">Сумма выплаты</span>
                <input
                  className={`flow-details__input${fieldErrors.amount ? " flow-details__input--error" : ""}`}
                  type="text"
                  inputMode="decimal"
                  placeholder="Если нужна ручная корректировка"
                  value={formValues.amount}
                  onChange={(event) => handleFieldChange("amount", event.target.value)}
                />
                {fieldErrors.amount ? (
                  <span className="flow-details__field-error">{fieldErrors.amount}</span>
                ) : (
                  <span className="flow-details__field-help">Поле необязательное. Оставьте пустым, если сумма уже определена.</span>
                )}
              </label>
            </div>
          )}
        </section>
      </div>
    );
  }

  function renderActionSlot() {
    if (status === "loading") {
      return (
        <div className="flow-action-group">
          <button className="flow-action-button" type="button" disabled>
            Загружаем шаг...
          </button>
        </div>
      );
    }

    if (status === "error") {
      return (
        <div className="flow-action-group">
          <button
            className="flow-action-button"
            type="button"
            onClick={() => setRetryKey((currentValue) => currentValue + 1)}
          >
            Повторить
          </button>
          <button className="flow-action-button--secondary" type="button" onClick={onBack}>
            Назад
          </button>
        </div>
      );
    }

    if (status === "not-found" || !article) {
      return (
        <div className="flow-action-group">
          <button className="flow-action-button" type="button" onClick={onBack}>
            Вернуться к штрихкоду
          </button>
        </div>
      );
    }

    if (submitStatus === "submitting") {
      return (
        <div className="flow-action-group">
          <button className="flow-action-button" type="button" disabled>
            Сохраняем реквизиты...
          </button>
        </div>
      );
    }

    if (submitStatus === "success") {
      return (
        <div className="flow-action-group">
          <button
            className="flow-action-button"
            type="button"
            disabled={!onContinue}
            onClick={() => onContinue?.(article.id)}
          >
            {onContinue ? "Перейти к завершению" : "Реквизиты сохранены"}
          </button>
          <button className="flow-action-button--secondary" type="button" onClick={resetSubmittedState}>
            Изменить данные
          </button>
        </div>
      );
    }

    return (
      <div className="flow-action-group">
        <button
          className="flow-action-button"
          type="button"
          onClick={handleSubmit}
          disabled={!isFormValid}
        >
          Сохранить реквизиты
        </button>
      </div>
    );
  }

  return (
    <FlowLayout
      activeStep="details"
      title="Реквизиты для выплаты"
      description="Заполните данные для перевода. После этого можно будет перейти к финальному статусу заявки."
      onBack={onBack}
      actionSlot={renderActionSlot()}
    >
      {renderBody()}
    </FlowLayout>
  );
}
