import os
import re
import pandas as pd
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDS = os.path.join(ROOT, "data", "raw", "nasa_pds")
OUTPUT = os.path.join(ROOT, "reports", "product_family_samples.csv")

families = defaultdict(list)

for current_root, dirs, files in os.walk(PDS):
    for filename in files:

        if not filename.lower().endswith(".lbl"):
            continue

        path = os.path.join(current_root, filename)

        match = re.search(
            r"([A-Z]{3})\d{4}",
            filename.upper()
        )

        if match:
            family = match.group(1)
            families[family].append(path)

results = []

for family, paths in sorted(families.items()):

    print(f"\nInspecting {family}: {len(paths)} files")

    for path in paths[:3]:

        with open(path, "r", errors="ignore") as f:
            content = f.read()

        def extract(pattern):
            m = re.search(pattern, content, re.I)
            return m.group(1).strip() if m else ""

        fields = re.findall(
            r'NAME\s*=\s*"([^"]+)"',
            content,
            re.I
        )

        results.append({
            "Family": family,
            "Filename": os.path.basename(path),
            "Product_ID": extract(r'PRODUCT_ID\s*=\s*"([^"]+)"'),
            "Experiment_ID": extract(r'SAM_EXPERIMENT_ID\s*=\s*(\d+)'),
            "Columns": extract(r'COLUMNS\s*=\s*(\d+)'),
            "Rows": extract(r'ROWS\s*=\s*(\d+)'),
            "Row_Bytes": extract(r'ROW_BYTES\s*=\s*(\d+)'),
            "Data_Fields": "; ".join(sorted(set(fields)))
        })

df = pd.DataFrame(results)
df.to_csv(OUTPUT, index=False)

print("\nInspection completed.")
print("Representative products:", len(df))
print("Saved:", OUTPUT)

print("\nPRODUCT FAMILY SUMMARY")
print(df[["Family", "Filename", "Columns", "Rows", "Row_Bytes"]]
      .to_string(index=False))