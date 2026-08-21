"""
Symptom Matcher Service — TF-IDF + Cosine Similarity matching.
Compares user-entered symptoms against the disease symptom database.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from backend.database.models import Disease, DiseaseSymptom
from backend.utils.text_utils import clean_symptom_text


class SymptomMatcher:
    """
    Matches user symptom text against disease symptom descriptions using TF-IDF.
    Loads symptom data from database and builds TF-IDF vectors.
    """

    def __init__(self):
        self._vectorizer = None
        self._disease_vectors = None
        self._disease_names = []
        self._disease_docs = []
        self._is_fitted = False

    def fit(self, db: Session):
        """
        Build TF-IDF vectors from disease symptoms in the database.
        Each disease gets a single document composed of all its symptom descriptions.
        """
        diseases = db.query(Disease).all()

        self._disease_names = []
        self._disease_docs = []

        for disease in diseases:
            symptoms = (
                db.query(DiseaseSymptom)
                .filter(DiseaseSymptom.disease_id == disease.disease_id)
                .all()
            )

            if not symptoms:
                continue

            # Combine all symptom keywords and descriptions into one document
            doc_parts = []
            for s in symptoms:
                doc_parts.append(s.symptom_keyword)
                doc_parts.append(s.symptom_description)

            doc = " ".join(doc_parts)
            doc = clean_symptom_text(doc)

            self._disease_names.append(disease.name)
            self._disease_docs.append(doc)

        if not self._disease_docs:
            print("[WARN] No symptom data found in database.")
            self._is_fitted = False
            return

        # Build TF-IDF vectorizer
        self._vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=5000,
            ngram_range=(1, 2),  # Unigrams and bigrams
        )
        self._disease_vectors = self._vectorizer.fit_transform(self._disease_docs)
        self._is_fitted = True
        print(f"[SYMPTOMS] TF-IDF fitted with {len(self._disease_names)} diseases")

    def match(self, user_symptoms: str) -> list[dict]:
        """
        Match user symptom text against disease symptom vectors.

        Args:
            user_symptoms: Raw symptom text from the user.

        Returns:
            List of dicts with disease name and similarity score, sorted descending.
        """
        if not self._is_fitted or not user_symptoms.strip():
            return self._empty_scores()

        # Clean and vectorize user input
        cleaned = clean_symptom_text(user_symptoms)
        if not cleaned:
            return self._empty_scores()

        try:
            user_vector = self._vectorizer.transform([cleaned])

            # Cosine similarity against all diseases
            similarities = cosine_similarity(user_vector, self._disease_vectors)[0]

            # Build results
            results = []
            for i, (name, score) in enumerate(zip(self._disease_names, similarities)):
                results.append({
                    "disease": name,
                    "symptom_score": float(score),
                })

            # Sort by score descending
            results.sort(key=lambda x: x["symptom_score"], reverse=True)
            return results

        except Exception as e:
            print(f"[ERROR] Symptom matching failed: {e}")
            return self._empty_scores()

    def _empty_scores(self) -> list[dict]:
        """Return zero scores for all diseases."""
        return [
            {"disease": name, "symptom_score": 0.0}
            for name in self._disease_names
        ]


# Global instance
_symptom_matcher = SymptomMatcher()


def get_symptom_matcher() -> SymptomMatcher:
    """Get the global symptom matcher instance."""
    return _symptom_matcher


def init_symptom_matcher(db: Session):
    """Initialize/refresh the symptom matcher with database data."""
    _symptom_matcher.fit(db)


def match_symptoms(user_symptoms: str) -> list[dict]:
    """Convenience function to match symptoms."""
    return _symptom_matcher.match(user_symptoms)
