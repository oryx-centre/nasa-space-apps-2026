#!/usr/bin/env python3
"""Harmonization of MODIS and VIIRS hot spots — Punjab, India, October 2025.

Method (the Oryx audit method applied to satellite fire data):
- Source: NASA FIRMS country archive files, 2025, India (keyless download).
  VIIRS S-NPP: https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/2025/viirs-snpp_2025_India.csv
  MODIS:       https://firms.modaps.eosdis.nasa.gov/data/country/modis/2025/modis_2025_India.csv
- Area of interest: Punjab, India (lon 73.8-76.9, lat 29.5-32.5). Window: Oct 2025
  (peak paddy-stubble burning season).
- Matching rule (harmonization): a MODIS detection and a VIIRS detection are the
  SAME fire event if they fall on the same calendar date AND within 0.01 degrees
  (~1.1 km, one MODIS pixel) in both latitude and longitude. Greedy one-to-one
  matching, MODIS detections processed in descending FRP order, nearest unmatched
  VIIRS detection wins. Unmatched detections are sensor-only.
- Outputs: filtered CSVs, matched-pairs CSV, daily calendar CSV, results JSON.
- Limitations (stated honestly): same-day matching ignores overpass-time
  differences; a 1 km box can merge distinct nearby fires and can split one large
  fire seen as several VIIRS pixels; MODIS misses small/low-intensity fires VIIRS
  sees (375 m vs 1 km); VIIRS sees fires MODIS misses. Agreement rates therefore
  measure cross-sensor consistency, not ground truth. Archive (2025) data, not
  live NRT — a live version would use the FIRMS API with a MAP_KEY.
Stdlib only. No invented data: every number below is computed from the files.
"""
import csv, json, math, os
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, 'data')
BBOX = (73.8, 29.5, 76.9, 32.5)  # lon_min, lat_min, lon_max, lat_max (Punjab)
WINDOW = '2025-10'
TOL = 0.01  # degrees, ~1.1 km

