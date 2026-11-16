import os
import warnings
import joblib
import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.metrics import silhouette_score

warnings.filterwarnings("ignore")

# ==========================================
# 1. PROJECT PATHS
# ==========================================

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_FILE = os.path.join(
    ROOT, "data", "processed",
    "nasa_sam_experiment_features.csv"
)

MODEL_DIR = os.path.join(ROOT, "models")
OUTPUT_DIR = os.path.join(ROOT, "outputs", "ml_analysis")
REPORT_DIR = os.path.join(ROOT, "reports")

for folder in [MODEL_DIR, OUTPUT_DIR, REPORT_DIR]:
    os.makedirs(folder, exist_ok=True)


# ==========================================
# 2. LOAD DATA
# ==========================================

print("\nLoading NASA SAM feature dataset...")

df = pd.read_csv(DATA_FILE)

print("Dataset shape:", df.shape)


# ==========================================
# 3. SELECT NUMERICAL FEATURES
# ==========================================

exclude_columns = [
    "experiment_id",
    "filename"
]

feature_df = df.drop(
    columns=exclude_columns,
    errors="ignore"
)

feature_df = feature_df.select_dtypes(
    include=[np.number]
)

# Replace infinite values
feature_df = feature_df.replace(
    [np.inf, -np.inf],
    np.nan
)

# Fill missing values using column medians
feature_df = feature_df.fillna(
    feature_df.median()
)

# Remove constant features
feature_df = feature_df.loc[
    :, feature_df.nunique() > 1
]

print("Numerical features:", feature_df.shape[1])


# ==========================================
# 4. LOG TRANSFORMATION
# ==========================================

print("\nApplying log transformation...")

# Counts and signal-intensity features are highly skewed.
# log1p preserves zero values.

feature_df = np.log1p(
    feature_df.clip(lower=0)
)


# ==========================================
# 5. FEATURE SCALING
# ==========================================

print("Scaling features...")

scaler = StandardScaler()

X_scaled = scaler.fit_transform(feature_df)


# ==========================================
# 6. PCA
# ==========================================

print("\nRunning PCA...")

pca = PCA(n_components=0.95, random_state=42)

X_pca = pca.fit_transform(X_scaled)

print("Original features:", X_scaled.shape[1])
print("PCA components:", X_pca.shape[1])

print(
    "Explained variance:",
    round(np.sum(pca.explained_variance_ratio_) * 100, 2),
    "%"
)


# ==========================================
# 7. K-MEANS CLUSTERING
# ==========================================

print("\nRunning K-Means clustering...")

best_k = None
best_score = -1
best_model = None

cluster_results = []

max_k = min(6, len(df) - 1)

for k in range(2, max_k + 1):

    model = KMeans(
        n_clusters=k,
        random_state=42,
        n_init=20
    )

    labels = model.fit_predict(X_pca)

    score = silhouette_score(
        X_pca,
        labels
    )

    cluster_results.append({
        "clusters": k,
        "silhouette_score": score
    })

    print(
        f"K={k} | Silhouette Score={score:.4f}"
    )

    if score > best_score:

        best_score = score
        best_k = k
        best_model = model


print("\nBest number of clusters:", best_k)
print("Best silhouette score:", round(best_score, 4))

cluster_labels = best_model.labels_


# ==========================================
# 8. ISOLATION FOREST
# ==========================================

print("\nRunning Isolation Forest...")

isolation_model = IsolationForest(
    contamination="auto",
    random_state=42,
    n_estimators=200
)

anomaly_predictions = isolation_model.fit_predict(X_pca)

# 1 = Normal, -1 = Anomaly
anomaly_status = np.where(
    anomaly_predictions == -1,
    "Anomaly",
    "Normal"
)


# ==========================================
# 9. CREATE RESULTS DATASET
# ==========================================

results = df.copy()

results["cluster"] = cluster_labels

results["anomaly_status"] = anomaly_status

results["anomaly_score"] = (
    isolation_model.decision_function(X_pca)
)

results_file = os.path.join(
    OUTPUT_DIR,
    "nasa_ml_results.csv"
)

results.to_csv(
    results_file,
    index=False
)


# ==========================================
# 10. PCA VISUALIZATION
# ==========================================

