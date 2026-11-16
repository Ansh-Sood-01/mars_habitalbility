import os
import glob
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(
    ROOT, "data", "raw", "nasa_sam_l1a", "all_spyr_qms"
)

OUTPUT_DIR = os.path.join(ROOT, "data", "processed")

os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR, "nasa_sam_experiment_features.csv"
)

files = glob.glob(
    os.path.join(DATA_DIR, "**", "*massxxx*.tab"),
    recursive=True
)

features = []

# Mass bins: 0-50, 50-100, ... 500-550
BIN_EDGES = np.arange(0, 551, 50)

for index, file in enumerate(files, start=1):

    print(f"Processing {index}/{len(files)}: {os.path.basename(file)}")

    try:

        df = pd.read_csv(file, skipinitialspace=True)

        df.columns = df.columns.str.strip()

        # Numeric conversion
        for col in [
            "TIME",
            "AMU",
            "COUNTS PER SECOND",
            "RF COUNTS PER SECOND"
        ]:

            df[col] = pd.to_numeric(
                df[col].astype(str).str.strip(),
                errors="coerce"
            )

        df = df.dropna(
            subset=[
                "TIME",
                "AMU",
                "COUNTS PER SECOND",
                "RF COUNTS PER SECOND"
            ]
        )

        if df.empty:
            continue

        amu = df["AMU"].to_numpy()
        counts = df["COUNTS PER SECOND"].to_numpy()
        rf = df["RF COUNTS PER SECOND"].to_numpy()
        time = df["TIME"].to_numpy()

        experiment_id = os.path.basename(
            os.path.dirname(file)
        ).replace("eid", "")

        row = {
            "experiment_id": experiment_id,
            "filename": os.path.basename(file),

            "records": len(df),

            "unique_amu": df["AMU"].nunique(),

            "min_amu": np.min(amu),
            "max_amu": np.max(amu),

            "mean_counts": np.mean(counts),
            "median_counts": np.median(counts),
            "std_counts": np.std(counts),

            "max_counts": np.max(counts),
            "min_counts": np.min(counts),

            "zero_count_percentage": np.mean(counts == 0) * 100,

            "mean_rf_counts": np.mean(rf),
            "median_rf_counts": np.median(rf),

            "time_duration_seconds": np.max(time) - np.min(time),

            "mean_amu": np.mean(amu),
            "std_amu": np.std(amu),

            "peak_amu": amu[np.argmax(counts)],

            "total_counts": np.sum(counts),
        }

        # Mass-bin features
        for i in range(len(BIN_EDGES) - 1):

            low = BIN_EDGES[i]
            high = BIN_EDGES[i + 1]

            mask = (amu >= low) & (amu < high)

            row[f"mean_counts_mz_{low}_{high}"] = (
                np.mean(counts[mask]) if np.any(mask) else 0
            )

            row[f"max_counts_mz_{low}_{high}"] = (
                np.max(counts[mask]) if np.any(mask) else 0
            )

        features.append(row)

    except Exception as error:

        print("ERROR:", file, error)


result = pd.DataFrame(features)

result.to_csv(OUTPUT_FILE, index=False)

print("\n========== FEATURE ENGINEERING COMPLETE ==========")

print("Experiments processed:", len(result))
print("Feature columns:", len(result.columns))

print("\nDataset shape:", result.shape)

print("\nMissing values:", result.isna().sum().sum())

print("\nFirst five rows:")
print(result.head().to_string(index=False))

print("\nSaved to:")
print(OUTPUT_FILE)