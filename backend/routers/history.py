"""
History Router — Case history search, advanced clinical filtering, global search, and PDF export.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc

from backend.database.connection import get_db
from backend.database.models import CaseHistory, User, Disease
from backend.services.auth_service import get_current_user
from backend.services.dataset_service import get_canonical_reference
from backend.services.pdf_report_generator import generate_clinical_pdf

router = APIRouter(prefix="/history", tags=["Case History"])


@router.get("")
def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    q: Optional[str] = Query(None, description="Free-text search by case ID, disease name, or symptom keyword"),
    min_confidence: Optional[float] = Query(None, description="Minimum confidence score (0.0 to 1.0)"),
    max_confidence: Optional[float] = Query(None, description="Maximum confidence score (0.0 to 1.0)"),
    disease: Optional[str] = Query(None, description="Exact condition name filter"),
    severity: Optional[str] = Query(None, description="Risk severity tier filter (malignant, precancerous, benign)"),
    status: Optional[str] = Query(None, description="Review status filter (low_confidence, complete)"),
    sort_by: Optional[str] = Query("newest", description="Sorting criterion (newest, oldest, confidence_desc, confidence_asc)"),
    limit: int = 50,
    offset: int = 0,
):
    """
    Get the current user's case history with search and clinical filtering.
    """
    query = db.query(CaseHistory).filter(CaseHistory.user_id == current_user.user_id)

    # 1. Search Query (Case ID or Disease Name or Symptoms Text)
    if q and q.strip():
        search_term = q.strip()
        search_clean = search_term.replace("#", "")
        conditions = [
            CaseHistory.predicted_disease.ilike(f"%{search_term}%"),
            CaseHistory.symptoms_text.ilike(f"%{search_term}%"),
        ]
        if search_clean.isdigit():
            conditions.append(CaseHistory.case_id == int(search_clean))
        query = query.filter(or_(*conditions))

    # 2. Confidence Range Filter
    if min_confidence is not None:
        # Normalize if passed as 0-100 percentage
        min_val = min_confidence / 100.0 if min_confidence > 1.0 else min_confidence
        query = query.filter(CaseHistory.confidence >= min_val)
    if max_confidence is not None:
        max_val = max_confidence / 100.0 if max_confidence > 1.0 else max_confidence
        query = query.filter(CaseHistory.confidence <= max_val)

    # 3. Disease Name Filter
    if disease and disease.strip() and disease.lower() != "all":
        query = query.filter(CaseHistory.predicted_disease.ilike(f"%{disease.strip()}%"))

    # 4. Severity Tier Filter
    if severity and severity.strip() and severity.lower() != "all":
        sev_lower = severity.strip().lower()
        if sev_lower == "malignant":
            query = query.filter(or_(
                CaseHistory.predicted_disease.ilike("%melanoma%"),
                CaseHistory.predicted_disease.ilike("%carcinoma%"),
            ))
        elif sev_lower == "precancerous" or sev_lower == "pre-cancerous":
            query = query.filter(or_(
                CaseHistory.predicted_disease.ilike("%actinic%"),
                CaseHistory.predicted_disease.ilike("%keratosis%"),
            ))
        elif sev_lower == "benign":
            query = query.filter(and_(
                ~CaseHistory.predicted_disease.ilike("%melanoma%"),
                ~CaseHistory.predicted_disease.ilike("%carcinoma%"),
                ~CaseHistory.predicted_disease.ilike("%actinic%"),
            ))

    # 5. Status Filter
    if status and status.strip():
        st_lower = status.strip().lower()
        if st_lower == "low_confidence" or st_lower == "review_advised":
            query = query.filter(CaseHistory.is_low_confidence == 1)
        elif st_lower == "complete":
            query = query.filter(CaseHistory.is_low_confidence == 0)

    # 6. Sorting
    if sort_by == "oldest":
        query = query.order_by(asc(CaseHistory.created_at))
    elif sort_by == "confidence_desc":
        query = query.order_by(desc(CaseHistory.confidence))
    elif sort_by == "confidence_asc":
        query = query.order_by(asc(CaseHistory.confidence))
    else:  # newest default
        query = query.order_by(desc(CaseHistory.created_at))

    total = query.count()
    cases = query.offset(offset).limit(limit).all()

    # Distinct disease names for filter dropdowns
    available_diseases = [
        d[0] for d in db.query(CaseHistory.predicted_disease)
        .filter(CaseHistory.user_id == current_user.user_id, CaseHistory.predicted_disease.isnot(None))
        .distinct()
        .all()
    ]

    return {
        "cases": [
            {
                "case_id": c.case_id,
                "predicted_disease": c.predicted_disease,
                "confidence": c.confidence,
                "symptoms_text": c.symptoms_text,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "image_ref": c.image_ref[:100] + "..." if c.image_ref and len(c.image_ref) > 100 else c.image_ref,
                "is_low_confidence": bool(c.is_low_confidence),
            }
            for c in cases
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
        "available_diseases": available_diseases,
    }


@router.get("/global-search")
def global_search(
    q: str = Query(..., min_length=1, description="Global search query across DermaAssist"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Universal Spotlight Search across Case History, Disease Reference Database,
    and Navigation Actions.
    """
    search_term = q.strip().lower()
    search_clean = search_term.replace("#", "")

    # 1. Matching Cases
    case_conditions = [
        CaseHistory.predicted_disease.ilike(f"%{search_term}%"),
        CaseHistory.symptoms_text.ilike(f"%{search_term}%"),
    ]
    if search_clean.isdigit():
        case_conditions.append(CaseHistory.case_id == int(search_clean))

    matched_cases = (
        db.query(CaseHistory)
        .filter(CaseHistory.user_id == current_user.user_id, or_(*case_conditions))
        .order_by(desc(CaseHistory.created_at))
        .limit(5)
        .all()
    )

    cases_results = [
        {
            "id": c.case_id,
            "title": f"Case #{c.case_id} — {c.predicted_disease or 'Unspecified'}",
            "subtitle": f"{round((c.confidence or 0)*100)}% Conf • {c.created_at.strftime('%b %d, %Y') if c.created_at else 'Recent'}",
            "symptoms": c.symptoms_text[:70] + "..." if c.symptoms_text and len(c.symptoms_text) > 70 else (c.symptoms_text or "—"),
            "url": f"/history/{c.case_id}",
            "type": "case",
            "icon": "📋",
        }
        for c in matched_cases
    ]

    # 2. Matching Diseases in Database
    matched_diseases = (
        db.query(Disease)
        .filter(or_(
            Disease.name.ilike(f"%{search_term}%"),
            Disease.description.ilike(f"%{search_term}%"),
            Disease.severity_level.ilike(f"%{search_term}%"),
        ))
        .limit(4)
        .all()
    )

    disease_results = [
        {
            "id": d.disease_id,
            "title": d.name,
            "subtitle": f"{d.severity_level or 'Clinical'} severity • {d.description[:60] if d.description else 'Reference profile'}...",
            "url": f"/disease/{d.disease_id}",
            "type": "disease",
            "icon": "📖",
        }
        for d in matched_diseases
    ]

    # 3. Quick Actions
    actions = [
        {"title": "Analyze New Skin Lesion", "subtitle": "Upload image & clinical symptoms for multimodal AI prediction", "url": "/analyze", "icon": "🔬", "keywords": ["analyze", "scan", "upload", "image", "new", "test", "predict"]},
        {"title": "Practitioner Dashboard", "subtitle": "View clinical KPIs, recent screening timeline & due follow-up reminders", "url": "/dashboard", "icon": "📊", "keywords": ["dashboard", "home", "stats", "kpi", "reminders"]},
        {"title": "Dataset Explorer", "subtitle": "Explore verified SCIN & ISIC clinical training archives", "url": "/dataset", "icon": "🗂️", "keywords": ["dataset", "isic", "scin", "images", "archive", "explore", "records"]},
        {"title": "Case Consultation Archive", "subtitle": "Review all past patient screening reports and differential tables", "url": "/history", "icon": "📋", "keywords": ["history", "cases", "archive", "past", "records"]},
        {"title": "Model Training Console", "subtitle": "Doctor-supervised fine-tuning & version rollback console", "url": "/admin/training", "icon": "🧠", "keywords": ["training", "console", "retrain", "model", "rollback", "continuous learning", "admin"]},
        {"title": "Practitioner Profile", "subtitle": "Account credentials and security settings", "url": "/profile", "icon": "👤", "keywords": ["profile", "account", "settings", "password", "user"]},
    ]

    matched_actions = [
        {
            "title": a["title"],
            "subtitle": a["subtitle"],
            "url": a["url"],
            "type": "action",
            "icon": a["icon"],
        }
        for a in actions
        if search_term in a["title"].lower() or any(search_term in k for k in a["keywords"])
    ][:3]

    return {
        "query": q,
        "total_results": len(cases_results) + len(disease_results) + len(matched_actions),
        "cases": cases_results,
        "diseases": disease_results,
        "actions": matched_actions,
    }


@router.get("/{case_id}")
def get_case_detail(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full details of a specific case, including matched reference example."""
    case = (
        db.query(CaseHistory)
        .filter(
            CaseHistory.case_id == case_id,
            CaseHistory.user_id == current_user.user_id,
        )
        .first()
    )

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case_dict = case.to_dict()

    # Attach canonical reference example from training dataset
    if case.predicted_disease:
        case_dict["reference_example"] = get_canonical_reference(case.predicted_disease)

    return case_dict


@router.get("/{case_id}/pdf")
def get_case_pdf(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and download clinical PDF report for a case."""
    case = (
        db.query(CaseHistory)
        .filter(
            CaseHistory.case_id == case_id,
            CaseHistory.user_id == current_user.user_id,
        )
        .first()
    )

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case_dict = case.to_dict()
    if case.predicted_disease:
        case_dict["reference_example"] = get_canonical_reference(case.predicted_disease)

    user_info = {
        "name": current_user.name,
        "email": current_user.email,
    }

    pdf_bytes = generate_clinical_pdf(case_dict, user_info=user_info)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=DermaAssist_Report_Case_{case_id}.pdf"
        },
    )
