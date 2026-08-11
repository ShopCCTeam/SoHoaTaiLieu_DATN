import { describe, it, expect } from "vitest";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

describe("API_ENDPOINTS — path builders", () => {
  it("trả đúng đường dẫn UPDATE_METADATA với documentId và versionId", () => {
    expect(API_ENDPOINTS.DOCUMENTS.UPDATE_METADATA("doc_123", "ver_456")).toBe(
      "/documents/doc_123/versions/ver_456/metadata"
    );
  });

  it("trả đúng đường dẫn TRIGGER_OCR với documentId và versionId", () => {
    expect(API_ENDPOINTS.DOCUMENTS.TRIGGER_OCR("doc_123", "ver_456")).toBe(
      "/documents/doc_123/versions/ver_456/ocr"
    );
  });

  it("trả đúng đường dẫn APPROVE cho document version và job", () => {
    expect(API_ENDPOINTS.DOCUMENTS.APPROVE("doc_123", "ver_456")).toBe(
      "/documents/doc_123/versions/ver_456/approve"
    );
    expect(API_ENDPOINTS.JOBS.APPROVE("job_789")).toBe(
      "/jobs/job_789/approve"
    );
  });

  it("trả đúng đường dẫn OCR JOB_STATUS với jobId", () => {
    expect(API_ENDPOINTS.OCR.JOB_STATUS("job_789")).toBe("/jobs/job_789");
    expect(API_ENDPOINTS.JOBS.STATUS("job_789")).toBe("/jobs/job_789");
  });

  it("trả đúng đường dẫn UPDATE_BLOCK cho job và document version", () => {
    expect(API_ENDPOINTS.OCR.UPDATE_BLOCK("job_789", "blk_001")).toBe(
      "/jobs/job_789/blocks/blk_001"
    );
    expect(
      API_ENDPOINTS.DOCUMENTS.UPDATE_BLOCK("doc_123", "ver_456", "blk_001")
    ).toBe("/documents/doc_123/versions/ver_456/ocr/blocks/blk_001");
  });
});
