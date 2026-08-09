# Document Lifecycle — Vòng Đời Tài Liệu

> File này định nghĩa state machine cho **Document**, **DocumentVersion**, **Processing Job** và **Index Status**.
> Tách 4 trạng thái để tránh "god status" — mỗi lifecycle chỉ phản ánh đúng concern của nó.

---

## 1. Document status

Trạng thái ở cấp tài liệu (theo `code_number` / `issuing_body`), không phụ thuộc phiên bản.

```
                create
                  │
                  ▼
              ┌───────┐
              │ DRAFT │  ← staff vừa upload, chưa review
              └───┬───┘
                  │ submit_for_review
                  ▼
          ┌──────────────┐
          │ UNDER_REVIEW │  ← staff/admin đang review metadata
          └──────┬───────┘
       approve  │  │ reject
                ▼  ▼
        ┌──────────┐  (back to DRAFT, có comment)
        │ APPROVED │
        └────┬─────┘
             │ archive
             ▼
        ┌──────────┐
        │ ARCHIVED │  ← vẫn xem được nhưng không sửa, không tạo version mới
        └──────────┘
```

### Quy tắc chuyển trạng thái

| From | To | Action | Permission |
|---|---|---|---|
| (none) | `DRAFT` | `POST /documents` | staff/admin |
| `DRAFT` | `UNDER_REVIEW` | `POST /documents/{id}/submit-review` | staff/admin |
| `UNDER_REVIEW` | `APPROVED` | `POST /documents/{id}/versions/{vid}/approve` | staff/admin |
| `UNDER_REVIEW` | `DRAFT` | `POST /documents/{id}/reject` (kèm comment) | staff/admin |
| `APPROVED` | `ARCHIVED` | `POST /documents/{id}/archive` | staff/admin |
| `ARCHIVED` | `APPROVED` | `POST /documents/{id}/restore` | admin |

---

## 2. DocumentVersion status

Mỗi version có status riêng (có thể khác document tổng). VD: document APPROVED nhưng có version cũ DRAFT.

```
       supersede or upload
              │
              ▼
         ┌───────┐
         │ DRAFT │
         └───────┘

  (status chỉ thay đổi khi approve; version cũ giữ nguyên status của nó)
```

| Action | Tác động |
|---|---|
| `POST /documents/{id}/versions` (upload mới) | Tạo version mới với `status=DRAFT` |
| `POST /documents/{id}/versions/{vid}/approve` | Set version → `APPROVED` |
| Soft delete version | Set `deleted_at` (không xoá thật) |

### Quy tắc

- Approve version **chỉ** khi `ocr_status = SUCCEEDED` (nếu version yêu cầu OCR).
- Approve version **chỉ** khi không còn `ocr_block.is_edited == false` với `confidence < 0.9`.
- Sau khi version `APPROVED`, **không được sửa metadata** — phải upload version mới.

---

## 3. Processing Job status

Áp dụng cho **OCR**, **Embedding**, **Indexing**, **Reindex**.

```
                  enqueue
                    │
                    ▼
                ┌────────┐
                │ QUEUED │
                └────┬───┘
              worker pick
                    ▼
              ┌────────────┐
              │ PROCESSING │  ← progress: 0..100
              └──────┬─────┘
               done  │   error
                    ▼   ▼
        ┌────────────┐  ┌────────┐
        │ SUCCEEDED  │  │ FAILED │
        └────────────┘  └────────┘

  (user có thể CANCELLED từ QUEUED hoặc PROCESSING)
```

| From | To | Trigger |
|---|---|---|
| (none) | `QUEUED` | API tạo job |
| `QUEUED` | `PROCESSING` | Celery worker pick |
| `PROCESSING` | `SUCCEEDED` | Task complete, lưu result |
| `PROCESSING` | `FAILED` | Exception, lưu `error` message |
| `QUEUED/PROCESSING` | `CANCELLED` | User gọi `POST /jobs/{id}/cancel` |

### Retry policy

- `FAILED` job được retry tối đa **3 lần** với backoff (60s, 300s, 1800s).
- Sau 3 lần vẫn fail → set `FINAL_FAILED` (status `FAILED`, `retry_count=3`), gửi notification cho admin.
- Idempotency: mỗi job có `idempotency_key` (UUID v7 + resource_id) để tránh duplicate khi retry.

---

## 4. Index Status (RAG)

Trạng thái vector embedding cho mỗi `document_version`.

```
       ocr_succeeded
              │
              ▼
        ┌────────────┐
        │ NOT_INDEXED│
        └─────┬──────┘
    enqueue embed
              ▼
        ┌──────────┐
        │ INDEXING │
        └────┬─────┘
       done  │  error
            ▼   ▼
    ┌──────────┐ ┌──────────────┐
    │ INDEXED  │ │ INDEX_FAILED │
    └──────────┘ └──────┬───────┘
                       │ re-enqueue (admin action)
                       ▼
                  (back to INDEXING)
```

| Trigger | Chuyển trạng thái |
|---|---|
| OCR job `SUCCEEDED` cho version | Tự động enqueue Embedding job |
| Embedding job `SUCCEEDED` | `NOT_INDEXED → INDEXING → INDEXED` |
| Embedding job `FAILED` | → `INDEX_FAILED`, alert admin |
| Admin update model version | Reindex all versions (`INDEXING → INDEXED`) |
| Document version superseded | Index cũ vẫn giữ (audit) nhưng **không** trả về retrieval |

---

## 5. Audit Log

Mọi state transition phải ghi vào `audit_logs`:

| Field | Type | Mô tả |
|---|---|---|
| `id` | UUID | Primary key |
| `user_id` | UUID | Người thực hiện (null cho system) |
| `action` | enum | `document.create`, `document.approve`, `ocr.trigger`, `model.activate`, ... |
| `target_type` | enum | `document`, `document_version`, `ocr_block`, `job`, `user`, `model` |
| `target_id` | UUID | ID đối tượng |
| `from_status` | enum nullable | Trạng thái trước |
| `to_status` | enum nullable | Trạng thái sau |
| `metadata` | JSONB | Diff, comment, IP, user agent |
| `request_id` | UUID | Trace request tương ứng |
| `created_at` | TIMESTAMPTZ | Thời điểm |

Retention: **1 năm** (xem rule `06-security.mdc`).

---

## 6. Invariants (bất biến)

Mọi lúc, hệ thống phải thoả:

1. `Document.latest_version` trỏ tới version có `status = APPROVED` cao nhất.
2. `OCRBlock.edited_at` phải có nếu `is_edited = true`.
3. `Job.started_at <= Job.finished_at` (nếu cả hai không null).
4. `Embedding.vector` có dimension khớp với `ModelVersion.dimension`.
5. `audit_logs` là append-only, không UPDATE/DELETE.
6. `Document.deleted_at NOT NULL` ⇒ tất cả version, OCR block, embedding **không xuất hiện** trong search/chat.
