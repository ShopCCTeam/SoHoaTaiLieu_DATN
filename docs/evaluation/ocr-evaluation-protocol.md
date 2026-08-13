# Protocol đánh giá OCR — Baseline và Fine-tune

> **Trạng thái:** Quy trình sẵn sàng, **chưa thực thi**. Tài liệu này không chứa corpus, annotation, OCR text, checkpoint, checksum hay số liệu kết quả.

## 1. Mục tiêu và điều kiện đầu vào

Protocol này so sánh PaddleOCR pretrained baseline với recognizer đã fine-tune cho tài liệu công tác sinh viên. Mọi mẫu phải được phê duyệt trước khi vào môi trường offline. Tesseract chỉ là fallback runtime, **không** là hệ thống đối chứng cho benchmark fine-tune.

| Điều kiện bắt buộc | Trạng thái cần có trước khi chạy |
|---|---|
| Phê duyệt sử dụng dữ liệu | Có reference nội bộ và retention policy trong manifest ngoài repository |
| Split dữ liệu | Train/validation/test theo **document-level**, không chia ngẫu nhiên theo trang hoặc dòng |
| Ảnh input | Render tại **300 DPI** để khớp pipeline runtime và dataset fine-tune |
| Test set | Không xuất hiện trong train/validation hoặc vòng chọn hyperparameter |
| Baseline | PaddleOCR pretrained được chạy trên test set đóng băng trước fine-tune |
| Bảo mật | Không commit PDF, image, label, OCR text, PII, checkpoint hoặc log chi tiết |

Nếu một điều kiện thiếu, người thực hiện phải ghi `NOT_RUN` và dừng, không suy diễn CER/WER hay accuracy.

## 2. Manifest và chống leakage

Dùng `services/ocr-training/manifest.schema.json` để kiểm tra metadata manifest. Manifest thật không được ghi đường dẫn PDF, ID sinh viên, tên người, OCR text hoặc secret. `manifest.example.yaml` chỉ là placeholder, không phải evidence dataset.

Mỗi document được gán vào đúng một split. Audit tối thiểu cần kiểm tra: số document ở từng split, giao nhau rỗng giữa ba split, DPI bằng 300 và trạng thái checksum được tính **ngoài repository**. Không đưa checksum giá trị thật vào log công khai nếu nó có thể hỗ trợ fingerprinting dữ liệu nội bộ.

## 3. Thứ tự chạy offline

| Bước | Thao tác | Artefact được phép commit | Điều kiện fail-closed |
|---|---|---|---|
| A | `data-audit` trên corpus được phê duyệt | Chỉ báo cáo tổng hợp không PII | Thiếu approval/manifest hoặc split giao nhau |
| B | `data-validate` kiểm format, annotation và 300 DPI | Kết quả pass/fail tổng hợp | Có trang/label lỗi hoặc test leakage |
| C | `ocr-baseline` bằng PaddleOCR pretrained | Bảng metric baseline | Test set chưa đóng băng |
| D | `ocr-train` offline | Model card không chứa checkpoint | Baseline chưa có hoặc data validation fail |
| E | `ocr-eval` trên test set đóng băng | Báo cáo Markdown tổng hợp | Fine-tune không trace được về manifest/model card |

Không chạy các bước này qua API, Celery hoặc workflow CI thông thường. Không tải model ngoài dự kiến trong lúc evaluation; model/runtime cần được chuẩn bị và phê duyệt riêng.

## 4. Metrics và cách báo cáo

Báo cáo phải có baseline và fine-tuned trên **cùng test set**. Accuracy không thay CER/WER; nếu một metric chưa tính, ghi `NOT_MEASURED` thay vì `0` hoặc giá trị mô phỏng.

| Metric | Công thức/đơn vị | Cách diễn giải |
|---|---|---|
| CER | Edit distance ký tự / số ký tự reference | Thấp hơn tốt hơn |
| WER | Edit distance từ / số từ reference | Thấp hơn tốt hơn |
| Accuracy | Theo định nghĩa recognizer được ghi trong report | Chỉ bổ trợ CER/WER |
| Processing time | ms/page, median và p95 | So sánh cùng phần cứng/cấu hình |
| Review rate | Tỷ lệ block dưới confidence threshold | Liên kết tác động vận hành OCR review |

Báo cáo nêu model ID, cấu hình, version PaddleOCR/PaddlePaddle, DPI, ngày chạy, phiên bản manifest và giới hạn phần cứng. Không đưa câu OCR mẫu nếu có nguy cơ PII; dùng mô tả lỗi đã khử định danh hoặc không đưa ví dụ.

## 5. Tiêu chí kết luận

Fine-tune chỉ được kết luận cải thiện khi CER/WER trên test set đóng băng tốt hơn baseline và processing time/review rate được báo cùng điều kiện. Nếu kết quả trái chiều, nêu trade-off thay vì chọn một metric thuận lợi. Model card phải liên kết báo cáo, manifest version, charset, config và đường dẫn checkpoint **nội bộ**; checkpoint không được commit.

## 6. Template trạng thái chưa chạy

```text
Corpus approval: NOT_AVAILABLE
Manifest validation: NOT_RUN
Baseline metrics: NOT_MEASURED
Fine-tuned metrics: NOT_MEASURED
CER/WER conclusion: NOT_AVAILABLE
```
