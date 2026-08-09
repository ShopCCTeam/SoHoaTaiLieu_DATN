# Known Issues / Tech Debt

Theo dõi các hạn chế, lỗi đã biết và nợ kỹ thuật cần xử lý.

## Phase 0 — Foundation

- [ ] Chưa có `apps/api/` (BE skeleton) — sẽ tạo ở lượt Phase 0 tiếp theo.
- [ ] Chưa có docker-compose — sẽ tạo cùng Phase 0.
- [ ] Chưa có Alembic / migration — sẽ tạo ở Phase 1.
- [ ] Chưa có CI — sẽ tạo ở Phase 10.
- [ ] OCR-medical-receipt skill (`ocr_medical_receipt_extractor`) fail cài do path encode sai — không ảnh hưởng, có thể bỏ qua.

## FE (đã cài bởi FE agent)

- [ ] Login hiện dùng Next.js route handler mock (`/api/auth/login`) — sẽ thay bằng backend thật ở Phase 1.
- [ ] Documents list hiện dùng fixture in-memory — sẽ nối API thật ở Phase 2.

## Cross-cutting

- [ ] Chưa định nghĩa ENV contract giữa FE ↔ BE (chờ Phase 0 BE).
- [ ] Chưa có shared package `packages/shared/` cho schemas DTO và permission matrix — sẽ tạo ở Phase 0.
- [ ] Cần xác nhận LLM local (Ollama) chạy ổn trên máy user trước khi vào Phase 8.

## Tài nguyên

- [ ] Chưa có dữ liệu `data/raw/*.pdf` thật — cần user cung cấp ~200 PDF để bắt đầu Phase 3.
- [ ] Chưa có infrastructure ML (GPU/CPU) — sẽ đánh giá ở Phase 4.
