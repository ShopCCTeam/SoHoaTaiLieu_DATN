-- Tạo database test cho integration tests.
-- Chạy một lần khi Postgres container khởi tạo lần đầu (docker-entrypoint-initdb.d).
-- Volume cũ phải `docker compose down -v` mới có tác dụng.
CREATE DATABASE ctsv_test OWNER ctsv_app;
