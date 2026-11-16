import os
import zipfile
import warnings
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import ExtraTreesClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    classification_report
)

warnings.filterwarnings("ignore")


# ============================================================
# 1. PROJECT PATHS
# ============================================================

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Competition dataset location
RAW = os.path.join(ROOT, "data", "raw", "competition")

# Output directories
MODEL_DIR = os.path.join(ROOT, "models")
REPORT_DIR = os.path.join(ROOT, "reports")
OUTPUT_DIR = os.path.join(ROOT, "outputs")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# 2. CHEMICAL FAMILY LABELS
# ============================================================

CLASSES = [
    "basalt",
    "carbonate",
    "chloride",
    "iron_oxide",
    "oxalate",
    "oxychlorine",
    "phyllosilicate",
    "silicate",
    "sulfate",
    "sulfide"
]


# Dataset files
TRAIN_ZIP = os.path.join(RAW, "train_features.zip")
VAL_ZIP = os.path.join(RAW, "val_features.zip")

TRAIN_LABELS = os.path.join(RAW, "train_labels.csv")
VAL_LABELS = os.path.join(RAW, "val_labels.csv")


# ============================================================
# 3. FEATURE EXTRACTION
# ============================================================

def extract_features(df):

    """Convert variable-sized spectra into fixed-length features."""

    required = ["time", "temp", "m/z", "abundance"]

    if not set(required).issubset(df.columns):
        missing = set(required) - set(df.columns)
        raise ValueError(f"Missing columns: {missing}")

    df = df[required].copy()

    df = df.replace([np.inf, -np.inf], np.nan).dropna()

    if df.empty:
        raise ValueError("Spectrum contains no valid measurements.")

    df["abundance"] = df["abundance"].clip(lower=0)

    # Log transformation
    df["log_abundance"] = np.log1p(
        df["abundance"] * 1e12
    )

    features = []

    # --------------------------------------------------------
    # MASS-TO-CHARGE FEATURES
    # --------------------------------------------------------

    mz_bins = np.arange(0, 201, 2)

    df["mz_bin"] = np.clip(
        np.digitize(df["m/z"], mz_bins) - 1,
        0,
        len(mz_bins) - 2
    )

    grouped_mz = df.groupby("mz_bin")["log_abundance"].agg(
        ["mean", "max", "std"]
    ).reindex(
        range(len(mz_bins) - 1),
        fill_value=0
    )

    for col in ["mean", "max", "std"]:
        features.extend(
            grouped_mz[col].fillna(0).to_numpy()
        )

    # --------------------------------------------------------
    # TEMPERATURE FEATURES
    # --------------------------------------------------------

    temp_min = float(df["temp"].min())
    temp_max = float(df["temp"].max())

    if temp_max <= temp_min:
        temp_max = temp_min + 1.0

    temp_edges = np.linspace(
        temp_min,
        temp_max,
        21
    )

    df["temp_bin"] = np.clip(
        np.digitize(df["temp"], temp_edges) - 1,
        0,
        19
    )

    temp_profile = df.groupby("temp_bin")["log_abundance"].agg(
        ["mean", "max", "std"]
    ).reindex(
        range(20),
        fill_value=0
    )

    for col in ["mean", "max", "std"]:
        features.extend(
            temp_profile[col].fillna(0).to_numpy()
        )

    # --------------------------------------------------------
    # GLOBAL STATISTICAL FEATURES
    # --------------------------------------------------------

    for col in [
        "time",
        "temp",
        "m/z",
        "abundance",
        "log_abundance"
    ]:

        values = df[col].to_numpy(dtype=float)

        features.extend([
            float(np.mean(values)),
            float(np.std(values)),
            float(np.min(values)),
            float(np.max(values)),
            float(np.percentile(values, 25)),
            float(np.percentile(values, 50)),
            float(np.percentile(values, 75))
        ])

    result = np.asarray(features, dtype=float)

    return np.nan_to_num(
        result,
        nan=0.0,
        posinf=0.0,
        neginf=0.0
    )


