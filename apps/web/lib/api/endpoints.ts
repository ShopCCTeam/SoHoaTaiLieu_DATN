export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: "/auth/login",
    ME: "/auth/me",
  },
  DOCUMENTS: {
    LIST: "/documents",
    DETAIL: (id: string) => `/documents/${id}`,
    UPLOAD: "/documents",
    CREATE_VERSION: (id: string) => `/documents/${id}/versions`,
    UPDATE_METADATA: (versionId: string) => `/document-versions/${versionId}/metadata`,
    TRIGGER_OCR: (versionId: string) => `/document-versions/${versionId}/ocr`,
    APPROVE: (versionId: string) => `/document-versions/${versionId}/approve`,
    INDEX_RAG: (versionId: string) => `/document-versions/${versionId}/index`,
  },
  OCR: {
    JOB_STATUS: (id: string) => `/ocr-jobs/${id}`,
    UPDATE_BLOCK: (id: string) => `/ocr-blocks/${id}`,
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
