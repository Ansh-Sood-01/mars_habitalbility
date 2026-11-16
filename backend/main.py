import os
import glob
import sys
import traceback

import joblib
import numpy as np
import pandas as pd

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DATA_PATH = os.path.join(
    ROOT, "data", "processed",
    "nasa_sam_experiment_features.csv"
)

NASA_QMS_RAW_DIR = os.path.join(
    ROOT, "data", "raw", "nasa_sam_l1a", "all_spyr_qms"
)

MODEL_DIR = os.path.join(ROOT, "models")

OUTPUT_DIR = os.path.join(
    ROOT, "outputs", "ml_analysis"
)

COMPETITION_MODEL_PATH = os.path.join(
    MODEL_DIR, "mars_multilabel_model.joblib"
)

SCALER_PATH = os.path.join(
    MODEL_DIR, "nasa_scaler.joblib"
)

PCA_PATH = os.path.join(
    MODEL_DIR, "nasa_pca.joblib"
)

KMEANS_PATH = os.path.join(
    MODEL_DIR, "nasa_kmeans.joblib"
)

ISOLATION_PATH = os.path.join(
    MODEL_DIR, "nasa_isolation_forest.joblib"
)

CLUSTER_RESULTS_PATH = os.path.join(
    OUTPUT_DIR, "nasa_ml_results.csv"
)

CLUSTER_SUMMARY_PATH = os.path.join(
    OUTPUT_DIR, "cluster_summary.csv"
)


# ============================================================
# 2. FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="MARS LAB API",
    description=(
        "Mars Spectrometry Analysis and "
        "Chemical Family Prediction API"
    ),
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.1.7:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 3. LOAD NASA SAM DATA
# ============================================================

try:
    experiments_df = pd.read_csv(DATA_PATH)

    print(
        f"NASA SAM experiments loaded: "
        f"{len(experiments_df)}"
    )

except Exception as error:
    experiments_df = pd.DataFrame()

    print("NASA SAM data loading error:", error)


# ============================================================
# 4. LOAD NASA SAM MACHINE LEARNING MODELS
# ============================================================

scaler = None
pca = None
kmeans = None
isolation_forest = None

try:
    scaler = joblib.load(SCALER_PATH)
    pca = joblib.load(PCA_PATH)
    kmeans = joblib.load(KMEANS_PATH)
    isolation_forest = joblib.load(ISOLATION_PATH)

    print("NASA SAM ML models loaded successfully.")

except Exception as error:
    print("NASA SAM model loading error:", error)


# ============================================================
# 5. LOAD COMPETITION CLASSIFICATION MODEL
# ============================================================

competition_model = None
chemical_classes = []

try:
    saved_model = joblib.load(COMPETITION_MODEL_PATH)

    competition_model = saved_model["model"]
    chemical_classes = saved_model["classes"]

    print("Competition prediction model loaded successfully.")

except Exception as error:
    print("Competition model loading error:", error)


# ============================================================
# 6. HELPER FUNCTIONS
# ============================================================

def clean_records(df):

    return df.replace(
        [np.inf, -np.inf], np.nan
    ).fillna(0)


def get_experiment_id(row):

    if "experiment_id" in row:
        return str(row["experiment_id"])

    if "eid" in row:
        return str(row["eid"])

    return None


def get_numeric_feature_columns(df):

    excluded = {
        "experiment_id",
        "eid",
        "filename",
        "file",
        "cluster",
        "anomaly",
        "is_anomaly"
    }

    return [
        col for col in df.columns
        if col not in excluded
        and pd.api.types.is_numeric_dtype(df[col])
    ]


