import os
import pandas as pd
import numpy as np

ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

BASE = os.path.join(
    ROOT,
    "data",
    "raw",
    "nasa_sam_l1a"
)

OUTPUT = os.path.join(
    ROOT,
    "reports",
    "all_qms_analysis.csv"
)

SEARCH_DIRS = [
    os.path.join(BASE, "all_spyr_qms"),
    os.path.join(BASE, "sample_qms")
]

results = []
processed = set()

print("=" * 65)
print("NASA SAM - ALL SPYR QMS PRODUCT ANALYSIS")
print("=" * 65)

for search_dir in SEARCH_DIRS:

    if not os.path.isdir(search_dir):
        continue

    for folder in os.listdir(search_dir):

        folder_path = os.path.join(search_dir, folder)

        if not os.path.isdir(folder_path):
            continue

        for filename in os.listdir(folder_path):

            if not filename.endswith(".tab"):
                continue

            if "_spyr_qms_massxxx_" not in filename:
                continue

            filepath = os.path.join(folder_path, filename)

            if filename in processed:
                continue

            processed.add(filename)

            try:

                df = pd.read_csv(
                    filepath,
                    skiprows=1,
                    header=None,
                    names=[
                        "TIME",
                        "AMU",
                        "COUNTS_PER_SECOND",
                        "RF_COUNTS_PER_SECOND"
                    ],
                    skipinitialspace=True
                )

                for col in df.columns:
                    df[col] = pd.to_numeric(
                        df[col],
                        errors="coerce"
                    )

                df = df.dropna()

                if df.empty:
                    continue

                results.append({

                    "product": filename,

                    "experiment_folder": folder,

                    "records": len(df),

                    "unique_amu": df["AMU"].nunique(),

                    "amu_min": df["AMU"].min(),

                    "amu_max": df["AMU"].max(),

                    "signal_min": df[
                        "COUNTS_PER_SECOND"
                    ].min(),

                    "signal_max": df[
                        "COUNTS_PER_SECOND"
                    ].max(),

                    "signal_mean": df[
                        "COUNTS_PER_SECOND"
                    ].mean(),

                    "signal_median": df[
                        "COUNTS_PER_SECOND"
                    ].median(),

                    "signal_std": df[
                        "COUNTS_PER_SECOND"
                    ].std(),

                    "unique_timestamps": df[
                        "TIME"
                    ].nunique(),

                    "time_start": df["TIME"].min(),

                    "time_end": df["TIME"].max(),

                    "missing_values": df.isnull().sum().sum()

                })

                print(
                    f"Processed {len(results)}: {filename}"
                )

            except Exception as error:

                print("ERROR:", filename)
                print(error)

# Create report
report = pd.DataFrame(results)

os.makedirs(
    os.path.dirname(OUTPUT),
    exist_ok=True
)

report.to_csv(
    OUTPUT,
    index=False
)

print("\n" + "=" * 65)
print("ANALYSIS SUMMARY")
print("=" * 65)

print("Total products processed:", len(report))

if not report.empty:

    print(
        "Total measurement records:",
        report["records"].sum()
    )

    print(
        "Average records per product:",
        round(report["records"].mean(), 2)
    )

    print(
        "Overall AMU minimum:",
        report["amu_min"].min()
    )

    print(
        "Overall AMU maximum:",
        report["amu_max"].max()
    )

    print("\nTop 10 products by measurement records:")

    print(
        report.nlargest(
            10,
            "records"
        )[
            [
                "product",
                "records",
                "unique_amu",
                "amu_min",
                "amu_max"
            ]
        ].to_string(index=False)
    )

print("\nReport saved to:")
print(OUTPUT)

print("\nAnalysis completed.")