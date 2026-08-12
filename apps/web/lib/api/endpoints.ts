export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: "/auth/login",
    ME: "/auth/me",
    REFRESH: "/auth/refresh",
    LOGOUT: "/auth/logout",
  },
  DOCUMENTS: {
    LIST: "/documents",
    DETAIL: (id: string) => `/documents/${id}`,
    UPLOAD: "/documents",
    CREATE_VERSION: (id: string) => `/documents/${id}/versions`,
    UPDATE_METADATA: (documentId: string, versionId: string) =>
      `/documents/${documentId}/versions/${versionId}/metadata`,
    TRIGGER_OCR: (documentId: string, versionId: string) =>
      `/documents/${documentId}/versions/${versionId}/ocr`,
    APPROVE: (documentId: string, versionId: string) =>
      `/documents/${documentId}/versions/${versionId}/approve`,
    INDEX_RAG: (documentId: string, versionId: string) =>
      `/documents/${documentId}/versions/${versionId}/index`,
    OCR_DETAIL: (documentId: string, versionId: string) =>
      `/documents/${documentId}/versions/${versionId}/ocr`,
    OCR_PAGE_IMAGE: (documentId: string, versionId: string, page: number) =>
      `/documents/${documentId}/versions/${versionId}/ocr/pages/${page}/image`,
    UPDATE_BLOCK: (documentId: string, versionId: string, blockId: string) =>
      `/documents/${documentId}/versions/${versionId}/ocr/blocks/${blockId}`,
    BATCH_REVIEW: (documentId: string, versionId: string) =>
      `/documents/${documentId}/versions/${versionId}/ocr/batch-review`,
  },
  OCR: {
    JOB_STATUS: (jobId: string) => `/jobs/${jobId}`,
    UPDATE_BLOCK: (jobId: string, blockId: string) => `/jobs/${jobId}/blocks/${blockId}`,
  },
  JOBS: {
    STATUS: (jobId: string) => `/jobs/${jobId}`,
    CANCEL: (jobId: string) => `/jobs/${jobId}/cancel`,
    APPROVE: (jobId: string) => `/jobs/${jobId}/approve`,
    UPDATE_BLOCK: (jobId: string, blockId: string) => `/jobs/${jobId}/blocks/${blockId}`,
  },
  SEARCH: {
    QUERY: "/search",
  },
  CHAT: {
    QUERY: "/chat/query",
    FEEDBACK: "/feedback",
  },
  ADMIN: {
    TRAINING_RUNS: "/admin/training-runs",
    MODEL_VERSIONS: "/admin/model-versions",
    ACTIVATE_MODEL: (id: string) => `/admin/model-versions/${id}/activate`,
    USERS: "/admin/users",
  },
};

