# MODEL_CARD — Template

> Copy file này thành `models/<name>/<version>/MODEL_CARD.md` khi có model mới.
> **KHÔNG commit checkpoint** — chỉ commit file metadata này.

## Thông tin cơ bản

| Field | Value |
|---|---|
| **Name** | `paddleocr-vietnamese-recognizer` |
| **Version** | `v0.1.0` |
| **Base model** | (pretrained checkpoint từ PaddleOCR) |
| **Training date** | `YYYY-MM-DD` |
| **Author** | (tên người train) |

## Dataset

| Split | Document count | Page count | Char count |
|---|---|---|---|
| Train | ? | ? | ? |
| Validation | ? | ? | ? |
| Test | ? | ? | ? |

**Dataset checksum (SHA-256)**: `sha256:...`

**Train/val/test split policy**: theo **document** (không theo trang/dòng).
Test set **không xuất hiện** trong train hoặc validation ở bất kỳ bước nào.

## Metrics

| Metric | Baseline (pretrained) | Fine-tuned |
|---|---|---|
| **CER (Character Error Rate)** | ? | ? |
| **WER (Word Error Rate)** | ? | ? |
| **Accuracy** | ? | ? |
| **Avg processing time / page (ms)** | ? | ? |

## Hyperparameters

```yaml
optimizer: AdamW
learning_rate: 0.0005
batch_size: 32
epochs: 50
early_stopping_patience: 5
image_height: 32
image_width: 320
charset: vietnamese-merged
```

## Artifacts (lưu ở MinIO)

| Path | Mô tả |
|---|---|
| `s3://models/<name>/<version>/checkpoint.pdparams` | Trọng số model |
| `s3://models/<name>/<version>/config.yml` | Config inference |
| `s3://models/<name>/<version>/charsets.txt` | Tập ký tự |

## Ghi chú

- (Các quyết định, vấn đề gặp phải, hướng cải thiện)
