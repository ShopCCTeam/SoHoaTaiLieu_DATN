# Hướng dẫn cài đặt Dev Environment — Windows 10

> **Phase 1.5** — xem `docs/PROGRESS.md` để biết tiến độ.
>
> **Mục tiêu**: sau khi làm theo hướng dẫn này, bạn có thể chạy `make up` để khởi động toàn bộ stack (Postgres + Redis + MinIO + API) + verify contract OpenAPI bằng oasdiff.

---

## 1. Yêu cầu phần cứng

| Tài nguyên | Tối thiểu | Khuyến nghị |
|---|---|---|
| OS | Windows 10 build 19041+ | Windows 11 |
| RAM | 8 GB | 16 GB |
| Disk trống | 20 GB | 50 GB |
| CPU | 4 cores | 8 cores (cho Docker + IDE + Chrome) |
| Quyền | Admin (PowerShell) | Admin |

**Bật virtualization** trong BIOS (VT-x / AMD-V) — thường đã bật sẵn trên máy mới.

---

## 2. Cài WSL2 (Ubuntu 22.04)

WSL2 là backend **bắt buộc** cho Docker Desktop trên Windows (rule đã chốt).

### 2.1 Mở PowerShell với quyền Admin

Click Start → gõ `PowerShell` → chuột phải → **Run as administrator**.

### 2.2 Cài đặt WSL

```powershell
wsl --install
```

Lệnh này tự động:
- Bật tính năng WSL
- Bật Virtual Machine Platform
- Tải Ubuntu 22.04 LTS về máy
- Set Ubuntu làm default distro

### 2.3 Restart máy

Sau khi restart, Ubuntu sẽ tự mở yêu cầu tạo username + password.

### 2.4 Verify

```powershell
wsl --status
```

Expect output:
```
Default Distribution: Ubuntu
Default Version: 2
```

### 2.5 Update Ubuntu

```bash
wsl
sudo apt update && sudo apt upgrade -y
```

---

## 3. Cài Docker Desktop

### 3.1 Download

Vào [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) → tải bản **Windows (AMD64)**.

### 3.2 Cài đặt

Chạy installer → giữ mặc định (bật WSL2 backend, shortcut desktop) → **Install**.

### 3.3 Restart

Sau khi cài xong, restart Windows (Docker Desktop cần khởi động cùng OS).

### 3.4 Khởi động Docker Desktop

Mở **Docker Desktop** từ Start menu → đợi icon ở system tray chuyển sang **xanh lá** (sẵn sàng).

### 3.5 Verify

```powershell
docker --version
docker compose version
docker run hello-world
```

Expect:
- `docker --version` → `Docker version 24.x.x, build ...`
- `docker compose version` → `Docker Compose version v2.x.x`
- `docker run hello-world` → cuối cùng có dòng `Hello from Docker!`

Nếu `docker run hello-world` fail → mở Docker Desktop → Settings → Resources → WSL Integration → bật Ubuntu.

---

## 4. Chuẩn bị repo

### 4.1 Clone (nếu chưa có)

```powershell
cd E:\
git clone <repo-url> SoHoaTaiLieu_DATN
cd SoHoaTaiLieu_DATN
```

### 4.2 Tạo file `.env`

```powershell
Copy-Item .env.example .env
```

Mở `.env` bằng editor, giữ nguyên giá trị mặc định cho dev (đã an toàn cho local). **Không commit**.

---

## 5. Cài oasdiff

oasdiff dùng để so sánh OpenAPI spec hiện tại với runtime schema sinh từ FastAPI — bắt breaking change sớm.

### 5.1 Windows (native)

