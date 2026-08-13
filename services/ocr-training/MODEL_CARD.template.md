# Model Card OCR — Template

> **TEMPLATE ONLY.** Không thay thế model card của một model đã train. Không commit checkpoint, OCR text, ảnh/PDF, PII, đường dẫn nội bộ hoặc secret vào file này.

## 1. Định danh

| Trường | Giá trị cần điền sau khi được phê duyệt |
|---|---|
| Model ID | `NOT_AVAILABLE` |
| Phiên bản | `NOT_AVAILABLE` |
| Base recognizer | `NOT_AVAILABLE` |
| Trạng thái | `NOT_TRAINED` / `EVALUATING` / `READY` / `RETIRED` |
| Ngày tạo | `YYYY-MM-DD` |
| Owner kỹ thuật | Vai trò/nhóm, không ghi PII nếu không cần thiết |

## 2. Dữ liệu và quyền sử dụng

Model chỉ được train sau khi manifest metadata đã pass validation và reference phê duyệt hợp lệ. Split train/validation/test phải theo document-level; test set không tham gia train, validation hoặc tuning.

| Trường | Giá trị |
|---|---|
| Manifest version | `NOT_AVAILABLE` |
| Approval reference | `NOT_AVAILABLE` |
| Dataset checksum | `NOT_AVAILABLE` hoặc reference ngoài repository |
| DPI render | `300` |
| Charset | `NOT_AVAILABLE` |
| Retention policy | `NOT_AVAILABLE` |

## 3. Cấu hình train và artifact

Ghi version PaddleOCR/PaddlePaddle, hyperparameter, seed, cấu hình phần cứng và reference checkpoint **nội bộ**. Không ghi checkpoint path thật nếu path lộ topology/nhận dạng nội bộ; thay bằng reference được kiểm soát.

| Trường | Giá trị |
|---|---|
| PaddleOCR / PaddlePaddle | `NOT_AVAILABLE` |
| Optimizer / learning rate | `NOT_AVAILABLE` |
| Batch size / epochs | `NOT_AVAILABLE` |
| Random seed | `NOT_AVAILABLE` |
| Hardware class | `NOT_AVAILABLE` |
| Checkpoint reference | `NOT_AVAILABLE` |

## 4. Đánh giá trên test set đóng băng

Không nhập giá trị mô phỏng. Nếu chưa chạy, dùng `NOT_MEASURED`; không thay bằng 0 hoặc tỷ lệ phần trăm dự kiến.

| Metric | Baseline pretrained | Fine-tuned | Điều kiện so sánh |
|---|---:|---:|---|
| CER | `NOT_MEASURED` | `NOT_MEASURED` | Cùng test set document-level, 300 DPI |
| WER | `NOT_MEASURED` | `NOT_MEASURED` | Cùng test set document-level, 300 DPI |
| Accuracy | `NOT_MEASURED` | `NOT_MEASURED` | Ghi rõ định nghĩa metric |
| Median latency (ms/page) | `NOT_MEASURED` | `NOT_MEASURED` | Cùng hardware/config |
| p95 latency (ms/page) | `NOT_MEASURED` | `NOT_MEASURED` | Cùng hardware/config |
| Review rate | `NOT_MEASURED` | `NOT_MEASURED` | Cùng threshold confidence |

## 5. Hạn chế, rủi ro và quyết định phát hành

Nêu rõ nhóm lỗi đã quan sát theo dạng khử định danh, trade-off CER/WER/latency, phạm vi tài liệu chưa phủ và điều kiện rollback. Tesseract không được dùng làm benchmark fine-tune; nó chỉ là fallback runtime.

> **Kết luận phát hành:** `NOT_READY` cho đến khi có baseline, fine-tune và evaluation độc lập trên test set đóng băng.
