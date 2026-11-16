import os
import requests

ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

BASE_URL = (
    "https://pds-geosciences.wustl.edu/"
    "msl/msl-m-sam-2-rdr-l0-v1/"
    "mslsam_1xxx/data/eid25032/level1a/"
)

FILES = [
    "sm25032f0085rdr1a_spyr_qms_massxxx_2.tab",
    "sm25032f0085rdr1a_spyr_qms_massxxx_2.xml"
]

DEST = os.path.join(
    ROOT,
    "data",
    "raw",
    "nasa_sam_l1a",
    "sample_qms"
)

os.makedirs(DEST, exist_ok=True)

for filename in FILES:

    url = BASE_URL + filename
    output = os.path.join(DEST, filename)

    print(f"\nDownloading: {filename}")

    try:
        response = requests.get(url, timeout=120)

        print("HTTP status:", response.status_code)

        response.raise_for_status()

        with open(output, "wb") as f:
            f.write(response.content)

        print("Saved:", output)
        print("Size:", len(response.content), "bytes")

    except requests.RequestException as e:
        print("Download failed:", e)

print("\nDownload process completed.")