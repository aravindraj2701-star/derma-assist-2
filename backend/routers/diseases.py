"""
Diseases Router — Disease information endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import Disease

router = APIRouter(tags=["Diseases"])


@router.get("/diseases")
def list_diseases(db: Session = Depends(get_db)):
    """Get all diseases in the database."""
    diseases = db.query(Disease).order_by(Disease.name).all()
    return {
        "diseases": [d.to_dict() for d in diseases],
        "total": len(diseases),
    }


@router.get("/disease/{disease_id}")
def get_disease(disease_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific disease."""
    disease = db.query(Disease).filter(Disease.disease_id == disease_id).first()
    if not disease:
        raise HTTPException(status_code=404, detail="Disease not found")
    return disease.to_dict()
