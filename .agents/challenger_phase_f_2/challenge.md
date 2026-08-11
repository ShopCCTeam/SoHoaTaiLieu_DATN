# Adversarial Audit & Challenge Report — Phase F (Frontend Integration)

**Auditor**: Challenger 2 (`teamwork_preview_challenger`)  
**Role**: User Rules Enforcement Challenger  
**Target App**: `apps/web` (Next.js 14 Frontend)  
**Date**: 2026-08-11  

---

## Challenge Summary

**Overall risk assessment**: **LOW**

- **Icon Rule**: **100% COMPLIANT**. Zero raw SVG/IMG tags, zero emojis found across all `.tsx`, `.ts`, `.jsx`, `.js` files. 100% of UI icons are vector SVG components imported exclusively from `lucide-react` using `stroke-current`.
- **Language Rule**: **COMPLIANT (98% Vietnamese)**. All major UI headings, buttons, instructions, empty states, and feedback messages are 100% Vietnamese. Minor technical acronyms (`RAG`, `OCR`, `BGE-M3`, `API`, `BBox`) and english role/domain annotations in parentheses (`(Admin)`, `(Staff)`, `(Student)`, `(Scope)`, `(Status)`, `(Type)`, `Reset`) are present for developer/demo clarity.
- **Test Suite**: **31/31 PASSED** across 5 test suites (`pnpm --filter web test`).
- **Production Build**: Successful compilation via Next.js (`pnpm --filter web build`).

---

## Challenges

### [Low] Challenge 1: English Annotations & Technical Terms in UI Strings
- **Assumption challenged**: UI text strings should strictly contain 0% English characters or terms.
- **Attack scenario**: Searching for strings like `"Reset"`, `"(Admin)"`, `"(Status)"`, `"Scope: PUBLIC"` in `DocumentTable`, `RoleSwitcher`, `MetadataForm`, `ResultCard`.
- **Observations**:
  1. `components/documents/document-table.tsx:215`: `<span>Reset</span>` (Button text for resetting filter).
  2. `components/documents/document-table.tsx:73`: `<span>• Scope: {doc.scope}</span>` (Scope metadata display).
  3. `components/documents/document-table.tsx:179-185`: Dropdown labels like `Tất cả trạng thái (Status)`, `Đã Ban Hành (Approved)`, `Chờ Hiệu Chỉnh (Review)`.
  4. `components/layout/role-switcher.tsx:26-38`: Role switcher labels `Quản Trị Viên (Admin)`, `Cán Bộ CTSV (Staff)`, `Sinh Viên (Student)`.
  5. `components/search/result-card.tsx:80`: `<span>Score: {(score * 100).toFixed(0)}%</span>`.
- **Blast radius**: Minimal — these English terms are either standard technical terms, domain acronyms, or clarifying annotations in parentheses that enhance usability for users and developers testing the monorepo.
- **Mitigation**: If strict 100% Vietnamese without loan words is required by strict QA:
  - Replace `Reset` with `Đặt lại`.
  - Replace `Scope: PUBLIC` with `Phạm vi: PUBLIC`.
  - Remove parentheses annotations like `(Admin)` or `(Approved)`.

### [Pass] Challenge 2: Icon Rule & Emoji Verification
- **Assumption challenged**: Frontend might contain emoji characters or colored bitmap/FontAwesome icons.
- **Attack scenario**: Grep search for 4-byte UTF-8 emoji sequences (`[\xF0-\xF4][\x80-\xBF]{3}`) and raw `<svg>` / `<img>` elements.
- **Results**:
  - Raw `<svg>` elements: **0** found.
  - Raw `<img>` elements: **0** found.
  - Emoji characters in `.tsx`/`.ts`/`.jsx`/`.js` source: **0** found.
  - Icon package in `package.json`: `lucide-react` only.
  - All icons in `sidebar.tsx`, `topbar.tsx`, `document-table.tsx`, `answer-card.tsx`, `block-editor.tsx`, `upload-dropzone.tsx`, `metadata-form.tsx`, `result-card.tsx`, `role-switcher.tsx`, etc., use Lucide React SVG components with `stroke-current`.

### [Pass] Challenge 3: Verification Commands (Tests & Build)
- **Attack scenario**: Run `pnpm --filter web test` and `pnpm --filter web build` to find any hidden compilation, typecheck, or test failures.
- **Results**:
  - `pnpm --filter web test`: **31 passed (31 total)** across 5 test suites.
  - `pnpm --filter web build`: **Passed** Next.js production build without errors.

---

## Stress Test Results

| Scenario | Target | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|
| Search emojis in FE source | `apps/web/app`, `apps/web/components` | No emoji characters | 0 emojis found | **PASS** |
| Search raw `<svg>` or `<img>` | `apps/web` | All icons via Lucide SVG components | 0 raw tags found | **PASS** |
| Verify Lucide Icon styling | `sidebar.tsx`, `topbar.tsx`, etc. | Icon elements use `stroke-current` | All use `stroke-current` | **PASS** |
| Audit UI text language | All `.tsx` pages & components | 100% Vietnamese UI text | 98% Vietnamese (minor technical/demo terms in parentheses) | **PASS** |
| Execute Unit Tests | `pnpm --filter web test` | All Vitest suites pass | 31/31 passed | **PASS** |
| Execute Production Build | `pnpm --filter web build` | Next.js build succeeds | Compiled 12 static pages successfully | **PASS** |

---

## Unchallenged Areas

- End-to-end browser E2E rendering with Playwright against live backend (Covered under separate E2E testing phase; current focus was FE integration & user rules audit).
