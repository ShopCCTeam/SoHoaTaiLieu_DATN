import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient, isApiMockMode } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";
import { useAuthStore } from "@/lib/auth/session";
import {
  apiDocumentToDomain,
  apiUserToDomain,
  apiCitationToDomain,
} from "@/lib/api/mappers";
import type {
  Document,
  Citation,
  User,
  ChatAnswerData,
  Job,
  SearchResult,
} from "@/lib/api/types";
import type {
  SearchResponse as ApiSearchResponse,
  SearchResultItem as ApiSearchResultItem,
} from "@ctsv/contracts";

/**
 * Custom Query Hooks using apiClient.
 *
 * Mọi hook wrap `apiClient` (unwrap envelope) rồi qua mapper snake_case
 * → camelCase domain. Component chỉ nhận domain model.
 */

export interface DocumentQueryParams {
  status?: string;
  type?: string;
  q?: string;
  keyword?: string;
  tags?: string[];
}

export interface SearchQueryParams {
  keyword?: string;
  tags?: string[];
}

function appendMetadataFilters(searchParams: URLSearchParams, params?: SearchQueryParams): void {
  if (params?.keyword) searchParams.set("keyword", params.keyword);
  for (const tag of params?.tags || []) {
    if (tag.trim()) searchParams.append("tags", tag.trim());
  }
}

export function useDocuments(params?: DocumentQueryParams) {
  const { token } = useAuthStore();
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.type) searchParams.set("type", params.type);
  if (params?.q) searchParams.set("q", params.q);
  appendMetadataFilters(searchParams, params);

  const endpoint = `${API_ENDPOINTS.DOCUMENTS.LIST}${
    searchParams.toString() ? `?${searchParams.toString()}` : ""
  }`;

  return useQuery({
    queryKey: ["documents", params],
    queryFn: async () => {
      // apiClient unwrap envelope, trả raw Document[] (snake_case) từ backend.
      const raw = await apiClient<
        Array<Parameters<typeof apiDocumentToDomain>[0]>
      >(endpoint, { token: token || undefined });
      return raw.map(apiDocumentToDomain) as Document[];
    },
  });
}

export function useUpdateMetadataMutation() {
  const { token } = useAuthStore();

  return useMutation({
    mutationFn: async ({
      documentId,
      versionId,
      changeSummary,
    }: {
      documentId: string;
      versionId: string;
      changeSummary?: string;
    }) => {
      const endpoint = API_ENDPOINTS.DOCUMENTS.UPDATE_METADATA(
        documentId,
        versionId
      );
      return apiClient(endpoint, {
        method: "PATCH",
        body: JSON.stringify({ change_summary: changeSummary }),
        token: token || undefined,
      });
    },
  });
}

export function useTriggerOCRMutation() {
  const { token } = useAuthStore();

  return useMutation({
    mutationFn: async ({
      documentId,
      versionId,
      idempotencyKey,
    }: {
      documentId: string;
      versionId: string;
      idempotencyKey?: string;
    }) => {
      const endpoint = API_ENDPOINTS.DOCUMENTS.TRIGGER_OCR(
        documentId,
        versionId
      );
      const headers: Record<string, string> = {};
      if (idempotencyKey) {
        headers["Idempotency-Key"] = idempotencyKey;
      }
      return apiClient<{ job_id: string; status: string }>(endpoint, {
        method: "POST",
        headers,
        token: token || undefined,
      });
    },
  });
}

export function useApproveVersionMutation() {
  const { token } = useAuthStore();

  return useMutation({
    mutationFn: async ({
      documentId,
      versionId,
    }: {
      documentId: string;
      versionId: string;
    }) => {
      const endpoint = API_ENDPOINTS.DOCUMENTS.APPROVE(
        documentId,
        versionId
      );
      return apiClient(endpoint, {
        method: "POST",
        token: token || undefined,
      });
    },
  });
}

export function useJobStatusQuery(jobId: string) {
  const { token } = useAuthStore();

  return useQuery({
    queryKey: ["job", jobId],
    queryFn: async () => {
      const endpoint = API_ENDPOINTS.OCR.JOB_STATUS(jobId);
      return apiClient<Job>(endpoint, { token: token || undefined });
    },
    enabled: Boolean(jobId),
  });
}

