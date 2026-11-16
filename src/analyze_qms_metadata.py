import os
import pandas as pd
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

BASE = os.path.join(
    ROOT,
    "data",
    "raw",
    "nasa_sam_l1a"
)

SEARCH_DIRS = [
    os.path.join(BASE, "all_spyr_qms"),
    os.path.join(BASE, "sample_qms")
]

OUTPUT = os.path.join(
    ROOT,
    "reports",
    "all_qms_metadata.csv"
)

def get_value(root, tag_name):

    for element in root.iter():

        tag = element.tag.split("}")[-1]

        if tag == tag_name:

            if element.text and element.text.strip():
                return element.text.strip()

    return None


results = []
processed = set()

print("=" * 65)
print("NASA SAM QMS XML METADATA ANALYSIS")
print("=" * 65)

for search_dir in SEARCH_DIRS:

    if not os.path.isdir(search_dir):
        continue

    for folder in os.listdir(search_dir):

        folder_path = os.path.join(search_dir, folder)

        if not os.path.isdir(folder_path):
            continue

        for filename in os.listdir(folder_path):

            if not filename.endswith(".xml"):
                continue

            if "_spyr_qms_massxxx_" not in filename:
                continue

            if filename in processed:
                continue

            processed.add(filename)

            filepath = os.path.join(
                folder_path,
                filename
            )

            try:

                tree = ET.parse(filepath)
                root = tree.getroot()

                record = {

                    "product": filename.replace(
                        ".xml", ".tab"
                    ),

                    "experiment_folder": folder,

                    "title": get_value(root, "title"),

                    "purpose": get_value(root, "purpose"),

                    "processing_level": get_value(
                        root, "processing_level"
                    ),

                    "domain": get_value(root, "domain"),

                    "discipline_name": get_value(
                        root, "discipline_name"
                    ),

                    "experiment_id": get_value(
                        root, "sam_experiment_id"
                    ),

                    "experiment_description": get_value(
                        root, "sam_experiment_description"
                    ),

                    "sol_number": get_value(
                        root, "sol_number"
                    ),

                    "start_date_time": get_value(
                        root, "start_date_time"
                    ),

                    "stop_date_time": get_value(
                        root, "stop_date_time"
                    ),

                    "product_type": get_value(
                        root, "product_type"
                    ),

                    "records_declared": get_value(
                        root, "records"
                    )
                }

                results.append(record)

                print(
                    f"Processed {len(results)}: {filename}"
                )

            except Exception as error:

                print("ERROR:", filename)
                print(error)


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
print("METADATA SUMMARY")
print("=" * 65)

print("Total XML products:", len(report))

for column in [
    "purpose",
    "processing_level",
    "domain",
    "experiment_description"
]:

    print(f"\n{column.upper()} DISTRIBUTION")

    print(
        report[column]
        .value_counts(dropna=False)
        .to_string()
    )

print("\nMetadata report saved:")
print(OUTPUT)

print("\nMetadata analysis completed.")