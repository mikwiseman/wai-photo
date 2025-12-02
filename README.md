# Photo Masking API

A FastAPI-based REST API that applies decorative masks to photos. The API crops images to mask shapes, prioritizing the top portion to capture faces in portrait photos.

## API Specification

**Base URL**: `https://web-production-dd101.up.railway.app`

### Authentication

All protected endpoints require an API key passed in the `X-API-Key` header.

```
X-API-Key: your-api-key
```

### Endpoints

#### Health Check
```
GET /health
```
Returns API health status. No authentication required.

**Response:**
```json
{
  "status": "healthy"
}
```

---

#### Mask by URL
```
POST /mask-by-url
```
Apply a random mask to an image fetched from a URL.

**Headers:**
| Header | Required | Description |
|--------|----------|-------------|
| Content-Type | Yes | `application/json` |
| X-API-Key | Yes | Your API key |

**Request Body:**
```json
{
  "url": "https://example.com/photo.jpg"
}
```

**Response:**
```json
{
  "success": true,
  "mask_used": "mask_3.png",
  "image_data": "<base64-encoded PNG>",
  "content_type": "image/png"
}
```

**Example:**
```bash
curl -X POST "https://web-production-dd101.up.railway.app/mask-by-url" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"url": "https://example.com/photo.jpg"}'
```

---

#### Mask by Upload
```
POST /mask-by-upload
```
Apply a random mask to an uploaded image file.

**Headers:**
| Header | Required | Description |
|--------|----------|-------------|
| X-API-Key | Yes | Your API key |

**Request Body:** `multipart/form-data` with `file` field

**Supported formats:** JPEG, PNG, WebP, GIF

**Response:**
```json
{
  "success": true,
  "mask_used": "mask_1.png",
  "image_data": "<base64-encoded PNG>",
  "content_type": "image/png"
}
```

**Example:**
```bash
curl -X POST "https://web-production-dd101.up.railway.app/mask-by-upload" \
  -H "X-API-Key: your-api-key" \
  -F "file=@photo.jpg"
```

---

### Error Responses

| Status Code | Description |
|-------------|-------------|
| 400 | Bad request (invalid URL, unsupported format) |
| 401 | Invalid or missing API key |
| 413 | Image exceeds 10MB limit |
| 500 | Server error |

**Error Response Format:**
```json
{
  "detail": "Error message"
}
```

---

## Local Development

### Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run
```bash
uvicorn main:app --reload --port 8000
```

### Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| API_KEY | API key for authentication | No (disabled if not set) |

---

## Deployment

The API is configured for Railway deployment with the included `Procfile`.

1. Connect GitHub repo to Railway
2. Set `API_KEY` environment variable
3. Deploy

---

## Interactive Docs

- Swagger UI: `/docs`
- ReDoc: `/redoc`
