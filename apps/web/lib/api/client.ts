import { ApiError, type ProblemDetail } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
const IS_MOCK = process.env.NEXT_PUBLIC_API_MODE !== "live";

interface RequestOptions extends RequestInit {
  token?: string;
}

interface ApiResponseEnvelope<T> {
  success: true;
  data: T;
  total?: number;
  page?: number;
  limit?: number;
}

function isProblemDetail(value: unknown): value is ProblemDetail {
  return (
    typeof value === "object" &&
    value !== null &&
    "type" in value &&
    "title" in value &&
    "status" in value &&
    "code" in value
  );
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<T> {
  const { token, headers, ...customConfig } = options;

  // In Next.js mock mode, if route starts with /api, call local Next.js route handler
  const url =
    IS_MOCK && endpoint.startsWith("/")
      ? `/api${endpoint}`
      : `${BASE_URL}${endpoint}`;

  const defaultHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (token) {
    defaultHeaders["Authorization"] = `Bearer ${token}`;
  }

  const config: RequestInit = {
    method: options.method || "GET",
    headers: {
      ...defaultHeaders,
      ...headers,
    },
    credentials: "include", // gửi HttpOnly cookie cho mock/BE
    ...customConfig,
  };

  let response: Response;
  try {
    response = await fetch(url, config);
  } catch (err) {
    throw new ApiError({
      type: "http://localhost:3000/problems/network",
      title: "Lỗi mạng",
      status: 0,
      detail: (err as Error).message,
      code: "INTERNAL",
      requestId: "n/a",
    });
  }

  const contentType = response.headers.get("Content-Type") || "";
  const isProblem = contentType.includes("application/problem+json");
  const raw = await response.json().catch(() => ({}));

  // RFC 7807 hoặc envelope error shape —{success: false, ...} — đều ném ApiError.
  if (isProblem && isProblemDetail(raw)) {
    throw new ApiError(raw);
  }
  if (raw && typeof raw === "object" && "success" in raw && !raw.success) {
    // Legacy mock có thể trả {success: false, message: ...}.
    if (isProblemDetail(raw)) throw new ApiError(raw);
    throw new ApiError({
      type: "http://localhost:3000/problems/internal",
      title: "Lỗi hệ thống",
      status: response.status,
      detail: (raw as { message?: string }).message,
      code: "INTERNAL",
      requestId: "n/a",
    });
  }

  if (!response.ok) {
    throw new ApiError({
      type: "http://localhost:3000/problems/internal",
      title: `HTTP ${response.status}`,
      status: response.status,
      detail: typeof raw === "object" ? JSON.stringify(raw) : String(raw),
      code: "INTERNAL",
      requestId: "n/a",
    });
  }

  // Success: unwrap envelope {success: true, data, ...} → trả về data.
  // Trường hợp backend trả raw (edge case) → trả nguyên raw.
  if (raw && typeof raw === "object" && "success" in raw && "data" in raw) {
    return (raw as ApiResponseEnvelope<T>).data;
  }
  return raw as T;
}
