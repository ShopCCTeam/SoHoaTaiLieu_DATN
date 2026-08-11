# Testing Standards

## TDD là Mặc Định (Test-Driven Development)
1. Viết test **RED** trước (chạy fail).
2. Viết code **GREEN** tối thiểu để pass test.
3. **REFACTOR**: cải thiện chất lượng code, giữ test pass.
- Áp dụng cho: business logic, utility functions, custom hooks, repositories, services.

## Khi nào KHÔNG cần test
- Type definitions, constants, pure configuration.
- Component chỉ làm presentation pass-through.
- Mock fixtures dùng cho demo.

## Test Layer & Target Coverage
| Layer | Tool | Mục tiêu Coverage |
|---|---|---|
| Unit | Vitest (FE), pytest (BE) | ≥ 80% cho service & domain logic |
| Component | Vitest + Testing Library | ≥ 60% cho shared component |
| Integration | HTTPX/pytest (BE), MSW (FE) | ≥ 50% cho API endpoint |
| E2E | Playwright | Critical path: login → upload → OCR → search → chat |

## Convention
- File test đặt cạnh file source: `foo.ts` → `foo.test.ts` hoặc trong `tests/` / `__tests__/`.
- Tên test theo cú pháp `should <behavior> when <condition>`.
- Mỗi test độc lập, không share state mutable, không phụ thuộc thứ tự chạy.

## E2E Test (Playwright)
- Test critical path trong thư mục `e2e/`.
- Dùng fixture mock BE (MSW) — không gọi BE thật trong CI ngoại trừ E2E staging check.
- Chạy `pnpm test` / `uv run pytest` trước khi commit & merge.
