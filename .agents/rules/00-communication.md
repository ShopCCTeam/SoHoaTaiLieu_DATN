# Communication & Project Conventions

## Ngôn ngữ
- **Giao tiếp với người dùng**: 100% tiếng Việt (bao gồm cả comment, commit message, doc, walkthrough, artifact).
- **Code identifier** (biến, hàm, class, file): tiếng Anh theo chuẩn ngành.
- **UI text, error message, log message**: tiếng Việt.
- **Doc, README, ADRs, walkthrough**: tiếng Việt.

## Rule Bắt Buộc Về Icons (User Global Rule)
- **KHÔNG DÙNG ICON MÀU**.
- **100% PHẢI DÙNG ICON SVG** (VD: Lucide React SVG components hoặc custom SVG vector inline).

## Tone & Phong cách làm việc
- Ngắn gọn, đi thẳng vào việc. Tránh small-talk.
- Luôn có bảng tóm tắt hoặc điểm chính trước khi vào chi tiết.
- Khi có nhiều lựa chọn thiết kế hoặc yêu cầu chưa rõ → dùng câu hỏi trắc nghiệm hoặc lựa chọn cụ thể thay vì liệt kê bullet mờ ảo.

## Quy chuẩn File & Folder
- File code ≤ 300 dòng (warning ở 500 dòng, refactor bắt buộc).
- Tên file theo kebab-case (`upload-dropzone.tsx`).
- Tên class PascalCase, hàm camelCase, hằng số UPPER_SNAKE.
- Một file = một concern. Tách component/service khi > 1 trách nhiệm.

## Commit & Branch
- Commit tiếng Việt, conventional: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.
- Một commit = một concern. Không trộn FE + BE trong cùng commit trừ khi coupling chặt.
- Branch: `feat/<phase>-<short-desc>`, `fix/<issue>-<short-desc>`.

## Quy trình Làm việc của Agent
- Trước khi sửa code → đọc file hiện tại bằng tool xem file, không sửa mù.
- Sau khi sửa substantive → check `tsc` / `lint` / `test`.
- Mọi task đa bước → track tiến độ rõ ràng.
- Mọi task phức tạp → viết plan vào `docs/PROGRESS.md` trước khi code.
