import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Default model location
MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
DEFAULT_MODEL_PATH = MODEL_DIR / "rf_prior_auth_model.joblib"

_cached_model = None
_model_load_attempted = False


def _get_model():
    """
    Attempt to load a pre-trained scikit-learn Random Forest model artifact.
    Returns None if no trained model file exists.
    """
    global _cached_model, _model_load_attempted
    if _model_load_attempted:
        return _cached_model

    _model_load_attempted = True
    model_path = os.getenv("ML_MODEL_PATH", str(DEFAULT_MODEL_PATH))

    if os.path.exists(model_path):
        try:
            import joblib
            _cached_model = joblib.load(model_path)
            logger.info(f"Loaded trained ML model from {model_path}")
        except Exception as e:
            logger.warning(f"Failed to load ML model artifact from {model_path}: {e}")
            _cached_model = None
    else:
        logger.info(f"No trained ML model artifact found at {model_path}. ML prediction will be marked unavailable.")
        _cached_model = None

    return _cached_model


def is_model_available() -> bool:
    """Check whether a trained ML model artifact is loaded and ready."""
    return _get_model() is not None


def extract_features_for_ml(patient: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured tabular features from the normalized patient dictionary
    for input into a machine learning classifier.
    """
    age = patient.get("age")
    try:
        age_num = float(age) if age is not None else 0.0
    except (ValueError, TypeError):
        age_num = 0.0

    prev_treatments = patient.get("previous_treatment", [])
    if not isinstance(prev_treatments, list):
        prev_treatments = []

    treatment_count = len(prev_treatments)
    total_treatment_days = 0
    for t in prev_treatments:
        if isinstance(t, dict):
            days = t.get("duration_days")
            if isinstance(days, (int, float)):
                total_treatment_days += int(days)

    docs = patient.get("documentation", {})
    doc_count = len(docs) if isinstance(docs, dict) else 0

    return {
        "age": age_num,
        "gender": str(patient.get("gender") or "unknown").lower(),
        "payer": str(patient.get("payer") or "unknown").lower(),
        "cpt_hcpcs_code": str(patient.get("cpt_hcpcs_code") or "").upper(),
        "icd10_code": str(patient.get("icd10_code") or "").upper(),
        "severity": str(patient.get("severity") or "unknown").lower(),
        "provider_specialty": str(patient.get("provider_specialty") or "unknown").lower(),
        "facility_type": str(patient.get("facility_type") or "unknown").lower(),
        "treatment_count": treatment_count,
        "total_treatment_days": total_treatment_days,
        "doc_count": doc_count,
    }


def predict_authorization(patient: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict authorization risk/outcome using a machine learning model.

    Returns a dictionary containing:
    - predicted_class: 'APPROVED', 'DENIED', 'MANUAL REVIEW', or None
    - approval_probability: float or None
    - denial_probability: float or None
    - review_probability: float or None
    - model_name: string
    - model_version: string
    - status: 'available' or 'unavailable'
    - message: status message

    IMPORTANT:
    - If no trained model artifact is found, this function fails safely and
      clearly reports that a trained model artifact is required.
    - It does NOT generate fake numbers or override the deterministic rule engine.
    """
    model_name = "Random Forest Classifier"
    model_version = "1.0"

    model = _get_model()

    if model is None:
        return {
            "status": "unavailable",
            "message": "ML prediction unavailable — trained model not configured.",
            "model_name": model_name,
            "model_version": model_version,
            "predicted_class": None,
            "approval_probability": None,
            "denial_probability": None,
            "review_probability": None,
        }

    try:
        features = extract_features_for_ml(patient)
        
        # If the model has a standard scikit-learn predict / predict_proba interface
        if hasattr(model, "predict_proba") and hasattr(model, "classes_"):
            import pandas as pd
            df_features = pd.DataFrame([features])
            
            # Align features with model if it has feature_names_in_
            if hasattr(model, "feature_names_in_"):
                expected_cols = list(model.feature_names_in_)
                # Check if all expected columns can be provided
                for col in expected_cols:
                    if col not in df_features.columns:
                        df_features[col] = 0
                df_features = df_features[expected_cols]

            probas = model.predict_proba(df_features)[0]
            classes = list(model.classes_)

            prob_map = {}
            for cls_name, p in zip(classes, probas):
                prob_map[str(cls_name).upper()] = float(p)

            pred_class = str(model.predict(df_features)[0]).upper()

            return {
                "status": "available",
                "message": "Prediction generated from trained Random Forest model.",
                "model_name": model_name,
                "model_version": model_version,
                "predicted_class": pred_class,
                "approval_probability": prob_map.get("APPROVED", 0.0),
                "denial_probability": prob_map.get("DENIED", 0.0),
                "review_probability": prob_map.get("MANUAL REVIEW", prob_map.get("MANUAL_REVIEW", 0.0)),
            }

        else:
            return {
                "status": "unavailable",
                "message": "Loaded model does not have a compatible classification interface.",
                "model_name": model_name,
                "model_version": model_version,
                "predicted_class": None,
                "approval_probability": None,
                "denial_probability": None,
                "review_probability": None,
            }
    except Exception as e:
        logger.error(f"Error executing ML inference: {e}")
        return {
            "status": "error",
            "message": f"ML prediction error: {str(e)}",
            "model_name": model_name,
            "model_version": model_version,
            "predicted_class": None,
            "approval_probability": None,
            "denial_probability": None,
            "review_probability": None,
        }
