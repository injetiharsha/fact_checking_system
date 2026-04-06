window.FACTLENS_CONFIG = {
  // Local dev hits localhost backend directly.
  // Vercel uses /backend rewrite proxy.
  // FastAPI-hosted frontend (same host) uses same-origin API.
  apiBaseUrl: (() => {
    const host = String(window.location.hostname || "").toLowerCase();
    if (host === "localhost" || host === "127.0.0.1") return "http://127.0.0.1:8000";
    if (host.endsWith(".vercel.app")) return "/backend";
    return "";
  })(),
};