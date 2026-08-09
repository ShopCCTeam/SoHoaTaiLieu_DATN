export type UserRole = "admin" | "staff" | "student";

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  scopes: string[];
  avatarUrl?: string;
  department?: string;
  status?: string;
}

export type DocumentType =
  | "QUY_CHE"
  | "QUY_DINH"
  | "THONG_BAO"
  | "QUYET_DINH"
  | "HUONG_DAN"
  | "MAU_DON";

export type DocumentStatus =
  | "draft"
  | "processing"
  | "review"
  | "approved"
  | "expired"
  | "failed";

export interface Document {
  id: string;
  title: string;
  type: DocumentType;
  status: DocumentStatus;
  createdAt: string;
  updatedAt: string;
  latestVersion: number;
  scope: string;
  codeNumber?: string;
  issuingBody?: string;
  effectiveFrom?: string;
  effectiveTo?: string;
  tags: string[];
  authorId: string;
  fileUrl?: string;
  fileSize?: number;
  pageCount?: number;
}

export interface DocumentVersion {
  id: string;
  documentId: string;
  versionNumber: number;
  status: DocumentStatus;
  createdAt: string;
  createdBy: string;
  effectiveFrom?: string;
  effectiveTo?: string;
  fileUrl: string;
  fileSize: number;
  checksum: string;
  changeSummary?: string;
  supersedesVersionId?: string;
  supersededByVersionId?: string;
}

export interface OCRBlock {
  id: string;
  pageNumber: number;
  bbox: [number, number, number, number]; // [x, y, width, height] percentage or normalized 0-100
  text: string;
  confidence: number;
  isEdited: boolean;
  editedBy?: string;
  editedAt?: string;
  originalText?: string;
}

export interface Citation {
  documentId: string;
  documentTitle: string;
  documentVersionId: string;
  pageNumber: number;
  quote: string;
  score: number;
  codeNumber?: string;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  content: string;
  timestamp: string;
  citations?: Citation[];
  isStreaming?: boolean;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
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
  accuracy: number;
  size: string;
  provider: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  statusCode?: number;
}
