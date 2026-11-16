import os
import csv
import xml.etree.ElementTree as ET
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(
    ROOT, "data", "raw", "nasa_sam_l1a", "all_spyr_qms"
)

OUTPUT_DIR = os.path.join(ROOT, "reports")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "qms_complete_metadata_audit.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def local_name(tag):
    return tag.split("}")[-1]


def get_value(root, tag_name):
    for element in root.iter():
        if local_name(element.tag) == tag_name:
            return (element.text or "").strip()
    return ""


rows = []

for current_dir, _, files in os.walk(DATA_DIR):

    for filename in files:

        if not filename.endswith(".xml"):
            continue

        family = next(
            (f for f in ["massxxx", "bandxxx", "miscdac", "fcupxxx"]
             if f in filename),
            "unknown"
        )

        path = os.path.join(current_dir, filename)

        try:
            root = ET.parse(path).getroot()

            rows.append({
                "filename": filename,
                "experiment_folder": os.path.basename(current_dir),
                "product_family": family,
                "experiment_id": get_value(root, "sam_experiment_id"),
                "sol_number": get_value(root, "sol_number"),
                "description": get_value(
                    root, "sam_experiment_description"
                ),
                "purpose": get_value(root, "purpose"),
                "processing_level": get_value(
                    root, "processing_level"
                ),
                "start_time": get_value(root, "start_date_time"),
                "stop_time": get_value(root, "stop_date_time"),
            })

        except Exception as error:
            print("XML ERROR:", filename, error)


fields = [
    "filename",
    "experiment_folder",
    "product_family",
    "experiment_id",
    "sol_number",
    "description",
    "purpose",
    "processing_level",
    "start_time",
    "stop_time",
]

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:

    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)


print("\n========== QMS METADATA AUDIT ==========")

print("Total XML products:", len(rows))

print("\nPRODUCT FAMILY COUNTS")

for family, count in Counter(
    row["product_family"] for row in rows
).items():
    print(family, ":", count)

print("\nUNIQUE EXPERIMENT IDs:",
      len(set(row["experiment_id"] for row in rows
              if row["experiment_id"])))

print("UNIQUE SOL NUMBERS:",
      len(set(row["sol_number"] for row in rows
              if row["sol_number"])))

print("\nPURPOSE DISTRIBUTION")

for name, count in Counter(
    row["purpose"] for row in rows
).items():
    print(name, ":", count)

print("\nPROCESSING LEVEL DISTRIBUTION")

for name, count in Counter(
    row["processing_level"] for row in rows
).items():
    print(name, ":", count)

print("\nREPORT SAVED:")
print(OUTPUT_FILE)
