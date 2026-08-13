/**
 * FE-domain models (camelCase) — dùng trong UI & state.
 *
 * Lưu ý: OpenAPI trả snake_case (contract chuẩn). FE dùng camelCase ở UI/state
 * để idiomatic. Mapping đi qua `lib/api/mappers/*` ở mọi entry/exit point.
 *
 * KHÔNG nhận raw response của `fetch`/`apiClient` rồi đưa vào component.
 * Luôn chạy qua mapper.
 */
import type {
  Document as ApiDocument,
  DocumentVersion as ApiDocumentVersion,
  User as ApiUser,
  OCRBlock as ApiOCRBlock,
  OCRPage as ApiOCRPage,
  Citation as ApiCitation,
  Job as ApiJob,
  SearchResultItem as ApiSearchResultItem,
  DocumentStatusEnum,
  DocumentScope,
  OCRReviewStatus,
} from "@ctsv/contracts";

// ---- Re-export enums (giữ nguyên tên, format đã UPPER_SNAKE) ----
export type DocumentStatus = DocumentStatusEnum;
export type { DocumentScope, OCRReviewStatus };

// ---- Domain models (camelCase) ----

export type UserRole = "admin" | "staff" | "student";

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  department?: string | null;
  avatarUrl?: string;
  status?: string;
}

export interface Document {
  id: string;
  title: string;
  type: ApiDocument["type"];
  status: DocumentStatus;
  scope: DocumentScope;
  codeNumber?: string | null;
  issuingBody?: string | null;
  effectiveFrom?: string | null;
  effectiveTo?: string | null;
  latestVersion: number;
  authorId?: string;
  tags: string[];
  createdAt: string;
  updatedAt: string;
  fileUrl?: string;
  fileSize?: number;
  pageCount?: number;
}

export interface SearchResult {
  chunkId: ApiSearchResultItem["chunk_id"];
  documentId: ApiSearchResultItem["document_id"];
  documentTitle: ApiSearchResultItem["document_title"];
  documentScope: ApiSearchResultItem["document_scope"];
  documentType: ApiSearchResultItem["document_type"];
  pageNumber: ApiSearchResultItem["page_number"];
  text: ApiSearchResultItem["text"];
  score: ApiSearchResultItem["score"];
  vectorScore: ApiSearchResultItem["vector_score"];
  fulltextScore: ApiSearchResultItem["fulltext_score"];
}

export interface DocumentVersion {
  id: string;
  documentId: string;
  versionNumber: number;
  status: DocumentStatus;
  ocrStatus: ApiDocumentVersion["ocr_status"];
  requiresReview: boolean;
  fileUrl: string;
  fileSize: number;
  checksum: string;
  supersedesVersionId?: string | null;
  supersededByVersionId?: string | null;
  changeSummary?: string | null;
  createdBy?: string;
  createdAt: string;
}

export interface OCRPage {
  id: ApiOCRPage["id"];
  pageNumber: ApiOCRPage["page_number"];
  width: ApiOCRPage["width"];
  height: ApiOCRPage["height"];
  imageKey?: ApiOCRPage["image_key"];
}

export interface OCRBlock {
  id: string;
  ocrJobId: string;
  pageNumber: number;
  /**
   * Bounding box theo PDF coordinate [x_min, y_min, x_max, y_max].
   * KHÔNG phải [x, y, width, height] — xem mapper *-to-canvas-px.ts.
   */
  bbox: [number, number, number, number];
  text: string;
  confidence: number;
  requiresReview: boolean;
  reviewStatus: OCRReviewStatus;
  reviewedBy?: string | null;
  reviewedAt?: string | null;
  isEdited: boolean;
  editedBy?: string | null;
  editedAt?: string | null;
  originalText?: string | null;
  processingTimeMs: number;
}

export interface Citation {
  documentId: string;
  documentVersionId: string;
  documentTitle: string;
  pageNumber: number;
  chunkId: string;
  quote: string;
  score: number;
  bbox?: [number, number, number, number];
}

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  content: string;
  timestamp: string;
  citations?: Citation[];
  isStreaming?: boolean;
}

export interface ChatAnswerData {
  answer: string;
  citations: Citation[];
  hasSufficientEvidence: boolean;
}

export interface Job {
  id: string;
  type: ApiJob["type"];
  status: ApiJob["status"];
  progress: number;
  error?: string | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  createdAt: string;
}

export interface TrainingRun {
  id: string;
  name: string;
  status: "running" | "completed" | "failed";
  startedAt: string;
  finishedAt?: string;
  docsIndexed: number;
  loss?: number;
  accuracy?: number;
}

export interface ModelVersion {
  id: string;
  version: string;
  name: string;
  isActive: boolean;
  createdAt: string;
  accuracy?: number;
  size: string;
  provider: string;
}

// ---- Problem Detail (RFC 7807) ----
export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail?: string | null;
  code: string;
  requestId: string;
  errors?: Array<{ field: string; message: string }>;
}

// ---- Auth response (tách access token: access in memory, refresh in HttpOnly cookie) ----
export interface LoginAnswerData {
  accessToken: string;
  expiresIn: number;
  user: User;
}

// ---- Typed API errors (FE side) ----
export class ApiError extends Error {
  statusCode: number;
  code: string;
  problem?: ProblemDetail;
  constructor(problem: ProblemDetail) {
    super(problem.detail || problem.title);
    this.name = "ApiError";
    this.statusCode = problem.status;
    this.code = problem.code;
    this.problem = problem;
  }
}
