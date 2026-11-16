import zipfile
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

zip_path = ROOT / "data" / "raw" / "competition" / "val_features.zip"
output_path = ROOT / "outputs" / "test_spectrum.csv"

with zipfile.ZipFile(zip_path, "r") as z:
    csv_files = [
        name for name in z.namelist()
        if name.lower().endswith(".csv")
    ]

    if not csv_files:
        raise FileNotFoundError("No CSV files found in validation ZIP.")

    selected_file = csv_files[0]

    with z.open(selected_file) as f:
        df = pd.read_csv(f)

required = ["time", "temp", "m/z", "abundance"]

missing = [col for col in required if col not in df.columns]

if missing:
    raise ValueError(f"Missing required columns: {missing}")

output_path.parent.mkdir(parents=True, exist_ok=True)
df[required].to_csv(output_path, index=False)

print("Test spectrum created successfully!")
print("Source:", selected_file)
print("Output:", output_path)
print("Rows:", len(df))
print("Columns:", list(df[required].columns))