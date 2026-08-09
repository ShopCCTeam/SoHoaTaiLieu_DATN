# docs/adr — Architecture Decision Records

> Mỗi ADR ghi lại **một quyết định kiến trúc quan trọng**, bối cảnh, lý do, và hệ quả.

## Quy ước đặt tên

```
NNNN-tieu-de-ngan-gon.md
```

Ví dụ:
- `0001-backend-stack.md` — chốt backend stack.
- `0002-pgvector-vs-qdrant.md` — chốt vector store.
- `0003-monolith-vs-microservice.md` — modular monolith.

## Template

```markdown
# ADR-NNNN: <Tiêu đề>

> Trạng thái: <Proposed | Accepted | Deprecated | Superseded by NNNN>
> Ngày: YYYY-MM-DD
> Tác giả: ...

## Bối cảnh
<Problem statement>

## Quyết định
<Công nghệ / pattern đã chọn>

## Lý do
<Tại sao chọn>

## Hệ quả
### Tích cực
### Tiêu cực

## Phương án bị loại
| Phương án | Lý do loại |

## Tài liệu tham chiếu
- ...
```

## Hiện có

- [ADR-0001: Chốt Backend Stack](./0001-backend-stack.md)
