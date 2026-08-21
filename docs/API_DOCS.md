# Derma Assist — API Documentation

Base URL: `http://localhost:8000`

Interactive Docs: `http://localhost:8000/docs` (Swagger UI)

---

## Authentication

All endpoints except `/auth/google` and `/health` require a JWT token.

Pass it in the `Authorization` header:
```
Authorization: Bearer <jwt_token>
```

---

## Endpoints

### POST /auth/google

Authenticate with Google OAuth or dev token.

**Request Body:**
```json
{
  "token": "google-id-token-or-dev-token"
}
```

**Response:**
```json
{
  "access_token": "jwt-token",
  "token_type": "bearer",
  "user": {
    "user_id": 1,
    "name": "User Name",
    "email": "user@email.com",
    "picture": "url"
  }
}
```

---

### POST /predict

Full skin analysis pipeline.

**Request:** `multipart/form-data`
- `image` (file, required): Skin image (JPG/JPEG/PNG, max 10MB)
- `symptoms` (string, optional): User symptom description

**Response:**
```json
{
  "case_id": 1,
  "predicted_disease": "Eczema",
  "confidence": 0.85,
  "predictions": [
    {
      "rank": 1,
      "disease": "Eczema",
      "image_score": 0.87,
      "symptom_score": 0.82,
      "combined_score": 0.855
    },
    ...
  ],
  "original_image": "base64...",
  "gradcam": {
    "heatmap": "base64...",
    "overlay": "base64..."
  },
  "symptoms_text": "itchy red patches",
  "reasoning": {
    "summary": "...",
    "evidence": "...",
    "precautions": "...",
    "consult_doctor": "...",
    "clarifying_question": "..."
  },
  "disease_info": { ... },
  "is_low_confidence": false,
  "is_conflicting": false,
  "image_weight": 0.7,
  "symptom_weight": 0.3,
  "disclaimer": "..."
}
```

---

### GET /history

Get the current user's case history.

**Query Parameters:**
- `limit` (int, default: 50)
- `offset` (int, default: 0)

**Response:**
```json
{
  "cases": [ ... ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

---

### GET /history/{case_id}

Get full details of a specific case.

**Response:** Full case object with predictions array.

---

### GET /diseases

List all diseases in the database.

**Response:**
```json
{
  "diseases": [ ... ],
  "total": 10
}
```

---

### GET /disease/{disease_id}

Get detailed disease information including symptoms.

---

### GET /health

Health check (no auth required).

**Response:**
```json
{
  "status": "healthy",
  "service": "Derma Assist API",
  "version": "1.0.0"
}
```

---

### POST /admin/reload-disease-data

Re-import disease data from CSV files. Development mode only.
