import os
import pandas as pd
import requests

ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

REPORT = os.path.join(
    ROOT, "reports", "spyr_qms_download_report.csv"
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

for row in failed.itertuples(index=False):

    print("\n" + "=" * 65)
    print("PRODUCT:", row.product)
    print("FOLDER:", row.experiment_folder)

    url = BASE_URL + row.experiment_folder + "/level1a/"

    try:
        response = session.get(url, timeout=60)

        print("Directory HTTP status:", response.status_code)

        if response.status_code != 200:
            print("Directory not accessible:", url)
            continue

        from html.parser import HTMLParser

        class LinkParser(HTMLParser):

            def __init__(self):
                super().__init__()
                self.links = []

            def handle_starttag(self, tag, attrs):
                if tag == "a":
                    for key, value in attrs:
                        if key == "href":
                            self.links.append(value)

        parser = LinkParser()
        parser.feed(response.text)

        matches = [
            link for link in parser.links
            if "qms_massxxx" in link.lower()
            or row.product[:13].lower() in link.lower()
        ]

        print("\nMatching files:")

        if matches:
            for link in matches:
                print(link)
        else:
            print("No matching files found.")

    except requests.RequestException as error:
        print("Error:", error)

print("\nCHECK COMPLETED")