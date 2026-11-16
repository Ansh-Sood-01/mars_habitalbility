import os
import glob
import pandas as pd
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(
    ROOT,
    "data",
    "raw",
    "nasa_sam_l1a",
    "all_spyr_qms"
)

OUTPUT_DIR = os.path.join(ROOT, "reports")
OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "mass_spectrum_consistency.csv"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

files = glob.glob(
    os.path.join(DATA_DIR, "**", "*massxxx*.tab"),
    recursive=True
)

results = []

for file in files:

    try:
        df = pd.read_csv(
            file,
            skipinitialspace=True
        )

        df.columns = df.columns.str.strip()

        df["AMU"] = pd.to_numeric(
            df["AMU"], errors="coerce"
        )

        df["TIME"] = pd.to_numeric(
            df["TIME"], errors="coerce"
        )

        df["COUNTS PER SECOND"] = pd.to_numeric(
            df["COUNTS PER SECOND"].astype(str).str.strip(),
            errors="coerce"
        )

        df = df.dropna(
            subset=["AMU", "TIME", "COUNTS PER SECOND"]
        )

        experiment = os.path.basename(
            os.path.dirname(file)
        )

        results.append({
            "experiment_folder": experiment,
            "filename": os.path.basename(file),
            "records": len(df),
            "unique_amu": df["AMU"].nunique(),
            "min_amu": df["AMU"].min(),
            "max_amu": df["AMU"].max(),
            "min_time": df["TIME"].min(),
            "max_time": df["TIME"].max(),
            "mean_counts": df["COUNTS PER SECOND"].mean(),
            "median_counts": df["COUNTS PER SECOND"].median(),
            "max_counts": df["COUNTS PER SECOND"].max(),
            "zero_count_percentage": (
                df["COUNTS PER SECOND"].eq(0).mean() * 100
            )
        })

    except Exception as error:
        print("ERROR:", file, error)

report = pd.DataFrame(results)

report.to_csv(OUTPUT_FILE, index=False)

print("\n========== MASS SPECTRUM CONSISTENCY ==========")

print("Files analyzed:", len(report))

if not report.empty:

    print("\nRECORD COUNT")
    print(report["records"].describe())

    print("\nUNIQUE AMU CHANNELS")
    print(report["unique_amu"].describe())

    print("\nAMU RANGE")
    print("Minimum:", report["min_amu"].min())
    print("Maximum:", report["max_amu"].max())

    print("\nZERO COUNT PERCENTAGE")
    print(report["zero_count_percentage"].describe())

    print("\nSAMPLE RESULTS")
    print(report.head(10).to_string(index=False))

print("\nREPORT SAVED:")
print(OUTPUT_FILE)
