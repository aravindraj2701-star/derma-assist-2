"""
ORM Models — All database tables for Derma Assist.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship
from backend.database.connection import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    profile_picture = Column(Text, nullable=True)
    role = Column(String(50), default="patient", nullable=False)  # patient / doctor / admin
    is_active = Column(Boolean, default=True, nullable=False)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    zip_code = Column(String(30), nullable=True)
    date_of_birth = Column(String(50), nullable=True)
    gender = Column(String(30), nullable=True)
    bio = Column(Text, nullable=True)
    specialization = Column(String(150), nullable=True)
    hospital_affiliation = Column(String(255), nullable=True)
    license_number = Column(String(100), nullable=True)
    emergency_contact = Column(String(100), nullable=True)
    emergency_phone = Column(String(50), nullable=True)
    allergies = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    cases = relationship("CaseHistory", back_populates="user", lazy="dynamic")
    login_activities = relationship("LoginActivity", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone or "",
            "address": self.address or "",
            "city": self.city or "",
            "state": self.state or "",
            "zip_code": self.zip_code or "",
            "date_of_birth": self.date_of_birth or "",
            "gender": self.gender or "",
            "bio": self.bio or "",
            "specialization": self.specialization or "",
            "hospital_affiliation": self.hospital_affiliation or "",
            "license_number": self.license_number or "",
            "emergency_contact": self.emergency_contact or "",
            "emergency_phone": self.emergency_phone or "",
            "allergies": self.allergies or "",
            "role": self.role or "patient",
            "is_active": bool(self.is_active),
            "status": "active" if self.is_active else "suspended",
            "picture": self.profile_picture or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_admin_dict(self, last_login_at=None):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "role": self.role or "patient",
            "is_active": bool(self.is_active),
            "status": "active" if self.is_active else "suspended",
            "picture": self.profile_picture or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": last_login_at.isoformat() if last_login_at else None,
        }



class Disease(Base):
    __tablename__ = "diseases"

    disease_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    precautions = Column(Text, nullable=True)
    consult_doctor_if = Column(Text, nullable=True)
    severity_level = Column(String(50), nullable=True)

    symptoms = relationship("DiseaseSymptom", back_populates="disease", lazy="joined")

    def __repr__(self):
        return f"<Disease {self.name}>"

    def to_dict(self):
        return {
            "disease_id": self.disease_id,
            "name": self.name,
            "description": self.description,
            "precautions": self.precautions,
            "consult_doctor_if": self.consult_doctor_if,
            "severity_level": self.severity_level,
            "symptoms": [s.to_dict() for s in self.symptoms],
        }


class DiseaseSymptom(Base):
    __tablename__ = "disease_symptoms"

    symptom_id = Column(Integer, primary_key=True, autoincrement=True)
    disease_id = Column(Integer, ForeignKey("diseases.disease_id"), nullable=False)
    symptom_keyword = Column(String(255), nullable=False)
    symptom_description = Column(Text, nullable=False)
    severity = Column(String(50), nullable=True)

    disease = relationship("Disease", back_populates="symptoms")

    def __repr__(self):
        return f"<Symptom {self.symptom_keyword} -> {self.disease_id}>"

    def to_dict(self):
        return {
            "symptom_id": self.symptom_id,
            "disease_id": self.disease_id,
            "symptom_keyword": self.symptom_keyword,
            "symptom_description": self.symptom_description,
            "severity": self.severity,
        }


class CaseHistory(Base):
    __tablename__ = "case_history"

    case_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    image_ref = Column(Text, nullable=True)
    predicted_disease = Column(String(255), nullable=True)
    confidence = Column(Float, nullable=True)
    symptoms_text = Column(Text, nullable=True)
    gradcam_image = Column(Text, nullable=True)  # base64 encoded
    ai_explanation = Column(Text, nullable=True)
    precautions = Column(Text, nullable=True)
    consult_doctor = Column(Text, nullable=True)
    is_low_confidence = Column(Integer, default=0)
    is_conflicting = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="cases")
    prediction_details = relationship(
        "PredictionDetail", back_populates="case", lazy="joined"
    )

    def __repr__(self):
        return f"<Case {self.case_id} -> {self.predicted_disease}>"

    def to_dict(self):
        return {
            "case_id": self.case_id,
            "user_id": self.user_id,
            "image_ref": self.image_ref,
            "predicted_disease": self.predicted_disease,
            "confidence": self.confidence,
            "symptoms_text": self.symptoms_text,
            "gradcam_image": self.gradcam_image,
            "ai_explanation": self.ai_explanation,
            "precautions": self.precautions,
            "consult_doctor": self.consult_doctor,
            "is_low_confidence": bool(self.is_low_confidence),
            "is_conflicting": bool(self.is_conflicting),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "predictions": [p.to_dict() for p in self.prediction_details],
        }


class PredictionDetail(Base):
    __tablename__ = "prediction_details"

    prediction_id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("case_history.case_id"), nullable=False)
    disease_name = Column(String(255), nullable=False)
    image_score = Column(Float, default=0.0)
    symptom_score = Column(Float, default=0.0)
    combined_score = Column(Float, default=0.0)
    rank = Column(Integer, default=0)

    case = relationship("CaseHistory", back_populates="prediction_details")

    def __repr__(self):
        return f"<Prediction {self.disease_name} rank={self.rank}>"

    def to_dict(self):
        return {
            "prediction_id": self.prediction_id,
            "case_id": self.case_id,
            "disease_name": self.disease_name,
            "image_score": round(self.image_score, 4),
            "symptom_score": round(self.symptom_score, 4),
            "combined_score": round(self.combined_score, 4),
            "rank": self.rank,
        }


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)

    user = relationship("User")

    def __repr__(self):
        return f"<PasswordResetToken user_id={self.user_id} used={self.used}>"


class FollowUpReminder(Base):
    __tablename__ = "follow_up_reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("case_history.case_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    reminder_type = Column(String(50), default="patient_rescan")  # patient_rescan / doctor_review_pending
    severity_tier = Column(String(50), default="benign_stable")   # malignant / precancerous / benign_alarm / benign_stable
    scheduled_for = Column(DateTime, nullable=False)
    status = Column(String(50), default="pending")                 # pending / sent / completed / dismissed
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("CaseHistory")
    user = relationship("User")

    def __repr__(self):
        return f"<FollowUpReminder case={self.case_id} type={self.reminder_type} status={self.status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "user_id": self.user_id,
            "reminder_type": self.reminder_type,
            "severity_tier": self.severity_tier,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "predicted_disease": self.case.predicted_disease if self.case else None,
            "confidence": self.case.confidence if self.case else None,
        }


class ModelTrainingCandidate(Base):
    __tablename__ = "model_training_candidates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("case_history.case_id"), nullable=False)
    image_path = Column(Text, nullable=True)
    original_prediction = Column(String(255), nullable=False)
    doctor_corrected_label = Column(String(255), nullable=True)
    doctor_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    doctor_notes = Column(Text, nullable=True)
    confidence_at_prediction = Column(Float, default=0.0)
    added_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pending_review")  # pending_review / approved_for_training / rejected / used_in_training

    case = relationship("CaseHistory")
    doctor = relationship("User")

    def __repr__(self):
        return f"<TrainingCandidate case={self.case_id} status={self.status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "image_path": self.image_path,
            "original_prediction": self.original_prediction,
            "doctor_corrected_label": self.doctor_corrected_label,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor.name if self.doctor else "Attending Dermatologist",
            "doctor_notes": self.doctor_notes,
            "confidence_at_prediction": round(self.confidence_at_prediction, 4),
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "status": self.status,
        }


class ModelVersion(Base):
    __tablename__ = "model_versions"

    version_id = Column(String(100), primary_key=True)
    trained_at = Column(DateTime, default=datetime.utcnow)
    training_candidate_count = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    malignant_recall = Column(Float, default=0.0)
    metrics_json = Column(Text, default="{}")
    promoted = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<ModelVersion {self.version_id} promoted={self.promoted}>"

    def to_dict(self):
        return {
            "version_id": self.version_id,
            "trained_at": self.trained_at.isoformat() if self.trained_at else None,
            "training_candidate_count": self.training_candidate_count,
            "accuracy": round(self.accuracy, 4),
            "malignant_recall": round(self.malignant_recall, 4),
            "metrics_json": self.metrics_json,
            "promoted": self.promoted,
            "notes": self.notes,
        }


class ChatAuditLog(Base):
    __tablename__ = "chat_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    case_id = Column(Integer, ForeignKey("case_history.case_id"), nullable=True)
    question = Column(Text, nullable=False)
    retrieved_chunks = Column(Text, nullable=True)
    answer = Column(Text, nullable=False)
    source_citations = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ChatAuditLog id={self.id} user={self.user_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "case_id": self.case_id,
            "question": self.question,
            "answer": self.answer,
            "source_citations": self.source_citations,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LoginActivity(Base):
    __tablename__ = "login_activity"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    login_at = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, default=True, nullable=False, index=True)
    failure_reason = Column(String(255), nullable=True)

    user = relationship("User", back_populates="login_activities")

    def __repr__(self):
        return f"<LoginActivity user={self.email} success={self.success} at={self.login_at}>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name if self.user else (self.email or "Anonymous"),
            "email": self.email or (self.user.email if self.user else "Unknown"),
            "user_role": self.user.role if self.user else "patient",
            "login_at": self.login_at.isoformat() if self.login_at else None,
            "ip_address": self.ip_address or "Unknown",
            "user_agent": self.user_agent or "Unknown",
            "success": bool(self.success),
            "failure_reason": self.failure_reason,
        }


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    action = Column(String(100), nullable=False)  # ROLE_CHANGE, STATUS_CHANGE, USER_PROMOTE, etc.
    target_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    details = Column(Text, nullable=True)

    admin = relationship("User", foreign_keys=[admin_id])
    target_user = relationship("User", foreign_keys=[target_user_id])

    def __repr__(self):
        return f"<AdminAuditLog admin={self.admin_id} action={self.action} target={self.target_user_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "admin_id": self.admin_id,
            "admin_name": self.admin.name if self.admin else "Administrator",
            "action": self.action,
            "target_user_id": self.target_user_id,
            "target_user_name": self.target_user.name if self.target_user else "User",
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "details": self.details,
        }


class Condition(Base):
    """Represents a dermatological condition record in the dataset library."""
    __tablename__ = "conditions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    condition_name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=True, index=True)
    body_locations = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    symptoms = Column(Text, nullable=True)
    image_path = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    severity = Column(String(50), nullable=True)
    malignant = Column(Integer, default=0)
    split = Column(String(50), default="train")
    date_added = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    images = relationship("ConditionImage", back_populates="condition", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<Condition {self.id}: {self.condition_name} ({self.category})>"

    def to_dict(self):
        # Resolve working image URL: prefer explicit image_url, then fallback to relative image_path
        resolved_url = self.image_url or (f"/dataset/image?path={self.image_path}" if self.image_path else "")
        return {
            "id": self.id,
            "condition_name": self.condition_name,
            "unified_disease_label": self.condition_name,  # compatibility alias for frontend
            "category": self.category or "Dermatological Condition",
            "body_location": self.body_locations or "Cutaneous Site",
            "body_locations": self.body_locations or "Cutaneous Site",
            "description": self.description or "",
            "symptoms": self.symptoms or "",
            "symptoms_description": self.symptoms or self.description or "",
            "image_path": self.image_path or "",
            "image_url": resolved_url,
            "source": self.source or "Clinical Archive",
            "severity": self.severity or ("Malignant" if self.malignant == 1 else "Benign"),
            "malignant": int(self.malignant or 0),
            "split": self.split or "train",
            "date_added": self.date_added or (self.created_at.strftime("%Y-%m-%d") if self.created_at else "2024-2026"),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "images": [img.to_dict() for img in self.images] if self.images else [],
        }


class ConditionImage(Base):
    """Related image entity for conditions that have multiple clinical/dermoscopic photos."""
    __tablename__ = "condition_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    condition_id = Column(Integer, ForeignKey("conditions.id"), nullable=False, index=True)
    image_path = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    is_primary = Column(Boolean, default=True)
    caption = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    condition = relationship("Condition", back_populates="images")

    def __repr__(self):
        return f"<ConditionImage {self.id} -> condition={self.condition_id}>"

    def to_dict(self):
        resolved_url = self.image_url or (f"/dataset/image?path={self.image_path}" if self.image_path else "")
        return {
            "id": self.id,
            "condition_id": self.condition_id,
            "image_path": self.image_path or "",
            "image_url": resolved_url,
            "is_primary": bool(self.is_primary),
            "caption": self.caption or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }




