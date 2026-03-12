import { useEffect, useRef, useState } from "react";
import { FlowLayout } from "../../components/flow/FlowLayout";
import {
  FlowUploadField,
  type FlowUploadStatus,
} from "../../components/flow/FlowUploadField";
import type { FlowStepKey } from "../../components/flow/flowSteps";
import type { Article } from "../../entities/article/model";
import { articleRepository } from "../../shared/api";
import "./FlowUploadStepScreen.css";

type FlowUploadStepScreenProps = {
  activeStep: FlowStepKey;
  articleId: number;
  description: string;
  errorBackLabel: string;
  errorText: string;
  errorTitle: string;
  idleActionLabel: string;
  notFoundBackLabel: string;
  onBack: () => void;
  onContinue?: (articleId: number) => void;
  sectionCaption: string;
  sectionTitle: string;
  successBodyText?: string;
  successTitle?: string;
  successActionLabel?: string;
  successFallbackLabel?: string;
  title: string;
  uploadDescription: string;
  uploadLabel: string;
  uploadSubmitLabel: string;
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

export function FlowUploadStepScreen({
  activeStep,
  articleId,
  description,
  errorBackLabel,
  errorText,
  errorTitle,
  idleActionLabel,
  notFoundBackLabel,
  onBack,
  onContinue,
  sectionCaption,
  sectionTitle,
  successBodyText = "Скрин сохранён для этого шага. Если всё верно, можно переходить дальше по сценарию.",
  successTitle = "Фото загружено",
  successActionLabel = "Продолжить",
  successFallbackLabel = "Скрин загружен",
  title,
  uploadDescription,
  uploadLabel,
  uploadSubmitLabel,
}: FlowUploadStepScreenProps) {
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
        <div className="flow-upload-step flow-upload-step--loading">
          <div className="flow-upload-step__placeholder flow-upload-step__placeholder--summary" />
          <div className="flow-upload-step__placeholder flow-upload-step__placeholder--upload" />
        </div>
      );
    }

    if (status === "error") {
      return (
        <section className="flow-upload-step__state-card">
          <h2 className="flow-upload-step__state-title">{errorTitle}</h2>
          <p className="flow-upload-step__state-text">{errorText}</p>
        </section>
      );
    }

    if (status === "not-found" || !article) {
      return (
        <section className="flow-upload-step__state-card">
          <h2 className="flow-upload-step__state-title">Товар недоступен</h2>
          <p className="flow-upload-step__state-text">
            Карточка больше не найдена. Вернитесь назад и выберите другой товар.
          </p>
        </section>
      );
    }

    return (
      <div className="flow-upload-step">
        <section className="flow-upload-step__summary-card">
          <div className="flow-upload-step__summary-head">
            <div className="flow-upload-step__summary-copy">
              <h2 className="flow-upload-step__summary-title">{article.title}</h2>
              <p className="flow-upload-step__summary-meta">
                {article.brandName} · Артикул {article.nmId}
              </p>
            </div>

            <span className="flow-upload-step__summary-badge">{article.cashbackPercent}% кэшбэк</span>
          </div>
        </section>

        <section className="flow-upload-step__section">
          <div className="flow-upload-step__section-header">
            <h2 className="flow-upload-step__section-title">{sectionTitle}</h2>
            <p className="flow-upload-step__section-caption">{sectionCaption}</p>
          </div>

          {uploadStatus === "success" ? (
            <section className="flow-upload-step__success-card" aria-live="polite">
              <span className="flow-upload-step__success-icon" aria-hidden="true" />

              <div className="flow-upload-step__success-copy">
                <h3 className="flow-upload-step__success-title">{successTitle}</h3>
                <p className="flow-upload-step__success-text">{successBodyText}</p>
              </div>

              {selectedFile ? (
                <div className="flow-upload-step__success-file">
                  <span className="flow-upload-step__success-file-label">Файл</span>
                  <strong className="flow-upload-step__success-file-name">{selectedFile.name}</strong>
                </div>
              ) : null}
            </section>
          ) : (
            <FlowUploadField
              label={uploadLabel}
              description={uploadDescription}
              file={selectedFile}
              status={uploadStatus}
              errorMessage={uploadError}
              onSelectFile={handleSelectFile}
            />
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
            {errorBackLabel}
          </button>
        </div>
      );
    }

    if (status === "not-found" || !article) {
      return (
        <div className="flow-action-group">
          <button className="flow-action-button" type="button" onClick={onBack}>
            {notFoundBackLabel}
          </button>
        </div>
      );
    }

    if (uploadStatus === "idle") {
      return (
        <div className="flow-action-group">
          <button className="flow-action-button" type="button" disabled>
            {idleActionLabel}
          </button>
        </div>
      );
    }

    if (uploadStatus === "selected") {
      return (
        <div className="flow-action-group">
          <button className="flow-action-button" type="button" onClick={handleUpload}>
            {uploadSubmitLabel}
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
          <button
            className="flow-action-button"
            type="button"
            disabled={!onContinue}
            onClick={() => onContinue?.(article.id)}
          >
            {onContinue ? successActionLabel : successFallbackLabel}
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
      activeStep={activeStep}
      title={title}
      description={description}
      onBack={onBack}
      actionSlot={renderActionSlot()}
    >
      {renderBody()}
    </FlowLayout>
  );
}
