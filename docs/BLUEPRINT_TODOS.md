# Đối chiếu bản vẽ dự án và TODO thực thi

> **Ngày lập:** 12/08/2026.  
> **Nguồn chuẩn:** bản vẽ/đề cương do nhóm cung cấp trong `pasted_content_2.txt`.  
> **Cách đánh giá:** ưu tiên mã nguồn, cấu hình, kiểm thử và CI hiện tại. Một hạng mục chỉ được gọi là **đã kiểm chứng** khi có bằng chứng chạy được; việc chỉ có source/test mock được ghi là **một phần**.

## 1. Kết luận điều hành

Hệ thống đã có một nền tảng backend/frontend tương đối đầy đủ: FastAPI, PostgreSQL/pgvector, MinIO, Redis, Celery worker, RBAC theo scope, upload PDF, OCR page/block, review block, chunking, hybrid search, citation và guardrail cosine. CI mới nhất trên `master` cũng đã chạy thành công các gate API và web. Tuy nhiên, dự án **chưa ở mức hoàn thành đề cương** vì các phần tạo giá trị học thuật và bằng chứng đánh giá còn thiếu: OCR tiếng Việt thật end-to-end, tiền xử lý ảnh, dữ liệu/corpus, CER/WER, BGE-M3/Ollama thật, LangChain, benchmark RAG, 16 tài liệu nộp và demo sạch.

> **Điểm chặn lớn nhất:** không được tiến hành fine-tune hay đo kết quả sau fine-tune trước khi nhận corpus, chia tập theo tài liệu, niêm phong test set và đo baseline CER/WER. Đây là đường găng không đảo ngược.

| Mức trạng thái | Ý nghĩa | Số nhóm chính |
|---|---|---:|
| **Đã kiểm chứng** | Có mã nguồn và bằng chứng chạy/CI phù hợp | 4 |
| **Một phần** | Đã có khung hoặc một nhánh chạy, nhưng thiếu tích hợp/dữ liệu/bằng chứng đề cương | 8 |
| **Chưa làm** | Chưa thấy implementation hoặc artefact | 12 |
| **Bị chặn** | Cần 200 PDF hoặc một phụ thuộc kỹ thuật tiền đề | 6 |

## 2. Lưu ý về baseline dùng để đối chiếu

Bản vẽ mô tả trạng thái nhánh `main` tại thời điểm lập. Working tree hiện có năm thay đổi **chưa commit**: `ocr_engine.py`, `tasks.py`, hai test OCR/grounding và `docs/PROGRESS.md`. Các thay đổi này đã bổ sung việc lưu PNG trang 300 DPI với key `documents/pages/{version_id}/{page}.png` và chỉ chuyển job sang `SUCCEEDED` sau indexing. Vì vậy, mục S6/K3 không còn là “chưa có code”, nhưng **chưa thể coi là hoàn tất sản phẩm tuần 9**: giao diện review vẫn vẽ nền mock, không nhận `image_key` hay ảnh thật từ backend.

CI GitHub chạy thành công gần nhất là `31574423152` trên `master` lúc 12/08/2026, gồm lint OpenAPI, build/test web, migration PostgreSQL, Ruff, mypy, coverage toàn cục và auth. Đây là bằng chứng automation độc lập. Nó không thay thế việc một thành viên khác chạy lại trên máy sạch hoặc bằng chứng nghiệp vụ với dữ liệu OCR thật.

## 3. Đối chiếu kiến trúc đích

