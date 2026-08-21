"""
Evidence Combiner Service — Combines image predictions and symptom scores.

Uses configurable weights (IMAGE_WEIGHT, SYMPTOM_WEIGHT) to produce a
combined ranking. Detects low confidence and conflicting evidence.

IMPORTANT: The weights are project-level configurable parameters.
They are NOT medically validated.
"""

from backend.config import settings


def combine_evidence(
    image_predictions: list[dict],
    symptom_scores: list[dict],
    image_weight: float = None,
    symptom_weight: float = None,
) -> dict:
    """
    Combine image and symptom predictions into a final ranked list.

    Args:
        image_predictions: List from image_predictor (rank, disease, confidence)
        symptom_scores: List from symptom_matcher (disease, symptom_score)
        image_weight: Weight for image evidence (default from config)
        symptom_weight: Weight for symptom evidence (default from config)

    Returns:
        Dict with:
        - predictions: Final ranked list with combined scores
        - is_low_confidence: Whether top prediction is below threshold
        - is_conflicting: Whether image and symptom evidence disagree
        - top_image_disease: Top disease from image alone
        - top_symptom_disease: Top disease from symptoms alone
    """
    if image_weight is None:
        image_weight = settings.IMAGE_WEIGHT
    if symptom_weight is None:
        symptom_weight = settings.SYMPTOM_WEIGHT

    # Build symptom score lookup
    symptom_lookup = {}
    for s in symptom_scores:
        symptom_lookup[s["disease"]] = s["symptom_score"]

    # Get all unique disease names (from both sources)
    all_diseases = set()
    for p in image_predictions:
        all_diseases.add(p["disease"])
    for s in symptom_scores:
        all_diseases.add(s["disease"])

    # Build image score lookup
    image_lookup = {}
    for p in image_predictions:
        image_lookup[p["disease"]] = p["confidence"]

    # Calculate combined scores
    combined = []
    for disease in all_diseases:
        img_score = image_lookup.get(disease, 0.0)
        sym_score = symptom_lookup.get(disease, 0.0)

        combined_score = (image_weight * img_score) + (symptom_weight * sym_score)

        combined.append({
            "disease": disease,
            "image_score": round(img_score, 4),
            "symptom_score": round(sym_score, 4),
            "combined_score": round(combined_score, 4),
        })

    # Sort by combined score descending
    combined.sort(key=lambda x: x["combined_score"], reverse=True)

    # Normalize combined scores to sum to 1.0
    total = sum(c["combined_score"] for c in combined)
    if total > 0:
        for c in combined:
            c["combined_score"] = round(c["combined_score"] / total, 4)

    # Assign ranks
    for i, c in enumerate(combined):
        c["rank"] = i + 1

    # Keep top 3
    top_3 = combined[:3]

    # Detect low confidence
    top_confidence = top_3[0]["combined_score"] if top_3 else 0.0
    is_low_confidence = top_confidence < settings.LOW_CONFIDENCE_THRESHOLD

    # Detect conflicting evidence
    top_image_disease = image_predictions[0]["disease"] if image_predictions else None
    top_symptom_disease = symptom_scores[0]["disease"] if symptom_scores and symptom_scores[0]["symptom_score"] > 0 else None
    is_conflicting = (
        top_image_disease is not None
        and top_symptom_disease is not None
        and top_image_disease != top_symptom_disease
        and (image_predictions[0]["confidence"] if image_predictions else 0) > settings.CONFLICT_THRESHOLD
        and (symptom_scores[0]["symptom_score"] if symptom_scores else 0) > settings.CONFLICT_THRESHOLD
    )

    return {
        "predictions": top_3,
        "is_low_confidence": is_low_confidence,
        "is_conflicting": is_conflicting,
        "top_image_disease": top_image_disease,
        "top_symptom_disease": top_symptom_disease,
        "image_weight": image_weight,
        "symptom_weight": symptom_weight,
    }