# ============================================================
# 4. LOAD SPECTROMETRY FEATURES FROM ZIP
# ============================================================

def load_features(zip_path, prefix):

    if not os.path.exists(zip_path):
        raise FileNotFoundError(
            f"Dataset ZIP not found: {zip_path}"
        )

    rows = []
    sample_ids = []

    with zipfile.ZipFile(zip_path) as archive:

        entries = sorted(
            name for name in archive.namelist()
            if name.startswith(prefix + "/")
            and name.endswith(".csv")
        )

        if not entries:
            raise ValueError(
                f"No CSV samples found under {prefix}/ in {zip_path}"
            )

        for i, name in enumerate(entries, 1):

            sample_id = os.path.splitext(
                os.path.basename(name)
            )[0]

            with archive.open(name) as stream:

                df = pd.read_csv(stream)

            rows.append(extract_features(df))
            sample_ids.append(sample_id)

            if i % 50 == 0 or i == len(entries):

                print(
                    f"Processed {prefix}: "
                    f"{i}/{len(entries)} samples"
                )

    return pd.DataFrame(
        rows,
        index=sample_ids
    )


# ============================================================
# 5. LOAD LABELS
# ============================================================

def load_labels(path):

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Label file not found: {path}"
        )

    df = pd.read_csv(path)

    if "sample_id" not in df.columns:
        raise ValueError(
            f"'sample_id' column missing in {path}"
        )

    df = df.set_index("sample_id")

    missing = set(CLASSES) - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing label columns: {missing}"
        )

    return df[CLASSES].astype(int)


# ============================================================
# 6. MAIN TRAINING PIPELINE
# ============================================================

