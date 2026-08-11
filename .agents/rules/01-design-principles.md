# Design Principles & Architecture

## SOLID (bắt buộc)
- **S**ingle Responsibility: 1 class/module = 1 lý do để thay đổi.
- **O**pen/Closed: mở rộng qua kế thừa/composition, không sửa code cũ.
- **L**iskov Substitution: subtype phải thay thế được base type.
- **I**nterface Segregation: tách interface nhỏ, không ép implement method thừa.
- **D**ependency Inversion: depend on abstraction (interface/type), không depend on concrete implementation.

## DRY / KISS / YAGNI
- **DRY**: trích logic lặp lại thành helper/service. **KHÔNG** trích sớm khi chỉ mới dùng ở 1 chỗ.
- **KISS**: giải pháp đơn giản nhất thỏa mãn yêu cầu hiện tại.
- **YAGNI**: không build feature cho "tương lai có thể cần". Chờ requirement thực sự.

## Clean Architecture Layers
```
presentation/   ← UI, route handlers, controllers
application/    ← use cases, services, DTOs
domain/         ← entities, value objects, business rules
infrastructure/ ← DB, API clients, file system, OCR/RAG
```
- Mỗi layer chỉ depend on layer bên trong nó, **không bao giờ** depend ngược.
- Domain layer **không** import framework (Next.js, FastAPI, Prisma...).

## Design Patterns Ưu Tiên Sử Dụng
| Pattern | Khi nào dùng |
|---|---|
| Repository | Che giấu data source, dễ test |
| Factory | Tạo object theo config/strategy |
| Strategy | Nhiều thuật toán cho cùng 1 task (vd: OCR engine, embedding model) |
| Observer / Pub-Sub | Background job, event bus (OCR job update, training run) |
| Decorator | Middleware (auth, logging, rate-limit) |
| Builder | Object phức tạp nhiều field optional (vd: Document metadata) |
| Facade | Che giấu complexity của subsystem (vd: LangChain RAG pipeline) |

## Anti-patterns Cần Tránh
- ❌ God class / God service (> 5 responsibility).
- ❌ Singleton mutable global state (dùng DI container thay thế).
- ❌ `any` trong TypeScript — dùng `unknown` rồi narrow.
- ❌ Circular dependency giữa các modules.
- ❌ Magic number / magic string — extract thành constant có tên rõ ràng.

## Tham Chiếu
- Xem skill `.skills/composition-patterns/` để chọn pattern phù hợp.
- Xem skill `.skills/universal-software-engineering/` cho checklist Clean Code.
