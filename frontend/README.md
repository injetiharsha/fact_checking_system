# FactLens Frontend

This frontend is a static HTML/CSS/JS app.

## Run locally

```bash
npm run dev
```

That serves `index.html` at [http://localhost:3000](http://localhost:3000).

## API configuration

Edit `public/config.js` to point `apiBaseUrl` at your backend origin.
For local development, it defaults to `http://127.0.0.1:8000`.

## Deployment

This version is suitable for GitHub Pages or any static host.
Make sure the backend is reachable over HTTPS and allows CORS from the frontend origin.
