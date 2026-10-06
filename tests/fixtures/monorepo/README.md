# Funds Watch

An oversight platform for local area development funds, built for a hackathon.

## Run it

```bash
pip install -r requirements.txt
uvicorn api.main:app --host 127.0.0.1 --port 8000
cd web
npm install
npm run dev                      # http://localhost:5173
```

Data comes from the public dashboard (<https://funds.example.gov.in/dashboard.html>).
