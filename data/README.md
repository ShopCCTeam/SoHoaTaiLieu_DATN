# data/ — Thư mục dữ liệu

> ⚠️ **KHÔNG COMMIT DỮ LIỆU THẬT VÀO ĐÂY** — xem `.gitignore` rule `data/**`.

## Cấu trúc dự kiến

```
data/
├── README.md                     ← file này
├── .gitkeep
├── fixtures/
│   └── synthetic/                ← Dữ liệu synthetic được phép commit (cho test/demo)
│       └── documents/            ← PDF synthetic, không chứa PII
└── raw/                          ← PDF gốc từ nhà trường (GITIGNORED)
    ├── training/
    ├── validation/
    └── test/
```

## Quy tắc

1. Mọi dữ liệu sinh viên thật (PDF, ảnh, transcript, label) **KHÔNG** được commit.
2. Train/validation/test split theo **document** (không theo trang/dòng) để tránh data leakage.
3. Checksum SHA-256 của mỗi split được lưu trong `training_runs.dataset_checksum` để audit.
4. Dữ liệu synthetic ở `fixtures/synthetic/` được phép commit để chạy demo offline.

## Khi cần chia sẻ dữ liệu training

- Dùng MinIO (nội bộ) hoặc Google Drive được cấp quyền.
- KHÔNG push qua git, KHÔNG paste qua chat/Slack không mã hoá.
