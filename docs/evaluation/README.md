# docs/evaluation — Báo cáo OCR Training

> Thư mục này chứa các báo cáo đánh giá model OCR sau mỗi lần training.

## Quy ước đặt tên

```
ocr-YYYY-MM-DD-<version>.md
```

Ví dụ:
- `ocr-2026-08-15-v2.0.0-finetuned.md`
- `ocr-2026-08-20-v2.1.0-finetuned.md`

## Template mỗi báo cáo

Mỗi file phải có:

1. **Tổng quan**: version, ngày train, base model.
2. **Dataset**: train/val/test counts, checksum.
3. **Hyperparameters**: optimizer, LR, batch size, epochs.
4. **Metrics**: CER, WER, accuracy, processing time (baseline vs fine-tuned).
5. **Confusion matrix** (optional, nếu có).
6. **Sample errors**: 5–10 ví dụ text bị OCR sai (chỉ text generic, không PII).
7. **Kết luận & hướng cải thiện**.

## Lưu ý quan trọng

- **KHÔNG** commit dữ liệu training, ảnh test, hay checkpoint.
- **CHỈ** commit báo cáo dạng Markdown (numbers + chart).
- Commit sample text lỗi generic — KHÔNG lộ PII (tên SV, MSSV).
