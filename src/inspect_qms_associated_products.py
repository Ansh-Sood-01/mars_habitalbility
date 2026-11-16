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

SEARCH_DIRS = [
    os.path.join(BASE, "all_spyr_qms"),
    os.path.join(BASE, "sample_qms")
]

products = {
    "massxxx": [],
    "bandxxx": [],
    "miscdac": [],
    "fcupxxx": []
}

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

            for product_type in products:

                if f"spyr_qms_{product_type}_" in filename:

                    if filename not in products[product_type]:

                        products[product_type].append(
                            filename
                        )

print("=" * 65)
print("ASSOCIATED SPYR QMS PRODUCT INVENTORY")
print("=" * 65)

for product_type, files in products.items():

    print(f"\n{product_type}: {len(files)} XML files")

    for filename in files[:5]:
        print(" ", filename)

print("\nInventory completed.")