export function useUpdateBlockMutation() {
  const { token } = useAuthStore();

  return useMutation({
    mutationFn: async (params: {
      documentId?: string;
      versionId?: string;
      jobId?: string;
      blockId: string;
      text?: string;
      reviewStatus?: string;
    }) => {
      const endpoint =
        params.documentId && params.versionId
          ? API_ENDPOINTS.DOCUMENTS.UPDATE_BLOCK(
              params.documentId,
              params.versionId,
              params.blockId
            )
          : API_ENDPOINTS.OCR.UPDATE_BLOCK(
              params.jobId || "default",
              params.blockId
            );
      return apiClient(endpoint, {
        method: "PATCH",
        body: JSON.stringify({
          text: params.text,
          review_status: params.reviewStatus,
        }),
        token: token || undefined,
      });
    },
  });
}

interface MockSearchResult {
  document: Parameters<typeof apiDocumentToDomain>[0];
  score: number;
  snippet: string;
  pageNumber: number;
}

function mapSearchResult(item: ApiSearchResultItem): SearchResult {
  return {
    chunkId: item.chunk_id,
    documentId: item.document_id,
    documentTitle: item.document_title,
    documentScope: item.document_scope,
    documentType: item.document_type,
    pageNumber: item.page_number,
    text: item.text,
    score: item.score,
    vectorScore: item.vector_score,
    fulltextScore: item.fulltext_score,
  };
}

function mapMockSearchResult(result: MockSearchResult): SearchResult {
  const document = apiDocumentToDomain(result.document);
  return {
    chunkId: `demo-${document.id}-${result.pageNumber}`,
    documentId: document.id,
    documentTitle: document.title,
    documentScope: document.scope,
    documentType: document.type,
    pageNumber: result.pageNumber,
    text: result.snippet,
    score: result.score,
    vectorScore: result.score,
    fulltextScore: null,
  };
}

export function useSearchRAG(query: string, params?: SearchQueryParams) {
  const { token } = useAuthStore();

  return useQuery({
    queryKey: ["search", query, params],
    queryFn: async () => {
      if (!query.trim()) return [];
      const searchParams = new URLSearchParams({ q: query });
      appendMetadataFilters(searchParams, params);
      const endpoint = `${API_ENDPOINTS.SEARCH.QUERY}?${searchParams.toString()}`;

      if (isApiMockMode()) {
        const raw = await apiClient<MockSearchResult[]>(endpoint, {
          token: token || undefined,
        });
        return raw.map(mapMockSearchResult);
      }

      const raw = await apiClient<ApiSearchResponse>(endpoint, {
        token: token || undefined,
      });
      return raw.items.map(mapSearchResult);
    },
    enabled: Boolean(query.trim()),
  });
}

export function useChatRAGMutation() {
  const { token } = useAuthStore();

  return useMutation({
    mutationFn: async (prompt: string) => {
      const raw = await apiClient<{
        answer: string;
        citations: Parameters<typeof apiCitationToDomain>[0][];
        has_sufficient_evidence: boolean;
      }>(API_ENDPOINTS.CHAT.QUERY, {
        method: "POST",
        body: JSON.stringify({ prompt }),
        token: token || undefined,
      });
      return {
        answer: raw.answer,
        citations: raw.citations.map(apiCitationToDomain),
        hasSufficientEvidence: raw.has_sufficient_evidence,
      } as ChatAnswerData;
    },
  });
}

export function useAdminUsers() {
  const { token } = useAuthStore();

  return useQuery({
    queryKey: ["admin", "users"],
    queryFn: async () => {
      const raw = await apiClient<
        Array<Parameters<typeof apiUserToDomain>[0]>
      >(API_ENDPOINTS.ADMIN.USERS, { token: token || undefined });
      return raw.map(apiUserToDomain) as User[];
    },
  });
}

export function useAdminModels() {
  const { token } = useAuthStore();

  return useQuery({
    queryKey: ["admin", "models"],
    queryFn: async () => {
      const raw = await apiClient<
        Array<{
          id: string;
          name: string;
          version: string;
          is_active: boolean;
          accuracy_score: number;
        }>
      >(API_ENDPOINTS.ADMIN.MODEL_VERSIONS, { token: token || undefined });
      return raw.map((m) => ({
        id: m.id,
        name: m.name,
        version: m.version,
        isActive: m.is_active,
        accuracy: m.accuracy_score,
      }));
    },
  });
}

