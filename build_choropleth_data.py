"""Erzeugt world_choropleth_data.js für weltkarte_temperaturen.html.

Verknüpft hauptstaedte_der_welt.csv (Koordinaten) und
temperaturen_hauptstaedte.csv (aktuelle Temperaturen, siehe
fetch_current_temps.py) mit Länder-Polygonen und schreibt das Ergebnis als
eingebettetes GeoJSON (COUNTRY_GEOJSON) plus Fallback-Marker (MARKER_ONLY)
für Länder ohne Polygon-Treffer.

Lädt die Ländergrenzen-Geodaten bei Bedarf automatisch nach
(GEOJSON_SOURCE, ~14 MB, wird nicht dauerhaft im Projekt gespeichert).
"""

import csv
import json
import os
import subprocess
import sys

GEOJSON_SOURCE = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"
GEOJSON_CACHE = "/tmp/world_countries.geo.json"

# German country name (as used in our CSVs) -> ISO 3166-1 alpha-3 code
ISO3 = {
    "Afghanistan": "AFG", "Ägypten": "EGY", "Albanien": "ALB", "Algerien": "DZA",
    "Andorra": "AND", "Angola": "AGO", "Antigua und Barbuda": "ATG",
    "Äquatorialguinea": "GNQ", "Argentinien": "ARG", "Armenien": "ARM",
    "Aserbaidschan": "AZE", "Äthiopien": "ETH", "Australien": "AUS",
    "Bahamas": "BHS", "Bahrain": "BHR", "Bangladesch": "BGD", "Barbados": "BRB",
    "Belarus (Weißrussland)": "BLR", "Belgien": "BEL", "Belize": "BLZ",
    "Benin": "BEN", "Bhutan": "BTN", "Bolivien": "BOL",
    "Bosnien und Herzegowina": "BIH", "Botswana": "BWA", "Brasilien": "BRA",
    "Brunei": "BRN", "Bulgarien": "BGR", "Burkina Faso": "BFA", "Burundi": "BDI",
    "Chile": "CHL", "China": "CHN", "Costa Rica": "CRI",
    "Côte d'Ivoire (Elfenbeinküste)": "CIV", "Dänemark": "DNK", "Deutschland": "DEU",
    "Dominica": "DMA", "Dominikanische Republik": "DOM", "Dschibuti": "DJI",
    "Ecuador": "ECU", "El Salvador": "SLV", "Eritrea": "ERI", "Estland": "EST",
    "Eswatini (Swasiland)": "SWZ", "Fidschi": "FJI", "Finnland": "FIN",
    "Frankreich": "FRA", "Gabun": "GAB", "Gambia": "GMB", "Georgien": "GEO",
    "Ghana": "GHA", "Grenada": "GRD", "Griechenland": "GRC", "Guatemala": "GTM",
    "Guinea": "GIN", "Guinea-Bissau": "GNB", "Guyana": "GUY", "Haiti": "HTI",
    "Honduras": "HND", "Indien": "IND", "Indonesien": "IDN", "Irak": "IRQ",
    "Iran": "IRN", "Irland": "IRL", "Island": "ISL", "Israel": "ISR",
    "Italien": "ITA", "Jamaika": "JAM", "Japan": "JPN", "Jemen": "YEM",
    "Jordanien": "JOR", "Kambodscha": "KHM", "Kamerun": "CMR", "Kanada": "CAN",
    "Kap Verde": "CPV", "Kasachstan": "KAZ", "Katar": "QAT", "Kenia": "KEN",
    "Kirgisistan": "KGZ", "Kiribati": "KIR", "Kolumbien": "COL", "Komoren": "COM",
    "Kongo, Demokratische Republik": "COD", "Kongo, Republik": "COG",
    "Korea, Nord (Nordkorea)": "PRK", "Korea, Süd (Südkorea)": "KOR",
    "Kosovo": "XKX", "Kroatien": "HRV", "Kuba": "CUB", "Kuwait": "KWT",
    "Laos": "LAO", "Lesotho": "LSO", "Lettland": "LVA", "Libanon": "LBN",
    "Liberia": "LBR", "Libyen": "LBY", "Liechtenstein": "LIE", "Litauen": "LTU",
    "Luxemburg": "LUX", "Madagaskar": "MDG", "Malawi": "MWI", "Malaysia": "MYS",
    "Malediven": "MDV", "Mali": "MLI", "Malta": "MLT", "Marokko": "MAR",
    "Marshallinseln": "MHL", "Mauretanien": "MRT", "Mauritius": "MUS",
    "Mexiko": "MEX", "Mikronesien": "FSM", "Moldau (Moldawien)": "MDA",
    "Monaco": "MCO", "Mongolei": "MNG", "Montenegro": "MNE", "Mosambik": "MOZ",
    "Myanmar": "MMR", "Namibia": "NAM", "Nauru": "NRU", "Nepal": "NPL",
    "Neuseeland": "NZL", "Nicaragua": "NIC", "Niederlande": "NLD", "Niger": "NER",
    "Nigeria": "NGA", "Nordmazedonien": "MKD", "Norwegen": "NOR", "Oman": "OMN",
    "Österreich": "AUT", "Osttimor (Timor-Leste)": "TLS", "Pakistan": "PAK",
    "Palau": "PLW", "Palästina": "PSE", "Panama": "PAN",
    "Papua-Neuguinea": "PNG", "Paraguay": "PRY", "Peru": "PER",
    "Philippinen": "PHL", "Polen": "POL", "Portugal": "PRT", "Ruanda": "RWA",
    "Rumänien": "ROU", "Russland": "RUS", "Salomonen": "SLB", "Sambia": "ZMB",
    "Samoa": "WSM", "San Marino": "SMR", "São Tomé und Príncipe": "STP",
    "Saudi-Arabien": "SAU", "Schweden": "SWE", "Schweiz": "CHE", "Senegal": "SEN",
    "Serbien": "SRB", "Seychellen": "SYC", "Sierra Leone": "SLE",
    "Simbabwe": "ZWE", "Singapur": "SGP", "Slowakei": "SVK", "Slowenien": "SVN",
    "Somalia": "SOM", "Spanien": "ESP", "Sri Lanka": "LKA",
    "St. Kitts und Nevis": "KNA", "St. Lucia": "LCA",
    "St. Vincent und die Grenadinen": "VCT", "Südafrika": "ZAF", "Sudan": "SDN",
    "Südsudan": "SSD", "Suriname": "SUR", "Syrien": "SYR", "Tadschikistan": "TJK",
    "Taiwan": "TWN", "Tansania": "TZA", "Thailand": "THA", "Togo": "TGO",
    "Tonga": "TON", "Trinidad und Tobago": "TTO", "Tschad": "TCD",
    "Tschechien": "CZE", "Tunesien": "TUN", "Türkei": "TUR",
    "Turkmenistan": "TKM", "Tuvalu": "TUV", "Uganda": "UGA", "Ukraine": "UKR",
    "Ungarn": "HUN", "Uruguay": "URY", "Usbekistan": "UZB", "Vanuatu": "VUT",
    "Vatikanstadt": "VAT", "Venezuela": "VEN",
    "Vereinigte Arabische Emirate": "ARE", "Vereinigte Staaten": "USA",
    "Vereinigtes Königreich": "GBR", "Vietnam": "VNM",
    "Zentralafrikanische Republik": "CAF", "Zypern": "CYP",
}

