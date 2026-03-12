import type { ChangeEvent } from "react";
import { useId, useRef } from "react";
import "./FlowUploadField.css";

export type FlowUploadStatus = "idle" | "selected" | "uploading" | "success" | "error";

type FlowUploadFieldProps = {
  accept?: string;
  description: string;
  errorMessage?: string;
  file: File | null;
  label: string;
  onSelectFile: (file: File | null) => void;
  status: FlowUploadStatus;
};

function formatFileSize(bytes: number) {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} КБ`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

export function FlowUploadField({
  accept = "image/*",
  description,
  errorMessage,
  file,
  label,
  onSelectFile,
  status,
}: FlowUploadFieldProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement | null>(null);

  function openPicker() {
    if (status === "uploading") {
      return;
    }

    inputRef.current?.click();
  }

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    onSelectFile(nextFile);
    event.target.value = "";
  }

  const statusLabel =
    status === "success"
      ? "Файл готов"
      : status === "uploading"
        ? "Идёт загрузка"
        : status === "error"
          ? "Нужна проверка"
          : file
            ? "Файл выбран"
            : "Файл не выбран";

  const actionLabel =
    status === "uploading"
      ? "Загрузка..."
      : file
        ? "Выбрать другой"
        : "Выбрать файл";

  return (
    <div className={`flow-upload${status !== "idle" ? ` flow-upload--${status}` : ""}`}>
      <input
        id={inputId}
        ref={inputRef}
        className="flow-upload__input"
        type="file"
        accept={accept}
        onChange={handleChange}
      />

      <button className="flow-upload__surface" type="button" onClick={openPicker}>
        <span className="flow-upload__icon" aria-hidden="true" />

        <span className="flow-upload__copy">
          <span className="flow-upload__label">{label}</span>
          <span className="flow-upload__description">{description}</span>
        </span>

        <span className="flow-upload__status">{statusLabel}</span>
      </button>

      {file ? (
        <div className="flow-upload__file">
          <div className="flow-upload__file-copy">
            <strong className="flow-upload__file-name">{file.name}</strong>
            <span className="flow-upload__file-meta">{formatFileSize(file.size)}</span>
          </div>

          <button className="flow-upload__file-action" type="button" onClick={openPicker}>
            {actionLabel}
          </button>
        </div>
      ) : null}

      {status === "uploading" ? (
        <div className="flow-upload__progress" aria-hidden="true">
          <span className="flow-upload__progress-bar" />
        </div>
      ) : null}

      {errorMessage ? <p className="flow-upload__error">{errorMessage}</p> : null}
    </div>
  );
}
