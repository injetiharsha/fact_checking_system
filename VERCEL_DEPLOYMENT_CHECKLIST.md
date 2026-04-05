# Vercel Deployment Checklist (Frontend-Only)

Use this sheet for the recommended architecture:

- frontend on Vercel
- backend on AWS

## What Vercel Must Host

- static files from `frontend/`
- optional custom domain and TLS
- no Python runtime
- no local checkpoints
- no OCR or model warmup

## Plan Comparison Table

Fill the Plan Value and Status columns.

| Requirement | Needed For Frontend-Only Deploy | Your Vercel Plan Value | Status (PASS/FAIL) | Notes |
|---|---|---|---|---|
| Static site hosting | Required |  |  |  |
| Custom domain and TLS | Recommended |  |  |  |
| Frontend asset caching | Recommended |  |  |  |
| Environment config strategy | Must define backend URL cleanly |  |  |  |
| Upload path behavior | Browser uploads must reach AWS backend successfully |  |  |  |
| CORS compatibility | AWS backend must allow Vercel origin |  |  |  |
| Observability | Enough to debug frontend-to-backend failures |  |  |  |

## AWS Backend Checks To Pair With This

- backend exposed over HTTPS
- backend env includes `CORS_ALLOW_ORIGINS` with your Vercel domain
- model cache and checkpoints stored on AWS host, not Vercel
- upload limits sized for PDF and image analysis
- reverse proxy or load balancer timeout exceeds worst-case request duration
