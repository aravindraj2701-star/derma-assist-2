"""
Predict Router — Full multimodal SCIN analysis pipeline endpoint.

POST /predict
POST /predict/report-pdf
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import json

from backend.database.connection import get_db
from backend.database.models import Disease, CaseHistory, PredictionDetail, User
from backend.services.auth_service import get_current_user
from backend.services.scin_predictor import predict_scin_multimodal
from backend.services.symptom_first_pipeline import run_symptom_first_pipeline
from backend.services.dataset_service import get_canonical_reference
from backend.services.pdf_report_generator import generate_clinical_pdf
from backend.utils.image_utils import validate_image, image_to_base64
from backend.config import settings

router = APIRouter(tags=["Prediction"])


@router.post("/predict")
async def predict(
    image: UploadFile = File(...),
    symptoms: Optional[str] = Form(default=""),
    patient_notes: Optional[str] = Form(default=""),
    body_location: Optional[str] = Form(default=""),
    duration: Optional[str] = Form(default=""),
    # SCIN Clinical Free-Text Fields
    body_part: Optional[str] = Form(default=""),
    textures: Optional[str] = Form(default=""),
    age: Optional[str] = Form(default=""),
    age_group: Optional[str] = Form(default=""),
    sex_at_birth: Optional[str] = Form(default=""),
    fitzpatrick_skin_type: Optional[str] = Form(default=""),
    # Optional boolean compatibility flags
    itching: Optional[bool] = Form(default=None),
    burning: Optional[bool] = Form(default=None),
    pain: Optional[bool] = Form(default=None),
    bleeding: Optional[bool] = Form(default=None),
    increasing_size: Optional[bool] = Form(default=None),
    darkening: Optional[bool] = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Google SCIN Multimodal Skin Condition Analysis Pipeline.

    Accepts:
    - Skin image (JPG/PNG)
    - Free-text clinical symptom descriptions (location, duration, texture, symptoms/evolution, patient notes)
    - Free-text patient demographic context (age, sex, Fitzpatrick skin phototype)

    Returns:
    - Multi-label ranked predictions with confidence percentages
    - Primary diagnosis and differential diagnoses
    - Multimodal feature contribution breakdown (image vs symptom alignment)
    - Fitzpatrick skin tone fairness evaluation context
    - Clinical recommendations and medical research disclaimer
    """
    # 1. Validate Image
    file_bytes = await image.read()
    img = validate_image(
        file_bytes,
        image.filename or "upload.jpg",
        settings.max_image_bytes,
    )

    # 2. Package Structured and Free-Text Symptoms
    resolved_location = (body_part or body_location or "").strip()
    resolved_duration = (duration or "").strip()
    resolved_textures = (textures or "").strip()
    resolved_symptoms = (symptoms or "").strip()
    resolved_notes = (patient_notes or "").strip()
    resolved_age = (age or age_group or "").strip()
    resolved_sex = (sex_at_birth or "").strip()
    resolved_fst = (fitzpatrick_skin_type or "").strip()

    symptom_payload = {
        "body_part": resolved_location,
        "body_location": resolved_location,
        "duration": resolved_duration,
        "condition_duration": resolved_duration,
        "textures": resolved_textures,
        "symptoms": resolved_symptoms,
        "patient_notes": resolved_notes,
        "age": resolved_age,
        "age_group": resolved_age,
        "sex_at_birth": resolved_sex,
        "fitzpatrick_skin_type": resolved_fst,
        "itching": itching,
        "burning": burning,
        "pain": pain,
        "bleeding": bleeding,
        "increasing_size": increasing_size,
        "darkening": darkening,
    }

    # 3. Symptom-First Multimodal Inference Pipeline
    scin_result = run_symptom_first_pipeline(img, symptom_payload)

    primary = scin_result["primary_prediction"]
    top_disease_name = primary["condition"]
    confidence_score = primary["confidence_pct"] / 100.0

    # 4. Format Predictions List
    final_predictions = []
    for pred in scin_result["all_predictions"]:
        final_predictions.append({
            "disease": pred["condition"],
            "condition": pred["condition"],
            "combined_score": pred["confidence_pct"] / 100.0,
            "confidence_pct": pred["confidence_pct"],
            "image_score": pred["image_score"],
            "symptom_score": pred["symptom_score"],
            "rank": pred["rank"],
            "risk_tier": pred["risk_tier"],
            "risk_level": pred["risk_level"],
        })

    # Retrieve matched reference example from visual embedding matcher
    reference_example = scin_result.get("reference_example") or get_canonical_reference(top_disease_name)

    # Disease database info if available
    disease_info = None
    disease_entry = db.query(Disease).filter(Disease.name == top_disease_name).first()
    if disease_entry:
        disease_info = disease_entry.to_dict()

    # 5. Save Case to Database
    original_image_b64 = image_to_base64(img)
    stored_symptoms = resolved_notes or f"Location: {resolved_location} | Duration: {resolved_duration} | Texture: {resolved_textures} | Symptoms: {resolved_symptoms}"

    case = CaseHistory(
        user_id=current_user.user_id,
        image_ref=original_image_b64,
        predicted_disease=top_disease_name,
        confidence=confidence_score,
        symptoms_text=stored_symptoms,
        gradcam_image="",
        ai_explanation=f"Multimodal SCIN analysis identified {top_disease_name} as the primary clinical presentation ({primary['confidence_pct']}% confidence).",
        precautions="Keep the affected area clean, avoid scratching, and seek in-person clinical assessment from a licensed dermatologist.",
        consult_doctor="Prompt medical evaluation is strongly advised for definitive in-person clinical examination and patch testing.",
        is_low_confidence=1 if primary["confidence_pct"] < 35.0 else 0,
        is_conflicting=0,
    )
    db.add(case)
    db.flush()

    for pred in final_predictions:
        detail = PredictionDetail(
            case_id=case.case_id,
            disease_name=pred["disease"],
            image_score=pred["image_score"],
            symptom_score=pred["symptom_score"],
            combined_score=pred["combined_score"],
            rank=pred["rank"],
        )
        db.add(detail)

    db.commit()
    db.refresh(case)

    # 5b. Auto-Schedule Clinical Follow-Up Reminder
    try:
        from backend.services.reminder_service import auto_schedule_case_reminder
        auto_schedule_case_reminder(
            db=db,
            case_id=case.case_id,
            user_id=current_user.user_id,
            predicted_disease=top_disease_name,
            risk_tier=primary.get("risk_tier", "benign"),
            symptoms_text=stored_symptoms,
        )
    except Exception as rem_err:
        logger.warning(f"Failed to auto-schedule follow-up reminder for Case #{case.case_id}: {rem_err}")

    # 6. Response Payload
    return {
        "case_id": case.case_id,
        "predicted_disease": top_disease_name,
        "confidence": confidence_score,
        "confidence_pct": primary["confidence_pct"],
        "primary_prediction": primary,
        "differential_diagnoses": scin_result["differential_diagnoses"],
        "predictions": final_predictions,
        "all_predictions": scin_result["all_predictions"],
        "differentiating_features": scin_result.get("differentiating_features", []),
        "original_image": original_image_b64,
        "reference_example": reference_example,
        "body_location": resolved_location,
        "duration": resolved_duration,
        "textures": resolved_textures,
        "symptoms": resolved_symptoms,
        "patient_notes": resolved_notes,
        "symptoms_text": stored_symptoms,
        "age": resolved_age,
        "sex_at_birth": resolved_sex,
        "fitzpatrick_skin_type": resolved_fst,
        "structured_symptoms": symptom_payload,
        "multimodal_breakdown": scin_result["multimodal_breakdown"],
        "fairness_context": scin_result["fairness_context"],
        "disease_info": disease_info,
        "is_low_confidence": primary["confidence_pct"] < 35.0,
        "disclaimer": scin_result["disclaimer"],
    }


@router.post("/predict/report-pdf")
def export_prediction_pdf(
    payload: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
):
    """
    Generate and download a clinical PDF report for the active prediction result.
    """
    user_info = {
        "name": current_user.name,
        "email": current_user.email,
    }
    if not payload.get("reference_example") and payload.get("predicted_disease"):
        payload["reference_example"] = get_canonical_reference(payload["predicted_disease"])

    pdf_bytes = generate_clinical_pdf(payload, user_info=user_info)
    case_id = payload.get("case_id", "report")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=DermaAssist_Report_Case_{case_id}.pdf"
        },
    )
