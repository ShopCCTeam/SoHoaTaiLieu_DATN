/**
 * Mappers: OpenAPI snake_case DTO ↔ FE camelCase domain models.
 *
 * Quy tắc:
 * - 1 DTO ↔ 1 domain model.
 * - Mapper chỉ làm field rename + enum translate, KHÔNG validate
 *   (validation đã ở Pydantic / Zod boundary).
 * - snake_case → camelCase dùng utility `snakeToCamel` (id, created_at → createdAt).
 * - Date giữ nguyên string ISO 8601; UI parse khi cần.
 *
 * Lý do tồn tại:
 * - OpenAPI contract snake_case (chuẩn ngành cho JSON API).
 * - FE camelCase (chuẩn TypeScript / React).
 * - Khi contract thay đổi → chỉ sửa mapper, không sửa component.
 */
import type {
  Document as ApiDocument,
  DocumentVersion as ApiDocumentVersion,
  User as ApiUser,
  OCRBlock as ApiOCRBlock,
  OCRPage as ApiOCRPage,
  Citation as ApiCitation,
  Job as ApiJob,
} from "@ctsv/contracts";
import type {
  Document,
  DocumentVersion,
  User,
  OCRBlock,
  OCRPage,
  Citation,
  Job,
  UserRole,
} from "./types";

const ROLE_MAP: Record<string, UserRole> = {
  admin: "admin",
  staff: "staff",
  student: "student",
};

// ---- User ----

export function apiUserToDomain(dto: ApiUser): User {
  return {
    id: dto.id,
    email: dto.email,
    fullName: dto.full_name,
    role: ROLE_MAP[dto.role] ?? "student",
    department: dto.department ?? undefined,
  };
}

// ---- Document ----

export function apiDocumentToDomain(dto: ApiDocument): Document {
  return {
    id: dto.id,
    title: dto.title,
    type: dto.type,
    status: dto.status,
    scope: dto.scope,
    codeNumber: dto.code_number,
    issuingBody: dto.issuing_body,
    effectiveFrom: dto.effective_from,
    effectiveTo: dto.effective_to,
    latestVersion: dto.latest_version,
    authorId: dto.author_id,
    tags: dto.tags ?? [],
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

// ---- DocumentVersion ----

export function apiDocumentVersionToDomain(dto: ApiDocumentVersion): DocumentVersion {
  return {
    id: dto.id,
    documentId: dto.document_id,
    versionNumber: dto.version_number,
    status: dto.status,
    ocrStatus: dto.ocr_status,
    requiresReview: dto.requires_review ?? false,
    fileUrl: dto.file_url,
    fileSize: dto.file_size ?? 0,
    checksum: dto.checksum,
    supersedesVersionId: dto.supersedes_version_id ?? undefined,
    supersededByVersionId: dto.superseded_by_version_id ?? undefined,
    changeSummary: dto.change_summary ?? undefined,
    createdBy: dto.created_by,
    createdAt: dto.created_at,
  };
}

// ---- OCRPage ----

export function apiOCRPageToDomain(dto: ApiOCRPage): OCRPage {
  return {
    id: dto.id,
    pageNumber: dto.page_number,
    width: dto.width,
    height: dto.height,
    imageKey: dto.image_key,
  };
}

// ---- OCRBlock ----

export function apiOCRBlockToDomain(dto: ApiOCRBlock): OCRBlock {
  const bbox = (dto.bbox ?? [0, 0, 0, 0]) as [number, number, number, number];
  return {
    id: dto.id,
    ocrJobId: dto.job_id ?? "",
    pageNumber: dto.page_number,
    bbox,
    text: dto.text_content,
    confidence: dto.confidence,
    requiresReview: dto.requires_review ?? false,
    reviewStatus: dto.review_status,
    reviewedBy: dto.reviewed_by ?? undefined,
    reviewedAt: dto.reviewed_at ?? undefined,
    isEdited: dto.edited_text != null,
    originalText: dto.original_text ?? undefined,
    processingTimeMs: dto.processing_time_ms ?? 0,
  };
}

// ---- Citation ----

export function apiCitationToDomain(dto: ApiCitation): Citation {
  return {
    documentId: dto.document_id,
    documentVersionId: dto.document_version_id,
    documentTitle: dto.title,
    pageNumber: dto.page_number,
    chunkId: dto.chunk_id,
    quote: dto.quote,
    score: dto.score,
    bbox: (dto.bbox ?? undefined) as [number, number, number, number] | undefined,
  };
}

// ---- Job ----

export function apiJobToDomain(dto: ApiJob): Job {
  return {
    id: dto.id,
    type: dto.type,
    status: dto.status,
    progress: dto.progress ?? 0,
    error: dto.error ?? undefined,
    startedAt: dto.started_at ?? undefined,
    finishedAt: dto.finished_at ?? undefined,
    createdAt: dto.created_at,
  };
}
