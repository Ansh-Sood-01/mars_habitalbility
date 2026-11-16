
import os
import re
import csv
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PDS_DIR = os.path.join(
    ROOT, "data", "raw", "nasa_pds"
)

OUTPUT_DIR = os.path.join(ROOT, "reports")

os.makedirs(OUTPUT_DIR, exist_ok=True)

results = []

print("=" * 65)
print("NASA PDS DATASET INSPECTION")
print("=" * 65)

label_files = []

for root, dirs, files in os.walk(PDS_DIR):
    for file in files:
        if file.lower().endswith(".lbl"):
            label_files.append(os.path.join(root, file))

print(f"\nTotal label files found: {len(label_files)}")

for i, label_path in enumerate(label_files, 1):

    try:
        with open(label_path, "r", errors="ignore") as f:
            content = f.read()

        def extract(pattern):
            match = re.search(
                pattern,
                content,
                re.IGNORECASE | re.MULTILINE
            )
            return match.group(1).strip().strip('"') if match else ""

        product_id = extract(r"PRODUCT_ID\s*=\s*(.+)")
        product_type = extract(r"PRODUCT_TYPE\s*=\s*(.+)")
        instrument = extract(r"INSTRUMENT_ID\s*=\s*(.+)")
        instrument_type = extract(r"INSTRUMENT_TYPE\s*=\s*(.+)")
        data_set = extract(r"DATA_SET_ID\s*=\s*(.+)")
        record_bytes = extract(r"RECORD_BYTES\s*=\s*(.+)")
        file_records = extract(r"FILE_RECORDS\s*=\s*(.+)")

        dat_match = re.search(
            r"\^\w+\s*=\s*\(\s*\"?([^\",)]+\.DAT)",
            content,
            re.IGNORECASE
        )

        dat_name = dat_match.group(1) if dat_match else ""

        dat_path = os.path.join(
            os.path.dirname(label_path),
            dat_name
        ) if dat_name else ""

        dat_size = (
            os.path.getsize(dat_path)
            if dat_path and os.path.isfile(dat_path)
            else 0
        )

        results.append({
            "label_file": os.path.basename(label_path),
            "product_id": product_id,
            "product_type": product_type,
            "instrument": instrument,
            "instrument_type": instrument_type,
            "data_set": data_set,
            "record_bytes": record_bytes,
            "file_records": file_records,
            "dat_file": dat_name,
            "dat_size_bytes": dat_size,
            "dat_exists": bool(dat_path and os.path.isfile(dat_path))
        })

    except Exception as e:
        print(f"Error reading {label_path}: {e}")

    if i % 500 == 0 or i == len(label_files):
        print(f"Inspected {i}/{len(label_files)} label files")

output_path = os.path.join(
    OUTPUT_DIR,
    "nasa_pds_inventory.csv"
)

if results:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=results[0].keys()
        )
        writer.writeheader()
        writer.writerows(results)

print("\n" + "=" * 65)
print("PRODUCT TYPE SUMMARY")
print("=" * 65)

for name, count in Counter(
    r["product_type"] for r in results
).most_common():
    print(f"{name or 'UNKNOWN'}: {count}")

print("\nDAT FILE SIZE SUMMARY")

for name, count in Counter(
    r["dat_size_bytes"] for r in results
).most_common(15):
    print(f"{name} bytes: {count} files")

print(f"\nInventory saved to: {output_path}")
print("\nInspection completed.")