def load(path, sensor):
    rows = []
    with open(path, newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            if not row['acq_date'].startswith(WINDOW):
                continue
            try:
                lat = float(row['latitude']); lon = float(row['longitude'])
                frp = float(row.get('frp') or 0)
            except ValueError:
                continue
            if not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
                continue
            rows.append({
                'lat': lat, 'lon': lon, 'date': row['acq_date'],
                'time': row['acq_time'], 'frp': frp,
                'satellite': row['satellite'], 'instrument': row['instrument'],
                'confidence': row.get('confidence', ''),
                'daynight': row.get('daynight', ''),
                'sensor': sensor,
            })
    return rows

viirs = load(os.path.join(DATA, 'viirs-snpp_2025_India.csv'), 'VIIRS')
modis = load(os.path.join(DATA, 'modis_2025_India.csv'), 'MODIS')
print(f'VIIRS Punjab Oct 2025: {len(viirs)}')
print(f'MODIS Punjab Oct 2025: {len(modis)}')

# --- greedy one-to-one matching, per day ---
by_day_v = defaultdict(list)
for i, v in enumerate(viirs):
    by_day_v[v['date']].append(i)
matched_pairs = []          # (modis_idx, viirs_idx, dist_deg)
used_v = set()
modis_sorted = sorted(range(len(modis)), key=lambda i: -modis[i]['frp'])
for mi in modis_sorted:
    m = modis[mi]
    best, bestd = None, None
    for vi in by_day_v.get(m['date'], []):
        if vi in used_v:
            continue
        v = viirs[vi]
        d = math.hypot(v['lat'] - m['lat'], v['lon'] - m['lon'])
        if d <= TOL and (bestd is None or d < bestd):
            best, bestd = vi, d
    if best is not None:
        used_v.add(best)
        matched_pairs.append((mi, best, bestd))
matched_m = {mi for mi, _, _ in matched_pairs}
matched_v = set(used_v)
print(f'matched pairs: {len(matched_pairs)}')

def frp_sum(rows, idxs=None):
    return round(sum((rows[i]['frp'] if idxs is None else rows[i]['frp']) for i in (range(len(rows)) if idxs is None else idxs)), 1)

n_v, n_m, n_match = len(viirs), len(modis), len(matched_pairs)
union = n_v + n_m - n_match
results = {
    'project': 'Harmonization of MODIS and VIIRS Hot Spots — Punjab, India, October 2025',
    'challenge': 'NASA Space Apps Challenge 2026 — Harmonization of MODIS and VIIRS Hot Spots',
    'area_of_interest': {'name': 'Punjab, India', 'lon': [73.8, 76.9], 'lat': [29.5, 32.5]},
    'window': '2025-10-01 to 2025-10-31',
    'sources': {
        'viirs': 'NASA FIRMS, VIIRS S-NPP, India 2025 country archive (viirs-snpp_2025_India.csv)',
        'modis': 'NASA FIRMS, MODIS C6.1, India 2025 country archive (modis_2025_India.csv)',
    },
    'matching_rule': 'Same calendar date AND within 0.01 deg (~1.1 km) in lat and lon; greedy one-to-one, MODIS by descending FRP, nearest unmatched VIIRS wins.',
    'counts': {
        'viirs_detections': n_v,
        'modis_detections': n_m,
        'matched_both_sensors': n_match,
        'viirs_only': n_v - n_match,
        'modis_only': n_m - n_match,
    },
    'agreement': {
        'jaccard_index_matched_over_union': round(n_match / union, 4) if union else None,
        'modis_detections_confirmed_by_viirs': round(n_match / n_m, 4) if n_m else None,
        'viirs_detections_confirmed_by_modis': round(n_match / n_v, 4) if n_v else None,
    },
    'frp_mw': {
        'viirs_total': frp_sum(viirs),
        'modis_total': frp_sum(modis),
        'matched_viirs_total': frp_sum(viirs, matched_v),
        'matched_modis_total': frp_sum(modis, matched_m),
    },
}

# --- daily burning-activity calendar ---
days = {}
for d in range(1, 32):
    days[f'2025-10-{d:02d}'] = {'viirs': 0, 'modis': 0, 'matched': 0, 'viirs_frp': 0.0, 'modis_frp': 0.0}
for v in viirs:
    days[v['date']]['viirs'] += 1
    days[v['date']]['viirs_frp'] = round(days[v['date']]['viirs_frp'] + v['frp'], 1)
for m in modis:
    days[m['date']]['modis'] += 1
    days[m['date']]['modis_frp'] = round(days[m['date']]['modis_frp'] + m['frp'], 1)
for mi, vi, _ in matched_pairs:
    days[modis[mi]['date']]['matched'] += 1
daily = [{'date': d, **days[d]} for d in sorted(days)]
results['daily_calendar'] = daily
viirs_daily = sorted(d['viirs'] for d in daily)
median_v = viirs_daily[len(viirs_daily) // 2]
results['critical_periods'] = {
    'october_median_daily_viirs_detections': median_v,
    'days_above_2x_median': [d['date'] for d in daily if d['viirs'] > 2 * median_v],
    'peak_day': max(daily, key=lambda d: d['viirs'])['date'],
    'peak_day_viirs_detections': max(d['viirs'] for d in daily),
}
results['limitations'] = [
    'Same-day matching ignores overpass-time differences between Terra/Aqua and Suomi-NPP.',
    'A 1.1 km box can merge distinct nearby fires and can split one large fire seen as several VIIRS pixels.',
    'MODIS (1 km) misses small/low-intensity fires VIIRS (375 m) detects; VIIRS also misses some MODIS detections.',
    'Agreement rates measure cross-sensor consistency, not ground truth.',
    'Archive 2025 data, not live near-real-time; a live version would use the FIRMS API with a MAP_KEY.',
]

# --- write outputs ---
with open(os.path.join(BASE, 'results.json'), 'w') as f:
    json.dump(results, f, indent=2)
with open(os.path.join(BASE, 'daily_calendar.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['date', 'viirs', 'modis', 'matched', 'viirs_frp', 'modis_frp'])
    w.writeheader(); w.writerows(daily)
with open(os.path.join(DATA, 'viirs_punjab_oct2025.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['lat', 'lon', 'date', 'time', 'frp', 'satellite', 'instrument', 'confidence', 'daynight', 'sensor'])
    w.writeheader(); w.writerows(viirs)
with open(os.path.join(DATA, 'modis_punjab_oct2025.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['lat', 'lon', 'date', 'time', 'frp', 'satellite', 'instrument', 'confidence', 'daynight', 'sensor'])
    w.writeheader(); w.writerows(modis)
with open(os.path.join(BASE, 'matched_pairs.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['date', 'modis_lat', 'modis_lon', 'modis_frp', 'viirs_lat', 'viirs_lon', 'viirs_frp', 'distance_deg'])
    for mi, vi, d in sorted(matched_pairs, key=lambda p: (modis[p[0]]['date'], -modis[p[0]]['frp'])):
        m, v = modis[mi], viirs[vi]
        w.writerow([m['date'], m['lat'], m['lon'], m['frp'], v['lat'], v['lon'], v['frp'], round(d, 5)])
print(json.dumps({k: results[k] for k in ['counts', 'agreement', 'frp_mw', 'critical_periods']}, indent=2))
print('outputs written: results.json, daily_calendar.csv, matched_pairs.csv, filtered CSVs')