| Khối trong bản vẽ | Trạng thái thực tế | Bằng chứng hiện có | Khoảng cách để gọi là xong |
|---|---|---|---|
| Next.js 14 + FastAPI + RBAC scope | **Đã kiểm chứng** | Frontend và API đã có; backend áp `Document.scope.in_(allowed_scopes)` trước retrieval; CI web/API thành công | Cần E2E live FE–BE thay vì mặc định mock để đóng demo |
| PostgreSQL + pgvector, MinIO, Redis + Celery | **Đã kiểm chứng** | Compose có 5 service; worker dùng Celery; migration/CI PostgreSQL pass | Cần runbook khởi động và test máy sạch |
| Render PyMuPDF 300 DPI, text layer 50 ký tự | **Đã kiểm chứng** | `ocr_render_dpi=300`, `ocr_text_layer_min_characters=50`; cả text layer và OCR có PNG render | Cần xác minh với PDF scan tiếng Việt thật, có log/bằng chứng ảnh |
| Lưu ảnh trang và `image_key` | **Một phần** | Worker mới upload `image/png` trước `OCRPage`; test kiểm PNG magic bytes | Chưa có endpoint/URL kiểm soát scope để FE tải ảnh; FE review vẫn placeholder |
| PaddleOCR chính, Tesseract fallback | **Một phần** | Extra OCR và image Docker có Paddle/Tesseract; strategy thật tồn tại | Chưa có bằng chứng một job worker đọc đúng tiếng Việt; CI không cài extra OCR |
| Tiền xử lý: khử nghiêng, khử nhiễu, nhị phân hoá | **Chưa làm** | Không thấy service/config/preprocess pipeline | Thiết kế stage, cấu hình bật/tắt, test và benchmark trước/sau |
| PP-Structure cho bảng | **Chưa làm** | Không thấy dependency hay model bảng | Cần schema, extraction, chunking bảng, API/UI và TEDS |
| Sửa chính tả bằng LLM nội bộ | **Chưa làm** | Không thấy post-OCR correction pipeline | Cần guard dữ liệu số/định danh, lưu bản gốc–bản sửa và đo CER |
| Màn duyệt OCR + bbox trên ảnh thật | **Một phần** | Có UI split view, block editor và bbox overlay | UI dùng watermark mock; bbox đang dùng toạ độ phần trăm trong khi BE lưu toạ độ pixel, cần chuẩn hoá mapping |
| Chunking, embedding BGE-M3, index | **Một phần** | Chunk/index code có; worker index trước job success | Default `embedding_provider="mock"`; Compose không có Ollama và không override endpoint container |
| Hybrid RRF + scope + guardrail cosine | **Một phần** | Vector + full-text + RRF; scope filter trước query; cosine threshold 0.6 có test biên | Chưa có corpus/vector thật, benchmark Recall@k/MRR, keyword/tag filter gắn kèm |
| Chuỗi LangChain Retriever → Prompt → LLM → Parser | **Chưa làm** | `pyproject.toml` không có LangChain; chat ghép prompt bằng chuỗi thủ công | Cần chain thật, callback trace, parser và test citation/no-answer |

## 4. Đối chiếu theo 16 tuần đề cương

