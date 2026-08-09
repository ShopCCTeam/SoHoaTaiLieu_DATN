import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E config — Frontend.
 *
 * Hiện chưa có test nào (Phase 0). File này tồn tại để:
 * 1. CI có thể chạy `pnpm test:e2e` mà không fail vì thiếu config.
 * 2. Chuẩn hoá cấu hình: dùng MSW để mock BE (không gọi API thật trong CI).
 * 3. Dùng Chromium only ở MVP; mở rộng WebKit/Firefox khi cần.
 *
 * Khi có test thật, tạo file ở `apps/web/e2e/*.spec.ts` và đảm bảo:
 * - Mock tất cả API call bằng MSW (xem `.skills/webapp-testing/`).
 * - Reset state giữa các test bằng fixtures.
 * - Không phụ thuộc vào BE thật đang chạy.
 */
export default defineConfig({
  testDir: "./e2e",
  // Không scan các test folder khác để tránh nhầm với vitest
  testIgnore: ["**/node_modules/**", "**/.next/**"],
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "pnpm dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
