"""
Training Router — Doctor review, candidate curation, and continuous learning console endpoints.
"""

from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User
from backend.services.auth_service import get_current_user
from backend.services.continuous_learning_service import (
    doctor_review_and_approve_candidate,
    get_training_dashboard_stats,
    execute_model_retraining,
    rollback_to_version,
)

router = APIRouter(prefix="/training", tags=["Continuous Learning & Model Training"])


class DoctorReviewRequest(BaseModel):
    doctor_corrected_label: Optional[str] = Field(None, description="Doctor-confirmed or corrected ground truth diagnosis")
    doctor_notes: Optional[str] = Field(None, description="Clinical justification and morphology notes")
    opt_in_training: bool = Field(True, description="Whether to approve this reviewed case into the training candidate pool")


class RollbackRequest(BaseModel):
    target_version_id: str = Field(..., description="Target model version identifier to restore")


@router.post("/doctor/cases/{case_id}/review")
def review_and_opt_in_case(
    case_id: int,
    payload: DoctorReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Doctor Review & Training Candidate Opt-In Endpoint.
    Attending dermatologist verifies the diagnosis and optionally approves
    the case into the curated model training candidate pool.
    """
    try:
        candidate = doctor_review_and_approve_candidate(
            db=db,
            case_id=case_id,
            doctor_id=current_user.user_id,
            corrected_label=payload.doctor_corrected_label,
            doctor_notes=payload.doctor_notes,
            opt_in_training=payload.opt_in_training,
        )
        return {
            "status": "success",
            "message": f"Case #{case_id} successfully reviewed and status updated to '{candidate.status}'.",
            "candidate": candidate.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/admin/stats")
def get_model_training_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Admin Training Console Statistics.
    Returns counts of approved candidates, active production version,
    benchmark accuracy/recall, and historical model versions.
    """
    return get_training_dashboard_stats(db)


@router.post("/admin/retrain")
def trigger_model_retraining(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Manual Retraining Trigger with Benchmark Safety Gate.
    Pulls doctor-approved cases, runs fine-tuning simulation,
    evaluates against fixed test benchmark, and promotes only if accuracy/recall improve.
    """
    result = execute_model_retraining(db=db, admin_id=current_user.user_id)
    if result["status"] == "error":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])
    return result


@router.post("/admin/rollback")
def rollback_model_deployment(
    payload: RollbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Reverts active production model to a verified previous checkpoint version.
    """
    try:
        return rollback_to_version(db=db, target_version_id=payload.target_version_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
