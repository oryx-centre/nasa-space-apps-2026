# Burning Activity Calendar — Harmonization of MODIS and VIIRS Hot Spots

**NASA Space Apps Challenge 2026** · Challenge: *Harmonization of MODIS and VIIRS Hot Spots* ·
Theme: The Next Frontier · Team: Oryx AI (solo — Amartya Kumar, `amartya-oryxai`) ·
Area of interest: Punjab, India · Window: October 2025

## What it is

A web application that harmonizes two satellite fire records — NASA FIRMS VIIRS (375 m) and
MODIS (1 km) — into a single burning-activity calendar for a selected area. The point of the
challenge is that the two records cannot be compared directly. We measured exactly how much
they disagree, and built the calendar from the union of both.

## Headline finding (computed, not claimed)

Punjab, October 2025: VIIRS saw **1,902** fires, MODIS saw **927**, only **102** were the same
fire seen by both sensors. Jaccard agreement **0.037**. Only **11.0%** of MODIS detections were
confirmed by VIIRS; only **5.4%** of VIIRS detections were confirmed by MODIS. The harmonized
record holds **2,727** distinct fire events. MODIS alone would miss more than half the burning
season. The critical period was **18–31 October** (11 days above twice the October median);
peak day **31 October** with 313 VIIRS detections.

Why they disagree (verified in the data, not assumed): the sensors pass 1–2 hours apart
(VIIRS ~13:00 IST, MODIS Aqua ~14:30 IST) and stubble fires burn for hours, so most fires are
genuinely seen by one sensor only; and VIIRS resolves small fires MODIS cannot see. The
agreement stays low at every matching tolerance (0.01°→0.05°), so the split record is real,
not a parameter artefact.

## Files

| File | What it is |
|---|---|
| `app/index.html` | Self-contained dashboard (open in any browser, no server needed) |
| `results.json` | All computed numbers, with method and limitations |
| `daily_calendar.csv` | Per-day VIIRS / MODIS / matched counts + FRP, 1–31 Oct 2025 |
| `matched_pairs.csv` | The 102 matched cross-sensor pairs (date, positions, FRP, distance) |
| `harmonize.py` | Analysis code (stdlib only) — filter, match, compute |
| `update_results.py` | Tolerance-sensitivity recomputation |
| `generate_dashboard.py` | Builds `app/index.html` from `results.json` (no hand-typed figures) |
| `data/viirs-snpp_2025_India.csv` | NASA FIRMS VIIRS S-NPP, India 2025 (646,376 rows) |
| `data/modis_2025_India.csv` | NASA FIRMS MODIS C6.1, India 2025 (94,917 rows) |
| `data/viirs_punjab_oct2025.csv` / `data/modis_punjab_oct2025.csv` | Filtered Punjab, Oct 2025 |
| `SUBMISSION.md` | Submission draft for the Space Apps project page |
| `BUILD_LOG.md` | Build log |

## Method

1. Downloaded NASA FIRMS country archive files for India, 2025 (keyless direct download).
2. Filtered to Punjab (lon 73.8–76.9, lat 29.5–32.5) and October 2025, peak stubble-burning season.
3. Matched detections across sensors: same calendar date AND within 0.02° (~2.2 km);
   greedy one-to-one, MODIS by descending FRP, nearest unmatched VIIRS wins.
4. Built the calendar from the union of both records.

## How to re-run

```bash
cd nasa-space-apps-2026
python3 harmonize.py        # filter + match at 0.01 deg, write results
python3 update_results.py   # sensitivity at 0.01/0.02/0.03/0.05, headline 0.02
python3 generate_dashboard.py
open app/index.html
```

## Limitations (stated in the dashboard too)

- Same-day matching ignores overpass-time differences; fires are short-lived.
- A fixed distance box can merge distinct nearby fires and split one large fire seen as several VIIRS pixels.
- MODIS (1 km) misses small fires VIIRS (375 m) detects; agreement measures cross-sensor consistency, not ground truth.
- Dates are FIRMS `acq_date` (UTC); the VIIRS night overpass falls after midnight IST, so a few detections sit on the UTC date before the IST date.
- Archive 2025 data, not live near-real-time.

## Live-data upgrade path

For a live version, register a free FIRMS MAP_KEY (instant self-serve, one email) and pull
near-real-time data via the FIRMS API, e.g.
`https://firms.modaps.eosdis.nasa.gov/api/country/csv/{MAP_KEY}/VIIRS_SNPP_NRT/IND/7`
and the same for `MODIS_NRT`. No code changes needed beyond the fetch step — the matching
and calendar code is sensor-agnostic.

## Data sources & citation

NASA FIRMS (Fire Information for Resource Management System), India 2025 country archive,
downloaded 14 Nov 2026 from firms.modaps.eosdis.nasa.gov. NASA open data; cite FIRMS.
No invented data: every number in this project is computed from those files.
