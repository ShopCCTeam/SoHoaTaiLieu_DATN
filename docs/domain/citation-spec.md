# Citation Spec — Trích Dẫn RAG

> File này là nguồn chuẩn cho **cấu trúc citation** mà Backend phải trả về và Frontend hiển thị.
> Frontend **không được** tự suy đoán cấu trúc; phải khớp với schema này.

## Schema (JSON)

```typescript
interface Citation {
  document_id: string;              // UUID
  document_version_id: string;      // UUID
  title: string;                    // Tiêu đề tài liệu (đã resolve, không phải ID)
  page_number: number;              // 1-based
  chunk_id: string;                 // UUID của chunk embedding
  quote: string;                    // Trích nguyên văn đoạn text được cite
  score: number;                    // 0..1, similarity score
  bbox?: [number, number, number, number]; // Optional: [x_min, y_min, x_max, y_max] trong PDF coordinate
}
```

## Quy tắc BE

1. **`title` phải là title hiện tại** của document (resolve tại query time), không phải title tại thời điểm embed.
2. **`page_number`** đếm theo trang PDF gốc (1-based). Nếu chunk nằm giữa 2 trang, lấy trang bắt đầu.
3. **`quote`** giới hạn **300 ký tự** (cắt ở word boundary, thêm "..." nếu bị cắt).
4. **`score`** là điểm cuối cùng sau rerank (nếu có), không phải raw vector score.
5. **`bbox`** chỉ có khi chunk có nguồn gốc OCR block; null nếu chunk từ text-extracted PDF.
6. Mỗi `citation` phải có **`document_id`** mà user hiện tại **được phép đọc** — kiểm tra scope ở retrieval, không phải sau khi search.

## Quy tắc FE

1. Khi click vào citation chip, điều hướng: `/documents/${citation.document_id}?page=${citation.page_number}&highlight=${citation.chunk_id}`.
2. Nếu user click vào citation mà mất quyền (VD: staff đổi role student), backend trả 403 — FE hiển thị toast "Bạn không có quyền truy cập tài liệu này".
3. Hiển thị `score` với 2 chữ số thập phân (VD: 0.94).
4. Nếu `has_sufficient_evidence = false`, **ẩn citation chip** và hiển thị "Không tìm thấy thông tin phù hợp" (không tạo citation giả).

## Anti-pattern (cấm)

- ❌ Trả citation nhưng `score = 0.0` (gây hiểu nhầm).
- ❌ Trả citation khi `has_sufficient_evidence = false`.
- ❌ Để Frontend tự build citation từ search result (citation **phải** đến từ chat endpoint).
- ❌ Truncate `quote` cắt giữa câu (phải cắt ở word/sentence boundary).
