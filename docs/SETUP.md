# Derma Assist — Setup Guide

## Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.10+ | Backend & ML |
| Node.js | 18+ | Frontend |
| PostgreSQL | 14+ | Database |
| Git | Latest | Version control |

---

## Step 1: Install PostgreSQL

1. Download from https://www.postgresql.org/download/windows/
2. Install with default settings
3. Remember your `postgres` password
4. Open pgAdmin or psql and create the database:

```sql
CREATE DATABASE derma_assist;
```

---

## Step 2: Backend Setup

```bash
# Navigate to project root
cd "derma assist 2"

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Configure environment
copy .env.example .env
```

Edit `backend/.env`:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/derma_assist
```

---

## Step 3: Seed the Database

```bash
# From project root
python database/seed_database.py
```

This creates tables and imports disease/symptom data from CSVs.

---

## Step 4: Start the Backend

```bash
# From project root
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Verify: http://localhost:8000/health

---

## Step 5: Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open: http://localhost:5173

---

## Step 6: Training the Model (Optional)

The app works in **mock mode** without a trained model. To train:

### 6.1 Get a Dataset

Download a skin disease dataset (e.g., from Kaggle):
- DermNet Dataset
- HAM10000
- ISIC Archive

Place it in `dataset/` with this structure:
```
dataset/
├── train/
│   ├── Acne/
│   ├── Eczema/
│   └── ...
├── validation/
└── test/
```

### 6.2 If Dataset Is Not Split

```bash
python scripts/split_dataset.py --input dataset/all_images --output dataset/ --train 0.70 --val 0.15 --test 0.15
```

### 6.3 Scan Dataset

```bash
python model/dataset_loader.py
```

### 6.4 Train

```bash
python model/train_model.py
```

### 6.5 Evaluate

```bash
python model/evaluate_model.py
```

---

## Step 7: Google OAuth (Optional)

1. Go to https://console.cloud.google.com
2. Create a project
3. Enable "Google Identity" API
4. Create OAuth 2.0 credentials (Web application)
5. Add `http://localhost:5173` as authorized origin
6. Copy Client ID to `backend/.env`:
   ```
   GOOGLE_CLIENT_ID=your-client-id
   ```
7. Create `frontend/.env`:
   ```
   VITE_GOOGLE_CLIENT_ID=your-client-id
   ```

Without Google OAuth, the app uses **Dev Login** mode.

---

## Step 8: LLM Integration (Optional)

### Google Gemini (Free Tier)
```
LLM_PROVIDER=gemini
LLM_API_KEY=your-api-key
LLM_MODEL=gemini-1.5-flash
```

### OpenAI
```
LLM_PROVIDER=openai
LLM_API_KEY=your-api-key
LLM_MODEL=gpt-3.5-turbo
```

Without an LLM key, the app uses a **deterministic fallback** explanation.

---

## Running Tests

```bash
# From project root
python -m pytest tests/ -v

# Or run individually
python tests/test_evidence_combiner.py
python tests/test_symptom_matcher.py
python tests/test_predict.py
```

---

## Common Issues

### "Could not connect to PostgreSQL"
- Ensure PostgreSQL is running
- Check DATABASE_URL in .env
- Verify the database exists

### "Model not found"
- This is normal before training
- The app works in mock mode
- Train the model following Step 6

### "npm: execution policy error"
- Run: `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser`
