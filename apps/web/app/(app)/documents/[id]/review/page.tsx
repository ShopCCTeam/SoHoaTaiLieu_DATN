"use client";

import React from "react";
import Link from "next/link";
import { notFound, useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import type {
  Document as ApiDocument,
  DocumentVersion as ApiDocumentVersion,
  OCRBlock as ApiOCRBlock,
  OCRPage as ApiOCRPage,
} from "@ctsv/contracts";
import { MOCK_DOCUMENTS, MOCK_OCR_BLOCKS } from "@/lib/mocks/fixtures";
import { useAuthStore } from "@/lib/auth/session";
import { apiClient, isApiMockMode } from "@/lib/api/client";
import { API_ENDPOINTS } from "@/lib/api/endpoints";
import { apiOCRBlockToDomain, apiOCRPageToDomain } from "@/lib/api/mappers";
import { OCRReviewPane } from "@/components/ocr/ocr-review-pane";
import { AlertTriangle, ArrowLeft, Sparkles } from "lucide-react";

type DocumentDetailDto = ApiDocument & { versions: ApiDocumentVersion[] };
type OCRDetailDto = {
  version_id: string;
  pages: ApiOCRPage[];
  blocks: ApiOCRBlock[];
};

type ReviewData = {
  title: string;
  versionId: string;
  pages: ReturnType<typeof apiOCRPageToDomain>[];
  blocks: ReturnType<typeof apiOCRBlockToDomain>[];
};

export default function DocumentOCRReviewPage() {
  const params = useParams();
  const rawId = params?.id;
  const docId = Array.isArray(rawId) ? rawId[0] : (rawId as string);
  const token = useAuthStore((state) => state.token);
  const mockMode = isApiMockMode();

  const reviewQuery = useQuery({
    queryKey: ["ocr-review", docId],
    enabled: Boolean(docId && token) && !mockMode,
    queryFn: async (): Promise<ReviewData> => {
      const document = await apiClient<DocumentDetailDto>(API_ENDPOINTS.DOCUMENTS.DETAIL(docId), {
        token: token ?? undefined,
      });
      const latestVersion = [...document.versions].sort(
        (left, right) => right.version_number - left.version_number,
      )[0];
      if (!latestVersion) {
        throw new Error("Tài liệu chưa có phiên bản để duyệt OCR.");
      }
      const ocrDetail = await apiClient<OCRDetailDto>(
        API_ENDPOINTS.DOCUMENTS.OCR_DETAIL(docId, latestVersion.id),
        { token: token ?? undefined },
      );
      return {
        title: document.title,
        versionId: ocrDetail.version_id,
        pages: ocrDetail.pages.map(apiOCRPageToDomain),
        blocks: ocrDetail.blocks.map(apiOCRBlockToDomain),
      };
    },
  });

  const mockDocument = MOCK_DOCUMENTS.find((document) => document.id === docId);
  if (mockMode && !mockDocument) {
    notFound();
  }

  if (!mockMode && reviewQuery.isPending) {
    return <p className="text-sm text-muted-foreground">Đang tải dữ liệu duyệt OCR…</p>;
  }

  if (!mockMode && reviewQuery.isError) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
        <AlertTriangle className="mb-2 h-5 w-5" />
        Không thể tải dữ liệu duyệt OCR. Vui lòng kiểm tra quyền truy cập hoặc thử lại.
      </div>
    );
  }

  const reviewData = reviewQuery.data;
  const documentTitle = mockMode ? mockDocument!.title : reviewData!.title;
  const blocks = mockMode ? MOCK_OCR_BLOCKS[docId] || MOCK_OCR_BLOCKS.doc_02 : reviewData!.blocks;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 glass-panel p-6 rounded-3xl border border-primary-200/80 shadow-rose-subtle">
        <div className="flex items-center gap-4">
          <Link
            href={`/documents/${docId}`}
            className="p-2.5 rounded-2xl bg-white/80 dark:bg-slate-900 border border-primary-200 text-slate-700 hover:bg-primary-100 transition-colors"
            title="Quay lại chi tiết văn bản"
            aria-label="Quay lại chi tiết văn bản"
          >
            <ArrowLeft className="w-5 h-5 stroke-current" />
          </Link>
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[11px] font-bold mb-1">
              <Sparkles className="w-3.5 h-3.5 stroke-current text-amber-600" />
              <span>Chế độ hiệu chỉnh OCR BBox</span>
            </div>
            <h1 className="text-xl font-black text-slate-900 dark:text-white tracking-tight">
              {documentTitle}
            </h1>
          </div>
        </div>
      </div>

      <OCRReviewPane
        documentTitle={documentTitle}
        initialBlocks={blocks}
        documentId={mockMode ? undefined : docId}
        versionId={mockMode ? undefined : reviewData!.versionId}
        pages={mockMode ? undefined : reviewData!.pages}
        authToken={mockMode ? undefined : token}
      />
    </div>
  );
}
