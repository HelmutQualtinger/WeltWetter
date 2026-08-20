#!/bin/bash
# Holt historische Temperaturen (Durchschnitt/Min/Max) für alle 5-Jahres-Schritte
# von 1955 bis 2025 und speichert jedes Jahr in einer eigenen CSV-Datei.
set -uo pipefail
cd "$(dirname "$0")"

YEARS="1955 1960 1965 1970 1975 1980 1985 1990 1995 2000 2005 2010 2015 2020 2025"
TOTAL_CITIES=$(( $(wc -l < hauptstaedte_der_welt.csv) - 1 ))

for year in $YEARS; do
  echo "=== Jahr $year ==="
  outfile="temperaturen_hauptstaedte_${year}.csv"
  for attempt in 1 2 3 4 5; do
    lines=0
    if [ -f "$outfile" ]; then
      lines=$(( $(wc -l < "$outfile") - 1 ))
    fi
    if [ "$lines" -ge "$TOTAL_CITIES" ]; then
      echo "Jahr $year bereits vollständig ($lines/$TOTAL_CITIES)"
      break
    fi
    echo "Jahr $year, Versuch $attempt (bisher $lines/$TOTAL_CITIES)"
    python3 fetch_historical_temps.py "$year"
  done
done

echo "=== Fertig ==="
for year in $YEARS; do
  f="temperaturen_hauptstaedte_${year}.csv"
  n=0
  [ -f "$f" ] && n=$(( $(wc -l < "$f") - 1 ))
  echo "$year: $n/$TOTAL_CITIES"
done
