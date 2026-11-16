import os
import re
import time
import requests
import pandas as pd

ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

REPORT = os.path.join(
    ROOT,
    "reports",
    "all_qms_analysis.csv"
)

OUTPUT = os.path.join(
    ROOT,
    "reports",
    "qms_remote_inventory.csv"
)

BASE_URL = (
    "https://pds-geosciences.wustl.edu/"
    "msl/msl-m-sam-2-rdr-l0-v1/"
    "mslsam_1xxx/data/"
)

df = pd.read_csv(REPORT)

folders = sorted(
    df["experiment_folder"].dropna().unique()
)

session = requests.Session()

results = []

print("=" * 65)
print("NASA REMOTE QMS PRODUCT INVENTORY")
print("=" * 65)

for i, folder in enumerate(folders, start=1):

    url = BASE_URL + folder + "/level1a/"

    print(f"\nChecking {i}/{len(folders)}: {folder}")

    try:

        response = session.get(
            url,
            timeout=60
        )

        response.raise_for_status()

        html = response.text

        for family in [
            "massxxx",
            "bandxxx",
            "miscdac",
            "fcupxxx"
        ]:

            pattern = (
                r'href=["\']([^"\']*'
                + re.escape(f"_spyr_qms_{family}_")
                + r'[^"\']*\.xml)["\']'
            )

            matches = re.findall(
                pattern,
                html,
                flags=re.IGNORECASE
            )

            for filename in matches:

                filename = filename.split("/")[-1]

                results.append({

                    "experiment_folder": folder,

                    "product_family": family,

                    "filename": filename,

                    "url": url + filename,

                    "http_status": response.status_code

                })

        print("Directory checked successfully.")

    except requests.RequestException as error:

        print("ERROR:", error)

        results.append({

            "experiment_folder": folder,

            "product_family": "UNKNOWN",

            "filename": "",

            "url": url,

            "http_status": "FAILED"

        })

    time.sleep(0.3)


report = pd.DataFrame(results)

report.to_csv(
    OUTPUT,
    index=False
)

print("\n" + "=" * 65)
print("REMOTE INVENTORY SUMMARY")
print("=" * 65)

if not report.empty:

    print(
        report.groupby(
            "product_family"
        ).size().to_string()
    )

print("\nTotal matching XML products:", len(report))

print("\nSaved report:")
print(OUTPUT)

print("\nInventory completed.")