import os
import pandas as pd
import numpy as np

ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

FILE = os.path.join(
    ROOT,
    "data",
    "raw",
    "nasa_sam_l1a",
    "all_spyr_qms",
    "eid25815",
    "sm25815f4725rdr1a_spyr_qms_massxxx_1.tab"
)

print("=" * 65)
print("NASA SAM QMS NUMERICAL DATA ANALYSIS")
print("=" * 65)

# Read the PDS table
df = pd.read_csv(
    FILE,
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

# Convert columns to numeric
for col in df.columns:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

print("\n1. DATASET INFORMATION")
print("-" * 65)

print("Shape:", df.shape)
print("\nData types:")
print(df.dtypes)

print("\n2. FIRST FIVE RECORDS")
print("-" * 65)

print(df.head())

print("\n3. MISSING VALUES")
print("-" * 65)

print(df.isnull().sum())

print("\n4. STATISTICAL SUMMARY")
print("-" * 65)

print(df.describe())

print("\n5. MASS-TO-CHARGE INFORMATION")
print("-" * 65)

print("Unique AMU values:", df["AMU"].nunique())

print("\nAMU range:")
print("Minimum:", df["AMU"].min())
print("Maximum:", df["AMU"].max())

print("\nFirst 30 unique AMU values:")

print(
    sorted(df["AMU"].dropna().unique())[:30]
)

print("\n6. SIGNAL INFORMATION")
print("-" * 65)

print(
    "Maximum counts per second:",
    df["COUNTS_PER_SECOND"].max()
)

print(
    "Minimum counts per second:",
    df["COUNTS_PER_SECOND"].min()
)

print(
    "Mean counts per second:",
    df["COUNTS_PER_SECOND"].mean()
)

print("\n7. TIME INFORMATION")
print("-" * 65)

print("Start time:", df["TIME"].min())
print("End time:", df["TIME"].max())

print(
    "Unique timestamps:",
    df["TIME"].nunique()
)

print("\nAnalysis completed.")