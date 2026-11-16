import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

FILE = os.path.join(
    ROOT,
    "data",
    "raw",
    "nasa_sam_l1a",
    "all_spyr_qms",
    "eid25815",
    "sm25815f4725rdr1a_spyr_qms_massxxx_1.tab"
)

OUTPUT = os.path.join(
    ROOT,
    "outputs",
    "qms_analysis"
)

os.makedirs(OUTPUT, exist_ok=True)

# Read data
df = pd.read_csv(
    FILE,
    skiprows=1,
    header=None,
    names=[
        "TIME",
        "AMU",
        "COUNTS_PER_SECOND",
        "RF_COUNTS_PER_SECOND"
    ],
    skipinitialspace=True
)

# Convert to numeric
for col in df.columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna()

# Sort by time
df = df.sort_values("TIME")

# Aggregate measurements by AMU
spectrum = (
    df.groupby("AMU")["COUNTS_PER_SECOND"]
    .mean()
    .reset_index()
)

# -------------------------------------------------
# 1. MASS SPECTRUM
# -------------------------------------------------

plt.figure(figsize=(14, 6))

plt.plot(
    spectrum["AMU"],
    spectrum["COUNTS_PER_SECOND"]
)

plt.xlabel("Mass-to-charge ratio (AMU)")
plt.ylabel("Mean counts per second")
plt.title("NASA SAM QMS Mass Spectrum")

plt.grid(True, alpha=0.3)
plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT, "mass_spectrum.png"),
    dpi=300
)

plt.close()

# -------------------------------------------------
# 2. LOGARITHMIC MASS SPECTRUM
# -------------------------------------------------

plt.figure(figsize=(14, 6))

plt.plot(
    spectrum["AMU"],
    spectrum["COUNTS_PER_SECOND"]
)

plt.yscale("log")

plt.xlabel("Mass-to-charge ratio (AMU)")
plt.ylabel("Mean counts per second (log scale)")
plt.title("NASA SAM QMS Logarithmic Mass Spectrum")

plt.grid(True, alpha=0.3)
plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT, "mass_spectrum_log.png"),
    dpi=300
)

plt.close()

# -------------------------------------------------
# 3. SIGNAL OVER TIME
# -------------------------------------------------

plt.figure(figsize=(14, 6))

plt.plot(
    df["TIME"],
    df["COUNTS_PER_SECOND"]
)

plt.xlabel("Spacecraft clock time (seconds)")
plt.ylabel("Counts per second")
plt.title("NASA SAM QMS Signal Over Time")

plt.grid(True, alpha=0.3)
plt.tight_layout()

plt.savefig(
    os.path.join(OUTPUT, "signal_over_time.png"),
    dpi=300
)

plt.close()

# -------------------------------------------------
# SAVE AGGREGATED SPECTRUM
# -------------------------------------------------

spectrum.to_csv(
    os.path.join(OUTPUT, "mass_spectrum.csv"),
    index=False
)

print("Visualization completed.")

print("\nGenerated files:")

for filename in os.listdir(OUTPUT):
    print(filename)

print("\nTop 15 AMU channels by mean signal:")

print(
    spectrum.sort_values(
        "COUNTS_PER_SECOND",
        ascending=False
    ).head(15).to_string(index=False)
)