| Tuần | Trạng thái đánh giá | Thực tế và khoảng cách còn lại |
|---:|---|---|
| 1 | **Chưa làm** | Không thấy báo cáo khảo sát hiện trạng CTSV. |
| 2 | **Một phần** | Có RBAC matrix/lifecycle; thiếu tài liệu đặc tả yêu cầu và sơ đồ use case cho admin, cán bộ, sinh viên. |
| 3 | **Một phần** | ADR-0001 chốt backend/pgvector; thiếu báo cáo so sánh PaddleOCR–Tesseract và BGE-M3 với phương án khác. |
| 4 | **Bị chặn một phần** | Chưa có 200 PDF; metadata field/tags có trong code nhưng thiếu quy ước metadata/từ khoá, kiểm kê và checksum corpus. |
| 5 | **Một phần** | Có migration/schema và màn hình FE; thiếu ERD, sơ đồ kiến trúc báo cáo, tài liệu thiết kế UI. |
| 6–7 | **Đã kiểm chứng ở mức backend/CI** | Upload PDF, version, RBAC, MinIO, worker, review API đã có; vẫn cần E2E frontend live cho demo. |
| 8–9 | **Một phần** | 300 DPI, OCR row/block, image upload mới, review UI khung đã có; thiếu JPG/PNG, preprocessing, OCR tiếng Việt thực chứng, UI ảnh thật. |
| 10 | **Bị chặn** | Chưa có corpus niêm phong và baseline; chưa có CER/WER hay độ chính xác trường quan trọng. |
| 11 | **Một phần** | Chunking/index/hybrid code có; vector đang mock mặc định, chưa chứng minh vector BGE-M3 thật trong DB. |
| 12 | **Chưa làm** | Chưa có LangChain; prompt và luồng chat còn thủ công. |
| 13 | **Một phần** | Hybrid RRF, citation, no-answer và RBAC có. `q` hiện lọc title/code ở danh sách; search chưa có keyword/tag filter độc lập. |
| 14 | **Một phần** | CI/migration/coverage có; thiếu biên bản test chức năng–bảo mật–hiệu năng, đo latency và kịch bản ổn định. |
| 15 | **Chưa làm** | Chưa có golden questions, Recall@k, MRR, citation accuracy, so sánh retriever/chunk size, hướng dẫn cài đặt/sử dụng. |
| 16 | **Chưa làm** | Chưa có báo cáo tổng kết, slide, demo script và ba lần diễn tập máy sạch. |

## 5. Nợ kỹ thuật K1–K8 sau khi đối chiếu lại

| Mã | Đánh giá hiện tại | Việc cần xử lý |
|---|---|---|
| K1 | **Còn mở** | `Dockerfile.api` vẫn dùng `uv sync --frozen ... || uv sync ...`; phải bỏ fallback để lockfile sai làm build fail. |
| K2 | **Còn mở, chặn S4/P3** | Config mặc định trỏ `localhost:11434`; Compose chưa có Ollama hoặc `host.docker.internal`. Cần chọn topology duy nhất và healthcheck/model readiness. |
| K3 | **Code đã có nhưng sản phẩm chưa đóng** | `image_key` đã được gán/upload trong working tree; cần endpoint/URL có RBAC và nối UI nền ảnh thật. |
| K4 | **Còn mở** | `--strict-markers` không phải skip gate. CI cần đếm skip theo allowlist/ceiling và fail khi vượt ngưỡng. |
| K5 | **Còn mở** | `numpy` được import trực tiếp trong Paddle strategy nhưng không khai báo direct trong extra OCR/mypy override. Mypy hiện pass cục bộ/CI, song dependency còn phụ thuộc transitive. |
| K6 | **Còn mở có điều kiện** | oasdiff dùng image `latest` và `continue-on-error: true`; cần pin version ngay, còn fail-on-diff chỉ bật sau khi runtime cover contract. |
| K7 | **Còn mở** | CI cài `--extra dev`, không cài `--extra ocr`; nhánh Paddle/Tesseract native không được kiểm chứng CI. |
| K8 | **Giảm rủi ro nhưng chưa đóng** | Có CI pass và transcript local 248 passed/83%, nhưng Definition of Done yêu cầu một thành viên khác tái chạy trên máy sạch. |

## 6. TODO ưu tiên — Làn 1, không chờ corpus

Các TODO dưới đây được sắp theo phụ thuộc. Không tự mở rộng sang Elasticsearch, vector store riêng, API LLM ngoài hoặc huấn luyện detector vùng chữ.

### P0 — chặn demo, baseline hoặc khả năng tái lập

- [ ] **T01 — Chốt topology Ollama nội bộ và bật BGE-M3/LLM thật** — *Khải; S4, P3, K2*.
  - Chọn một phương án: thêm service `ollama` vào Compose **hoặc** cấu hình host gateway cho Docker Desktop; không dùng `localhost` bên trong API/worker container.
  - Thêm healthcheck và kiểm tra hai model `bge-m3`, `qwen2.5:8b`; `embedding_provider=bge-m3`, `llm_provider=ollama` trong profile demo.
  - **XONG khi:** job index tạo vector 1024 chiều thật trong PostgreSQL; chat live có câu trả lời/citation từ dữ liệu synthetic đã phê duyệt; dán `docker compose ps`, query đếm vector khác `NULL`, và log không lộ OCR/PII.

