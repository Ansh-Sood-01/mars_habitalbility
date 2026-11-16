import os
import pandas as pd
import requests
import time

ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

REPORT = os.path.join(
    ROOT, "reports", "spyr_qms_download_report.csv"
)

DEST = os.path.join(
    ROOT, "data", "raw", "nasa_sam_l1a", "all_spyr_qms"
)

BASE_URL = (
    "https://pds-geosciences.wustl.edu/"
    "msl/msl-m-sam-2-rdr-l0-v1/"
    "mslsam_1xxx/data/"
)

df = pd.read_csv(REPORT)

failed = df[
    (df["tab_status"] == "FAILED") |
    (df["xml_status"] == "FAILED")
]

session = requests.Session()

recovered = 0

for row in failed.itertuples(index=False):

    product = row.product
    folder = row.experiment_folder

    print("\nRecovering:", product)

    url_base = BASE_URL + folder + "/level1a/"

    destination = os.path.join(DEST, folder)
    os.makedirs(destination, exist_ok=True)

    for ext in ["tab", "xml"]:

        filename = product + "_1." + ext
        url = url_base + filename
        output = os.path.join(destination, filename)

        try:
            response = session.get(url, timeout=120)
            response.raise_for_status()

            with open(output, "wb") as f:
                f.write(response.content)

            print("Downloaded:", filename)
            print("Size:", len(response.content))

            if ext == "tab":
                recovered += 1

        except requests.RequestException as error:
            print("Failed:", filename)
            print(error)

        time.sleep(0.3)

print("\nRecovery completed.")
print("TAB files recovered:", recovered)