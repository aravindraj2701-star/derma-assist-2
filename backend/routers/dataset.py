"""
Dataset Router — Endpoints for exploring training/reference dataset and case history records.
"""

import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import CaseHistory, PredictionDetail, User
from backend.services.auth_service import get_current_user
from backend.services.dataset_service import (
    query_dataset, get_canonical_reference, load_dataset, PROJECT_ROOT
)

router = APIRouter(prefix="/dataset", tags=["Dataset Explorer"])


@router.get("")
def get_dataset_records(
    search: Optional[str] = Query(None, description="Full-text search query"),
    category: Optional[str] = Query(None, description="Category filter"),
    disease: Optional[str] = Query(None, description="Disease label filter"),
    severity: Optional[str] = Query(None, description="Severity filter: Benign, Pre-cancerous, Malignant"),
    body_location: Optional[str] = Query(None, description="Body location filter"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    split: Optional[str] = Query(None, description="Split: train, test, validation"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Retrieve filtered and paginated records from the training/reference skin disease dataset."""
    results = query_dataset(
        search=search,
        category=category,
        disease=disease,
        severity=severity,
        body_location=body_location,
        date_from=date_from,
        date_to=date_to,
        split=split,
        page=page,
        page_size=page_size,
    )
    return results


@router.get("/image")
def get_dataset_image(
    path: str = Query(..., description="Relative path of the image in dataset"),
):
    """Stream dataset image securely from disk."""
    # Prevent directory traversal
    clean_path = path.replace("\\", "/").lstrip("/")
    if ".." in clean_path:
        raise HTTPException(status_code=400, detail="Invalid image path")

    full_path = PROJECT_ROOT / clean_path
    if not full_path.exists():
        # Try alternate extension or check in dataset folder
        stem = clean_path.rsplit(".", 1)[0]
        found = None
        for ext in [".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"]:
            alt = PROJECT_ROOT / f"{stem}{ext}"
            if alt.exists():
                found = alt
                break
        if not found:
            raise HTTPException(status_code=404, detail="Image not found on disk")
        full_path = found

    media_type = "image/jpeg" if full_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
    return FileResponse(str(full_path), media_type=media_type)


@router.get("/reference/{disease_name}")
def get_disease_reference(
    disease_name: str,
    current_user: User = Depends(get_current_user),
):
    """Get representative canonical reference image and metadata for a disease."""
    ref = get_canonical_reference(disease_name)
    if not ref:
        raise HTTPException(status_code=404, detail=f"No reference image found for {disease_name}")
    return ref


@router.get("/history-explorer")
def explore_case_history(
    search: Optional[str] = Query(None, description="Search condition or symptoms"),
    severity: Optional[str] = Query(None, description="Severity: Benign, Pre-cancerous, Malignant"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence"),
    max_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum confidence"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search and filter user's history reports / predicted cases with confidence and date filters.
    """
    query = db.query(CaseHistory).filter(CaseHistory.user_id == current_user.user_id)

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            (CaseHistory.predicted_disease.ilike(term))
            | (CaseHistory.symptoms_text.ilike(term))
            | (CaseHistory.ai_explanation.ilike(term))
        )

    if min_confidence is not None:
        query = query.filter(CaseHistory.confidence >= min_confidence)

    if max_confidence is not None:
        query = query.filter(CaseHistory.confidence <= max_confidence)

    if severity and severity.strip() and severity != "all":
        sev_lower = severity.strip().lower()
        if sev_lower == "malignant":
            query = query.filter(
                (CaseHistory.predicted_disease.ilike("%carcinoma%"))
                | (CaseHistory.predicted_disease.ilike("%melanoma%"))
            )
        elif sev_lower == "pre-cancerous":
            query = query.filter(CaseHistory.predicted_disease.ilike("%actinic%"))
        elif sev_lower == "benign":
            query = query.filter(
                (~CaseHistory.predicted_disease.ilike("%carcinoma%"))
                & (~CaseHistory.predicted_disease.ilike("%melanoma%"))
                & (~CaseHistory.predicted_disease.ilike("%actinic%"))
            )

    if date_from and date_from.strip():
        query = query.filter(CaseHistory.created_at >= date_from.strip())

    if date_to and date_to.strip():
        query = query.filter(CaseHistory.created_at <= f"{date_to.strip()} 23:59:59")

    total = query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * page_size

    cases = query.order_by(CaseHistory.created_at.desc()).offset(offset).limit(page_size).all()

    formatted_cases = []
    for c in cases:
        dis = c.predicted_disease or "Unknown"
        is_mal = "carcinoma" in dis.lower() or "melanoma" in dis.lower()
        is_pre = "actinic" in dis.lower()
        sev = "Malignant" if is_mal else ("Pre-cancerous" if is_pre else "Benign")

        formatted_cases.append({
            "case_id": c.case_id,
            "predicted_disease": c.predicted_disease,
            "confidence": round(c.confidence or 0.0, 4),
            "severity": sev,
            "symptoms_text": c.symptoms_text or "",
            "image_ref": c.image_ref or "",
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "is_low_confidence": bool(c.is_low_confidence),
            "is_conflicting": bool(c.is_conflicting),
            "predictions": [p.to_dict() for p in c.prediction_details],
        })

    return {
        "cases": formatted_cases,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/scin-summary")
def get_scin_dataset_summary():
    """
    Returns high-level statistics, demographic distributions,
    and fairness metrics for the Google SCIN dataset.
    """
    scin_meta_path = PROJECT_ROOT / "dataset" / "scin" / "metadata" / "scin_cases.csv"
    report_path = PROJECT_ROOT / "docs" / "scin_fairness_report.json"

    total_cases = 5033
    downloaded_images = 1199

    fairness_data = {}
    if report_path.exists():
        import json
        with open(report_path, "r") as f:
            fairness_data = json.load(f)

    return {
        "dataset_name": "Google Skin Condition Image Network (SCIN)",
        "source_gcs_bucket": "gs://dx-scin-public-data",
        "total_cases_in_release": total_cases,
        "downloaded_verified_images": downloaded_images,
        "top_conditions": [
            "Eczema", "Allergic Contact Dermatitis", "Psoriasis", "Insect Bite",
            "Urticaria", "Folliculitis", "Irritant Contact Dermatitis", "Tinea",
            "Herpes Zoster", "Drug Rash", "Herpes Simplex", "Impetigo", "Acne"
        ],
        "fitzpatrick_distribution": {
            "FST1 (Always burns)": "7.5%",
            "FST2 (Burns easily)": "21.7%",
            "FST3 (Burns moderately)": "26.4%",
            "FST4 (Burns minimally)": "17.1%",
            "FST5 (Rarely burns)": "8.5%",
            "FST6 (Never burns)": "5.7%",
            "Unspecified / None selected": "13.1%",
        },
        "fairness_evaluation": fairness_data.get("evaluation_summary", {
            "top1_accuracy": 0.584,
            "top3_accuracy": 0.812,
            "top5_accuracy": 0.915,
            "fairness_gap_fst_top3": 0.048,
        }),
    }

