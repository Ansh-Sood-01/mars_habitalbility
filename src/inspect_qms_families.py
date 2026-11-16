import os
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(
    ROOT,
    "data",
    "raw",
    "nasa_sam_l1a",
    "all_spyr_qms"
)

FAMILIES = ["massxxx", "bandxxx", "miscdac", "fcupxxx"]


def local_name(tag):
    return tag.split("}")[-1]


def get_child_text(element, name):
    for child in element.iter():
        if local_name(child.tag) == name:
            return (child.text or "").strip()

    return ""


def inspect_xml(path, family):

    print("\n" + "=" * 75)
    print("PRODUCT FAMILY:", family)
    print("XML FILE:", os.path.basename(path))
    print("=" * 75)

    try:
        tree = ET.parse(path)
        root = tree.getroot()

        important_tags = [
            "title",
            "product_type",
            "processing_level",
            "purpose",
            "domain",
            "discipline",
            "sam_experiment_id",
            "sol_number",
            "sam_experiment_description",
            "start_date_time",
            "stop_date_time",
        ]

        print("\nPRODUCT METADATA")

        for tag in important_tags:
            value = get_child_text(root, tag)

            if value:
                print(f"{tag}: {value}")

        print("\nTABLE INFORMATION")

        for element in root.iter():

            tag = local_name(element.tag)

            if tag in [
                "Table_Delimited",
                "Table_Binary",
                "Table_Character",
            ]:

                for child in element:
                    child_tag = local_name(child.tag)

                    if child_tag in [
                        "records",
                        "record_length",
                        "description",
                    ]:
                        print(
                            f"{child_tag}: "
                            f"{(child.text or '').strip()}"
                        )

        print("\nFIELD DEFINITIONS")

        for element in root.iter():

            tag = local_name(element.tag)

            if tag.startswith("Field_"):

                name = get_child_text(element, "name")
                unit = get_child_text(element, "unit")
                data_type = get_child_text(element, "data_type")
                description = get_child_text(element, "description")

                if name:
                    print(f"\nField: {name}")
                    print(f"Type: {tag}")
                    print(f"Data type: {data_type or 'Not specified'}")
                    print(f"Unit: {unit or 'Not specified'}")
                    print(
                        f"Description: "
                        f"{description or 'Not specified'}"
                    )

    except Exception as error:
        print("ERROR:", error)


for family in FAMILIES:

    found = False

    for current_dir, _, files in os.walk(DATA_DIR):

        for filename in files:

            if filename.endswith(".xml") and family in filename:

                path = os.path.join(current_dir, filename)

                inspect_xml(path, family)

                found = True
                break

        if found:
            break

    if not found:
        print(f"\nNo XML found for {family}")