- [ ] **T02 — Làm OCR native chạy được trong worker với mẫu tiếng Việt không nhạy cảm** — *Duy Anh; S5*.
  - Rebuild worker từ lockfile đóng băng, kiểm tra PaddleOCR primary và Tesseract fallback; không bật mock ngoài test.
  - **XONG khi:** một job `SUCCEEDED`, có ít nhất một `ocr_block` chứa dòng tiếng Việt đã biết; kèm output worker, trạng thái job, object MinIO và ảnh page 300 DPI. Không dùng PDF thật nếu chưa được phép.

- [ ] **T03 — Thêm tiền xử lý ảnh có thể cấu hình** — *Duy Anh; S7*.
  - Tạo stage trước OCR gồm deskew, denoise, binarisation; config bật/tắt và tham số; giữ render 300 DPI làm đầu vào chuẩn.
  - **XONG khi:** test unit/integration chứng minh stage dùng đúng config và báo cáo so sánh latency/CER trên cùng test set khi đã có corpus.

- [ ] **T04 — Hoàn tất ảnh thật cho màn duyệt OCR** — *Huy; S6/K3*.
  - Mở API/adapter lấy page image theo `image_key` với check document scope trước storage; không public URL hay bypass RBAC.
  - Nối Next.js review pane với ảnh thật, chuẩn hoá bbox pixel của backend sang overlay theo kích thước ảnh; bỏ watermark mock.
  - **XONG khi:** staff thấy ảnh và bbox đúng chỗ; student bị chặn ảnh scope không được phép; có Playwright/E2E hoặc bằng chứng API + screenshot từ môi trường demo.

- [x] **T05 — Hỗ trợ upload JPG/PNG an toàn** — *Huy; S3*.
  - Cập nhật OpenAPI trước, validator MIME/magic bytes, storage key/content type, lifecycle version và strategy OCR ảnh.
  - **XONG khi:** một JPG và một PNG hợp lệ tạo `ocr_blocks`; tệp giả đổi đuôi bị chặn; PDF flow không hồi quy; contract, types, FE và backend test đồng bộ.

- [x] **T06 — Chuyển chat sang LangChain chain thật** — *Khải; S1*.
  - Bổ sung dependency đã pin; tạo retriever adapter giữ filter RBAC trước retrieval, prompt template, Ollama adapter, output parser và callback trace.
  - **XONG khi:** một query live đi qua chain, trả citation hợp lệ hoặc no-answer; trace không chứa nội dung tài liệu/PII; test xác minh scope/no-answer/citation.

### P1 — tính năng đề cương và độ tin cậy CI

- [ ] **T07 — Bộ lọc từ khoá/tag xuyên suốt documents và hybrid search** — *Khải; S2*.
  - Giữ `q` hiện có cho title/code; thiết kế rõ filter keyword/tag độc lập trong OpenAPI, thêm filter vào SQL vector và full-text trước candidate retrieval.
  - **XONG khi:** gọi list và search cùng filter cho đúng tập con, không làm rò document ngoài scope; test RBAC + API output nguyên văn.

- [ ] **T08 — Đóng K1: lockfile fail-closed khi Docker build** — *Khải*.
  - Bỏ nhánh `|| uv sync --no-dev --extra ocr`; thêm CI step `uv lock --check` và smoke Docker build chỉ dùng `--frozen`.
  - **XONG khi:** lock hợp lệ build pass; lock cố ý lệch bị build/CI fail; restore lock chuẩn và dán output.

