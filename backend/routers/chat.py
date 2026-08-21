"""
Chat Router — RAG-based Medical Chatbot Endpoints.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import User
from backend.services.auth_service import get_optional_current_user
from backend.services.rag_service import execute_chat_query

router = APIRouter(prefix="/chat", tags=["Medical Chatbot"])


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000, description="User's medical or case question")
    case_id: Optional[int] = Field(None, description="Optional active screening case ID to scope answers")


class SourceCitation(BaseModel):
    disease: str
    section: str
    source: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]
    retrieved_count: int


@router.post("", response_model=ChatResponse)
def ask_medical_chatbot(
    payload: ChatRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    RAG-grounded Medical Chatbot Query Endpoint.
    Retrieves verified clinical reference knowledge and active case report data,
    generating educational, zero-hallucination answers with source citations.
    """
    if not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    user_id = current_user.user_id if current_user else None

    result = execute_chat_query(
        db=db,
        question=payload.question.strip(),
        case_id=payload.case_id,
        user_id=user_id,
    )

    return result
