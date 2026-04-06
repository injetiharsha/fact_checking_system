window.FACTLENS_CONFIG = {
  // Static frontend configuration.
  // Use localhost for local dev, and replace with your HTTPS backend origin for deployment.
  apiBaseUrl: (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://127.0.0.1:8000"
    : "http://13.217.24.76:8000/",
};