def main():

    print("=" * 60)
    print("MARS HABITABILITY - MACHINE LEARNING PIPELINE")
    print("=" * 60)

    print("\nChecking dataset files...")

    required_files = [
        TRAIN_ZIP,
        VAL_ZIP,
        TRAIN_LABELS,
        VAL_LABELS
    ]

    for file in required_files:

        if not os.path.exists(file):
            raise FileNotFoundError(
                f"Required file missing: {file}"
            )

        print(f"Found: {os.path.basename(file)}")

    # --------------------------------------------------------
    # LOAD TRAINING DATA
    # --------------------------------------------------------

    print("\nLoading training spectra...")

    X_train = load_features(
        TRAIN_ZIP,
        "train_features"
    )

    y_train = load_labels(TRAIN_LABELS)

    # --------------------------------------------------------
    # LOAD VALIDATION DATA
    # --------------------------------------------------------

    print("\nLoading validation spectra...")

    X_val = load_features(
        VAL_ZIP,
        "val_features"
    )

    y_val = load_labels(VAL_LABELS)

    # --------------------------------------------------------
    # MATCH SAMPLE IDS
    # --------------------------------------------------------

    train_ids = X_train.index.intersection(
        y_train.index
    )

    val_ids = X_val.index.intersection(
        y_val.index
    )

    X_train = X_train.loc[train_ids]
    y_train = y_train.loc[train_ids]

    X_val = X_val.loc[val_ids]
    y_val = y_val.loc[val_ids]

    if X_train.empty or X_val.empty:

        raise ValueError(
            "No matching samples between features and labels."
        )

    if list(X_train.columns) != list(X_val.columns):

        raise ValueError(
            "Training and validation feature dimensions differ."
        )

    print("\n" + "=" * 60)

    print(f"Training samples: {len(X_train)}")
    print(f"Validation samples: {len(X_val)}")
    print(f"Feature dimensions: {X_train.shape[1]}")
    print(f"Chemical families: {len(CLASSES)}")

    print("=" * 60)

    # --------------------------------------------------------
    # MODEL INITIALIZATION
    # --------------------------------------------------------

    model = MultiOutputClassifier(

        ExtraTreesClassifier(

            n_estimators=250,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1

        ),

        n_jobs=-1

    )

    # --------------------------------------------------------
    # TRAIN MODEL
    # --------------------------------------------------------

    print("\nTraining ExtraTrees model...")

    model.fit(
        X_train,
        y_train
    )

    print("\nTraining completed successfully!")

    # --------------------------------------------------------
    # VALIDATION PREDICTIONS
    # --------------------------------------------------------

    print("\nGenerating validation predictions...")

    y_pred = model.predict(X_val)

    probability_columns = []

    for estimator in model.estimators_:

        probabilities = estimator.predict_proba(X_val)

        classes = list(estimator.classes_)

        if 1 in classes:

            probability_columns.append(
                probabilities[:, classes.index(1)]
            )

        else:

            probability_columns.append(
                np.zeros(len(X_val))
            )

    y_prob = np.column_stack(
        probability_columns
    )

    # --------------------------------------------------------
    # EVALUATION METRICS
    # --------------------------------------------------------

    results = {

        "macro_f1": f1_score(
            y_val,
            y_pred,
            average="macro",
            zero_division=0
        ),

        "micro_f1": f1_score(
            y_val,
            y_pred,
            average="micro",
            zero_division=0
        ),

        "macro_precision": precision_score(
            y_val,
            y_pred,
            average="macro",
            zero_division=0
        ),

        "macro_recall": recall_score(
            y_val,
            y_pred,
            average="macro",
            zero_division=0
        ),

        "micro_precision": precision_score(
            y_val,
            y_pred,
            average="micro",
            zero_division=0
        ),

        "micro_recall": recall_score(
            y_val,
            y_pred,
            average="micro",
            zero_division=0
        )

    }

    print("\n" + "=" * 60)
    print("VALIDATION METRICS")
    print("=" * 60)

    for name, value in results.items():

        print(f"{name}: {value:.4f}")

    # --------------------------------------------------------
    # CLASSIFICATION REPORT
    # --------------------------------------------------------

    report = classification_report(

        y_val,
        y_pred,
        target_names=CLASSES,
        zero_division=0

    )

    print("\nPER-CLASS CLASSIFICATION REPORT")
    print(report)

    # --------------------------------------------------------
    # SAVE METRICS
    # --------------------------------------------------------

    metrics_path = os.path.join(
        REPORT_DIR,
        "validation_metrics.txt"
    )

    with open(metrics_path, "w") as f:

        for name, value in results.items():

            f.write(
                f"{name}: {value:.4f}\n"
            )

        f.write("\n")
        f.write(report)

    # --------------------------------------------------------
    # SAVE PREDICTIONS
    # --------------------------------------------------------

    predictions = pd.DataFrame(

        y_pred,
        index=X_val.index,
        columns=CLASSES

    )

    predictions.index.name = "sample_id"

    predictions.to_csv(

        os.path.join(
            OUTPUT_DIR,
            "validation_predictions.csv"
        )

    )

    # --------------------------------------------------------
    # SAVE SCORES
    # --------------------------------------------------------

    probabilities = pd.DataFrame(

        y_prob,
        index=X_val.index,
        columns=CLASSES

    )

    probabilities.index.name = "sample_id"

    probabilities.to_csv(

        os.path.join(
            OUTPUT_DIR,
            "validation_scores.csv"
        )

    )

    # --------------------------------------------------------
    # SAVE TRAINED MODEL
    # --------------------------------------------------------

    model_path = os.path.join(
        MODEL_DIR,
        "mars_multilabel_model.joblib"
    )

    joblib.dump(

        {
            "model": model,
            "classes": CLASSES
        },

        model_path

    )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("PROJECT TRAINING COMPLETED")
    print("=" * 60)

    print("\nSaved model:")
    print(model_path)

    print("\nSaved metrics:")
    print(metrics_path)

    print("\nSaved predictions:")
    print(
        os.path.join(
            OUTPUT_DIR,
            "validation_predictions.csv"
        )
    )

    print("\nSaved scores:")
    print(
        os.path.join(
            OUTPUT_DIR,
            "validation_scores.csv"
        )
    )

    print("\nAll operations completed successfully!")


# ============================================================
# 7. EXECUTION
# ============================================================

if __name__ == "__main__":
    main()