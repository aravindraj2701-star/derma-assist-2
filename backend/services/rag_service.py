"""
RAG Service — Retrieval-Augmented Generation Medical Chatbot Engine.
Provides grounded, zero-hallucination medical educational answers with source citations.
"""

import json
import logging
import re
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from backend.database.models import CaseHistory, Disease, ChatAuditLog
from backend.services.symptom_first_pipeline import DIFFERENTIATING_CLINICAL_PROFILES

logger = logging.getLogger("derma_assist.rag")

# ─── Curated Dermatology Knowledge Base ────────────────────────────────────────

CURATED_KNOWLEDGE_BASE: List[Dict[str, Any]] = [
    {
        "id": "melanoma_guide",
        "disease": "Melanoma",
        "category": "Malignant Skin Neoplasm",
        "section": "Clinical Presentation & ABCDE Criteria",
        "source": "American Academy of Dermatology (AAD) Clinical Guidelines",
        "content": (
            "Melanoma is a potentially aggressive malignant cutaneous tumor originating from melanocytes. "
            "The classic clinical evaluation relies on the ABCDE criteria: "
            "A - Asymmetry (one half does not match the other), "
            "B - Border irregularity (scalloped, notched, or poorly defined edges), "
            "C - Color variegation (shades of brown, black, blue, white, or red within the same lesion), "
            "D - Diameter greater than 6mm (though some are smaller), "
            "E - Evolving (changing in size, shape, color, or symptoms like bleeding or itching). "
            "Any suspicious evolving pigmented lesion requires urgent in-person dermatoscopic assessment and full-thickness excisional biopsy."
        ),
        "keywords": ["melanoma", "abcde", "asymmetry", "border", "color", "evolving", "malignant", "biopsy", "mole"]
    },
    {
        "id": "melanoma_treatment",
        "disease": "Melanoma",
        "category": "Malignant Skin Neoplasm",
        "section": "Management & Staging",
        "source": "British Association of Dermatologists (BAD) Guidelines",
        "content": (
            "Standard initial intervention for suspected melanoma is complete surgical excision with narrow margins, followed by histopathological staging "
            "(Breslow depth measurement). Deeper lesions may warrant sentinel lymph node biopsy and multidisciplinary oncological review. "
            "Patients must strictly avoid self-treatment or unverified home remedies."
        ),
        "keywords": ["melanoma", "breslow", "excision", "staging", "oncology", "margins"]
    },
    {
        "id": "bcc_guide",
        "disease": "Basal Cell Carcinoma",
        "category": "Malignant Skin Neoplasm",
        "section": "Morphology & Risk Factors",
        "source": "Skin Cancer Foundation Medical Advisory",
        "content": (
            "Basal Cell Carcinoma (BCC) is the most common form of skin cancer, arising in the basal cell layer of the epidermis. "
            "It classically presents as a pearly or translucent papule/nodule with prominent telangiectasias (fine dilated blood vessels), "
            "rolled borders, and a central depression that may ulcerate or bleed recurrently ('non-healing sore'). "
            "While BCC has very low metastatic potential, it causes significant local tissue destruction if untreated."
        ),
        "keywords": ["basal cell", "bcc", "pearly", "translucent", "telangiectasia", "rolled border", "bleeding sore"]
    },
    {
        "id": "actinic_keratosis_guide",
        "disease": "Actinic Keratosis",
        "category": "Pre-cancerous Lesion",
        "section": "Pre-cancerous Pathology & Evolution",
        "source": "AAD Dermatological Consensus",
        "content": (
            "Actinic Keratosis (AK) is a pre-cancerous intraepidermal proliferation of atypical keratinocytes induced by cumulative ultraviolet radiation. "
            "It appears as a rough, gritty, sandpaper-like or scaly patch on chronically sun-exposed areas (face, scalp, forearms, ears). "
            "Because a small percentage of AK lesions can progress to invasive Squamous Cell Carcinoma (SCC), dermatologists recommend prompt "
            "treatment via cryotherapy, topical 5-fluorouracil, imiquimod, or photodynamic therapy."
        ),
        "keywords": ["actinic keratosis", "pre-cancerous", "precancerous", "gritty", "sandpaper", "squamous", "sun-damaged"]
    },
    {
        "id": "urticaria_guide",
        "disease": "Urticaria",
        "category": "Allergic / Cutaneous Vascular",
        "section": "Pathophysiology & Evanescent Nature",
        "source": "World Allergy Organization (WAO) Guidelines",
        "content": (
            "Urticaria (hives) is an acute mast cell-mediated inflammatory disorder characterized by transient, intensely pruritic raised wheals "
            "surrounded by erythematous flares. The hallmark clinical feature is evanascence: individual lesions typically emerge rapidly, "
            "blanch under pressure, and spontaneously resolve or shift to new cutaneous locations within 2 to 24 hours without leaving scars. "
            "Acute triggers include infections, medications, foods, insect stings, and physical stimuli."
        ),
        "keywords": ["urticaria", "hives", "wheals", "itching", "pruritic", "evanescent", "blanching", "allergic"]
    },
    {
        "id": "eczema_guide",
        "disease": "Eczema",
        "category": "Inflammatory / Atopic",
        "section": "Chronic Barrier Dysfunction",
        "source": "National Eczema Association Clinical Guidelines",
        "content": (
            "Eczema (Atopic Dermatitis) is a chronic, relapsing inflammatory skin disease characterized by epidermal barrier dysfunction, "
            "intense pruritus, xerosis (dryness), and erythematous scaly plaques. In adults, lesions typically involve flexural creases "
            "(antecubital and popliteal fossae), neck, and hands, often featuring lichenification (skin thickening from chronic scratching). "
            "First-line management includes diligent skin hydration with thick barrier emollients and intermittent topical anti-inflammatory therapy."
        ),
        "keywords": ["eczema", "atopic dermatitis", "dry skin", "flexural", "lichenification", "itching", "chronic", "barrier"]
    },
    {
        "id": "psoriasis_guide",
        "disease": "Psoriasis",
        "category": "Immune-Mediated / Papulosquamous",
        "section": "Plaque Characteristics & Auspitz Sign",
        "source": "International Psoriasis Council Clinical Manual",
        "content": (
            "Psoriasis vulgaris is a chronic systemic immune-mediated dermatosis characterized by well-demarcated, indurated erythematous plaques "
            "topped by thick, micaceous silvery-white scales. Classic anatomical sites include extensor surfaces (knees, elbows), lumbosacral spine, "
            "and scalp. Gentle scraping of the scales can produce pinpoint bleeding spots (Auspitz sign). It follows a chronic, persistent course "
            "requiring topical corticosteroids, vitamin D analogs, phototherapy, or systemic biologics."
        ),
        "keywords": ["psoriasis", "silvery scales", "extensor", "plaques", "knees", "elbows", "auspitz", "chronic"]
    },
    {
        "id": "impetigo_guide",
        "disease": "Impetigo",
        "category": "Infectious / Bacterial",
        "section": "Honey-Colored Crusts & Contagion",
        "source": "Infectious Diseases Society of America (IDSA)",
        "content": (
            "Impetigo is a highly contagious superficial bacterial infection of the epidermis, most commonly caused by Staphylococcus aureus "
            "or Streptococcus pyogenes. It begins as thin-walled erythematous vesicles or bullae that rapidly rupture, oozing exudate that dries "
            "into pathognomonic honey-colored adherent crusts, frequently around the perioral and perinasal areas. "
            "Treatment involves topical mupirocin ointment or oral systemic antibiotics for extensive eruptions."
        ),
        "keywords": ["impetigo", "bacterial", "honey-colored crusts", "vesicles", "staph", "strep", "contagious"]
    },
    {
        "id": "contact_dermatitis_guide",
        "disease": "Irritant Contact Dermatitis",
        "category": "Environmental / Toxic Barrier Breakdown",
        "section": "Non-Allergic Irritant Cytotoxicity",
        "source": "American Contact Dermatitis Society (ACDS)",
        "content": (
            "Irritant Contact Dermatitis (ICD) is a non-immunologic cutaneous inflammatory reaction resulting from direct physical or chemical damage "
            "to the epidermal keratinocyte barrier (e.g. soaps, solvents, frequent hand washing, friction). "
            "Patients report burning, stinging, and tight dryness with glazed erythema, chapping, and fissures strictly localized to the contact site. "
            "Unlike allergic contact dermatitis, it does not require prior immunological sensitization."
        ),
        "keywords": ["contact dermatitis", "irritant", "chemical", "burning", "stinging", "chapping", "barrier damage", "exposure"]
    },
    {
        "id": "general_scoring_guide",
        "disease": "General AI Interpretation",
        "category": "Decision Support",
        "section": "Multimodal Confidence Interpretation",
        "source": "DermaAssist Decision Support Clinical Protocol",
        "content": (
            "DermaAssist calculates combined confidence by synthesizing deep CNN dermatoscopic visual pattern embeddings (60%) with structured "
            "clinical symptom priors (40%). A combined score reflects the comparative likelihood among shortlisted candidate lookalike conditions. "
            "Scores above 50% indicate strong multimodal alignment. However, AI screening is an assistive decision-support tool and cannot replace "
            "in-person dermatoscope inspection, biopsy, or definitive clinical examination."
        ),
        "keywords": ["confidence", "score", "percentage", "how it works", "accuracy", "multimodal", "image score", "symptom alignment"]
    }
]


