"""Historische Temperaturen (Durchschnitt/Min/Max) aller Hauptstädte für ein Jahr
abrufen (Open-Meteo Archive/ERA5-API, Daten verfügbar ab 1940).

Nutzung:
    python3 fetch_historical_temps.py [JAHR]
    (Standard: 1950)

Liest hauptstaedte_der_welt.csv (Land, Hauptstadt, Breitengrad, Laengengrad)
und schreibt temperaturen_hauptstaedte_<JAHR>.csv
(Land, Stadt, Durchschnittstemperatur_C_<JAHR>, Minimum_C_<JAHR>, Maximum_C_<JAHR>).

Resume-fähig: bereits erfolgreich abgerufene Städte werden bei erneutem
Aufruf übersprungen; unvollständige Zeilen (z. B. durch Rate-Limit-Fehler)
werden automatisch erneut abgerufen. Bei "Minutely API request limit
exceeded" wird ca. 65s gewartet und der Batch erneut versucht.
"""

import csv
import json
import subprocess
import sys
import time
import statistics

YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 1950

INPUT_PATH = "hauptstaedte_der_welt.csv"
OUTPUT_PATH = f"temperaturen_hauptstaedte_{YEAR}.csv"
BATCH = 10

with open(INPUT_PATH, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

done_keys = set()
existing_rows = []
try:
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row[f"Durchschnittstemperatur_C_{YEAR}"] == "":
                continue  # incomplete row -> retry
            existing_rows.append(row)
            done_keys.add((row["Land"], row["Stadt"]))
except FileNotFoundError:
    pass

todo = [b for b in rows if (b["Land"], b["Hauptstadt"]) not in done_keys]
print(f"Already done: {len(done_keys)}, remaining: {len(todo)}", file=sys.stderr)


def fetch(batch, retries=3):
    lats = ",".join(b["Breitengrad"] for b in batch)
    lons = ",".join(b["Laengengrad"] for b in batch)
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lats}&longitude={lons}"
        f"&start_date={YEAR}-01-01&end_date={YEAR}-12-31"
        "&daily=temperature_2m_mean,temperature_2m_min,temperature_2m_max"
        "&timezone=auto"
    )
    cmd = ["curl", "-s", "--max-time", "60", "-H",
           "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36", url]
    for attempt in range(1, retries + 1):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=75)
        except subprocess.TimeoutExpired:
            print(f"  attempt {attempt} timed out", file=sys.stderr)
            time.sleep(2)
            continue
        if out.returncode != 0:
            print(f"  attempt {attempt} curl error: {out.stderr[:200]}", file=sys.stderr)
            time.sleep(2)
            continue
        try:
            parsed = json.loads(out.stdout)
        except json.JSONDecodeError:
            print(f"  attempt {attempt} bad JSON: {out.stdout[:200]}", file=sys.stderr)
            time.sleep(2)
            continue
        if isinstance(parsed, dict) and parsed.get("error"):
            reason = parsed.get("reason", str(parsed))
            print(f"  attempt {attempt} API error: {reason}", file=sys.stderr)
            time.sleep(65 if "limit" in reason.lower() else 5)
            continue
        return parsed
    return None


new_results = []

for i in range(0, len(todo), BATCH):
    batch = todo[i:i + BATCH]
    data = fetch(batch)
    if data is None:
        print(f"Batch {i}-{i + len(batch)} FAILED after retries, skipping "
              f"(will retry on next run)", file=sys.stderr)
        continue
    if isinstance(data, dict):
        data = [data]
    for b, d in zip(batch, data):
        avg_t = min_t = max_t = None
        try:
            daily = d["daily"]
            means = [x for x in daily["temperature_2m_mean"] if x is not None]
            mins = [x for x in daily["temperature_2m_min"] if x is not None]
            maxs = [x for x in daily["temperature_2m_max"] if x is not None]
            if means:
                avg_t = round(statistics.mean(means), 1)
            if mins:
                min_t = round(min(mins), 1)
            if maxs:
                max_t = round(max(maxs), 1)
        except (KeyError, TypeError):
            pass
        new_results.append((b["Land"], b["Hauptstadt"], avg_t, min_t, max_t))
    print(f"Batch {i}-{i + len(batch)} done ({len(data)} results)", file=sys.stderr)
    time.sleep(6)

with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Land", "Stadt", f"Durchschnittstemperatur_C_{YEAR}",
                f"Minimum_C_{YEAR}", f"Maximum_C_{YEAR}"])
    for row in existing_rows:
        w.writerow([row["Land"], row["Stadt"],
                    row[f"Durchschnittstemperatur_C_{YEAR}"],
                    row[f"Minimum_C_{YEAR}"], row[f"Maximum_C_{YEAR}"]])
    for land, stadt, avg_t, min_t, max_t in new_results:
        w.writerow([
            land, stadt,
            avg_t if avg_t is not None else "",
            min_t if min_t is not None else "",
            max_t if max_t is not None else "",
        ])

total = len(existing_rows) + len(new_results)
print(f"Total rows in file now: {total} / {len(rows)}", file=sys.stderr)
if total < len(rows):
    print("Nicht vollständig — Skript einfach erneut ausführen, um "
          "fehlende Städte nachzuholen.", file=sys.stderr)
