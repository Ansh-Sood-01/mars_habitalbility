import os
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(
    ROOT, "data", "raw", "nasa_sam_l1a", "sample_qms"
)

TAB_FILE = os.path.join(
    DATA_DIR, "sm25032f0085rdr1a_spyr_qms_massxxx_2.tab"
)

XML_FILE = os.path.join(
    DATA_DIR, "sm25032f0085rdr1a_spyr_qms_massxxx_2.xml"
)

# ==========================================
# 1. Inspect actual measurement data
# ==========================================

print("\n" + "=" * 65)
print("NASA SAM QMS MEASUREMENT DATA")
print("=" * 65)

print("\nTAB FILE SIZE:", os.path.getsize(TAB_FILE), "bytes")

with open(TAB_FILE, "r", encoding="utf-8", errors="replace") as f:
    for i in range(15):
        line = f.readline()
        if not line:
            break
        print(f"Line {i + 1}: {line.rstrip()!r}")

# ==========================================
# 2. Inspect XML metadata
# ==========================================

print("\n" + "=" * 65)
print("NASA PDS XML METADATA")
print("=" * 65)

tree = ET.parse(XML_FILE)
root = tree.getroot()

def local_name(tag):
    return tag.split("}")[-1]

important_tags = {
    "name",
    "local_identifier",
    "field_number",
    "data_type",
    "unit",
    "description",
    "minimum",
    "maximum",
    "scaling_factor",
    "value_offset",
    "records",
    "record_length",
    "file_name",
    "delimiter",
}

for element in root.iter():
    tag = local_name(element.tag)
    value = (element.text or "").strip()

    if tag in important_tags and value:
        print(f"{tag}: {value}")

print("\nINSPECTION COMPLETED")
