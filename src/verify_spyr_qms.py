import os
import pandas as pd

ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

BASE = os.path.join(
    ROOT,
    "data",
    "raw",
    "nasa_sam_l1a"
)

REPORT = os.path.join(
    ROOT,
    "reports",
    "spyr_qms_download_report.csv"
)

report = pd.read_csv(REPORT)

print("=" * 60)
print("SPYR QMS DATASET VERIFICATION")
print("=" * 60)

tab_count = 0
xml_count = 0
missing_tab = []
missing_xml = []

for row in report.itertuples(index=False):

    product = row.product
    folder = row.experiment_folder

    # Search in the original and recovery directories
    search_dirs = [
        os.path.join(BASE, "all_spyr_qms", folder),
        os.path.join(BASE, "sample_qms", folder),
    ]

    found_tab = False
    found_xml = False

    for directory in search_dirs:

        if not os.path.isdir(directory):
            continue

        for filename in os.listdir(directory):

            if filename.startswith(product):

                if filename.endswith(".tab"):
                    found_tab = True

                elif filename.endswith(".xml"):
                    found_xml = True

    if found_tab:
        tab_count += 1
    else:
        missing_tab.append(product)

    if found_xml:
        xml_count += 1
    else:
        missing_xml.append(product)

print("\nExpected products:", len(report))
print("TAB files found:", tab_count)
print("XML files found:", xml_count)

print("\nMissing TAB files:", len(missing_tab))
print("Missing XML files:", len(missing_xml))

if missing_tab:
    print("\nMissing TAB products:")
    for item in missing_tab:
        print(item)

if missing_xml:
    print("\nMissing XML products:")
    for item in missing_xml:
        print(item)

print("\nVerification completed.")