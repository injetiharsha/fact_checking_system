window.FACTLENS_CONFIG = {
  // Static frontend configuration.
  // Local dev hits local backend directly.
  // Production uses same-origin /backend and Vercel rewrites to avoid mixed-content blocks.
  apiBaseUrl: (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://127.0.0.1:8000"
    : "/backend",
};