def prepare_nasa_features(df):
    """Prepare NASA SAM features using the exact training transformations."""
    if scaler is None:
        raise RuntimeError("NASA scaler is not loaded.")

    # Keep exactly the same feature names and column order used during fit.
    if hasattr(scaler, "feature_names_in_"):
        feature_columns = list(scaler.feature_names_in_)
        missing = [col for col in feature_columns if col not in df.columns]
        if missing:
            raise ValueError(f"Missing NASA model features: {missing}")
        X = df[feature_columns].copy()
    else:
        feature_columns = get_numeric_feature_columns(df)
        X = df[feature_columns].copy()

    # Match training cleanup. The current 97-row feature table has no missing
    # values; zero fill is retained as a safe fallback for API input rows.
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)

    # CRITICAL: train_nasa_ml.py applies log1p after clipping all features
    # to non-negative values and BEFORE StandardScaler.
    X = np.log1p(X.clip(lower=0))

    return X


def prepare_competition_features(df):

    # Import the exact feature extractor used in training.
    from src.train import extract_features

    required = [
        "time",
        "temp",
        "m/z",
        "abundance"
    ]

    missing = [
        col for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    features = extract_features(df)

    if len(features) != 395:
        raise ValueError(
            f"Expected 395 features, received {len(features)}."
        )

    return pd.DataFrame(
        [features],
        columns=range(len(features))
    )




def build_enriched_nasa_dataframe():
    """Return NASA experiments with labels generated by the loaded pipelines."""
    if experiments_df.empty:
        return pd.DataFrame()
    if scaler is None or pca is None:
        raise RuntimeError("NASA scaler/PCA models are not loaded.")
    if kmeans is None or isolation_forest is None:
        raise RuntimeError("NASA clustering/anomaly models are not fully loaded.")

    # Same sequence as training: feature selection -> cleanup -> log1p ->
    # StandardScaler -> PCA -> K-Means / Isolation Forest.
    X = prepare_nasa_features(experiments_df)
    X_scaled = scaler.transform(X)
    X_pca = pca.transform(X_scaled)

    result = experiments_df.copy()
    result["cluster"] = kmeans.predict(X_pca).astype(int)
    result["anomaly"] = isolation_forest.predict(X_pca).astype(int)
    result["anomaly_status"] = np.where(
        result["anomaly"].to_numpy() == -1, "Anomaly", "Normal"
    )
    result["anomaly_score"] = isolation_forest.decision_function(
        X_pca
    ).astype(float)

    return result


# ============================================================
# 7. ROOT ENDPOINT
# ============================================================

@app.get("/")
def home():

    return {
        "project": "MARS LAB",
        "description": (
            "Planetary Sample Spectrometry "
            "Analysis for Habitability Evidence"
        ),
        "version": "2.0.0",
        "status": "running",
        "documentation": "/docs"
    }


# ============================================================
# 8. HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():

    return {
        "status": "healthy",
        "nasa_data_loaded": not experiments_df.empty,
        "nasa_models_loaded": all([
            scaler is not None,
            pca is not None,
            kmeans is not None,
            isolation_forest is not None
        ]),
        "competition_model_loaded": (
            competition_model is not None
        )
    }


# ============================================================
# 9. PROJECT OVERVIEW
# ============================================================

@app.get("/api/overview")
def overview():
    total_experiments = int(len(experiments_df))
    feature_columns = get_numeric_feature_columns(experiments_df) if not experiments_df.empty else []
    cluster_count = 0
    anomaly_count = 0
    explained_variance = 0.0

    if pca is not None and hasattr(pca, "explained_variance_ratio_"):
        explained_variance = round(
            float(np.sum(pca.explained_variance_ratio_)) * 100, 2
        )

    if not experiments_df.empty:
        try:
            enriched = build_enriched_nasa_dataframe()
            cluster_count = int(enriched["cluster"].nunique())
            anomaly_count = int((enriched["anomaly"] == -1).sum())
        except Exception as error:
            print("Overview derived-statistics warning:", error)

    return {
        "project": "MARS LAB",
        "total_experiments": total_experiments,
        "total_features": int(len(feature_columns)),
        "total_clusters": cluster_count,
        "total_anomalies": anomaly_count,
        "pca_components": int(pca.n_components_) if pca is not None else 0,
        "pca_explained_variance": explained_variance,
        "chemical_families": len(chemical_classes),
        "competition_model_available": competition_model is not None,
    }


# ============================================================
# 10. GET ALL EXPERIMENTS
# ============================================================

@app.get("/api/experiments")
def get_experiments():
    if experiments_df.empty:
        return {"total": 0, "experiments": []}
    try:
        df = build_enriched_nasa_dataframe()
        return {
            "total": len(df),
            "experiments": clean_records(df).to_dict(orient="records")
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not prepare experiment records: {str(error)}"
        )

# ============================================================
# 11. GET INDIVIDUAL EXPERIMENT
# ============================================================

@app.get("/api/experiment/{experiment_id}")
def get_experiment(experiment_id: str):

    if experiments_df.empty:
        raise HTTPException(
            status_code=404,
            detail="NASA SAM dataset not available."
        )

    if "experiment_id" in experiments_df.columns:
        matches = experiments_df[
            experiments_df["experiment_id"].astype(str)
            == str(experiment_id)
        ]

    elif "eid" in experiments_df.columns:
        matches = experiments_df[
            experiments_df["eid"].astype(str)
            == str(experiment_id)
        ]

    else:
        raise HTTPException(
            status_code=500,
            detail="Experiment ID column not found."
        )

    if matches.empty:
        raise HTTPException(
            status_code=404,
            detail="Experiment not found."
        )

    return clean_records(
        matches
    ).to_dict(orient="records")[0]


# ============================================================
# 12. INDIVIDUAL EXPERIMENT MASS SPECTRUM
# ============================================================

@app.get("/api/experiment/{experiment_id}/spectrum")
def get_experiment_spectrum(experiment_id: str):
    """Read the original QMS mass TAB file for one experiment."""
    if experiments_df.empty:
        raise HTTPException(status_code=404, detail="NASA SAM dataset not available.")

    id_column = "experiment_id" if "experiment_id" in experiments_df.columns else "eid"
    if id_column not in experiments_df.columns:
        raise HTTPException(status_code=500, detail="Experiment ID column not found.")

    matches = experiments_df[
        experiments_df[id_column].astype(str) == str(experiment_id)
    ]
    if matches.empty:
        raise HTTPException(status_code=404, detail="Experiment not found.")

    filename = str(matches.iloc[0].get("filename", "")).strip()
    if not filename or os.path.basename(filename) != filename:
        raise HTTPException(status_code=404, detail="Original QMS filename is unavailable.")

    # Search only within the configured NASA SAM QMS data directory.
    raw_file = None
    for candidate in glob.glob(
        os.path.join(NASA_QMS_RAW_DIR, "**", filename),
        recursive=True
    ):
        if os.path.isfile(candidate):
            raw_file = candidate
            break

    if raw_file is None:
        raise HTTPException(
            status_code=404,
            detail="Original mass spectrum file was not found in the local QMS archive."
        )

    try:
        raw = pd.read_csv(raw_file, skipinitialspace=True)
        raw.columns = raw.columns.astype(str).str.strip()

        required = ["AMU", "COUNTS PER SECOND"]
        missing = [column for column in required if column not in raw.columns]
        if missing:
            raise ValueError(f"Missing columns in QMS TAB file: {missing}")

        raw["AMU"] = pd.to_numeric(raw["AMU"], errors="coerce")
        raw["COUNTS PER SECOND"] = pd.to_numeric(
            raw["COUNTS PER SECOND"], errors="coerce"
        )
        raw = raw.dropna(subset=required).sort_values("AMU")

        if raw.empty:
            raise ValueError("The QMS file contains no valid mass measurements.")

        # Keep peak values while limiting response size for browser rendering.
        bucket_count = min(1200, len(raw))
        sampled = []
        for bucket in range(bucket_count):
            start = int(bucket * len(raw) / bucket_count)
            end = int((bucket + 1) * len(raw) / bucket_count)
            chunk = raw.iloc[start:max(start + 1, end)]
            if not chunk.empty:
                peak_index = chunk["COUNTS PER SECOND"].idxmax()
                peak = raw.loc[peak_index]
                sampled.append({
                    "amu": float(peak["AMU"]),
                    "counts_per_second": float(peak["COUNTS PER SECOND"])
                })

        return {
            "experiment_id": str(experiment_id),
            "filename": filename,
            "total_measurements": int(len(raw)),
            "displayed_points": len(sampled),
            "x_label": "AMU (mass-to-charge ratio)",
            "y_label": "Counts per second",
            "points": sampled
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read QMS mass spectrum: {str(error)}"
        )


# ============================================================
# 13. CLUSTER ANALYSIS
# ============================================================

@app.get("/api/clusters")
def get_clusters():
    if experiments_df.empty:
        raise HTTPException(status_code=404, detail="NASA dataset not available.")
    try:
        df = build_enriched_nasa_dataframe()
        total = max(len(df), 1)
        summary = []
        for cluster_id, group in df.groupby("cluster", sort=True):
            count = int(len(group))
            anomaly_count = int((group["anomaly"] == -1).sum())
            summary.append({
                "cluster": int(cluster_id),
                "experiment_count": count,
                "anomaly_count": anomaly_count,
                "percentage": round(count * 100.0 / total, 2),
            })
        return {
            "total_clusters": int(df["cluster"].nunique()),
            "clusters": summary,
            "experiments": clean_records(df).to_dict(orient="records"),
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Cluster analysis failed: {str(error)}"
        )

# ============================================================
# 13. ANOMALY DETECTION
# ============================================================

@app.get("/api/anomalies")
def get_anomalies():
    if experiments_df.empty:
        raise HTTPException(status_code=404, detail="NASA dataset not available.")
    try:
        df = build_enriched_nasa_dataframe()
        anomalies = df[df["anomaly"] == -1].copy()
        return {
            "total_experiments": int(len(df)),
            "anomaly_count": int(len(anomalies)),
            "normal_count": int(len(df) - len(anomalies)),
            "anomalies": clean_records(anomalies).to_dict(orient="records"),
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Anomaly detection failed: {str(error)}"
        )

# ============================================================
# 14. PCA VISUALIZATION
# ============================================================

@app.get("/api/visualization/pca")
def pca_visualization():
    if experiments_df.empty:
        raise HTTPException(status_code=404, detail="NASA dataset not available.")

    if scaler is None or pca is None:
        raise HTTPException(status_code=500, detail="PCA models are unavailable.")

    try:
        X = prepare_nasa_features(experiments_df)
        X_scaled = scaler.transform(X)
        X_pca = pca.transform(X_scaled)

        enriched = build_enriched_nasa_dataframe()
        cluster_labels = enriched["cluster"].to_numpy(dtype=int)
        anomaly_flags = (enriched["anomaly"].to_numpy(dtype=int) == -1)

        result = []
        for i, coordinates in enumerate(X_pca):
            if "experiment_id" in experiments_df.columns:
                experiment_id = str(experiments_df.iloc[i]["experiment_id"])
            elif "eid" in experiments_df.columns:
                experiment_id = str(experiments_df.iloc[i]["eid"])
            else:
                experiment_id = str(i)

            result.append({
                "experiment_id": experiment_id,
                "pc1": float(coordinates[0]),
                "pc2": float(coordinates[1]) if X_pca.shape[1] > 1 else 0.0,
                "cluster": int(cluster_labels[i]),
                "anomaly": bool(anomaly_flags[i]),
            })

        return {
            "total_points": len(result),
            "explained_variance": (
                pca.explained_variance_ratio_[:2].tolist()
                if hasattr(pca, "explained_variance_ratio_") else []
            ),
            "points": result,
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=f"PCA visualization failed: {str(error)}")


# ============================================================
# 15. COMPETITION MODEL - SPECTRUM PREDICTION
# ============================================================

@app.post("/api/predict")
async def predict_spectrum(
    file: UploadFile = File(...)
):

    if competition_model is None:
        raise HTTPException(
            status_code=500,
            detail="Competition prediction model not loaded."
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file."
        )

    try:

        contents = await file.read()

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )

        df = pd.read_csv(
            pd.io.common.BytesIO(contents)
        )

        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="No measurements found in CSV."
            )

        required_columns = [
            "time",
            "temp",
            "m/z",
            "abundance"
        ]

        missing = [
            col for col in required_columns
            if col not in df.columns
        ]

        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing columns: {missing}"
            )

        # Extract the same 395 features used in training.
        X = prepare_competition_features(df)

        # Generate multi-label predictions.
        predictions = competition_model.predict(X)[0]

        # Generate positive-class scores.
        scores = []

        for estimator in competition_model.estimators_:

            probabilities = estimator.predict_proba(X)

            classes = list(estimator.classes_)

            if 1 in classes:

                positive_index = classes.index(1)

                score = float(
                    probabilities[0][positive_index]
                )

            else:
                score = 0.0

            scores.append(score)

        prediction_results = []

        for i, chemical in enumerate(chemical_classes):

            detected = int(predictions[i])

            prediction_results.append({
                "chemical_family": chemical,
                "prediction": detected,
                "score": round(scores[i], 4),
                "status": (
                    "Detected"
                    if detected == 1
                    else "Not Detected"
                )
            })

        detected_families = [
            item["chemical_family"]
            for item in prediction_results
            if item["prediction"] == 1
        ]

        # Clean spectrum data and preserve narrow peaks for visualization.
        spectrum = df[required_columns].replace(
            [np.inf, -np.inf], np.nan
        ).dropna().copy()
        spectrum["m/z"] = pd.to_numeric(spectrum["m/z"], errors="coerce")
        spectrum["abundance"] = pd.to_numeric(
            spectrum["abundance"], errors="coerce"
        ).clip(lower=0)
        spectrum = spectrum.dropna(subset=["m/z", "abundance"])

        if len(spectrum) > 1500:
            spectrum = spectrum.sort_values("m/z").reset_index(drop=True)
            bucket_edges = np.linspace(0, len(spectrum), 1501).astype(int)
            peak_rows = []
            for bucket in range(1500):
                chunk = spectrum.iloc[
                    bucket_edges[bucket]:bucket_edges[bucket + 1]
                ]
                if not chunk.empty:
                    peak_rows.append(chunk.loc[chunk["abundance"].idxmax()])
            spectrum = pd.DataFrame(peak_rows).reset_index(drop=True)

        return {
            "success": True,
            "filename": file.filename,
            "total_measurements": len(spectrum),
            "features_extracted": len(X.columns),
            "total_chemical_families": len(chemical_classes),
            "detected_count": len(detected_families),
            "detected_families": detected_families,
            "predictions": prediction_results,
            "spectrum": spectrum.to_dict(
                orient="records"
            )
        }

    except HTTPException:
        raise

    except Exception as error:

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Spectrum prediction failed: {str(error)}"
        )


# ============================================================
# 16. STARTUP INFORMATION
# ============================================================

@app.on_event("startup")
async def startup_event():

    print("\n" + "=" * 55)
    print("MARS LAB BACKEND INITIALIZED")
    print("=" * 55)

    print(
        "NASA SAM experiments:",
        len(experiments_df)
    )

    print(
        "Competition chemical families:",
        len(chemical_classes)
    )

    print(
        "Competition model:",
        "Loaded" if competition_model is not None
        else "Not loaded"
    )

    print(
        "NASA ML models:",
        "Loaded" if scaler is not None and pca is not None
        else "Not fully loaded"
    )

    print("=" * 55)