/**
 * Generated OpenAPI types — auto-generated, KHÔNG sửa trực tiếp.
 *
 * Để regenerate: `pnpm --filter @ctsv/contracts generate`
 * Source: docs/api/openapi.yaml
 */
export type { components, paths, operations } from "./generated";

/**
 * Helpers shorthand cho code FE.
 * Component name trong OpenAPI `components.schemas.X` → `components["X"]`.
 */
import type { components } from "./generated";

export type Schemas = components["schemas"];
export type Responses = components["responses"];

export type Document = Schemas["Document"];
export type DocumentVersion = Schemas["DocumentVersion"];
export type DocumentScope = Schemas["DocumentScope"];
export type DocumentStatusEnum = Schemas["DocumentStatus"];
export type JobStatus = Schemas["JobStatus"];
export type Job = Schemas["Job"];
export type UploadResponse = Schemas["UploadResponse"];
export type OCRBlock = Schemas["OCRBlock"];
export type OCRPage = Schemas["OCRPage"];
export type OCRReviewStatus = Schemas["OCRReviewStatus"];
export type Citation = Schemas["Citation"];
export type ChatResponse = Schemas["ChatResponse"];
export type ProblemDetail = Schemas["ProblemDetail"];
export type User = Schemas["User"];
export type LoginResponse = Schemas["LoginResponse"];
export type SuccessEnvelope = Schemas["SuccessEnvelope"];
