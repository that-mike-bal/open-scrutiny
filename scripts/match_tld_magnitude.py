#!/usr/bin/env python3
"""
Match TLD strings from existing_tld_strings.json against ICANN magnitude data
from icann_magnitude_non_delegated_tlds.csv and produce a sorted output CSV.
"""

import csv
import json
import os

BASE_DIR = "."
JSON_PATH = os.path.join(BASE_DIR, "data", "existing_tld_strings.json")
CSV_PATH = "./icann_magnitude_non_delegated_tlds.csv"
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "tld_strings_by_magnitude.csv")

# 1. Load TLD strings from JSON
with open(JSON_PATH, "r") as f:
    tld_strings = json.load(f)

print(f"Loaded {len(tld_strings)} TLD strings from JSON")

# 2. Parse the CSV and build a lookup (case-insensitive)
csv_lookup = {}  # lowercase TLD -> row dict

with open(CSV_PATH, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        tld = row["Top-Level Domain"].strip().lower()
        csv_lookup[tld] = row

print(f"Loaded {len(csv_lookup)} TLDs from CSV")

# 3. Match each JSON TLD against CSV data
matched = []
unmatched = []

for tld in tld_strings:
    tld_lower = tld.strip().lower()
    if tld_lower in csv_lookup:
        row = csv_lookup[tld_lower]
        # Parse magnitude as float for sorting
        try:
            magnitude = float(row["Magnitude"])
        except (ValueError, TypeError):
            magnitude = 0.0

        matched.append({
            "tld_string": tld_lower,
            "magnitude": row["Magnitude"],
            "magnitude_float": magnitude,
            "status": row.get("status", ""),
            "daily_rank": row.get("Daily Rank", ""),
            "weekly_rank": row.get("Weekly Rank", ""),
            "monthly_rank": row.get("Monthly Rank", ""),
            "quarterly_rank": row.get("Quarterly Rank", ""),
            "coverage": row.get("Coverage", ""),
            "unique_sources": row.get("Unique Sources", ""),
            "queries_per_thousand": row.get("Queries Per Thousand", ""),
            "query_volume": row.get("Query Volume", ""),
            "avg_query_source": row.get("Avg Query/Source", ""),
            "has_magnitude_data": "TRUE",
        })
    else:
        unmatched.append({
            "tld_string": tld_lower,
            "magnitude": "",
            "magnitude_float": 0.0,
            "status": "",
            "daily_rank": "",
            "weekly_rank": "",
            "monthly_rank": "",
            "quarterly_rank": "",
            "coverage": "",
            "unique_sources": "",
            "queries_per_thousand": "",
            "query_volume": "",
            "avg_query_source": "",
            "has_magnitude_data": "FALSE",
        })

# 4. Sort: matched by magnitude descending, unmatched alphabetically
matched.sort(key=lambda x: x["magnitude_float"], reverse=True)
unmatched.sort(key=lambda x: x["tld_string"])

# 5. Write output CSV
output_columns = [
    "tld_string", "magnitude", "status", "daily_rank", "weekly_rank",
    "monthly_rank", "quarterly_rank", "coverage", "unique_sources",
    "queries_per_thousand", "query_volume", "avg_query_source",
    "has_magnitude_data",
]

all_rows = matched + unmatched

with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=output_columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(all_rows)

# 6. Summary
print(f"\n{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")
print(f"Total TLD strings in JSON:     {len(tld_strings)}")
print(f"TLDs WITH magnitude data:      {len(matched)}")
print(f"TLDs WITHOUT magnitude data:   {len(unmatched)}")
print(f"Match rate:                     {len(matched)/len(tld_strings)*100:.1f}%")
print(f"{'='*60}")

if matched:
    print(f"\nTop 10 by magnitude:")
    for i, row in enumerate(matched[:10], 1):
        print(f"  {i:2d}. {row['tld_string']:<20s}  magnitude={row['magnitude']}")

if unmatched:
    print(f"\nFirst 10 unmatched (alphabetical):")
    for row in unmatched[:10]:
        print(f"      {row['tld_string']}")

print(f"\nOutput written to: {OUTPUT_PATH}")
