# Hướng dẫn sử dụng AI trong dự án

Tài liệu này quy định cách dùng trợ lý AI như một công cụ hỗ trợ phát triển, không thay thế trách nhiệm rà soát của con người.

## Phạm vi và tính xác thực

AI có thể hỗ trợ phân tích mã nguồn, đề xuất thiết kế, viết bản nháp mã/tài liệu và thực hiện kiểm tra theo yêu cầu. Mọi kết luận do AI tạo ra, kể cả các cụm như “đã hoàn tất” hoặc “đã xác minh”, chỉ có giá trị khi đi kèm bằng chứng có thể lặp lại: diff mã nguồn, contract, lệnh kiểm thử và kết quả thực thi.

Thư mục `.agents/` là artefact làm việc cục bộ. Thư mục này được giữ trên máy để tham khảo nhưng bị Git bỏ qua; nội dung của nó không phải tài liệu chính thức, không được dùng làm bằng chứng chất lượng và không được đưa vào pull request hay bản phát hành.

## Quy trình bắt buộc

Trước khi chấp nhận thay đổi có AI hỗ trợ, người thực hiện phải đọc rule/ADR/contract liên quan, rà soát diff và chạy các quality gate phù hợp. Thay đổi API phải bắt đầu từ `docs/api/openapi.yaml`; kiểm soát RBAC/scope phải nằm ở backend trước truy hồi dữ liệu; không tự tin vào kết quả hiển thị trên frontend.

Kết quả bàn giao phải phân biệt rõ phần đã thay đổi, kiểm thử đã chạy, hạng mục chưa xác minh và giới hạn môi trường. Không tự commit, push, chạy migration, Docker Compose hoặc thao tác phá huỷ nếu chưa có yêu cầu rõ ràng của người có thẩm quyền.

## Bảo mật và dữ liệu

Không đưa password, token, PII, `.env`, PDF/OCR thật, dữ liệu trong `data/` hoặc model artifact ra ngoài phạm vi được phê duyệt. Nếu phát hiện secret có khả năng đã lọt vào lịch sử công khai, phải báo cáo để chủ sở hữu **thu hồi/đổi khóa** trước; xóa tệp đơn thuần không được xem là biện pháp khắc phục.
