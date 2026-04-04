**Predeploy**
Use this after benchmark gates are done and before deployment.

Smoke benchmark pack:
```powershell
.\.venv\Scripts\python.exe benchmark_multi_test.py --claims-file benchmark_claims\predeploy_smoke_10.json --output logs\predeploy_smoke_10_results.json
```

API smoke tests:
Start the API:
```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Health check:
```powershell
curl http://127.0.0.1:8000/health
```

Single-claim smoke tests:
```powershell
curl -X POST http://127.0.0.1:8000/check -H "Content-Type: application/json" -d "{\"claim\":\"Mars has two moons.\"}"
curl -X POST http://127.0.0.1:8000/check -H "Content-Type: application/json" -d "{\"claim\":\"Humans can breathe in space without equipment.\"}"
curl -X POST http://127.0.0.1:8000/check -H "Content-Type: application/json" -d "{\"claim\":\"The Indian Space Research Organisation is commonly known by the acronym ISRO.\"}"
curl -X POST http://127.0.0.1:8000/check -H "Content-Type: application/json" -d "{\"claim\":\"హైదరాబాద్ తెలంగాణ రాజధాని.\"}"
curl -X POST http://127.0.0.1:8000/check -H "Content-Type: application/json" -d "{\"claim\":\"ಚೆನ್ನೈ ಕರ್ನಾಟಕದ ರಾಜಧಾನಿ.\"}"
```

What to check:
- response status is `200`
- response JSON is valid
- verdict is sensible
- evidence is present for checkable claims
- app does not crash or hang

Short rate-limit/load check:
```powershell
.\.venv\Scripts\python.exe benchmark_multi_test.py --claims-file benchmark_claims\predeploy_smoke_10.json --output logs\predeploy_smoke_10_load.json
```

Deploy only if:
- health endpoint is healthy
- smoke pack does not regress badly
- no burst of `429` errors
- no repeated empty-evidence failures

**Postdeploy**
Immediately after deploy:

Health:
```powershell
curl http://127.0.0.1:8000/health
```

Live smoke:
```powershell
curl -X POST http://127.0.0.1:8000/check -H "Content-Type: application/json" -d "{\"claim\":\"Mars has two moons.\"}"
curl -X POST http://127.0.0.1:8000/check -H "Content-Type: application/json" -d "{\"claim\":\"India became independent in 1950.\"}"
```

Monitor:
- request failures
- timeouts
- `429` rate from Groq and search providers
- `NEUTRAL` rate
- blocked-not-checkable rate
- known-failure families

Daily manual review:
- 10 random successful responses
- all user-reported bad responses
- all high-confidence false positives
