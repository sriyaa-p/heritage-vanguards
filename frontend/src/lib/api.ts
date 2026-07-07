// API base URL resolution — works in all environments:
//   1. Explicit env var (Railway/Render/Vercel production deployments)
//   2. Same-origin inference: if the frontend is NOT on port 3000, the backend
//      is served via the same host (e.g. Nginx reverse-proxy or Railway service mesh)
//   3. Local dev fallback: direct backend at localhost:8000
export const API =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined"
    ? window.location.port === "3000"
      ? "http://localhost:8000"   // local Next.js dev server → direct backend
      : window.location.origin    // Docker/Nginx/Railway → same origin, Nginx proxies /api
    : "http://localhost:8000");    // SSR fallback