- [ ] **T09 — Đóng K4/K7: CI kiểm chứng skip và OCR native** — *Duy Anh + Khải*.
  - Thêm skip allowlist/ceiling rõ ràng; CI fail khi skip ngoài danh sách.
  - Tạo job OCR-native có `--extra ocr` hoặc gate coverage theo module để không che nhánh native bằng coverage global.
  - **XONG khi:** CI cho thấy số skip, lý do, coverage/gate OCR; không có `continue-on-error` cho các gate bắt buộc.

- [ ] **T10 — Đóng K5/K6: dependency và contract gate tái lập** — *Khải*.
  - Khai báo trực tiếp `numpy` trong extra OCR và mypy override phù hợp nếu package không typed; kiểm tra môi trường dev-only và dev+ocr.
  - Pin version oasdiff; giữ diff informational cho tới khi API đủ endpoint rồi tạo mốc bật fail-on-diff.
  - **XONG khi:** hai trạng thái môi trường mypy cùng pass; image oasdiff không dùng `latest`; có ADR/todo nêu tiêu chí bật blocking diff.

- [ ] **T11 — E2E live frontend–backend và biên bản ổn định** — *Cả nhóm; tuần 14*.
  - Chạy login → upload → job → review → approve → search → chat bằng API live, không dùng Next mock.
  - **XONG khi:** biên bản chứa các test chức năng, RBAC/security, latency OCR/chat; một thành viên khác tái chạy trên máy sạch; warning teardown được sửa hoặc được phân loại/giới hạn có lý do.

### P2 — điểm cộng, chỉ bắt đầu sau P0/P1 và không ảnh hưởng baseline

- [ ] **T12 — PP-Structure và dữ liệu bảng** — *Huy; P1*.
  - Chốt DTO/schema table, contract/migration cần thiết, rule “một bảng một chunk”, lặp header khi cắt theo hàng, bbox UI.
  - **XONG khi:** bảng có cấu trúc được persist/review/retrieve; báo TEDS, CER ô và Recall@k theo ô/bảng trên tập đánh giá.

- [ ] **T13 — Sửa chính tả OCR có guard dữ liệu nhạy cảm** — *Khải; P2*.
  - Chỉ xử lý block confidence thấp; không đổi số hiệu, ngày, mã sinh viên, tên riêng; lưu parallel original/corrected text và audit.
  - **XONG khi:** phép đo CER trước/sau trên cùng tập test, ví dụ lỗi, test đảm bảo dữ liệu bất biến không bị đổi.

- [ ] **T14 — Tối ưu RAG sau khi có benchmark** — *Khải; P4*.
  - Đánh giá vector-only, full-text-only, RRF và ba chunk size trước khi cân nhắc cross-encoder.
  - **XONG khi:** bảng Recall@k/MRR/citation accuracy quyết định cấu hình; không thêm reranker nếu số liệu không biện minh.

## 7. TODO Làn 2 — thực hiện ngay khi nhận 200 PDF

- [ ] **T15 — Kiểm kê và chuẩn hoá corpus (T1)** — *Khải xin dữ liệu; Duy Anh chuẩn hoá*.
  - Chỉ xử lý trong môi trường nội bộ; tạo inventory gồm file ID, checksum, số trang, nhóm tài liệu, chất lượng scan, lỗi đọc.
  - **XONG khi:** có bảng thống kê và manifest checksum, không đưa PDF/OCR thật vào Git.

- [ ] **T16 — Chia train/val/test và niêm phong test (T2)** — *Duy Anh*.
  - Chia theo **tài liệu**, không theo trang; lưu seed, manifest và hash test set read-only.
  - **XONG khi:** ba manifest bất biến, test set hash đã ghi và review chéo; chỉ sau đó mới mở bước baseline.

- [ ] **T17 — Đo baseline OCR gốc (T3, E1/E3/E7)** — *Duy Anh*.
  - Chạy PaddleOCR chưa fine-tune trên test set niêm phong với 300 DPI và cấu hình preprocessing đã chốt.
  - **XONG khi:** CER, WER, field accuracy (số hiệu/ngày/đơn vị), OCR seconds/page, command/version/config/seed được ghi; gồm mẫu lỗi đại diện.

