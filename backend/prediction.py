import os
import sys
import io

import joblib
import numpy as np
import pandas as pd

from fastapi import APIRouter, UploadFile, File, HTTPException

# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

MODEL_PATH = os.path.join(
    ROOT,
    "models",
    "mars_multilabel_model.joblib"
)

# Import the exact feature extraction function used in training
from src.train import extract_features, CLASSES

router = APIRouter(
    prefix="/api",
    tags=["Spectrum Prediction"]
)

# --------------------------------------------------
# LOAD TRAINED MODEL
# --------------------------------------------------

try:
    saved_model = joblib.load(MODEL_PATH)

    model = saved_model["model"]
    class_names = saved_model["classes"]

    print("Competition prediction model loaded successfully.")

except Exception as error:
    model = None
    class_names = CLASSES

    print("Model loading error:", error)


# --------------------------------------------------
# SPECTRUM PREDICTION ENDPOINT
# --------------------------------------------------

@router.post("/predict")
async def predict_spectrum(file: UploadFile = File(...)):

    if model is None:
        raise HTTPException(
            status_code=500,
            detail="Prediction model is not loaded."
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV spectrum file."
        )

    try:

        # Read uploaded CSV
        contents = await file.read()

        df = pd.read_csv(io.BytesIO(contents))

        required_columns = [
            "time",
            "temp",
            "m/z",
            "abundance"
        ]

        missing_columns = [
            col for col in required_columns
            if col not in df.columns
        ]

        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing columns: {missing_columns}"
            )

        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="Uploaded spectrum is empty."
            )

        # --------------------------------------------------
        # FEATURE EXTRACTION
        # --------------------------------------------------

        features = extract_features(df)

        if len(features) != 395:
            raise HTTPException(
                status_code=500,
                detail=f"Expected 395 features, received {len(features)}."
            )

        X = pd.DataFrame(
            [features],
            columns=range(len(features))
        )

        # --------------------------------------------------
        # PREDICTION
        # --------------------------------------------------

        predictions = model.predict(X)[0]

        probability_columns = []

        for estimator in model.estimators_:

            probabilities = estimator.predict_proba(X)

            estimator_classes = list(estimator.classes_)

            if 1 in estimator_classes:

                positive_index = estimator_classes.index(1)

                probability = float(
                    probabilities[0][positive_index]
                )

            else:
                probability = 0.0

            probability_columns.append(probability)

        # --------------------------------------------------
        # FORMAT RESULTS
        # --------------------------------------------------

        results = []

        for i, chemical in enumerate(class_names):

            score = probability_columns[i]

            results.append({
                "chemical_family": chemical,
                "prediction": int(predictions[i]),
                "score": round(score, 4),
                "status": (
                    "Detected"
                    if predictions[i] == 1
                    else "Not Detected"
                )
            })

        detected = [
            item for item in results
            if item["prediction"] == 1
        ]

        # --------------------------------------------------
        # SPECTRUM DATA FOR FRONTEND VISUALIZATION
        # --------------------------------------------------

        spectrum_data = df[
            ["time", "temp", "m/z", "abundance"]
        ].replace(
            [np.inf, -np.inf], np.nan
        ).dropna()

        spectrum_data["abundance"] = (
            spectrum_data["abundance"].clip(lower=0)
        )

        spectrum_data = spectrum_data.to_dict(
            orient="records"
        )

        # --------------------------------------------------
        # RESPONSE
        # --------------------------------------------------

        return {
            "success": True,
            "filename": file.filename,
            "total_measurements": len(df),
            "features_extracted": len(features),
            "chemical_families": len(class_names),
            "detected_count": len(detected),
            "detected_families": [
                item["chemical_family"]
                for item in detected
            ],
            "predictions": results,
            "spectrum": spectrum_data
        }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(error)}"
        )