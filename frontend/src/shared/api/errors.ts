export type ReadOnlyDataErrorKind =
  | "network"
  | "unavailable"
  | "invalid_response"
  | "unknown";

type ReadOnlyDataErrorOptions = {
  cause?: unknown;
  kind: ReadOnlyDataErrorKind;
  status?: number;
};

export class ReadOnlyDataError extends Error {
  cause?: unknown;
  kind: ReadOnlyDataErrorKind;
  status?: number;

  constructor(message: string, options: ReadOnlyDataErrorOptions) {
    super(message);
    this.name = "ReadOnlyDataError";
    this.cause = options.cause;
    this.kind = options.kind;
    this.status = options.status;
  }
}

export function isReadOnlyDataError(error: unknown): error is ReadOnlyDataError {
  return error instanceof ReadOnlyDataError;
}

export function toReadOnlyDataError(error: unknown): ReadOnlyDataError {
  if (isReadOnlyDataError(error)) {
    return error;
  }

  return new ReadOnlyDataError("Unexpected read-only data error.", {
    cause: error,
    kind: "unknown",
  });
}
