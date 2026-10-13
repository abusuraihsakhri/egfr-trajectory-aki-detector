# eGFR Trajectory & AKI Detector

A local-first research/education tool for screening dated serum creatinine changes against **KDIGO 2012 acute kidney injury (AKI) criteria** and describing longitudinal eGFR measurements. The browser tool runs as static HTML/JavaScript; the Python analysis engine uses only the standard library.

**Not a validated medical device.** The output is not a diagnosis, cannot rule out AKI, and must not guide treatment without qualified clinical review.

## Features

- **Timed creatinine screening:** rise ≥0.3 mg/dL in 48 hours, ≥1.5× within 7 days, and stage 1–3 thresholds using prior documented results.
- **Optional urine-output stage:** sustained mL/kg/hour plus duration (or new kidney replacement therapy for AKI); final stage uses the highest supported criterion.
- **eGFR trajectory:** least-squares slope in mL/min/1.73 m²/year from dated supplied eGFR values. A historical exploratory rapid-decline flag (<−5/year) is only shown with ≥365 days of follow-up; **this is not a KDIGO 2024 diagnostic threshold**.
- **Browser CSV import, chart, local JSON export:** no API calls, analytics, cookies, persistent storage or third-party scripts in the web application.
- **Python CLI and FastAPI:** JSON request support, validation, and an independent `POST /api/trajectory` endpoint.
- The previous generic calculator/worker suite remains available as legacy functionality; its numeric thresholds and mock responders **are not KDIGO AKI algorithms**.

## Browser application

The root `index.html` provides the static application and is packaged for GitHub Pages via `.github/workflows/pages.yml`. A verified live link will be added when Pages deployment and the public URL are confirmed.

Open `index.html` in a recent desktop or mobile browser; keep `app.js` and `ui.js` in the same directory. Paste de-identified CSV data or select `sample_renal_trajectory.csv`. The analysis uses the **latest timestamp** against preceding documented measurements, not a retrospective scan for past resolved AKI episodes.

CSV columns:

```csv
timestamp,creatinine_mg_dl,egfr_ml_min_1_73m2
2026-01-01T08:00:00Z,1.0,82
2026-01-02T08:00:00Z,1.2,70
2026-01-03T08:00:00Z,1.5,55
```

Either biomarker value may be empty, but each row requires a timestamp and at least one value. Timezone-less ISO timestamps are treated as UTC; ambiguous duplicate timestamps are rejected. Use dated observations from the same subject only. Do not enter names, MRNs, dates of birth, or other identifiers.

## Python and API

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python cli.py trajectory --input sample_renal_trajectory.json
python egfr_trajectory.py trajectory --input sample_renal_trajectory.json
python cli.py serve --host 127.0.0.1 --port 8000
```

The API documents its endpoints at `http://127.0.0.1:8000/docs`. Request example:

```bash
curl -s http://127.0.0.1:8000/api/trajectory -H 'Content-Type: application/json' \
  --data-binary @sample_renal_trajectory.json
```

The trajectory endpoint accepts `observations`, optional `urine_output_ml_kg_h` and `urine_duration_hours` together, and optional boolean `renal_replacement_therapy` (new treatment for AKI only). Invalid values produce HTTP 422. CLI option `--output` writes JSON locally.

Legacy endpoints remain: `/health`, `/metrics` (JSON counters), `/api/audit`, `/api/chat`, and `/api/audit/logs`. The generic worker CLI remains `python cli.py audit`; generic calculators and CSV batching remain in `egfr_trajectory.py`. These separate experimental features are not substitutes for the renal trajectory algorithm.

## Interpretation and limits

- KDIGO serum-creatinine staging requires an **observed temporal increase**. The program does not impute a baseline, infer AKI from eGFR alone, or classify a solitary high creatinine as AKI.
- AKI may occur without the available tests; urine-output staging is incomplete without a measured sustained rate. False negatives are possible. No pediatric eGFR stage-3 branch or full dialysis-history handling is included.
- Two dated eGFR results suffice to compute a descriptive slope, but sparse measurements, non-steady-state function, assay variation and regression noise make individual estimates uncertain. CKD diagnosis requires appropriate longitudinal and clinical evidence.
- KDIGO 2024 emphasizes evaluation of eGFR changes and biological variability; this tool's 5-unit/year indicator is a **historical heuristic**, not KDIGO 2024 guidance.
- The app is **not clinically validated** on outcome data and has not undergone regulatory review.

Guideline sources: [KDIGO 2012 AKI guideline](https://kdigo.org/guidelines/acute-kidney-injury/) and [KDIGO 2024 CKD guideline](https://kdigo.org/guidelines/ckd-evaluation-and-management/).

## Privacy and security

The static site never sends records to a server and does not store them between sessions. The optional API is a server-side application: do not send clinical identifiers or identifiable records to a shared instance. The legacy pattern-based identifier checks are limited filters, **not HIPAA de-identification, Safe Harbor certification, or comprehensive PHI detection**.

The legacy audit trail is **in-memory and nonpersistent**. It HMAC-signs metadata per record and verifies the full HMAC chain, but it cannot prove durability or integrity across process restarts without external persistence. Configure `AUDIT_SECRET_KEY` using a strong random value and rotate any key previously committed to repository history. Never put credentials into tracked files.

Docker:

```bash
export AUDIT_SECRET_KEY="$(openssl rand -hex 32)"
docker compose up --build
```

## Development and checks

```bash
python -m compileall -q agents cli.py egfr_trajectory.py renal_trajectory.py
python -m pytest -q
node --check app.js
node --check ui.js
node tests/test_browser.js
```

GitHub Actions runs the Python suite on 3.10–3.12 and exercises the browser engine with Node.js. The Pages workflow copies only static assets (`index.html`, `app.js`, `ui.js`) into its deployment artifact. No Pyodide or backend service is needed for the browser calculations.

## License

MIT; see [LICENSE](LICENSE).