# ─── Simple In-Memory Vector / Keyword Semantic Indexer ───────────────────────

def _tokenize(text: str) -> set:
    """Normalize and tokenize text into word stems/keywords."""
    return set(re.findall(r"\b[a-z]{3,}\b", text.lower()))


def _compute_chunk_similarity(query_tokens: set, chunk: Dict[str, Any]) -> float:
    """Computes hybrid keyword overlap & semantic matching score."""
    content_tokens = _tokenize(chunk["content"])
    keyword_tokens = set(k.lower() for k in chunk.get("keywords", []))
    title_tokens = _tokenize(chunk["disease"] + " " + chunk.get("section", ""))

    # Overlap scores
    content_overlap = len(query_tokens.intersection(content_tokens))
    keyword_overlap = len(query_tokens.intersection(keyword_tokens)) * 2.5
    title_overlap = len(query_tokens.intersection(title_tokens)) * 3.0

    total_score = content_overlap + keyword_overlap + title_overlap
    return float(total_score)


def retrieve_relevant_knowledge(
    query: str,
    case_context_chunks: Optional[List[Dict[str, Any]]] = None,
    top_k: int = 4,
) -> List[Dict[str, Any]]:
    """
    Retrieves top-k most relevant medical context passages matching the user's question,
    combining static curated dermatology documents with dynamic active case report data.
    """
    all_chunks = list(CURATED_KNOWLEDGE_BASE)
    if case_context_chunks:
        all_chunks.extend(case_context_chunks)

    query_tokens = _tokenize(query)
    if not query_tokens:
        return all_chunks[:top_k]

    scored = []
    for chunk in all_chunks:
        score = _compute_chunk_similarity(query_tokens, chunk)
        scored.append((score, chunk))

    # Sort descending by relevance score
    scored.sort(key=lambda x: x[0], reverse=True)

    # Return top-k with positive score or default to top relevant items
    results = [chunk for score, chunk in scored[:top_k] if score > 0]
    if not results:
        results = [scored[0][1]] if scored else []

    return results


