import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

INPUT = os.path.join(
    ROOT, "data", "raw", "nasa_sam_l1a",
    "level1a_inventory.csv"
)

OUTPUT = os.path.join(
    ROOT, "reports", "l1a_product_analysis.csv"
)

# Read inventory without treating the first record as a header
df = pd.read_csv(
    INPUT,
    header=None,
    names=["record_type", "product_identifier"]
)

df["product_identifier"] = (
    df["product_identifier"].astype(str).str.strip()
)

print("=" * 65)
print("NASA SAM LEVEL 1A INVENTORY ANALYSIS")
print("=" * 65)

print("\nTotal records:", len(df))

print("\nRecord types:")
print(df["record_type"].value_counts().to_string())

print("\nFirst 15 products:")
print(df.head(15).to_string(index=False))

# Search for important instrument/product categories
categories = {
    "QMS": ["qms"],
    "EGA": ["ega"],
    "GC": ["gc"],
    "TLS": ["tls"],
    "TEMPERATURE": ["temp"],
    "HOUSEKEEPING": ["hk"],
    "MESSAGE": ["message"]
}

print("\n" + "=" * 65)
print("PRODUCT CATEGORY COUNTS")
print("=" * 65)

for category, keywords in categories.items():

    mask = df["product_identifier"].str.contains(
        "|".join(keywords),
        case=False,
        regex=True
    )

    matching = df[mask]

    print(f"\n{category}: {len(matching)} products")

    for product in matching["product_identifier"].head(5):
        print(" ", product)

df.to_csv(OUTPUT, index=False)

print("\nFull analysis saved to:", OUTPUT)