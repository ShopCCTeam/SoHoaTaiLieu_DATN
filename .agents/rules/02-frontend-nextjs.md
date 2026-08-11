# Frontend Standards (Next.js + React + TS)

Scope: `apps/web/**/*.{ts,tsx,js,jsx}`

## Tech stack cố định
- **Framework**: Next.js 14+ (App Router), TypeScript Strict Mode.
- **Styling**: Tailwind CSS + CSS variables cho design system.
- **State Management**: Zustand v5 cho client state, TanStack Query v5 cho server state.
- **Animation**: Framer Motion.
- **Icons**: Lucide React (**100% SVG icon**, **tuyệt đối KHÔNG dùng icon màu**).
- **Validation & Form**: Zod cho validation runtime, React Hook Form cho form phức tạp.

## Component Rules
- **Function component** only. Không dùng class component.
- Tách component khi > 150 dòng hoặc > 2 concern.
- Props interface khai báo inline ngay trên component, dùng `React.FC<Props>`.
- Một file = một component export. Sub-component nội bộ → file riêng nếu > 30 dòng.

## Server vs Client Components
- Default là **Server Component**. Chỉ thêm `"use client"` khi cần:
  - `useState`, `useEffect`, `useRef`
  - Event handlers (`onClick`, `onChange`)
  - Browser APIs (`localStorage`, `IntersectionObserver`)
- **Không** fetch data trong Client Component nếu có thể fetch trong Server Component.

## Performance (theo Vercel React Best Practices)
- ❌ Không barrel imports (`import { Button } from "@/components"`) — import trực tiếp từ file component.
- ✅ Dùng `next/dynamic` cho component nặng (> 50KB).
- ✅ `React.memo` chỉ khi prop là non-primitive và render tốn > 5ms.
- ✅ Dùng `useDeferredValue` cho search input lớn.
- ✅ Pagination hoặc virtualization cho list > 100 items.
- ✅ Image: dùng `next/image` với `width/height` hoặc `fill + sizes`.

## Accessibility (A11y)
- Mọi `<button>` icon-only phải có `aria-label`.
- Mọi `<img>` phải có `alt`.
- Heading hierarchy đúng: `<h1>` → `<h2>` → `<h3>` không nhảy cấp.
- Focus state visible (Tailwind `focus-visible:ring-2`).
- Form label gắn với input qua `htmlFor`/`id`.

## State Management
- **Server data** (fetch API): TanStack Query. **Không** lưu vào Zustand.
- **UI ephemeral state** (modal, dropdown, tab): `useState` cục bộ.
- **Cross-page state** (auth, theme, role): Zustand với `persist` middleware.
- **Derived state**: tính trong render, không lưu (`useMemo` chỉ khi tốn > 5ms).

## Error handling
- Mỗi page có `error.tsx` riêng.
- Mutation có `onError` → toast user-friendly.
- API error: đọc `error.response.data.message` (hoặc RFC 7807 detail), không show raw error object.

## Refer Skill khi làm việc
- Skill `.skills/vercel-react-best-practices/` cho rule tối ưu hiệu năng.
- Skill `.skills/react-best-practices/` cho component design patterns.
- Skill `.skills/frontend-design/` cho UI/UX principles.
- Skill `.skills/web-design-guidelines/` cho a11y & WCAG.
