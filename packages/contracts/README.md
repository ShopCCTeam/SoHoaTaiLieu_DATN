# packages/contracts — Shared FE/BE Types

> **Trạng thái**: scaffold. Sẽ code ở Phase 0 BE.

## Mục đích

Single source of truth cho TypeScript types dùng chung giữa Frontend và Backend.
Sinh tự động từ OpenAPI spec (`docs/api/openapi.yaml`) bằng `openapi-typescript`.

## Cấu trúc dự kiến

```
packages/contracts/
├── src/
│   ├── index.ts          # generated types
│   └── api-types.ts      # hand-curated types (Citation, Document, ...)
├── package.json
├── tsconfig.json
└── README.md
```

## Cài đặt (FE side)

Sau khi có package này, `apps/web/package.json` sẽ thêm:

```json
{
  "dependencies": {
    "@ctsv/contracts": "workspace:*"
  }
}
```

## Sinh types

```bash
pnpm --filter @ctsv/contracts generate
# tương đương: openapi-typescript ../../docs/api/openapi.yaml -o src/generated.ts
```
