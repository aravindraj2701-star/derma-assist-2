# Derma Assist — Architecture

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       USER (Browser)                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              REACT FRONTEND (Vite)                     │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │  Login   │ │Dashboard │ │ Analyze  │ │ Results  │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐              │  │
│  │  │ History  │ │ Profile  │ │ Disease  │              │  │
│  │  └──────────┘ └──────────┘ └──────────┘              │  │
│  └────────────────────┬───────────────────────────────────┘  │
│                       │ Axios (JWT Auth)                     │
└───────────────────────┼──────────────────────────────────────┘
                        │ HTTP / REST API
┌───────────────────────┼──────────────────────────────────────┐
│                FASTAPI BACKEND                               │
│                       │                                      │
│  ┌────────────────────┼──────────────────────────────────┐   │
│  │              API ROUTERS                              │   │
│  │  /auth/google  /predict  /history  /diseases  /health │   │
│  └────────────────────┼──────────────────────────────────┘   │
│                       │                                      │
│  ┌────────────────────┼──────────────────────────────────┐   │
│  │              SERVICES                                 │   │
│  │                    │                                  │   │
│  │  ┌─────────────┐  │  ┌─────────────┐                 │   │
│  │  │   Image     │  │  │  Symptom    │                 │   │
│  │  │ Predictor   │  │  │  Matcher    │                 │   │
│  │  │(EfficientNet)│  │  │ (TF-IDF)   │                 │   │
│  │  └──────┬──────┘  │  └──────┬──────┘                 │   │
│  │         │         │         │                         │   │
│  │  ┌──────┴──────┐  │  ┌──────┴──────┐                 │   │
│  │  │  Grad-CAM   │  │  │  Evidence   │                 │   │
│  │  │             │  │  │  Combiner   │                 │   │
│  │  └─────────────┘  │  └──────┬──────┘                 │   │
│  │                    │         │                         │   │
│  │                    │  ┌──────┴──────┐                 │   │
│  │                    │  │    LLM      │                 │   │
│  │                    │  │  Reasoning  │                 │   │
│  │                    │  └─────────────┘                 │   │
│  └────────────────────┼──────────────────────────────────┘   │
│                       │                                      │
│  ┌────────────────────┼──────────────────────────────────┐   │
│  │         SQLAlchemy ORM                                │   │
│  └────────────────────┼──────────────────────────────────┘   │
│                       │                                      │
└───────────────────────┼──────────────────────────────────────┘
                        │
┌───────────────────────┼──────────────────────────────────────┐
│              POSTGRESQL DATABASE                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │  users   │ │ diseases │ │  case    │ │  prediction  │   │
│  │          │ │          │ │ history  │ │  details     │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
│  ┌──────────────┐                                           │
│  │   disease    │                                           │
│  │  symptoms    │                                           │
│  └──────────────┘                                           │
└──────────────────────────────────────────────────────────────┘
```

## Prediction Pipeline

```
Image Upload + Symptoms Text
        │
        ├──────────────────────────┐
        │                          │
        ▼                          ▼
  Image Validation          Text Cleaning
        │                          │
        ▼                          ▼
  Resize to 224x224         TF-IDF Vectorization
        │                          │
        ▼                          ▼
  EfficientNetB0            Cosine Similarity
  (Transfer Learning)       vs Disease Symptoms
        │                          │
        ▼                          ▼
  Softmax Probabilities     Disease Rankings
  (Top-3 predictions)              │
        │                          │
        ├──────────┬───────────────┘
        │          │
        ▼          ▼
     Grad-CAM   Evidence Combiner
        │     (IMAGE_WEIGHT * img +
        │      SYMPTOM_WEIGHT * sym)
        │          │
        │          ▼
        │    LLM Reasoning / Fallback
        │          │
        │          ▼
        └────► Save to PostgreSQL
                   │
                   ▼
            Return JSON Response
```

## Database Schema

```
users (1) ──── (N) case_history (1) ──── (N) prediction_details
                                                    │
diseases (1) ──── (N) disease_symptoms              │
    │                                               │
    └───────────────────────────────────────────────┘
                  (referenced by disease_name)
```

## Key Design Decisions

1. **Mock mode**: App works without a trained model, using random scores
2. **Dev auth bypass**: Works without Google OAuth using dev-token
3. **LLM fallback**: Deterministic template when no API key is configured
4. **Configurable weights**: IMAGE_WEIGHT and SYMPTOM_WEIGHT are not hardcoded
5. **Dynamic classes**: Disease classes come from dataset, not hardcoded
6. **Class weights**: Handles imbalanced datasets during training
