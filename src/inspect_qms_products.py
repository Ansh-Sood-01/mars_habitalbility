import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT = os.path.join(
    ROOT, "data", "raw", "nasa_sam_l1a",
    "level1a_inventory.csv"
)

OUTPUT = os.path.join(
    ROOT, "reports", "qms_product_summary.csv"
)

df = pd.read_csv(
    INPUT,
    header=None,
    names=["record_type", "product_identifier"]
)

df["product_identifier"] = df["product_identifier"].astype(str)

# Extract the product name from each identifier
df["product_type"] = (
    df["product_identifier"]
    .str.extract(r"rdr1a_(.*)::", expand=False)
)

qms = df[
    df["product_identifier"].str.contains(
        "_qms_", case=False, na=False
    )
].copy()

print("=" * 65)
print("NASA SAM QMS PRODUCT ANALYSIS")
print("=" * 65)

print("\nTotal QMS products:", len(qms))

print("\nQMS PRODUCT TYPE DISTRIBUTION")

print(
    qms["product_type"]
    .value_counts()
    .to_string()
)

print("\n" + "=" * 65)
print("REPRESENTATIVE QMS PRODUCTS")
print("=" * 65)

for product_type, group in qms.groupby("product_type"):

    print(f"\n{product_type}")
    print("Count:", len(group))

    for identifier in group["product_identifier"].head(5):
        print(identifier)

qms.to_csv(OUTPUT, index=False)

print("\nSaved:", OUTPUT)