import os
import pandas as pd
import numpy as np

ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

INPUT = os.path.join(
    ROOT,
    "data",
    "raw",
    "nasa_sam_l1a",
    "sample_qms",
    "sm25032f0085rdr1a_spyr_qms_massxxx_2.tab"
)

OUTPUT = os.path.join(
    ROOT,
    "data",
    "processed",
    "qms_massxxx_clean.csv"
)

REPORT = os.path.join(
    ROOT,
    "reports",
    "qms_measurement_analysis.txt"
)

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
os.makedirs(os.path.dirname(REPORT), exist_ok=True)

# -----------------------------------------
# 1. Load NASA QMS data
# -----------------------------------------

df = pd.read_csv(
    INPUT,
    skipinitialspace=True
)

df.columns = df.columns.str.strip()

# Convert numeric columns
numeric_columns = [
    "TIME",
    "AMU",
    "COUNTS PER SECOND",
    "RF COUNTS PER SECOND"
]

for col in numeric_columns:

    df[col] = pd.to_numeric(
        df[col].astype(str).str.strip(),
        errors="coerce"
    )

# -----------------------------------------
# 2. Basic statistics
# -----------------------------------------

lines = []

def report(message=""):
    print(message)
    lines.append(str(message))

report("=" * 65)
report("NASA SAM QMS MEASUREMENT ANALYSIS")
report("=" * 65)

report(f"\nTotal records: {len(df)}")

report(f"Columns: {list(df.columns)}")

report("\nData types:")
report(df.dtypes.to_string())

report("\nMissing values:")
report(df.isna().sum().to_string())

# -----------------------------------------
# 3. AMU analysis
# -----------------------------------------

report("\n" + "=" * 65)
report("MASS-TO-CHARGE ANALYSIS")
report("=" * 65)

amu_values = sorted(
    df["AMU"].dropna().unique()
)

report(f"\nUnique AMU values: {len(amu_values)}")

report(f"Minimum AMU: {df['AMU'].min()}")
report(f"Maximum AMU: {df['AMU'].max()}")

report("\nAMU distribution:")
report(df["AMU"].value_counts().sort_index().to_string())

# -----------------------------------------
# 4. TIME analysis
# -----------------------------------------

report("\n" + "=" * 65)
report("TIME ANALYSIS")
report("=" * 65)

report(f"\nUnique timestamps: {df['TIME'].nunique()}")

report(f"Minimum TIME: {df['TIME'].min()}")
report(f"Maximum TIME: {df['TIME'].max()}")

# -----------------------------------------
# 5. Ion signal analysis
# -----------------------------------------

report("\n" + "=" * 65)
report("ION SIGNAL ANALYSIS")
report("=" * 65)

report("\nCounts per second statistics:")

report(
    df["COUNTS PER SECOND"]
    .describe()
    .to_string()
)

report("\nRF counts per second statistics:")

report(
    df["RF COUNTS PER SECOND"]
    .describe()
    .to_string()
)

# -----------------------------------------
# 6. Strongest signals
# -----------------------------------------

report("\n" + "=" * 65)
report("TOP 20 ION SIGNALS")
report("=" * 65)

top_signals = df.nlargest(
    20,
    "COUNTS PER SECOND"
)[
    [
        "TIME",
        "AMU",
        "COUNTS PER SECOND",
        "RF COUNTS PER SECOND"
    ]
]

report(top_signals.to_string(index=False))

# -----------------------------------------
# 7. Duplicate analysis
# -----------------------------------------

report("\n" + "=" * 65)
report("DUPLICATE ANALYSIS")
report("=" * 65)

report(
    f"\nDuplicate TIME-AMU pairs: "
    f"{df.duplicated(['TIME', 'AMU']).sum()}"
)

# -----------------------------------------
# 8. Save outputs
# -----------------------------------------

df.to_csv(OUTPUT, index=False)

with open(REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

report("\nCleaned data saved:")
report(OUTPUT)

report("\nAnalysis report saved:")
report(REPORT)

print("\nANALYSIS COMPLETED")