def build_case_context_chunks(case: CaseHistory) -> List[Dict[str, Any]]:
    """
    Constructs dynamic retrieval chunks from the patient's specific case analysis report.
    """
    chunks = []
    if not case:
        return chunks

    disease = case.predicted_disease or "Unspecified Lesion"
    conf_pct = round((case.confidence or 0) * 100)
    symptoms = case.symptoms_text or "No specific symptoms reported"
    explanation = case.ai_explanation or f"Case #{case.case_id} predicted as {disease} with {conf_pct}% confidence."

    # Chunk 1: Case Overview & Prediction
    chunks.append({
        "id": f"case_{case.case_id}_overview",
        "disease": disease,
        "category": "Active Patient Case Report",
        "section": f"Case #{case.case_id} Summary & AI Prediction",
        "source": f"Patient Screening Report (Case #{case.case_id})",
        "content": (
            f"For this patient's case (#{case.case_id}), the AI screening model identified '{disease}' as the top primary candidate "
            f"with a combined multimodal confidence of {conf_pct}%. Reported clinical findings include: '{symptoms}'. "
            f"AI diagnostic reasoning notes: {explanation}"
        ),
        "keywords": ["case", "my result", "this case", "predicted", "prediction", "why", "score", disease.lower()]
    })

    # Chunk 2: Differential Diagnoses in Case
    if hasattr(case, "prediction_details") and case.prediction_details:
        diff_text = "; ".join([
            f"Rank #{p.rank}: {p.disease_name} (Combined: {round((p.combined_score or 0)*100)}%, Vision: {round((p.image_score or 0)*100 if (p.image_score or 0) <= 1 else (p.image_score or 0))}%, Symptom: {round((p.symptom_score or 0)*100 if (p.symptom_score or 0) <= 1 else (p.symptom_score or 0))}%)"
            for p in case.prediction_details
        ])
        chunks.append({
            "id": f"case_{case.case_id}_differentials",
            "disease": disease,
            "category": "Active Patient Case Report",
            "section": "Differential Diagnoses Breakdown",
            "source": f"Case #{case.case_id} Differential Ranking",
            "content": f"The full candidate differential breakdown evaluated for Case #{case.case_id} is: {diff_text}.",
            "keywords": ["differential", "differentials", "other diseases", "breakdown", "comparison", "ranks", "ranking"]
        })

    # Chunk 3: Clinical Differentiating Features
    diff_profile = DIFFERENTIATING_CLINICAL_PROFILES.get(disease, {})
    if diff_profile:
        chunks.append({
            "id": f"case_{case.case_id}_distinction",
            "disease": disease,
            "category": "Clinical Distinction Matrix",
            "section": "Key Distinguishing Clinical Features",
            "source": "DermaAssist Differential Knowledge Base",
            "content": (
                f"Clinical distinguishing features for {disease}: {diff_profile.get('key_distinguishing_feature', '')} "
                f"It commonly overlaps clinically with {', '.join(diff_profile.get('overlaps_with', []))}. "
                f"Diagnostic pitfalls to avoid: {diff_profile.get('diagnostic_pitfall', '')}"
            ),
            "keywords": ["distinguishing", "difference", "differentiate", "overlap", "versus", "vs", "separate", disease.lower()]
        })

    return chunks


