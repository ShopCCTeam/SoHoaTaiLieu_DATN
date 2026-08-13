# services/ocr-training — OCR Training Pipeline

> **Trạng thái**: training pipeline vẫn là scaffold và **chưa có corpus/model fine-tune**. Repository hiện chỉ có artefact governance/template để chuẩn bị evaluation offline, không có evidence baseline, CER/WER hoặc training run.

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

## Artefact governance đã có

- `manifest.schema.json`: schema metadata-only cho corpus đã được phê duyệt; không chứa PDF, image, OCR text, PII hoặc checkpoint.
- `manifest.example.yaml`: placeholder, không phải manifest/evidence dataset thật.
- `MODEL_CARD.template.md`: template bắt buộc ghi `NOT_MEASURED` khi chưa có benchmark.
- `docs/evaluation/ocr-evaluation-protocol.md`: protocol baseline/fine-tune/evaluation document-level, 300 DPI.
- `docs/runbooks/07-ocr-evaluation-offline.md`: runbook chỉ kích hoạt trong môi trường offline được phê duyệt.

## Commands (sẽ có)

```bash
make data-audit
make data-validate
make ocr-baseline
make ocr-train
make ocr-eval
```
