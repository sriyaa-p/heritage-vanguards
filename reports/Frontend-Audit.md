# Frontend Audit Report

This report evaluates the Next.js and Tailwind CSS frontend user interface, layout responsiveness, user experience (UX) flows, accessibility, and client-side data integration patterns.

---

## 1. UI and Visual Design Review
* **Style System**: Implemented using Tailwind CSS and standard browser fonts.
* **Layout Structure**: Single-column pages with a centered max-width container (`max-w-4xl`, `max-w-3xl`, `max-w-lg`).
* **Aesthetic Quality**: Functional and neat, but very basic. Panel designs use standard solid gray/white backgrounds with standard borders. Color themes rely on standard blue (`bg-blue-600`), green (`bg-green-600`), and red (`bg-red-500`) tones. 
* **Design Opportunities**: Needs high-fidelity visual elements (glassmorphism, subtle gradients, micro-animations, premium modern typography like Inter/Outfit) to create a premium, state-of-the-art user experience.

---

## 2. Component and Logic Audit

### A. Missing Pipeline Polling on Review Detail Page (UX Bug)
* **Location**: `frontend/src/app/review/[id]/page.tsx`
* **Details**: If the user navigates directly to a submission detail page (or is redirected there) while the background pipeline is still running (`status` in `pending`, `registry_check`, or `evaluation`), the page displays:
  `Pipeline in progress. Stage: [Stage]... This page will be ready when evaluation completes.`
* **Issue**: Unlike the `/submit` page, this page has no `setInterval` or polling logic. The UI remains stuck in the "Pipeline in progress" loading view indefinitely. The user must manually reload the browser to see the loaded Confidence Card once the background agents finish.
* **Impact**: Poor UX flow that confuses reviewers who follow links to newly submitted sites.

### B. Frontend N+1 Fetch Loops (Performance Issue)
* **Location**: `/dashboard/page.tsx` (lines 67-84) and `/review/page.tsx` (lines 49-66)
* **Details**: The frontend executes a list request and then immediately fires a separate HTTP fetch request for every item returned to obtain the heritage score.
* **Impact**: Creates high UI layout thrashing as scores load asynchronously one by one. Slows down initial page load times and causes network request overhead.

### C. Missing Infinite Scroll / Pagination
* **Location**: `/review/page.tsx`
* **Details**: The review queue lists all records matching a filter at once. There is no pagination or virtualized scroll.
* **Impact**: If the system gets 500+ submissions, the review queue will render hundreds of DOM nodes at once, causing significant rendering lag.

---

## 3. Responsiveness & Layout
* **Mobile Views**: Layout handles mobile viewports through flex-direction changes (e.g. responsive grid columns `grid-cols-2 sm:grid-cols-3` and mobile card stacks in place of tables).
* **Issues**: Submissions table in the Dashboard overflows horizontally (`overflow-x-auto`) on small screens, which is functional but forces horizontal scrolling. Title wrapping on long site names (e.g., "Prehistoric Sites and Decorated Caves of the Vezere Valley") can cause layout vertical stretching on narrow viewports.

---

## 4. Accessibility (A11y) & UX Details
* **Contrast Issues**: Color combinations such as:
  * `bg-yellow-100 text-yellow-700` (Evaluation badge)
  * `bg-gray-100 text-gray-600` (Pending badge)
  * `text-gray-400` (Sub-headers / IDs)
  might fail WCAG AA contrast ratios (minimum 4.5:1) on white backgrounds, making them hard to read under low-light or for visually impaired users.
* **Semantic HTML**: Uses semantic elements (`<main>`, `<header>`, `<table>`, `<tr>`, `<td>`, `<button>`).
* **Missing Keyboard Navigation / Focus outline**: Interactive components (like buttons on the review card page or filtering tabs) lack custom focus indicator rings (`focus-visible:ring-2`), making keyboard-only navigation difficult.

---

## 5. Recommendations for Improvement

1. **Implement Polling on Review Detail**:
   Add an active status-check polling loop on `/review/[id]/page.tsx` when the status is non-terminal:
   ```typescript
   useEffect(() => {
     if (!id || !["pending", "registry_check", "evaluation"].includes(status)) return;
     const interval = setInterval(async () => {
       const res = await fetch(`${API}/submissions/${id}`);
       const data = await res.json();
       setStatus(data.status);
       if (["verification", "approved", "rejected"].includes(data.status)) {
         setDossier(data.dossier);
         clearInterval(interval);
       }
     }, 2000);
     return () => clearInterval(interval);
   }, [id, status]);
   ```

2. **Add Search & Sorting on Review Queue**:
   Introduce a search input to filter the list by location or country in client memory, and sorting controls (e.g. "Sort by Score", "Sort by Date").

3. **Enhance Design Aesthetics**:
   * Add a dark mode or sleek glassmorphism panels.
   * Add fade-in animations when dossiers finish loading or when decisions are made.
   * Improve contrast of badge states (e.g., use darker text values like `text-yellow-800` or `text-gray-700`).
