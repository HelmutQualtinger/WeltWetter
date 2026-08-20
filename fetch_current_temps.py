"""Aktuelle Temperaturen aller Hauptstädte abrufen (Open-Meteo Forecast API).

Liest hauptstaedte_der_welt.csv (Land, Hauptstadt, Breitengrad, Laengengrad)
und schreibt temperaturen_hauptstaedte.csv (Land, Stadt, Temperatur_C).
"""

import csv
import json
import subprocess
import sys

INPUT_PATH = "hauptstaedte_der_welt.csv"
OUTPUT_PATH = "temperaturen_hauptstaedte.csv"
BATCH = 80

with open(INPUT_PATH, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

results = []

for i in range(0, len(rows), BATCH):
    batch = rows[i:i + BATCH]
    lats = ",".join(b["Breitengrad"] for b in batch)
    lons = ",".join(b["Laengengrad"] for b in batch)
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lats}&longitude={lons}&current=temperature_2m&timezone=auto"
    )
    cmd = ["curl", "-s", "-H",
           "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36", url]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        print(f"Batch {i} failed: {out.stderr}", file=sys.stderr)
        continue
    data = json.loads(out.stdout)
    if isinstance(data, dict):
        data = [data]
    for b, d in zip(batch, data):
        try:
            temp = d["current"]["temperature_2m"]
        except (KeyError, TypeError):
            temp = None
        results.append((b["Land"], b["Hauptstadt"], temp))
    print(f"Batch {i}-{i + len(batch)} done ({len(data)} results)", file=sys.stderr)

with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Land", "Stadt", "Temperatur_C"])
    for land, stadt, temp in results:
        w.writerow([land, stadt, temp if temp is not None else ""])

missing = [r for r in results if r[2] is None]
print(f"Total: {len(results)}, missing: {len(missing)}", file=sys.stderr)
