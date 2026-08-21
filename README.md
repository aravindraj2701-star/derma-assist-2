# 🩺 Derma Assist

## AI-Powered Skin Disease Detection and Clinical Decision Support System

> **⚠️ DISCLAIMER:** This is a decision-support tool for educational purposes. It does NOT replace professional medical advice, diagnosis, or treatment. Always consult a qualified dermatologist.

---

## 🎯 What It Does

1. User uploads a skin image and describes symptoms
2. **AI Image Analysis** — EfficientNetB0 classifies the skin condition
3. **Symptom Matching** — TF-IDF + Cosine Similarity matches symptoms to diseases
4. **Evidence Combination** — Weighted fusion of both signals
5. **Grad-CAM** — Visual explanation of which areas influenced the AI
6. **LLM Reasoning** — Natural language explanation (with fallback)
7. **Case History** — All analyses are saved for the logged-in user

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | React + Vite + JavaScript |
| Backend | FastAPI (Python) |
| Database | PostgreSQL |
| ML Model | EfficientNetB0 (TensorFlow) |
| Symptom Matching | TF-IDF + Cosine Similarity (scikit-learn) |
| Explainability | Grad-CAM |
| LLM | Google Gemini / OpenAI (optional) |
| Auth | Google OAuth 2.0 + JWT |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL 14+** (running on localhost:5432)

### 1. Clone & Setup Database

```bash
# Create PostgreSQL database
psql -U postgres -c "CREATE DATABASE derma_assist;"
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Copy env file and configure
copy .env.example .env
# Edit .env with your PostgreSQL credentials

# Seed the database
cd ..
python database/seed_database.py

# Start backend
cd backend
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 4. Open the App

Visit **http://localhost:5173**

---

## 📁 Project Structure

```
derma-assist-2/
├── backend/          # FastAPI backend
│   ├── main.py       # App entry point
│   ├── config.py     # Configuration
│   ├── database/     # ORM models, connection
│   ├── routers/      # API endpoints
│   ├── services/     # Business logic
│   └── utils/        # Helpers
├── frontend/         # React + Vite
│   └── src/
│       ├── pages/    # All page components
│       ├── components/
│       ├── context/  # Auth state
│       └── api/      # Axios client
├── model/            # ML pipeline
│   ├── train_model.py
│   ├── dataset_loader.py
│   └── evaluate_model.py
├── database/         # CSV seed data
├── dataset/          # Place image dataset here
├── scripts/          # Utility scripts
├── tests/            # Unit tests
└── docs/             # Documentation
```

---

## 🧪 Training the Model

```bash
# 1. Place dataset in dataset/ folder (train/validation/test structure)

# 2. Scan and validate dataset
python model/dataset_loader.py

# 3. Train model
python model/train_model.py

# 4. Evaluate
python model/evaluate_model.py
```

See [docs/SETUP.md](docs/SETUP.md) for detailed instructions.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/google` | Google OAuth login |
| POST | `/predict` | Full analysis pipeline |
| GET | `/history` | User's case history |
| GET | `/history/{id}` | Case details |
| GET | `/diseases` | All diseases |
| GET | `/disease/{id}` | Disease details |
| GET | `/health` | Health check |

See [docs/API_DOCS.md](docs/API_DOCS.md) for full API reference.

---

## 📄 License

This project is for educational purposes as part of a college project.