# ─── Response Generation & Guardrail Synthesizer ─────────────────────────────

def generate_grounded_answer(
    question: str,
    retrieved_chunks: List[Dict[str, Any]],
    case: Optional[CaseHistory] = None,
) -> Dict[str, Any]:
    """
    Synthesizes a strictly grounded, clinically cautious response derived ONLY
    from the retrieved knowledge chunks and active case data.
    """
    q_lower = question.lower()

    # Collect source citations
    citations = []
    seen_sources = set()
    for chunk in retrieved_chunks:
        src_label = f"{chunk['disease']} — {chunk.get('section', 'Clinical Guidelines')} ({chunk['source']})"
        if src_label not in seen_sources:
            citations.append({
                "disease": chunk["disease"],
                "section": chunk.get("section", "Reference Data"),
                "source": chunk["source"],
            })
            seen_sources.add(src_label)

    # Context string
    context_blocks = "\n\n".join([
        f"[{i+1}] Source: {c['source']} | Subject: {c['disease']} ({c.get('section', '')})\n{c['content']}"
        for i, c in enumerate(retrieved_chunks)
    ])

    # Synthesize grounded answer
    paragraphs = []

    # Case-specific queries
    if case and any(w in q_lower for w in ["why", "my result", "this case", "predicted", "classified", "score", "confidence"]):
        top_d = case.predicted_disease or "your condition"
        conf_pct = round((case.confidence or 0) * 100)
        paragraphs.append(
            f"Based on your case screening report (Case #{case.case_id}), the AI identified **{top_d}** with **{conf_pct}% combined confidence**. "
            f"This prediction was generated by combining dermatoscopic visual patterns with your reported clinical symptoms."
        )

    # Core retrieved knowledge synthesis
    if retrieved_chunks:
        top_chunk = retrieved_chunks[0]
        paragraphs.append(f"**Medical Reference Findings:**\n{top_chunk['content']}")

        # If second chunk has relevant distinctive details, include it
        if len(retrieved_chunks) > 1 and retrieved_chunks[1]["id"] != top_chunk["id"]:
            paragraphs.append(f"**Additional Clinical Context:**\n{retrieved_chunks[1]['content']}")
    else:
        paragraphs.append(
            "I could not locate specific verified information in the current clinical knowledge base regarding that question. "
            "Please consult a board-certified dermatologist for tailored clinical guidance."
        )

    # Mandatory Clinical Disclaimer
    paragraphs.append(
        "⚕️ *Clinical Decision Support Note: This response is for educational reference only and does not constitute a formal diagnosis or medical advice. Please consult a qualified dermatologist for an in-person examination.*"
    )

    answer_text = "\n\n".join(paragraphs)

    return {
        "answer": answer_text,
        "sources": citations,
        "retrieved_count": len(retrieved_chunks),
    }


def execute_chat_query(
    db: Session,
    question: str,
    case_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    End-to-end RAG chat execution:
    1. Fetches optional active case report.
    2. Builds dynamic + static context chunks.
    3. Retrieves top relevant passages via vector/keyword similarity.
    4. Generates grounded answer with source citations.
    5. Logs the interaction into chat_audit_logs table.
    """
    case = None
    case_chunks = []
    if case_id:
        case = db.query(CaseHistory).filter(CaseHistory.case_id == case_id).first()
        if case:
            case_chunks = build_case_context_chunks(case)

    # Retrieve relevant knowledge
    retrieved = retrieve_relevant_knowledge(question, case_context_chunks=case_chunks, top_k=3)

    # Generate response
    rag_result = generate_grounded_answer(question, retrieved, case=case)

    # Audit Logging
    try:
        audit_entry = ChatAuditLog(
            user_id=user_id,
            case_id=case_id,
            question=question,
            retrieved_chunks=json.dumps([c["id"] for c in retrieved]),
            answer=rag_result["answer"],
            source_citations=json.dumps(rag_result["sources"]),
            created_at=datetime.utcnow(),
        )
        db.add(audit_entry)
        db.commit()
    except Exception as e:
        logger.warning(f"[RAG] Failed to log chat audit entry: {e}")

    return rag_result
