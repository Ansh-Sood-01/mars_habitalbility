import os
import time
import pandas as pd
import requests

ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

REPORT = os.path.join(
    ROOT,
    "reports",
    "qms_remote_inventory.csv"
)

DEST = os.path.join(
    ROOT,
    "data",
    "raw",
    "nasa_sam_l1a",
    "all_spyr_qms"
)

OUTPUT = os.path.join(
    ROOT,
    "reports",
    "associated_qms_download_report.csv"
)

ALLOWED = [
    "bandxxx",
    "miscdac",
    "fcupxxx"
]

df = pd.read_csv(REPORT)

df = df[
    df["product_family"].isin(ALLOWED)
].copy()

session = requests.Session()

results = []

print("=" * 65)
print("NASA SAM ASSOCIATED QMS DOWNLOAD")
print("=" * 65)

print("Products to process:", len(df))

for index, row in df.iterrows():

    folder = row["experiment_folder"]
    xml_filename = row["filename"]
    family = row["product_family"]

    tab_filename = os.path.splitext(
        xml_filename
    )[0] + ".tab"

    url_base = row["url"].rsplit("/", 1)[0] + "/"

    destination = os.path.join(
        DEST,
        folder
    )

    os.makedirs(destination, exist_ok=True)

    print(
        f"\n[{len(results) + 1}/{len(df)}] "
        f"{folder} - {family}"
    )

    for filename in [tab_filename, xml_filename]:

        url = url_base + filename

        output = os.path.join(
            destination,
            filename
        )

        status = "FAILED"
        size = 0
        error_message = ""

        if os.path.exists(output) and os.path.getsize(output) > 0:

            status = "ALREADY_EXISTS"
            size = os.path.getsize(output)

            print("Already exists:", filename)

        else:

            try:

                response = session.get(
                    url,
                    timeout=120
                )

                response.raise_for_status()

                content = response.content

                if not content:
                    raise ValueError("Empty response")

                with open(output, "wb") as file:
                    file.write(content)

                status = "DOWNLOADED"
                size = len(content)

                print("Downloaded:", filename, size, "bytes")

            except Exception as error:

                error_message = str(error)

                print("FAILED:", filename)
                print(error_message)

                if os.path.exists(output):
                    os.remove(output)

            time.sleep(0.2)

        results.append({

            "experiment_folder": folder,
            "product_family": family,
            "filename": filename,
            "status": status,
            "size_bytes": size,
            "error": error_message

        })


report = pd.DataFrame(results)

report.to_csv(
    OUTPUT,
    index=False
)

print("\n" + "=" * 65)
print("DOWNLOAD SUMMARY")
print("=" * 65)

print("\nFile status:")
print(report["status"].value_counts().to_string())

print("\nProduct family summary:")

print(
    report.groupby(
        ["product_family", "status"]
    ).size().to_string()
)

print("\nTotal files processed:", len(report))

print("\nReport saved:")
print(OUTPUT)

print("\nDownload process completed.")