# Fallback for entries with a broken/"-99" ISO3 code in the source dataset
NAME_FALLBACK = {"Frankreich": "France", "Norwegen": "Norway", "Kosovo": "Kosovo"}


def load_world_geojson():
    if not os.path.exists(GEOJSON_CACHE):
        print(f"Downloading country boundaries to {GEOJSON_CACHE} ...", file=sys.stderr)
        cmd = ["curl", "-s", "-H", "User-Agent: Mozilla/5.0", "-o", GEOJSON_CACHE, GEOJSON_SOURCE]
        subprocess.run(cmd, check=True, timeout=120)
    with open(GEOJSON_CACHE, encoding="utf-8") as f:
        return json.load(f)


def round_coords(obj):
    if isinstance(obj, list):
        if obj and isinstance(obj[0], (int, float)):
            return [round(x, 3) for x in obj]
        return [round_coords(x) for x in obj]
    return obj


def main():
    coords = {}
    with open("hauptstaedte_der_welt.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            coords[r["Land"]] = (float(r["Breitengrad"]), float(r["Laengengrad"]), r["Hauptstadt"])

    temps = {}
    with open("temperaturen_hauptstaedte.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Temperatur_C"] != "":
                temps[r["Land"]] = float(r["Temperatur_C"])

    world = load_world_geojson()
    by_iso3 = {}
    by_name = {}
    for feat in world["features"]:
        code = feat["properties"].get("ISO3166-1-Alpha-3")
        name = feat["properties"].get("name")
        if code and code != "-99":
            by_iso3[code] = feat
        if name:
            by_name[name] = feat

    matched_features = []
    unmatched = []

    for land, iso3 in ISO3.items():
        if land not in temps or land not in coords:
            continue
        feat = by_iso3.get(iso3)
        if feat is None and land in NAME_FALLBACK:
            feat = by_name.get(NAME_FALLBACK[land])
        lat, lon, stadt = coords[land]
        if feat is None:
            unmatched.append(land)
            continue
        matched_features.append({
            "type": "Feature",
            "geometry": {
                "type": feat["geometry"]["type"],
                "coordinates": round_coords(feat["geometry"]["coordinates"]),
            },
            "properties": {"land": land, "stadt": stadt, "temp": temps[land], "lat": lat, "lon": lon},
        })

    print(f"Matched: {len(matched_features)}", file=sys.stderr)
    if unmatched:
        print(f"Unmatched (rendered as marker): {unmatched}", file=sys.stderr)

    geojson = {"type": "FeatureCollection", "features": matched_features}
    marker_only = [
        {"land": land, "stadt": coords[land][2], "temp": temps[land], "lat": coords[land][0], "lon": coords[land][1]}
        for land in unmatched
    ]

    with open("world_choropleth_data.js", "w", encoding="utf-8") as f:
        f.write("const COUNTRY_GEOJSON = ")
        f.write(json.dumps(geojson, ensure_ascii=False, separators=(",", ":")))
        f.write(";\nconst MARKER_ONLY = ")
        f.write(json.dumps(marker_only, ensure_ascii=False))
        f.write(";\n")

    print(f"Output size: {os.path.getsize('world_choropleth_data.js') / 1e6:.1f} MB", file=sys.stderr)


if __name__ == "__main__":
    main()
