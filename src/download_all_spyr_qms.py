import os
import time
import requests
import pandas as pd

# ==========================================
# PROJECT PATHS
# ==========================================

ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

INVENTORY = os.path.join(
    ROOT,
    "data",
    "raw",
    "nasa_sam_l1a",
    "level1a_inventory.csv"
)

DEST = os.path.join(
    ROOT,
    "data",
    "raw",
    "nasa_sam_l1a",
    "all_spyr_qms"
)

REPORT = os.path.join(
    ROOT,
    "reports",
    "spyr_qms_download_report.csv"
)

BASE_URL = (
    "https://pds-geosciences.wustl.edu/"
    "msl/msl-m-sam-2-rdr-l0-v1/"
    "mslsam_1xxx/data/"
)

os.makedirs(DEST, exist_ok=True)
os.makedirs(os.path.dirname(REPORT), exist_ok=True)

# ==========================================
# LOAD NASA INVENTORY
# ==========================================

df = pd.read_csv(
    INVENTORY,
    header=None,
    names=["record_type", "product_identifier"]
)

df["product_identifier"] = (
    df["product_identifier"].astype(str)
)

# Select SPYR QMS mass products only
products = df[
    df["product_identifier"].str.contains(
        r"_spyr_qms_massxxx::",
        case=False,
        na=False,
        regex=True
    )
].copy()

products = products.drop_duplicates(
    subset=["product_identifier"]
)

print("=" * 65)
print("NASA SPYR QMS MASS PRODUCT DOWNLOADER")
print("=" * 65)

print("Products identified:", len(products))

session = requests.Session()

results = []

# ==========================================
# DOWNLOAD PRODUCTS
# ==========================================

for index, row in enumerate(
    products.itertuples(index=False),
    start=1
):

    identifier = row.product_identifier

    # Remove version identifier
    product_name = identifier.split("::")[0].split(":")[-1]

    # Extract experiment folder
    experiment_id = product_name[:7]

    if not experiment_id.startswith("sm"):
        print("Skipping invalid identifier:", identifier)
        continue

    experiment_folder = "eid" + experiment_id[2:]

    folder_url = (
        BASE_URL
        + experiment_folder
        + "/level1a/"
    )

    destination_folder = os.path.join(
        DEST,
        experiment_folder
    )

    os.makedirs(destination_folder, exist_ok=True)

    print(f"\n[{index}/{len(products)}] {product_name}")

    result = {
        "product": product_name,
        "experiment_folder": experiment_folder,
        "tab_status": "NOT_DOWNLOADED",
        "xml_status": "NOT_DOWNLOADED"
    }

    for extension in ["tab", "xml"]:

        filename = product_name + "_2." + extension

        url = folder_url + filename

        output = os.path.join(
            destination_folder,
            filename
        )

        if os.path.exists(output) and os.path.getsize(output) > 0:
            print(f"Already exists: {filename}")
            result[extension + "_status"] = "EXISTS"
            continue

        try:

            response = session.get(
                url,
                timeout=120
            )

            response.raise_for_status()

            with open(output, "wb") as f:
                f.write(response.content)

            print(
                f"Downloaded {filename}: "
                f"{len(response.content):,} bytes"
            )

            result[extension + "_status"] = "DOWNLOADED"

        except requests.RequestException as error:

            print("Download failed:", filename)
            print(error)

            result[extension + "_status"] = "FAILED"

        time.sleep(0.3)

    results.append(result)

# ==========================================
# SAVE DOWNLOAD REPORT
# ==========================================

report_df = pd.DataFrame(results)

report_df.to_csv(
    REPORT,
    index=False
)

print("\n" + "=" * 65)
print("DOWNLOAD SUMMARY")
print("=" * 65)

print("Products processed:", len(report_df))

print("\nTAB status:")
print(report_df["tab_status"].value_counts().to_string())

print("\nXML status:")
print(report_df["xml_status"].value_counts().to_string())

print("\nReport saved:", REPORT)

print("\nDOWNLOAD PROCESS COMPLETED")