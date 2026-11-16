import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT = os.path.join(
    ROOT, "reports", "qms_complete_metadata_audit.csv"
)

OUTPUT = os.path.join(
    ROOT, "reports", "qms_experiment_coverage.csv"
)

df = pd.read_csv(INPUT)

# Create experiment-level product coverage
coverage = (
    df.pivot_table(
        index=["experiment_id", "sol_number"],
        columns="product_family",
        values="filename",
        aggfunc="count",
        fill_value=0
    )
    .reset_index()
)

# Ensure all expected families exist
for family in ["massxxx", "bandxxx", "miscdac", "fcupxxx"]:
    if family not in coverage.columns:
        coverage[family] = 0

# Determine availability
coverage["has_mass"] = coverage["massxxx"] > 0
coverage["has_band"] = coverage["bandxxx"] > 0
coverage["has_miscdac"] = coverage["miscdac"] > 0
coverage["has_fcup"] = coverage["fcupxxx"] > 0

coverage["has_all_main"] = (
    coverage["has_mass"]
    & coverage["has_band"]
    & coverage["has_miscdac"]
)

coverage.to_csv(OUTPUT, index=False)

print("\n========== EXPERIMENT COVERAGE ==========")

print("Total experiments:", len(coverage))

for family in ["massxxx", "bandxxx", "miscdac", "fcupxxx"]:
    print(
        f"{family}:",
        int((coverage[family] > 0).sum())
    )

print(
    "Experiments with all three main families:",
    int(coverage["has_all_main"].sum())
)

print("\nMISSING PRODUCT COMBINATIONS")

print(
    coverage[
        ["has_mass", "has_band", "has_miscdac"]
    ].value_counts()
)

print("\nSAMPLE EXPERIMENTS")

print(coverage.head(15).to_string(index=False))

print("\nREPORT SAVED:")
print(OUTPUT)