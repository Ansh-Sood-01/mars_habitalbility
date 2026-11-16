import os
import sys
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    log_loss,
    confusion_matrix
)

# Import existing feature extraction and dataset functions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from train import (
    ROOT,
    CLASSES,
    VAL_ZIP,
    VAL_LABELS,
    load_features,
    load_labels
)

# ============================================================
# 1. PROJECT PATHS
# ============================================================

MODEL_PATH = os.path.join(
    ROOT, "models", "mars_multilabel_model.joblib"
)

OUTPUT_DIR = os.path.join(
    ROOT, "outputs", "evaluation"
)

REPORT_DIR = os.path.join(
    ROOT, "reports"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)


# ============================================================
# 2. LOAD TRAINED MODEL
# ============================================================

print("=" * 60)
print("MARS LAB - MODEL EVALUATION")
print("=" * 60)

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Trained model not found: {MODEL_PATH}"
    )

saved = joblib.load(MODEL_PATH)

model = saved["model"]
classes = saved["classes"]

print("\nTrained model loaded successfully.")


# ============================================================
# 3. LOAD VALIDATION DATA
# ============================================================

print("\nLoading validation spectra...")

X_val = load_features(VAL_ZIP, "val_features")
y_val = load_labels(VAL_LABELS)

common_ids = X_val.index.intersection(y_val.index)

X_val = X_val.loc[common_ids]
y_val = y_val.loc[common_ids, classes]

if X_val.empty:
    raise ValueError("No matching validation samples found.")

print("Validation samples:", len(X_val))
print("Features:", X_val.shape[1])
print("Chemical families:", len(classes))


# ============================================================
# 4. GENERATE PREDICTIONS
# ============================================================

print("\nGenerating predictions...")

y_pred = model.predict(X_val)

probability_columns = []

for estimator in model.estimators_:

    probabilities = estimator.predict_proba(X_val)

    estimator_classes = list(estimator.classes_)

    if 1 in estimator_classes:
        positive_prob = probabilities[
            :, estimator_classes.index(1)
        ]
    else:
        positive_prob = np.zeros(len(X_val))

    probability_columns.append(positive_prob)

y_prob = np.column_stack(probability_columns)


# ============================================================
# 5. PER-LABEL EVALUATION
# ============================================================

print("\nCalculating per-label metrics...")

metrics = []

for i, label in enumerate(classes):

    actual = y_val.iloc[:, i].to_numpy()
    predicted = y_pred[:, i]
    probabilities = np.clip(y_prob[:, i], 1e-15, 1 - 1e-15)

    precision = precision_score(
        actual, predicted, zero_division=0
    )

    recall = recall_score(
        actual, predicted, zero_division=0
    )

    f1 = f1_score(
        actual, predicted, zero_division=0
    )

    label_log_loss = log_loss(
        actual,
        probabilities,
        labels=[0, 1]
    )

    metrics.append({
        "chemical_family": label,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "log_loss": label_log_loss,
        "positive_samples": int(actual.sum()),
        "total_samples": len(actual)
    })


metrics_df = pd.DataFrame(metrics)

metrics_path = os.path.join(
    OUTPUT_DIR, "per_label_metrics.csv"
)

metrics_df.to_csv(metrics_path, index=False)


# ============================================================
# 6. OVERALL METRICS
# ============================================================

macro_f1 = f1_score(
    y_val, y_pred, average="macro", zero_division=0
)

micro_f1 = f1_score(
    y_val, y_pred, average="micro", zero_division=0
)

macro_precision = precision_score(
    y_val, y_pred, average="macro", zero_division=0
)

macro_recall = recall_score(
    y_val, y_pred, average="macro", zero_division=0
)

micro_precision = precision_score(
    y_val, y_pred, average="micro", zero_division=0
)

micro_recall = recall_score(
    y_val, y_pred, average="micro", zero_division=0
)

macro_log_loss = metrics_df["log_loss"].mean()

