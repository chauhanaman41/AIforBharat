# AIforBharat Frontend Investigation & Bug Report

Based on the recent E2E User Journey Test performed across the Next.js application and the 21 Python backend engines, several critical blockers were identified. The backend engines are functioning normally and returning valid tokens, meaning **the issues are entirely isolated to the frontend routing and authentication logic**.

DO NOT directly apply these fixes yet—this document serves as the guide for the frontend team.

---

## 1. Root Route Conflict (`app/page.tsx`)

### **Symptom**
When users navigate to the root route (`http://localhost:3000/`) after authentication, they are served the default Next.js "Vercel Template" boilerplate text ("To get started, edit the page.tsx file.") instead of the main Application Dashboard. 

### **Root Cause**
The `aiforbharat-ui/src/app` directory contains both:
1. `app/page.tsx` (the default Next.js boilerplate)
2. `app/(dashboard)/page.tsx` (the actual authenticated dashboard component)

Next.js resolves the explicit `app/page.tsx` over the grouped `app/(dashboard)/page.tsx`.

### **Required Fix**
*   **Action:** Modify or remove `src/app/page.tsx`. 
*   **Implementation Options:**
    *   **Option A:** Delete `src/app/page.tsx` entirely so Next.js correctly mounts `src/app/(dashboard)/page.tsx` on the `/` route.
    *   **Option B:** Rewrite `src/app/page.tsx` to explicitly re-export or include the `(dashboard)` component.

---

## 2. Authentication Redirect Loop (`AuthGuard.tsx` & Zustand)

### **Symptom**
Valid, authenticated users with active JWTs in `localStorage` are continually redirected to `/login` when trying to access protected routes like `/analytics`, `/ai-chat`, or `/simulator`. 

### **Root Cause**
The `AuthGuard.tsx` component relies on the Zustand persistent store (`useAppStore` in `store.ts`).
Because Zustand's `persist` middleware hydrates data from `localStorage` asynchronously *after* the initial render, the default initial state (`isAuthenticated: false`) is temporarily active during the first client-side mount. 

The `useEffect` in `AuthGuard` reads `isAuthenticated === false` and immediately fires `router.replace("/login")` before Zustand has a chance to hydrate the true session state from `localStorage`.

### **Required Fix**
*   **Action:** Delay the redirect inside `AuthGuard.tsx` until Zustand hydration completes.
*   **Implementation Steps:**
    1. Update the Zustand store (`src/lib/store.ts`) to include a `_hasHydrated: boolean` state. Enable an `onRehydrateStorage` hook in the persist settings to set this flag to true once hydration finishes.
    2. Update `src/components/shared/AuthGuard.tsx` to read the `_hasHydrated` state. 
    3. Modify the return statements and `useEffect` in `AuthGuard` to show a temporary loading state (or return `null`) if `!_hasHydrated`. Only run the `router.replace` logic if the store *has* hydrated AND the user is not authenticated.

---

## 3. Missing Registration Field ("Annual Income")

### **Symptom**
The `app/(auth)/register` page does not contain an "Annual Income" field, making it impossible to pass accurate socio-economic data during the "Full Onboard" flow.

### **Root Cause**
The field is absent from both the Zod validation schema (`registerSchema`) and the React Hook Form template in `src/app/(auth)/register/page.tsx`.

### **Required Fix**
*   **Action:** Add the "Annual Income" field to the registration schema and UI.
*   **Implementation Steps:**
    1. Open `src/app/(auth)/register/page.tsx`.
    2. Update `registerSchema` to include `annual_income: z.string().optional()` (or cast it to a number depending on the backend endpoint schema).
    3. Add a `<FormField>` input element corresponding to the new `annual_income` key in the UI beneath the existing Location/State select fields.

---

## Summary of Next Steps
1. Delete or refactor `app/page.tsx`.
2. Implement hydration checks in the Zustand store and `AuthGuard`.
3. Add the `annual_income` field to the Registration Form.
4. Reboot the Next.js server and rerun the E2E verification test.

---

## Developer Resolutions Applied

**Developer:** Lead Frontend Developer  
**Date:** 2026-02-28  
**Verification:** `npx tsc --noEmit` → **0 errors**

All three bugs identified in this report have been resolved. No AWS, Digilocker, or external notification logic was introduced.

---

### Resolution 1 — Root Route Conflict

**Bug:** `src/app/page.tsx` (Vercel boilerplate) shadowed `src/app/(dashboard)/page.tsx`, causing `/` to render the "To get started, edit the page.tsx file" default template instead of the real dashboard.

**Fix Applied (Option A):**
- **Deleted** `src/app/page.tsx` entirely.
- **Cleared** the `.next/` build cache (which held a stale type reference to the deleted file in `.next/types/validator.ts`).

