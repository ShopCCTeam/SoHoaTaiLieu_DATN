import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
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
} from "@/lib/api/types";

/**
 * Custom Query Hooks using apiClient.
 *
 * Mọi hook wrap `apiClient` (unwrap envelope) rồi qua mapper snake_case
 * → camelCase domain. Component chỉ nhận domain model.
 */

export function useDocuments(params?: {
  status?: string;
  type?: string;
  query?: string;
}) {
  const { token } = useAuthStore();
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.type) searchParams.set("type", params.type);
  if (params?.query) searchParams.set("query", params.query);

  const endpoint = `/documents${
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

export function useSearchRAG(query: string) {
  const { token } = useAuthStore();

  return useQuery({
    queryKey: ["search", query],
    queryFn: async () => {
      if (!query.trim()) return [];
      const raw = await apiClient<Array<{
        document: Parameters<typeof apiDocumentToDomain>[0];
        score: number;
        snippet: string;
        pageNumber: number;
      }>>(`/search?q=${encodeURIComponent(query)}`, {
        token: token || undefined,
      });
      return raw.map((r) => ({
        document: apiDocumentToDomain(r.document),
        score: r.score,
        snippet: r.snippet,
        pageNumber: r.pageNumber,
      }));
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
      }>("/chat/query", {
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
      >("/admin/users", { token: token || undefined });
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
      >("/admin/models", { token: token || undefined });
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