1. Vào [github.com/oasdiff/oasdiff/releases/latest](https://github.com/oasdiff/oasdiff/releases/latest).
2. Download `oasdiff_xxx_windows_amd64.zip`.
3. Giải nén vào `C:\tools\oasdiff\`.
4. Thêm `C:\tools\oasdiff\` vào **PATH**:
   - Start → gõ `environment variables` → **Edit the system environment variables**.
   - **Environment Variables** → **Path** (user) → **Edit** → **New** → dán `C:\tools\oasdiff\`.
   - OK → OK → OK.
5. Mở **PowerShell mới** (để load PATH mới) → verify:

```powershell
oasdiff --version
```

### 5.2 WSL (Ubuntu)

```bash
wsl
curl -sSfL https://github.com/oasdiff/oasdiff/releases/latest/download/oasdiff-linux-amd64 \
  -o /usr/local/bin/oasdiff
chmod +x /usr/local/bin/oasdiff
oasdiff --version
```

### 5.3 Verify cách dùng cơ bản

```powershell
# So sánh 2 file OpenAPI (exit 0 = khớp, exit 1 = có breaking change)
oasdiff diff docs/api/openapi.yaml docs/api/openapi.yaml
```

---

## 6. Chạy stack dev

### 6.1 Khởi động stack

```powershell
make up
```

Lệnh này:
- Pull images (Postgres 16 + pgvector, Redis 7, MinIO, build API) ~ 5-10 phút lần đầu.
- Start 4 containers: `ctsv-postgres`, `ctsv-redis`, `ctsv-minio`, `ctsv-api`.
- Mount source code `apps/api/` vào container (hot reload).

### 6.2 Đợi Postgres ready

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Đợi cột `Status` của `ctsv-postgres` hiện `(healthy)`.

### 6.3 Verify env

```powershell
bash scripts/verify-env.sh
```

Expect:
```
=== TỔNG KẾT: 6 pass, 0 fail ===
```

### 6.4 Seed 3 demo users

```powershell
make seed
```

Expect output:
```
admin@ctsv.edu.vn / Demo@2026
staff@ctsv.edu.vn / Demo@2026
student@ctsv.edu.vn / Demo@2026
```

### 6.5 Test API

```powershell
curl http://localhost:8000/health/live
```

Expect:
```json
{"status":"ok"}
```

### 6.6 Đăng nhập thử

```powershell
curl -X POST http://localhost:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"admin@ctsv.edu.vn","password":"Demo@2026"}'
```

Expect HTTP 200 + envelope `{success: true, data: {access_token, ...}}`.

---

## 7. Tắt stack

```powershell
make down       # Stop containers, giữ volumes (data không mất)
make down -v    # Stop + XOÁ volumes (reset sạch — cần seed lại)
```

---

## 8. Troubleshooting

### 8.1 Docker Desktop không start

- Check virtualization đã bật trong BIOS.
- Check Windows feature **Hyper-V** / **Virtual Machine Platform** đã bật.
- Xem logs: `C:\Users\<you>\AppData\Local\Docker\log.txt`.

### 8.2 `docker run hello-world` fail với WSL

- Mở Docker Desktop → Settings → Resources → WSL Integration → bật Ubuntu → **Apply & Restart**.

### 8.3 Port 5432/6379/9000/8000 đã bị chiếm

Sửa `.env`:
```env
POSTGRES_PORT=5433
REDIS_PORT=6380
MINIO_PORT=9002
MINIO_CONSOLE_PORT=9003
API_PORT=8001
```

Rồi `make up` lại.

### 8.4 `oasdiff` không nhận sau khi cài

- Mở **PowerShell mới** (PATH chỉ load khi shell start).
- Test trực tiếp: `& "C:\tools\oasdiff\oasdiff.exe" --version`.

### 8.5 WSL mất kết nối network

```powershell
wsl --shutdown
netsh winsock reset
Restart-Computer
```

---

## 9. References

- [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- [WSL2 Install](https://learn.microsoft.com/en-us/windows/wsl/install)
- [oasdiff docs](https://github.com/oasdiff/oasdiff)
- [PostgreSQL 16 + pgvector image](https://hub.docker.com/r/pgvector/pgvector)
- Rule workspace: `.cursor/rules/08-governance.mdc` (giới hạn quyền agent khi sửa code).
- Plan chi tiết: `docs/plans/2026-08-09-phase-1.5-dev-env.md`.