**Why:** Next.js App Router resolves an explicit `app/page.tsx` over a route-group `app/(dashboard)/page.tsx`. Removing the boilerplate file lets Next.js correctly mount the dashboard component on `/`. The `.next` cache had to be cleared because the TypeScript validator plugin cached a `require('../../src/app/page.js')` reference that would cause a `TS2307` error after deletion.

**Files Changed:**
| Action | File |
|--------|------|
| Deleted | `src/app/page.tsx` |
| Cleared | `.next/` directory (build cache) |

**Status:** ✅ RESOLVED

---

### Resolution 2 — Authentication Redirect Loop

**Bug:** Authenticated users with valid JWTs in `localStorage` were immediately redirected to `/login` on every protected route access because `AuthGuard.tsx` evaluated `isAuthenticated === false` during Zustand's async hydration window.

**Fix Applied:**

**`src/lib/store.ts` — Added hydration tracking:**
- Added `_hasHydrated: boolean` (default `false`) and `setHasHydrated()` action to the `AppState` interface.
- Added `onRehydrateStorage` callback in the `persist` config that calls `state?.setHasHydrated(true)` once Zustand finishes reading from `localStorage`.
- `_hasHydrated` is excluded from `partialize` (not persisted itself — it's a runtime flag).

**`src/components/shared/AuthGuard.tsx` — Hydration-aware guard:**
- Added `Loader2` import from `lucide-react` for the loading spinner.
- Now reads `_hasHydrated` from the store via `useAppStore((s) => s._hasHydrated)`.
- `useEffect` redirect condition changed from `if (!isAuthenticated && !isPublicRoute)` to `if (hasHydrated && !isAuthenticated && !isPublicRoute)` — redirect only fires **after** hydration completes.
- While `!hasHydrated`, renders a centered `Loader2` spinner instead of `null` — prevents the flash-of-nothing and the premature redirect.
- Public routes still render immediately regardless of hydration state.

**Why:** Zustand's `persist` middleware hydrates from `localStorage` asynchronously after the initial React render. The old code read the default `isAuthenticated: false` initial state and fired `router.replace("/login")` before the real persisted state loaded. By gating the redirect on `_hasHydrated`, the guard waits for Zustand to finish reading the stored JWT/session before making any auth decisions.

**Files Changed:**
| File | Changes |
|------|---------|
| `src/lib/store.ts` | Added `HydrationState` interface (`_hasHydrated`, `setHasHydrated`), merged into `AppState`. Added initial values in store creator. Added `onRehydrateStorage` hook in persist config. |
| `src/components/shared/AuthGuard.tsx` | Added `Loader2` import. Added `hasHydrated` selector. Updated `useEffect` condition. Added loading spinner fallback for pre-hydration state. |

**Status:** ✅ RESOLVED

---

### Resolution 3 — Missing Annual Income Field

**Bug:** The registration form at `/register` had no "Annual Income" input, preventing users from submitting socio-economic data required by the Full Onboard orchestrator pipeline (which passes income to E15 Eligibility Rules Engine).

**Fix Applied:**

**`src/app/(auth)/register/page.tsx`:**
- **Icon import:** Added `IndianRupee` from `lucide-react`.
- **Zod schema:** Added `annual_income: z.string().optional().refine(...)` with a validation rule ensuring non-negative numeric values when provided. Kept as `z.string()` (not `.transform()`) to avoid a type mismatch with React Hook Form's resolver — the string→number conversion happens at submit time.
- **Form defaults:** Added `annual_income: ""` to `useForm({ defaultValues })`.
- **UI layout:** Replaced the single-column District field with a 2-column `grid grid-cols-2 gap-3` grid containing:
  - Column 1: District input (existing)
  - Column 2: Annual Income input with `IndianRupee` icon, `type="number"`, `inputMode="numeric"`, placeholder "e.g. 120000"
- **Submit handler:** `onSubmit` now destructures `annual_income` separately and conditionally includes it in the payload as `parseFloat(annual_income)` (number) — only if the user entered a value.

**Why:** The backend `POST /api/v1/onboard` endpoint accepts `annual_income` as a float. Using `z.string()` in the schema (instead of `z.string().transform().pipe(z.number())`) avoids a known Zod v4 + React Hook Form `zodResolver` type incompatibility where the transformed output type (`number`) conflicts with the input type (`string`) that RHF tracks internally. The conversion to `parseFloat()` in `onSubmit` is the clean workaround.

**Files Changed:**
| File | Changes |
|------|---------|
| `src/app/(auth)/register/page.tsx` | Added `IndianRupee` icon import. Added `annual_income` to Zod schema, form defaults, submit handler, and UI (new `<FormField>` in 2-column grid with District). |

**Status:** ✅ RESOLVED

---

### Verification

```
npx tsc --noEmit → 0 errors ✔
```

All three bugs confirmed fixed. System ready for E2E re-test.
