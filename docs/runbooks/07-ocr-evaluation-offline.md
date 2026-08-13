# 07 — Đánh giá OCR offline với corpus được phê duyệt

> Runbook này chỉ được kích hoạt khi có corpus được phê duyệt và người phụ trách xác nhận môi trường offline. Nó **không** cho phép chạy training qua API, Celery, CI thường hoặc máy không đủ kiểm soát dữ liệu.

## Trigger

Dùng runbook khi cần đo baseline PaddleOCR, fine-tune recognizer hoặc so sánh một model ứng viên với baseline trên test set đóng băng. Không dùng để xử lý OCR job production thông thường.

## Pre-check

| Kiểm tra | Điều kiện đạt | Nếu không đạt |
|---|---|---|
| Phê duyệt corpus | Có reference nội bộ và retention policy | Dừng; không copy corpus vào repository |
| Manifest | Khớp `manifest.schema.json`, DPI 300, split document-level | Dừng; sửa manifest ngoài repository |
| Leakage | Train/validation/test không giao nhau theo document | Dừng; đóng băng split mới |
| Runtime | PaddleOCR/PaddlePaddle đã được phê duyệt và chuẩn bị | Dừng; không tự pull model/dependency nặng |
| Storage | Checkpoint/log chi tiết có kho nội bộ được kiểm soát | Dừng; không lưu artifact vào Git |
| Test set | Không được dùng để tune config | Dừng; kiểm tra lại quy trình experiment |

## Steps

Người vận hành thực hiện các bước tại môi trường offline đã được phê duyệt. Không ghi command có đường dẫn corpus cụ thể vào ticket công khai hoặc log repository.

1. Chạy audit/validation trên manifest và corpus ngoài repository. Lưu kết quả tổng hợp, không lưu text/ảnh/PII.
2. Render hoặc xác minh toàn bộ input evaluation tại **300 DPI**. Không trộn dữ liệu baseline/fine-tune khác cấu hình DPI.
3. Chạy PaddleOCR pretrained baseline trên test set đóng băng; ghi CER, WER, accuracy theo định nghĩa rõ ràng, median/p95 ms/page và review rate.
4. Chỉ khi baseline hợp lệ, chạy fine-tune theo config đã review. Test set không được mở cho vòng tuning.
5. Chạy evaluation cuối trên chính test set đó. Lập báo cáo từ `docs/evaluation/ocr-evaluation-protocol.md` và model card từ `MODEL_CARD.template.md`.
6. Đánh giá quyết định phát hành bằng CER/WER, latency, review rate và scope corpus; không chỉ dựa trên accuracy.

## Verify

Kết quả chỉ được đánh dấu `COMPLETED` khi bảng baseline và fine-tuned cùng có metric trên cùng test set, manifest có evidence không leakage và model card liên kết đúng report/config/version. Báo cáo commit được phải dùng số liệu tổng hợp; không chèn OCR sample có PII hoặc checksum/path nội bộ.

## Rollback và xử lý lỗi

Nếu manifest invalid, phát hiện leakage, runtime tải model ngoài phê duyệt, hoặc metric không tái lập được, dừng experiment. Giữ checkpoint/log trong storage nội bộ theo retention policy, đánh trạng thái model `NOT_READY` hoặc `FAILED`, và không thay model active production. Việc rollback model production tuân theo runbook rollback riêng sau khi có model version đã được phát hành hợp lệ.
