export const API =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined"
    ? (window.location.port === "3000"
        ? "http://localhost:8000"
        : window.location.origin)
    : "http://localhost:8000");

