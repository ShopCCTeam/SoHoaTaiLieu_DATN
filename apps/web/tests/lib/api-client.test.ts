import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

describe("apiClient — routing mock vs live mode", () => {
  const originalEnv = { ...process.env };
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockFetch = vi.fn();
    global.fetch = mockFetch as unknown as typeof fetch;
  });

  afterEach(() => {
    process.env = { ...originalEnv };
    vi.resetModules();
  });

  it("khi NEXT_PUBLIC_API_MODE=mock: prepend /api cho endpoint", async () => {
    process.env.NEXT_PUBLIC_API_MODE = "mock";
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000/api/v1";

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: [] }),
      headers: new Headers(),
    } as Response);

    const { apiClient } = await import("@/lib/api/client");
    await apiClient("/documents");

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/documents",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          Accept: "application/json",
        }) as Record<string, string>,
      })
    );
  });

  it("khi NEXT_PUBLIC_API_MODE=live: dùng BASE_URL đầy đủ", async () => {
    process.env.NEXT_PUBLIC_API_MODE = "live";
    process.env.NEXT_PUBLIC_API_BASE_URL = "https://api.example.edu.vn/api/v1";

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: [] }),
      headers: new Headers(),
    } as Response);

    const { apiClient } = await import("@/lib/api/client");
    await apiClient("/documents");

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.example.edu.vn/api/v1/documents",
      expect.any(Object)
    );
  });

  it("thêm Authorization header khi có token", async () => {
    process.env.NEXT_PUBLIC_API_MODE = "mock";

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: { id: "u1" } }),
      headers: new Headers(),
    } as Response);

    const { apiClient } = await import("@/lib/api/client");
    await apiClient("/auth/me", { token: "mock_jwt_admin_2026" });

    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/auth/me",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer mock_jwt_admin_2026",
        }) as Record<string, string>,
      })
    );
  });

  it("throw ApiError với statusCode khi response không OK", async () => {
    process.env.NEXT_PUBLIC_API_MODE = "mock";

    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 403,
      json: async () => ({ success: false, code: "FORBIDDEN", message: "Cấm truy cập" }),
      headers: new Headers(),
    } as Response);

    const { apiClient } = await import("@/lib/api/client");
    const { ApiError } = await import("@/lib/api/types");

    let caught: unknown;
    try {
      await apiClient("/admin/users");
    } catch (e) {
      caught = e;
    }

    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as InstanceType<typeof ApiError>).statusCode).toBe(403);
  });

  it("throw ApiError(500) khi fetch fail mạng", async () => {
    process.env.NEXT_PUBLIC_API_MODE = "mock";

    mockFetch.mockRejectedValueOnce(new Error("Network request failed"));

    const { apiClient } = await import("@/lib/api/client");
    const { ApiError } = await import("@/lib/api/types");

    let caught: unknown;
    try {
      await apiClient("/documents");
    } catch (e) {
      caught = e;
    }

    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as InstanceType<typeof ApiError>).code).toBe("INTERNAL");
  });
});