import { useEffect, useRef, useState } from "react";
import { FlowLayout } from "../../components/flow/FlowLayout";
import {
  FlowUploadField,
  type FlowUploadStatus,
} from "../../components/flow/FlowUploadField";
import type { Article } from "../../entities/article/model";
import { articleRepository } from "../../shared/api";
import "./FlowOrderScreen.css";

type FlowOrderScreenProps = {
  articleId: number;
  onBack: () => void;
  onContinue?: (articleId: number) => void;
};

type ScreenStatus = "loading" | "ready" | "error" | "not-found";

const MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024;

function validateUploadFile(file: File) {
  if (!file.type.startsWith("image/")) {
    return "Нужен скриншот в формате изображения.";
  }

  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    return "Файл слишком большой. Используйте изображение до 10 МБ.";
  }

  return "";
}

export function FlowOrderScreen({ articleId, onBack, onContinue }: FlowOrderScreenProps) {
  const [article, setArticle] = useState<Article | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [status, setStatus] = useState<ScreenStatus>("loading");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<FlowUploadStatus>("idle");
  const [uploadError, setUploadError] = useState("");
  const uploadTimerRef = useRef<number | null>(null);

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
      if (uploadTimerRef.current) {
        window.clearTimeout(uploadTimerRef.current);
      }
    };
  }, []);

  function resetUploadState() {
    if (uploadTimerRef.current) {
      window.clearTimeout(uploadTimerRef.current);
      uploadTimerRef.current = null;
    }

    setSelectedFile(null);
    setUploadStatus("idle");
    setUploadError("");
  }

  function handleSelectFile(file: File | null) {
    if (uploadTimerRef.current) {
      window.clearTimeout(uploadTimerRef.current);
      uploadTimerRef.current = null;
    }

    if (!file) {
      resetUploadState();
      return;
    }

    const validationError = validateUploadFile(file);
    setSelectedFile(file);

    if (validationError) {
      setUploadStatus("error");
      setUploadError(validationError);
      return;
    }

    setUploadStatus("selected");
    setUploadError("");
  }

  function handleUpload() {
    if (!selectedFile) {
      return;
    }

    const validationError = validateUploadFile(selectedFile);

    if (validationError) {
      setUploadStatus("error");
      setUploadError(validationError);
      return;
    }

    setUploadStatus("uploading");
    setUploadError("");

    uploadTimerRef.current = window.setTimeout(() => {
      if (selectedFile.name.toLowerCase().includes("fail")) {
        setUploadStatus("error");
        setUploadError("Не удалось обработать скрин. Попробуйте ещё раз или выберите другой файл.");
        return;
      }

      setUploadStatus("success");
    }, 1200);
  }

  function renderBody() {
    if (status === "loading") {
      return (
        <div className="flow-order flow-order--loading">
          <div className="flow-order__placeholder flow-order__placeholder--summary" />
          <div className="flow-order__placeholder flow-order__placeholder--upload" />
        </div>
      );
    }

    if (status === "error") {
      return (
        <section className="flow-order__state-card">
          <h2 className="flow-order__state-title">Не удалось открыть шаг покупки</h2>
          <p className="flow-order__state-text">
            Попробуйте обновить шаг или вернитесь к условиям по товару.
          </p>
        </section>
      );
    }

    if (status === "not-found" || !article) {
      return (
        <section className="flow-order__state-card">
          <h2 className="flow-order__state-title">Товар недоступен</h2>
          <p className="flow-order__state-text">
            Карточка больше не найдена. Вернитесь назад и выберите другой товар.
          </p>
        </section>
      );
    }

    return (
      <div className="flow-order">
        <section className="flow-order__summary-card">
          <div className="flow-order__summary-head">
            <div className="flow-order__summary-copy">
              <h2 className="flow-order__summary-title">{article.title}</h2>
              <p className="flow-order__summary-meta">
                {article.brandName} · Артикул {article.nmId}
              </p>
            </div>

            <span className="flow-order__summary-badge">{article.cashbackPercent}% кэшбэк</span>
          </div>
        </section>

        <section className="flow-order__section">
          <div className="flow-order__section-header">
            <h2 className="flow-order__section-title">Загрузите скрин заказа</h2>
            <p className="flow-order__section-caption">
              Нужен читаемый скрин с подтверждением покупки по выбранному товару.
            </p>
          </div>

          <FlowUploadField
            label="Добавить скрин заказа"
            description="Подойдёт изображение из галереи или новый снимок из телефона."
            file={selectedFile}
            status={uploadStatus}
            errorMessage={uploadError}
            onSelectFile={handleSelectFile}
          />
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
            Вернуться к условиям
          </button>
        </div>
      );
    }

    if (uploadStatus === "idle") {
      return (
        <div className="flow-action-group">
          <button className="flow-action-button" type="button" disabled>
            Выберите скрин заказа
          </button>
        </div>
      );
    }

    if (uploadStatus === "selected") {
      return (
        <div className="flow-action-group">
          <button className="flow-action-button" type="button" onClick={handleUpload}>
            Загрузить скрин
          </button>
        </div>
      );
    }

    if (uploadStatus === "uploading") {
      return (
        <div className="flow-action-group">
          <button className="flow-action-button" type="button" disabled>
            Загружаем...
          </button>
        </div>
      );
    }

    if (uploadStatus === "success") {
      return (
        <div className="flow-action-group">
          <button className="flow-action-button" type="button" disabled={!onContinue} onClick={() => onContinue?.(article.id)}>
            {onContinue ? "Продолжить" : "Скрин загружен"}
          </button>
          <button className="flow-action-button--secondary" type="button" onClick={resetUploadState}>
            Выбрать другой файл
          </button>
        </div>
      );
    }

    const canRetryUpload = selectedFile ? !validateUploadFile(selectedFile) : false;

    return (
      <div className="flow-action-group">
        <button
          className="flow-action-button"
          type="button"
          onClick={canRetryUpload ? handleUpload : undefined}
          disabled={!canRetryUpload}
        >
          {canRetryUpload ? "Повторить загрузку" : "Выберите корректный файл"}
        </button>
        <button className="flow-action-button--secondary" type="button" onClick={resetUploadState}>
          Сбросить выбор
        </button>
      </div>
    );
  }

  return (
    <FlowLayout
      activeStep="order"
      title="Скрин заказа"
      description="Подтвердите покупку, чтобы перейти к следующему шагу сценария."
      onBack={onBack}
      actionSlot={renderActionSlot()}
    >
      {renderBody()}
    </FlowLayout>
  );
}
