# RBAC Matrix — Phân Quyền Theo Vai Trò

> File này là nguồn chuẩn cho **role-based access control** giữa FE, BE và policy.
> Mọi permission check ở backend **BẮT BUỘC** phải khớp với bảng này.

## Vai trò

| Role | Đối tượng | Mô tả |
|---|---|---|
| `admin` | Quản trị hệ thống | Toàn quyền, bao gồm quản lý user, model, training |
| `staff` | Cán bộ Phòng CTSV | Upload, sửa OCR, duyệt văn bản, xem tất cả scope |
| `student` | Sinh viên | Chỉ xem tài liệu `PUBLIC` & `STUDENT_AFFAIRS`, chat RAG |

## Scope của tài liệu

| Scope | Ai được xem |
|---|---|
| `PUBLIC` | Tất cả (kể cả chưa login) — nhưng API vẫn cần auth để log audit |
| `STUDENT_AFFAIRS` | `student`, `staff`, `admin` |
| `INTERNAL` | `staff`, `admin` (sinh viên **không được** thấy ngay cả qua RAG) |

## Ma trận quyền (Capability Matrix)

Ký hiệu: ✅ = cho phép, ❌ = cấm, 🔒 = cho phép có điều kiện.

### 1. Quản lý tài liệu

| Capability | admin | staff | student |
|---|---|---|---|
| `document:list:all` | ✅ | ✅ | ❌ (chỉ xem PUBLIC + STUDENT_AFFAIRS) |
| `document:list:public` | ✅ | ✅ | ✅ |
| `document:read:internal` | ✅ | ✅ | ❌ (403) |
| `document:create` | ✅ | ✅ | ❌ |
| `document:update:metadata` | ✅ | ✅ | ❌ |
| `document:delete` | ✅ | ❌ | ❌ |
| `document:upload:new_version` | ✅ | ✅ | ❌ |
| `document:approve` | ✅ | ✅ | ❌ |
| `document:archive` | ✅ | ✅ | ❌ |

### 2. OCR

| Capability | admin | staff | student |
|---|---|---|---|
| `ocr:trigger` | ✅ | ✅ | ❌ |
| `ocr:block:edit` | ✅ | ✅ | ❌ |
| `ocr:block:read:internal` | ✅ | ✅ | ❌ |

### 3. Search & RAG

| Capability | admin | staff | student |
|---|---|---|---|
| `search:basic` | ✅ | ✅ | ✅ |
| `rag:chat` | ✅ | ✅ | ✅ (chỉ trên tài liệu được phép xem) |
| `rag:export_citations` | ✅ | ✅ | ❌ |

### 4. Admin

| Capability | admin | staff | student |
|---|---|---|---|
| `admin:user:list` | ✅ | ❌ | ❌ |
| `admin:user:create` | ✅ | ❌ | ❌ |
| `admin:user:update_role` | ✅ | ❌ | ❌ |
| `admin:user:deactivate` | ✅ | ❌ | ❌ |
| `admin:model:list` | ✅ | ❌ | ❌ |
| `admin:model:activate` | ✅ | ❌ | ❌ |
| `admin:training:run` | ✅ | ❌ | ❌ |
| `admin:training:view_log` | ✅ | ❌ | ❌ |
| `audit:read` | ✅ | 🔒 (chỉ log liên quan đến mình) | 🔒 (chỉ log liên quan đến mình) |

## Triển khai

### Backend (FastAPI)

```python
# app/core/security.py
from enum import Enum

class Permission(str, Enum):
    DOCUMENT_LIST_ALL = "document:list:all"
    DOCUMENT_CREATE = "document:create"
    OCR_TRIGGER = "ocr:trigger"
    ADMIN_USER_LIST = "admin:user:list"
    # ...

ROLE_PERMISSIONS = {
    "admin": {p.value for p in Permission},
    "staff": {
        Permission.DOCUMENT_LIST_ALL,
        Permission.DOCUMENT_CREATE,
        Permission.OCR_TRIGGER,
        Permission.OCR_BLOCK_EDIT,
        Permission.DOCUMENT_APPROVE,
        Permission.DOCUMENT_UPLOAD_NEW_VERSION,
    },
    "student": set(),  # tất cả permission khác đều 403, kể cả search/chat (kiểm tra scope ở retrieval)
}

def has_permission(role: str, permission: Permission) -> bool:
    return permission.value in ROLE_PERMISSIONS.get(role, set())
```

### Frontend (chỉ để UX, không phải security)

Permission map hiện có ở `apps/web/lib/auth/permissions.ts`. Sẽ được sync với matrix này khi Phase BE ready.

## Audit rule

Mọi mutation phải ghi vào `audit_logs`:
- `user_id`, `action` (VD: `document.approve`, `user.update_role`), `target_id`, `target_type`, `metadata`, `request_id`, `timestamp`.

## Liên kết

- Spec FE: `apps/web/lib/auth/permissions.ts` (sync sau khi BE định nghĩa xong).
- OpenAPI: `docs/api/openapi.yaml`.
- ADR-001 sắp tới sẽ giải thích lý do chọn enum permission thay vì policy engine (Casbin, OPA).
