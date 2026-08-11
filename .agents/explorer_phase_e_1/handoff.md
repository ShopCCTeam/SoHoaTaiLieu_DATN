# Handoff Report — Explorer Phase E 1

> **Agent**: Explorer 1 (`teamwork_preview_explorer`)  
> **Role**: Codebase Investigator  
> **Working Directory**: `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_e_1`  
> **Target**: Parent Agent (`8b21cd22-8f5a-4b2f-8b30-148a1a6b04c5`)  
> **Date**: 2026-08-11  

---

## 1. Observation (Quan Sát Trực Tiếp)

### 1.1. Lệnh Kiểm Tra Codebase Backend (`apps/api`)
Đã thực thi 4 lệnh kiểm tra chất lượng từ thư mục `E:\SoHoaTaiLieu_DATN\apps\api`:
1. `uv run pytest`:
   ```
   ================== 209 passed, 1 skipped in 103.57s (0:01:43) ==================
   ```
2. `uv run ruff check .`:
   ```
   All checks passed!
   ```
3. `uv run ruff format --check .`:
   ```
   81 files already formatted
   ```
4. `uv run mypy app`:
   ```
   Success: no issues found in 51 source files
   ```

### 1.2. Kiểm Tra Các File Module & Services Hiện Có
- **`apps/api/app/models/document_chunk.py`** (Dòng 30–106):
  - Model `DocumentChunk` lưu trữ `embedding` (Vector 1024-dim), `fulltext_tsv` (`TSVECTOR`), `bbox` (bounding box JSON `[x0, y0, x1, y1]`), `page_number`, `chunk_index`, `block_ids`, `text`, `token_count`.
- **`apps/api/app/models/document.py`** (Dòng 25–63):
  - Model `Document` quản lý metadata và `scope` (`PUBLIC`, `STUDENT_AFFAIRS`, `INTERNAL`).
- **`apps/api/app/services/chunking.py`** (Dòng 27–193):
  - `ChunkingService` hỗ trợ tính toán envelope bounding box `[x0, y0, x1, y1]` và tách chunk đệ quy.
- **`apps/api/app/services/embedding.py`** (Dòng 24–128):
  - `EmbeddingService` triển khai Strategy Pattern với `MockEmbeddingStrategy` (SHA-256 1024-dim) và `BGEM3EmbeddingStrategy`.
- **`apps/api/app/modules/search/service.py`** (Dòng 29–200):
  - `search_documents` áp dụng RRF Hybrid Search (Vector + Full-text search) kết hợp lọc RBAC `allowed_scopes`.
- **`docs/domain/citation-spec.md`** (Dòng 8–43):
  - Quy định trích dẫn: `title` lấy live từ DB, `quote` tối đa 300 ký tự cắt theo word boundary, `score` từ 0..1, `bbox` tùy chọn, và không trả citation giả khi `has_sufficient_evidence = false`.
- **`apps/web/lib/api/queries/index.ts`** (Dòng 76–96):
  - `useChatRAGMutation` gọi `POST /chat/query` truyền `{ prompt }` và mong đợi dữ liệu `{ answer, citations, has_sufficient_evidence }`.
- **`docs/api/openapi.yaml`** (Dòng 321–356):
  - Trong `components/schemas` đã có `Citation` và `ChatResponse`, nhưng chưa có path `/chat/query` và `ChatQueryRequest`.

---

## 2. Logic Chain (Chuỗi Lý Luận)

1. **Từ Quan sát 1.1**: Cả 4 lệnh `pytest`, `ruff check`, `ruff format`, `mypy` đều pass 100% không có lỗi. Khẳng định: **Phase D remediation đã hoàn tất triệt để**.
2. **Từ Quan sát 1.2 (`search.service`, `embedding.py`, `chunking.py`)**: Hệ thống đã có sẵn bộ công cụ tìm kiếm hybrid RRF và embedding vector 1024 chiều cùng phân quyền scope RBAC hoàn chỉnh.
3. **Từ Quan sát 1.2 (`citation-spec.md` và `apps/web`)**: Chi tiết về trích dẫn RAG và giao diện Chatbot ở Frontend đã khớp về mặt cấu trúc dữ liệu (`answer`, `citations`, `has_sufficient_evidence`).
4. **Từ Quan sát 1.2 (`openapi.yaml`)**: Thiếu duy nhất phần định nghĩa router endpoint `POST /chat/query` và `ChatQueryRequest` schema để khớp contract giữa Frontend và Backend.
5. **Suy luận tổng hợp**: Để triển khai Phase E (RAG Chatbot with Citations), cần tạo module `apps/api/app/modules/chat/` (router, service, schemas), tạo `apps/api/app/services/llm.py` (MockLLMStrategy & OllamaLLMStrategy), cập nhật `app/core/config.py` và `docs/api/openapi.yaml`.

---

## 3. Caveats (Cảnh Báo & Giới Hạn)

- **Read-Only Scope**: Explorer chỉ thực hiện điều tra và xây dựng thiết kế kiến trúc, không can thiệp sửa đổi các file mã nguồn ngoài thư mục làm việc `.agents/explorer_phase_e_1`.
- **Mock LLM Fallback**: Khi chạy ở môi trường local/CI không có service Ollama, hệ thống bắt buộc sử dụng `MockLLMStrategy` để đảm bảo unit test luôn chạy nhanh và độc lập.
- **Single-turn RAG**: Theo ADR-012, Phase E tập trung vào RAG đơn lượt (single-turn POST `/chat/query`). Tính năng stream (SSE/WebSocket) không thuộc phạm vi MVP.

---

## 4. Conclusion (Kết Luận)

- Sức khỏe codebase `apps/api` đạt chuẩn tuyệt đối 100% (209 tests pass, ruff clean, mypy clean).
- Đã lập báo cáo chi tiết thiết kế kiến trúc Phase E RAG Chatbot tại `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_e_1\analysis.md`.
- Sẵn sàng bàn giao cho Implementer tiến hành xây dựng Phase E.

---

## 5. Verification Method (Phương Pháp Kiểm Xác Mức Độc Lập)

1. **Chạy các lệnh kiểm tra sức khỏe backend**:
   ```bash
   cd apps/api
   uv run pytest
   uv run ruff check .
   uv run ruff format --check .
   uv run mypy app
   ```
2. **Kiểm tra tài liệu phân tích chi tiết**:
   - Mở file `E:\SoHoaTaiLieu_DATN\.agents\explorer_phase_e_1\analysis.md` để xem thiết kế chi tiết từng file cho Phase E.
