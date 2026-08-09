# models/ — Thư mục model artifacts

> ⚠️ **KHÔNG COMMIT MODEL CHECKPOINT VÀO ĐÂY** — xem `.gitignore` rule `models/**`, `*.pdparams`, `*.safetensors`, `*.ckpt`, `*.pth`, `*.pt`, `*.onnx`.

## Cấu trúc dự kiến

```
models/
├── README.md                       ← file này
├── .gitkeep
├── model-card-template.md          ← template MODEL_CARD (được phép commit)
└── paddleocr-vietnamese/
    ├── v1.0.0-pretrained/         ← (gitignored) baseline
    └── v2.0.0-finetuned/          ← (gitignored) fine-tuned
        ├── checkpoint.pdparams
        ├── config.yml
        ├── charsets.txt
        └── MODEL_CARD.md
```

## MODEL_CARD (template)

Mỗi model version phải có file `MODEL_CARD.md` với các trường:

| Field | Ví dụ |
|---|---|
| `name` | `paddleocr-vietnamese-recognizer` |
| `version` | `v2.0.0-finetuned` |
| `base_model` | `paddleocr-vietnamese-pretrained-v1` |
| `training_date` | `2026-08-09` |
| `dataset_checksum` | `sha256:abc123...` |
| `train_docs_count` | 150 |
| `val_docs_count` | 25 |
| `test_docs_count` | 25 |
| `cer_baseline` | 0.082 |
| `cer_finetuned` | 0.034 |
| `wer_baseline` | 0.156 |
| `wer_finetuned` | 0.072 |
| `avg_processing_time_ms_per_page` | 850 |
| `checkpoint_path_minio` | `s3://models/paddleocr-vietnamese/v2.0.0/checkpoint.pdparams` |
| `config_path_minio` | `s3://models/paddleocr-vietnamese/v2.0.0/config.yml` |
| `charsets_path_minio` | `s3://models/paddleocr-vietnamese/v2.0.0/charsets.txt` |
| `notes` | "..." |

## Khi nào model được commit?

**KHÔNG BAO GIỜ**. Checkpoint lưu ở MinIO. Chỉ commit `MODEL_CARD.md` (metadata) và code inference.
