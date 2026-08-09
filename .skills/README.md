# Project Skills (`.skills/`)

Local Agent Skills cho dự án **"Số hóa tài liệu Công tác sinh viên"**. Mỗi skill là một thư mục chứa `SKILL.md` (frontmatter + hướng dẫn) theo chuẩn Agent Skill của Cursor / Claude Code / AutoSkill.

**Cài từ:** https://github.com/ECNU-ICALK/AutoSkill.git (commit snapshot tháng 5/2026).

## Quản lý

- **`autoskill/`** — Local Skill Manager. Theo dõi phiên làm việc, đề xuất tạo/cập nhật/ghép/bỏ skill dựa trên kinh nghiệm thực tế. **KHÔNG tự ý sửa skill này.**

## Foundation (Common)

| Skill | Phase dùng | Mô tả ngắn |
|---|---|---|
| `composition-patterns` | 9 | React composition patterns (compound components, slot, props) |
| `react-best-practices` | 9 | Best practices khi viết React |
| `web-design-guidelines` | 9 | Design system guidelines cho web UI |
| `frontend-design` | 9 | Production-grade frontend design |
| `webapp-testing` | 9, 10 | Playwright toolkit cho local web testing |
| `doc-coauthoring` | 11 | Workflow viết tài liệu/đặc tả kỹ thuật |
| `pdf` | 2, 6 | Xử lý PDF (trích text, merge, split, OCR) |
| `test-driven-development` | 1–10 | TDD cho mọi feature |
| `systematic-debugging` | 1–10 | Debug có hệ thống |
| `writing-plans` | 0–10 | Viết plan trước khi code |
| `writing-skills` | khi cần | Tạo/cập nhật skill |
| `finishing-a-development-branch` | mỗi phase | Merge / PR / cleanup khi xong phase |
| `using-git-worktrees` | mỗi phase | Isolation khi làm việc song song |

## Backend (BE) — FastAPI, Postgres, OCR, ML

| Skill | Phase dùng | Mô tả ngắn |
|---|---|---|
| `fastapi-local-oop-background-task-system` | 2, 5 | Background task OOP không cần Celery (alternative) |
| `fastapi-oop-background-task-management-system` | 2, 5 | Tương tự, biến thể GLM4.7 |
| `fastapi-base64-image-form-submission` | 2 | Upload ảnh base64 qua form |
| `fastapi-generic-dynamic-filtering-with-pydantic-and-sqlalchemy` | 6, 7 | Dynamic filter cho SQLAlchemy |
| `ocr_medical_receipt_extractor` | 5 | Reference OCR cho receipt (học pattern) |
| `ocr-text-to-wikimedia-source-converter` | 5 | OCR pipeline + output structured |
| `postgresql-inventory-and-price-tracking-schema` | 1 | Schema Postgres reference |
| `postgres-sql-generator-from-english` | 1 | Generate SQL từ tiếng Anh |
| `postgresgpt-sql-generator` | 1 | SQL generator biến thể |
| `linux_high_concurrency_sysctl_tuning` | 0, 10 | Tuning sysctl cho server chạy worker |
| `tensorflow-mirroredstrategy-inference-with-transformers` | 4 | Multi-GPU inference |
| `tensorflow-multi-gpu-batch-text-generation` | 4 | Multi-GPU training |

## RAG

| Skill | Phase dùng | Mô tả ngắn |
|---|---|---|
| `local-pdf-rag-pipeline-with-langchain-and-ollama` | 7, 8 | **Reference chính** — LangChain + Ollama + Chroma |
| `langchain-local-pdf-rag-pipeline` | 7, 8 | Biến thể LangChain RAG |

## Cách dùng

1. **Trong Cursor**: các skill tự động được load từ `.skills/` khi agent nhận diện trigger phù hợp.
2. **Vibe-coding**: trong prompt, dùng cụm từ trigger có trong mỗi `SKILL.md` (xem mục `triggers:` ở frontmatter).
3. **Đề xuất thêm skill mới**: agent sẽ tự đề xuất dựa trên `autoskill/`. Chỉ chấp thuận khi:
   - Có bằng chứng lặp lại ≥ 2 lần trong dự án.
   - Đã search trùng lặp với skill hiện có.
   - Không vi phạm extraction boundary (xem `autoskill/SKILL.md`).

## Cập nhật

Để cập nhật lên phiên bản mới từ upstream:

```bash
# Lưu danh sách skill đã cài
cp -r .skills .skills.bak

# Re-clone repo
rm -rf temp_autoskill_repo
git clone https://github.com/ECNU-ICALK/AutoSkill.git temp_autoskill_repo

# Xem skill mới
ls temp_autoskill_repo/SkillBank/Common
ls temp_autoskill_repo/SkillBank/ConvSkill/english_gpt4_8_GLM4.7

# Cài lại theo danh sách (xem install_skills.ps1)
```

## Lưu ý

- **Không commit** file `.env`, dữ liệu gốc (`data/raw/*.pdf`), model artifact (`models/*.pt`).
- **Không sửa** `autoskill/SKILL.md` trừ khi được yêu cầu rõ.
- **Không duplicate**: trước khi thêm skill, search trong `.skills/` đã có.
