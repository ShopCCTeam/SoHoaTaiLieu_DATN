# services/ocr-training — OCR Training Pipeline

> **Trạng thái**: scaffold. Sẽ code ở Phase 3 (training pipeline).

## Mục đích

Fine-tune PaddleOCR Vietnamese recognizer bằng dữ liệu riêng (CTSV documents).

## Cấu trúc dự kiến

```
services/ocr-training/
├── configs/             # training config yaml
├── scripts/             # CLI: data-audit, data-validate, train, eval
├── datasets/            # (gitignored) chứa ảnh + label
├── training/            # training loop code
├── evaluation/          # CER, WER, confusion matrix
├── Makefile
└── MODEL_CARD.md        # metadata cho mỗi model version
```

## Quy tắc (xem `.cursor/rules/04-database-rag-ocr.mdc`)

- Train/val/test split **theo document**, không random theo trang.
- Test set **không xuất hiện** trong train hoặc validation.
- Luôn so sánh baseline pretrained vs fine-tuned.
- Metrics bắt buộc: CER, WER, processing_time_ms/page, accuracy.
- Tesseract **chỉ** là fallback runtime, không dùng để đánh giá.
- Mỗi model version lưu trong PostgreSQL + checkpoint ở MinIO.

## Commands (sẽ có)

```bash
make data-audit
make data-validate
make ocr-baseline
make ocr-train
make ocr-eval
```