overall_metrics = {
    "macro_f1": macro_f1,
    "micro_f1": micro_f1,
    "macro_precision": macro_precision,
    "macro_recall": macro_recall,
    "micro_precision": micro_precision,
    "micro_recall": micro_recall,
    "macro_log_loss": macro_log_loss
}


# ============================================================
# 7. CONFUSION MATRICES
# ============================================================

print("\nGenerating confusion matrices...")

fig, axes = plt.subplots(5, 2, figsize=(13, 22))

for i, label in enumerate(classes):

    actual = y_val.iloc[:, i].to_numpy()
    predicted = y_pred[:, i]

    cm = confusion_matrix(
        actual,
        predicted,
        labels=[0, 1]
    )

    ax = axes[i // 2, i % 2]

    image = ax.imshow(cm, cmap="Blues")

    ax.set_title(label.replace("_", " ").title())

    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])

    for row in range(2):
        for col in range(2):

            ax.text(
                col,
                row,
                str(cm[row, col]),
                ha="center",
                va="center",
                color="black",
                fontsize=12
            )

    ax.set_xticklabels(["Negative", "Positive"])
    ax.set_yticklabels(["Negative", "Positive"])

plt.tight_layout()

confusion_path = os.path.join(
    OUTPUT_DIR, "confusion_matrices.png"
)

plt.savefig(confusion_path, dpi=300)
plt.close()


# ============================================================
# 8. F1 SCORE VISUALIZATION
# ============================================================

plt.figure(figsize=(12, 6))

plt.bar(
    metrics_df["chemical_family"],
    metrics_df["f1_score"]
)

plt.title("F1 Score by Chemical Family")
plt.xlabel("Chemical Family")
plt.ylabel("F1 Score")

plt.xticks(rotation=40, ha="right")
plt.ylim(0, 1)

plt.tight_layout()

f1_chart_path = os.path.join(
    OUTPUT_DIR, "f1_scores.png"
)

plt.savefig(f1_chart_path, dpi=300)
plt.close()


# ============================================================
# 9. SAVE FINAL REPORT
# ============================================================

report_path = os.path.join(
    REPORT_DIR, "complete_model_evaluation.txt"
)

with open(report_path, "w", encoding="utf-8") as file:

    file.write("MARS LAB - MODEL EVALUATION REPORT\n")
    file.write("=" * 55 + "\n\n")

    file.write(f"Validation samples: {len(X_val)}\n")
    file.write(f"Features: {X_val.shape[1]}\n")
    file.write(f"Chemical families: {len(classes)}\n\n")

    file.write("OVERALL METRICS\n")
    file.write("-" * 55 + "\n")

    for name, value in overall_metrics.items():
        file.write(f"{name}: {value:.4f}\n")

    file.write("\nPER-LABEL METRICS\n")
    file.write("-" * 55 + "\n")

    file.write(metrics_df.to_string(index=False))

    file.write("\n\nINTERPRETATION NOTE\n")
    file.write(
        "Log loss evaluates the quality of predicted scores. "
        "Lower values are better. Extra Trees probability "
        "outputs are not necessarily calibrated probabilities.\n"
    )

    file.write(
        "\nThese results measure performance on the supplied "
        "validation dataset and do not independently establish "
        "chemical identification or habitability.\n"
    )


# ============================================================
# 10. DISPLAY RESULTS
# ============================================================

print("\n" + "=" * 60)
print("OVERALL MODEL PERFORMANCE")
print("=" * 60)

for name, value in overall_metrics.items():
    print(f"{name}: {value:.4f}")

print("\nPER-LABEL RESULTS")
print(metrics_df.to_string(index=False))

print("\n" + "=" * 60)
print("EVALUATION COMPLETED SUCCESSFULLY")
print("=" * 60)

print("\nGenerated files:")
print(metrics_path)
print(confusion_path)
print(f1_chart_path)
print(report_path)
