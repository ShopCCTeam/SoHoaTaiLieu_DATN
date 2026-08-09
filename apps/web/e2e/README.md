# E2E Tests

> Folder này chứa Playwright E2E test cho Next.js frontend.

## Quy tắc

- **Mock tất cả API call** bằng MSW (xem `.skills/webapp-testing/`). KHÔNG gọi BE thật trong CI.
- **Critical path**:
  - Login flow (với cookie-based auth từ BE).
  - Upload document (với 202 Accepted + poll job).
  - OCR review (canvas + bbox).
  - Search RAG.
  - Chat RAG.
- **Fixture**: mỗi test tự setup state, không phụ thuộc test khác.
- **Chạy local**:
  ```bash
  pnpm --filter web test:e2e
  ```
  Browser binary cần cài trước (1 lần):
  ```bash
  pnpm --filter web exec playwright install --with-deps chromium
  ```

## Cấu trúc đề xuất

```
e2e/
├── auth/
│   ├── login.spec.ts
│   └── refresh-token.spec.ts
├── documents/
│   ├── upload.spec.ts
│   └── review.spec.ts
├── search/
│   └── rag-search.spec.ts
└── chat/
    └── rag-chat.spec.ts
```

## Hiện trạng

- File `.gitkeep` chỉ để giữ folder. Test thật sẽ thêm ở phase sau.
