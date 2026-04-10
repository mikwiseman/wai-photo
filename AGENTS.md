# WaiPhoto

Photo masking API -- applies decorative masks to photos, prioritizing faces.

## Stack

- **Framework**: FastAPI (Python)
- **Deploy**: Railway
- **Auth**: API key via `X-API-Key` header

## Commands

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000   # http://localhost:8000/docs
```

## Endpoints

- `POST /mask-by-url` -- mask image from URL
- `POST /mask-by-upload` -- mask uploaded image
- `GET /health` -- health check
