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
    "nasa_sam_l1a",
    "all_spyr_qms",
    "eid25815"
)

TAB_FILE = os.path.join(
    BASE,
    "sm25815f4725rdr1a_spyr_qms_massxxx_1.tab"
)

XML_FILE = os.path.join(
    BASE,
    "sm25815f4725rdr1a_spyr_qms_massxxx_1.xml"
)

print("=" * 65)
print("QMS MASS PRODUCT INSPECTION")
print("=" * 65)

# 1. Inspect TAB file
print("\n1. TAB FILE PREVIEW")
print("-" * 65)

with open(TAB_FILE, "r", encoding="utf-8", errors="replace") as f:
    for i in range(15):
        line = f.readline()
        if not line:
            break
        print(line.rstrip())

# 2. Inspect XML metadata
print("\n2. XML METADATA")
print("-" * 65)

tree = ET.parse(XML_FILE)
root = tree.getroot()

for element in root.iter():

    tag = element.tag.split("}")[-1]

    if element.text and element.text.strip():

        text = element.text.strip()

        if len(text) < 250:
            print(f"{tag}: {text}")

print("\nInspection completed.")