- [ ] **T18 — Gán nhãn train/val và fine-tune recognizer (T4/T5)** — *Duy Anh*.
  - Viết annotation convention, quality check liên người gán, version dataset; fine-tune **recognizer**, không detector.
  - **XONG khi:** đường cong train/val, hyperparameter, checkpoint internal và tái lập được từ manifest; artifact không commit Git.

- [ ] **T19 — Đo sau fine-tune và model card (T6, E2/E6)** — *Duy Anh*.
  - Chạy lại đúng test set đã niêm phong, cùng kịch bản baseline; so sánh minh bạch trước/sau.
  - **XONG khi:** report CER/WER/field accuracy/latency, 5–10 lỗi, model card hoàn chỉnh; nếu tệ hơn vẫn nêu trung thực nguyên nhân.

## 8. TODO bằng chứng, tài liệu và bảo vệ

- [ ] **T20 — Viết bộ tài liệu tuần 1–5** — *Cả nhóm, phân theo vai trò*.
  - Bao gồm khảo sát hiện trạng, đặc tả yêu cầu, use case ba vai trò, so sánh công nghệ OCR/embedding, metadata/keyword convention, bảo mật–scope, kiến trúc, ERD và thiết kế UI.
  - **XONG khi:** 9 artefact có nguồn/phiên bản, được review nội bộ và đối chiếu với OpenAPI/schema/source.

- [ ] **T21 — Xây bộ câu hỏi vàng và đánh giá RAG (E4–E6)** — *Khải*.
  - Soạn 30–50 câu hỏi, gold chunk/citation, thao tác chấm citation; đo Recall@k, MRR, citation accuracy, ba retriever và ba chunk size; đo 10 câu hỏi manual-vs-system.
  - **XONG khi:** dataset câu hỏi versioned không chứa PII, script đo tái lập, bảng kết quả có số và phần phân tích thất bại.

- [ ] **T22 — Soạn biên bản test và tài liệu tuần 14–15** — *Cả nhóm*.
  - Biên bản chức năng/bảo mật/hiệu năng; hướng dẫn cài đặt và sử dụng; báo cáo OCR; báo cáo RAG.
  - **XONG khi:** mỗi số liệu E1–E7 truy ra được command, version, ngày chạy, người chạy và artifact nội bộ.

- [ ] **T23 — Đóng gói bảo vệ tuần 16** — *Cả nhóm*.
  - Báo cáo tổng kết, slide, demo script có phương án no-answer và error recovery, checklist môi trường sạch.
  - **XONG khi:** diễn tập end-to-end tối thiểu ba lần trên máy sạch, ghi lỗi/phương án khắc phục và video/screenshot nội bộ nếu được phép.

## 9. Trình tự thực hiện đề nghị

1. **Ngay bây giờ:** T01, T02, T03, T04, T05, T06 song song theo ownership; đồng thời T08–T11 để cổng chất lượng không che lỗi.
2. **Song song không phụ thuộc dữ liệu:** T07, T20 và phác thảo T21/T22/T23.
3. **Ngay khi nhận corpus:** T15 → T16 → T17 là đường găng không đảo được.
4. **Chỉ sau baseline:** T18 → T19; P1/P2/P4 chỉ làm nếu không ảnh hưởng T17/T19 và deliverable bắt buộc.

## 10. Phạm vi chưa xác minh trong lần đối chiếu này

Tôi không đọc `.env`, PDF thật, `data/`, model checkpoint hay OCR text thật. Tôi cũng không chạy Docker, migration, fine-tune hoặc thay đổi code. Các claim runtime OCR/MinIO đang dựa vào transcript, CI và test đã có; bước T02/T04/T11 đặt ra bằng chứng thao tác thật còn thiếu để đóng Definition of Done của bản vẽ.
