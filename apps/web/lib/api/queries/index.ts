import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { Document, User } from "@/lib/api/types";
import { useAuthStore } from "@/lib/auth/session";

/**
 * Custom Query Hooks using apiClient
 * Seamlessly switches between Next.js Mock Route Handlers and FastAPI Backend via NEXT_PUBLIC_API_MODE
 */

export function useDocuments(params?: { status?: string; type?: string; query?: string }) {
  const { token } = useAuthStore();
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.type) searchParams.set("type", params.type);
  if (params?.query) searchParams.set("query", params.query);

  const endpoint = `/documents${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;

  return useQuery({
    queryKey: ["documents", params],
    queryFn: async () => {
      const res = await apiClient<{ success: boolean; data: Document[]; total: number }>(
        endpoint,
        { token: token || undefined }
      );
      return res.data;
    },
  });
}

export function useSearchRAG(query: string) {
  const { token } = useAuthStore();

  return useQuery({
    queryKey: ["search", query],
    queryFn: async () => {
      if (!query.trim()) return [];
      const res = await apiClient<{ success: boolean; data: any[] }>(
        `/search?q=${encodeURIComponent(query)}`,
        { token: token || undefined }
      );
      return res.data;
    },
    enabled: Boolean(query.trim()),
  });
}

export function useChatRAGMutation() {
  const { token } = useAuthStore();

  return useMutation({
    mutationFn: async (prompt: string) => {
      const res = await apiClient<{ success: boolean; data: { answer: string; citations: any[] } }>(
        "/chat/query",
        {
          method: "POST",
          body: JSON.stringify({ prompt }),
          token: token || undefined,
        }
      );
      return res.data;
    },
  });
}

export function useAdminUsers() {
  const { token } = useAuthStore();

  return useQuery({
    queryKey: ["admin", "users"],
    queryFn: async () => {
      const res = await apiClient<{ success: boolean; data: User[] }>(
        "/admin/users",
        { token: token || undefined }
      );
      return res.data;
    },
  });
}

export function useAdminModels() {
  const { token } = useAuthStore();

  return useQuery({
    queryKey: ["admin", "models"],
    queryFn: async () => {
      const res = await apiClient<{ success: boolean; data: any[] }>(
        "/admin/models",
        { token: token || undefined }
      );
      return res.data;
    },
  });
}
