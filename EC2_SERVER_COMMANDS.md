# EC2 Server Commands

Use these commands on your AWS EC2 terminal inside the project folder.

## Go To Project

```bash
cd ~/fact_checking_system
source .venv/bin/activate
```

## Start Server In Foreground

Use this when you want to watch logs live in the terminal.

```bash
cd ~/fact_checking_system
source .venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## Stop Foreground Server

In the same terminal where the server is running:

```bash
Ctrl+C
```

## Start Server In Background

Use this when you want the server to keep running after you leave the terminal.

```bash
cd ~/fact_checking_system
source .venv/bin/activate
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
```

## Check If Server Is Running

```bash
ps aux | grep uvicorn
```

If running, you should see a line like:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## Stop Background Server

```bash
pkill -f "uvicorn main:app"
```

## Confirm It Stopped

```bash
ps aux | grep uvicorn
```

If only `grep uvicorn` appears, the server is stopped.

## Health Check On EC2

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"message":"Fact Checking System Running"}
```

## Public Health Check

Run this from your laptop browser or terminal:

```text
http://EC2_PUBLIC_IP:8000/health
```

Replace `EC2_PUBLIC_IP` with your real public IP.

## View Recent Logs

```bash
tail -n 30 ~/fact_checking_system/server.log
```

## Full Restart

```bash
cd ~/fact_checking_system
source .venv/bin/activate
pkill -f "uvicorn main:app"
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
curl http://127.0.0.1:8000/health
```