print("\nGenerating visualizations...")

if X_pca.shape[1] >= 2:

    plt.figure(figsize=(10, 7))

    scatter = plt.scatter(
        X_pca[:, 0],
        X_pca[:, 1],
        c=cluster_labels,
        cmap="viridis",
        s=90
    )

    plt.xlabel("Principal Component 1")
    plt.ylabel("Principal Component 2")

    plt.title("NASA SAM Experiment Clustering")

    plt.colorbar(
        scatter,
        label="Cluster"
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(OUTPUT_DIR, "cluster_visualization.png"),
        dpi=300
    )

    plt.close()


# ==========================================
# 11. ANOMALY VISUALIZATION
# ==========================================

plt.figure(figsize=(10, 7))

normal_mask = anomaly_status == "Normal"
anomaly_mask = anomaly_status == "Anomaly"

plt.scatter(
    X_pca[normal_mask, 0],
    X_pca[normal_mask, 1],
    label="Normal",
    s=65
)

plt.scatter(
    X_pca[anomaly_mask, 0],
    X_pca[anomaly_mask, 1],
    label="Anomaly",
    s=90,
    marker="x"
)

plt.xlabel("Principal Component 1")
plt.ylabel("Principal Component 2")

plt.title("NASA SAM Anomaly Detection")

plt.legend()
plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT_DIR, "anomaly_visualization.png"),
    dpi=300
)

plt.close()


# ==========================================
# 12. CLUSTER SUMMARY
# ==========================================

cluster_summary = results.groupby("cluster").agg(
    experiments=("experiment_id", "count"),
    mean_signal=("mean_counts", "mean"),
    mean_peak_amu=("peak_amu", "mean"),
    mean_zero_percentage=("zero_count_percentage", "mean")
).reset_index()

cluster_summary.to_csv(
    os.path.join(OUTPUT_DIR, "cluster_summary.csv"),
    index=False
)


# ==========================================
# 13. SAVE MODELS
# ==========================================

print("\nSaving trained models...")

joblib.dump(
    scaler,
    os.path.join(MODEL_DIR, "nasa_scaler.joblib")
)

joblib.dump(
    pca,
    os.path.join(MODEL_DIR, "nasa_pca.joblib")
)

joblib.dump(
    best_model,
    os.path.join(MODEL_DIR, "nasa_kmeans.joblib")
)

joblib.dump(
    isolation_model,
    os.path.join(MODEL_DIR, "nasa_isolation_forest.joblib")
)


# ==========================================
# 14. SAVE REPORT
# ==========================================

anomaly_count = np.sum(
    anomaly_status == "Anomaly"
)

report = f"""
NASA SAM MACHINE LEARNING REPORT
=================================

Total experiments: {len(df)}

Original numerical features: {feature_df.shape[1]}

PCA components: {X_pca.shape[1]}

PCA explained variance: {np.sum(pca.explained_variance_ratio_) * 100:.2f}%

Best number of clusters: {best_k}

Best silhouette score: {best_score:.4f}

Normal experiments: {len(df) - anomaly_count}

Anomalous experiments: {anomaly_count}

IMPORTANT:
Anomaly detection identifies unusual feature patterns.
Clusters represent statistical similarities.
Neither result establishes mineral identity,
biological activity, or planetary habitability.
"""

report_file = os.path.join(
    REPORT_DIR,
    "nasa_ml_report.txt"
)

with open(report_file, "w", encoding="utf-8") as f:
    f.write(report)


# ==========================================
# 15. FINAL OUTPUT
# ==========================================

print("\n========================================")
print("NASA SAM MACHINE LEARNING COMPLETE")
print("========================================")

print("Experiments:", len(df))
print("PCA components:", X_pca.shape[1])
print("Best clusters:", best_k)
print("Silhouette score:", round(best_score, 4))
print("Anomalies:", anomaly_count)

print("\nGenerated files:")

print("1.", results_file)

print("2.", os.path.join(OUTPUT_DIR, "cluster_visualization.png"))

print("3.", os.path.join(OUTPUT_DIR, "anomaly_visualization.png"))

print("4.", os.path.join(OUTPUT_DIR, "cluster_summary.csv"))

print("5.", report_file)

print("\nTrained models saved in:", MODEL_DIR)