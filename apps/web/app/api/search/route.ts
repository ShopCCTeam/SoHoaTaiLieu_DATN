import { NextRequest, NextResponse } from "next/server";
import { requireMockUser } from "@/lib/auth/server-helper";
import { problemResponse } from "@/lib/api/problem-response";
import { MOCK_DOCUMENTS } from "@/lib/mocks/fixtures";

export const dynamic = "force-dynamic";

/* DEMO ONLY — mirrors T07 query semantics; FastAPI remains the live security boundary. */

export async function GET(request: NextRequest) {
  const auth = requireMockUser(request);
  if ("problem" in auth) {
    return problemResponse(
      auth.problem.status,
      auth.problem.code,
      auth.problem.title,
      auth.problem.detail,
      auth.problem.requestId,
    );
  }

  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q")?.trim().toLowerCase() || "";
  const keyword = searchParams.get("keyword")?.trim().toLowerCase() || "";
  const tags = searchParams
    .getAll("tags")
    .map((tag) => tag.trim().toLowerCase())
    .filter(Boolean);

  const visibleDocuments = MOCK_DOCUMENTS.filter((document) => {
    if (auth.user.role === "student" && document.scope === "INTERNAL") {
      return false;
    }

    const searchableMetadata = [
      document.title,
      document.codeNumber || "",
      document.issuingBody || "",
      ...document.tags,
    ]
      .join(" ")
      .toLowerCase();
    const documentTags = new Set(document.tags.map((tag) => tag.toLowerCase()));

    return (
      (!q || searchableMetadata.includes(q)) &&
      (!keyword || searchableMetadata.includes(keyword)) &&
      tags.every((tag) => documentTags.has(tag))
    );
  });

  const results = visibleDocuments.map((document, index) => ({
    document,
    score: Number((0.94 - index * 0.04).toFixed(2)),
    snippet: `Kết quả DEMO cho ${document.title}.`,
    pageNumber: 1,
  }));

  return NextResponse.json({
    success: true,
    data: results,
    total: results.length,
  });
}
