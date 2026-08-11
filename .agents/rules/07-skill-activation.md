# Skill Activation Guide

> Repo đã cài sẵn 27 skill trong `.skills/`.
> **Nguyên tắc số 1**: **Project rules và ADR luôn ưu tiên cao hơn nội dung skill**. Skill là tài liệu tham khảo, không có quyền ghi đè rule dự án hay ADR đã chốt.

## Stack Cố Định
- **Backend**: Python 3.11 + FastAPI + SQLAlchemy 2.x + Alembic + PostgreSQL 16 + pgvector + Celery + Redis + MinIO + PaddleOCR + BGE-M3 + Ollama.
- **Frontend**: Next.js 14 (App Router) + React 18 + TypeScript Strict + Tailwind + Zustand + TanStack Query.
- **KHÔNG dùng**: Node.js BE, Qdrant (dùng pgvector), Tesseract làm primary evaluator, base64 image upload, TensorFlow OCR.

## Bảng Tra Cứu Kích Hoạt Skill
| Task | Đọc Skill |
|---|---|
| Viết code FE (component, hook, page) | `.skills/vercel-react-best-practices/`, `.skills/react-best-practices/` |
| Design UI/UX, glassmorphism, motion | `.skills/frontend-design/`, `.skills/web-design-guidelines/` |
| Viết BE Python FastAPI | `.skills/fastapi-local-oop-background-task-system/`, `.skills/fastapi-generic-dynamic-filtering-with-pydantic-and-sqlalchemy/` |
| Background job / queue | `.skills/fastapi-local-oop-background-task-management-system/` |
| RAG / LangChain / Ollama | `.skills/langchain-local-pdf-rag-pipeline/`, `.skills/local-pdf-rag-pipeline-with-langchain-and-ollama/` |
| Database / SQL / schema (PostgreSQL) | `.skills/postgres-sql-generator-from-english/` |
| Test code | `.skills/test-driven-development/`, `.skills/webapp-testing/` |
| Debug code chạy sai | `.skills/systematic-debugging/` |
| Design pattern | `.skills/composition-patterns/`, `.skills/universal-software-engineering/` |
| Tạo plan trước khi code | `.skills/writing-plans/` |
| Viết commit hoàn chỉnh (gộp PR) | `.skills/finishing-a-development-branch/` |
| Review security | `.skills/security-requirement-extraction/` |

## Skills Bị Loại Khỏi Map (Do Xung Đột Stack)
- ❌ `.skills/nodejs-best-practices/` (Đã chốt Python BE).
- ❌ `.skills/fastapi-base64-image-form-submission/` (Upload PDF qua multipart).
- ❌ `.skills/postgresql-inventory-and-price-tracking-schema/` (Sai domain).
- ❌ `.skills/tensorflow-mirroredstrategy-inference-with-transformers/` (Dùng PaddlePaddle).
- ❌ `.skills/mongodb-schema-design/` (Đã chốt PostgreSQL).

## Workflow Khi Nhận Task Phức Tạp
1. Đọc yêu cầu → Xác định domain.
2. Match skill theo bảng trên. **Không auto-load 27 skill** cùng lúc.
3. Đọc SKILL.md. Verify scope xem có xung đột với Rule/ADR không.
4. Lập kế hoạch và thực hiện theo SOLID & Clean Code.
5. Verify bằng test/lint trước khi báo hoàn thành.
