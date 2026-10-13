'use strict';
/* Offline de-identified-only AKI screening. No network or browser storage. */
(function (root) {
  function number(value, name, allowZero = false) {
    if (typeof value === 'boolean' || value === null || value === undefined || String(value).trim() === '') {
      throw new Error(`${name} must be a finite number`);
    }
    const n = Number(value);
    if (!Number.isFinite(n) || (allowZero ? n < 0 : n <= 0)) throw new Error(`${name} must be positive/valid and finite`);
    return n;
  }
  function dateMillis(text) {
    if (typeof text !== 'string') throw new Error('timestamp must be ISO 8601');
    const s = text.trim();
    const valid = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,6})?)?(Z|[+-]\d{2}:\d{2})?)?$/i.exec(s);
    if (!valid) throw new Error(`Invalid ISO 8601 timestamp: ${s}`);
    const y = Number(valid[1]), m = Number(valid[2]), d = Number(valid[3]);
    const check = new Date(Date.UTC(y, m - 1, d));
    if (check.getUTCFullYear() !== y || check.getUTCMonth() + 1 !== m || check.getUTCDate() !== d) throw new Error(`Invalid date: ${s}`);
    const normalized = s.includes('T') && !/(Z|[+-]\d{2}:\d{2})$/i.test(s) ? s + 'Z' : s;
    const t = Date.parse(normalized);
    if (!Number.isFinite(t)) throw new Error(`Invalid date: ${s}`);
    return t;
  }
  function assessTrajectory(observations, opts = {}) {
    if (!Array.isArray(observations) || observations.length === 0 || observations.length > 10000) throw new Error('Provide 1–10000 observations');
    const data = observations.map((row, i) => {
      if (!row || typeof row !== 'object' || Array.isArray(row)) throw new Error(`Observation ${i + 1} must be an object`);
      const scr = row.creatinine_mg_dl, egfr = row.egfr_ml_min_1_73m2;
      if ((scr == null || scr === '') && (egfr == null || egfr === '')) throw new Error(`Observation ${i + 1} needs creatinine or eGFR`);
      return { time: dateMillis(row.timestamp),
        scr: scr == null || scr === '' ? null : number(scr, 'creatinine_mg_dl'),
        egfr: egfr == null || egfr === '' ? null : number(egfr, 'egfr_ml_min_1_73m2') };
    }).sort((a, b) => a.time - b.time);
    if (data.some((row, i) => i && row.time === data[i - 1].time)) throw new Error('Duplicate timestamps are ambiguous');
    const ratePresent = opts.urine_output_ml_kg_h != null && opts.urine_output_ml_kg_h !== '';
    const durationPresent = opts.urine_duration_hours != null && opts.urine_duration_hours !== '';
    if (ratePresent !== durationPresent) throw new Error('Urine rate and duration must be provided together');
    let urineStage = null;
    if (ratePresent) {
      const rate = number(opts.urine_output_ml_kg_h, 'urine_output_ml_kg_h', true);
      const hours = number(opts.urine_duration_hours, 'urine_duration_hours');
      urineStage = (rate === 0 && hours >= 12) || (rate < 0.3 && hours >= 24) ? 3 :
        rate < 0.5 && hours >= 12 ? 2 : rate < 0.5 && hours >= 6 ? 1 : 0;
    }
    const latest = data[data.length - 1], previous = data.slice(0, -1);
    const prior = hours => previous.filter(r => r.scr !== null && latest.time - r.time > 0 && latest.time - r.time <= hours * 3600000).map(r => r.scr);
    const p48 = prior(48), p7d = prior(168);
    const rise = latest.scr !== null && p48.length ? latest.scr - Math.min(...p48) : null;
    const baseline = latest.scr !== null && p7d.length ? Math.min(...p7d) : null;
    const ratio = baseline !== null ? latest.scr / baseline : null;
    let creatStage = null;
    if (rise !== null || ratio !== null) {
      const riseCriterion = rise !== null && rise >= 0.3 - 1e-9;
      const ratioCriterion = ratio !== null && ratio >= 1.5 - 1e-9;
      creatStage = 0;
      if (riseCriterion || ratioCriterion) creatStage = 1;
      if (ratio !== null && ratio >= 2 - 1e-9) creatStage = 2;
      if ((ratio !== null && ratio >= 3 - 1e-9) || (latest.scr >= 4 && (riseCriterion || ratioCriterion))) creatStage = 3;
    }
    const rrt = opts.renal_replacement_therapy === true;
    const stages = [creatStage, urineStage, rrt ? 3 : null].filter(v => v !== null);
    const akiStage = stages.length ? Math.max(...stages) : null;
    const egfrRows = data.filter(r => r.egfr !== null);
    let slope = null, span = null, rapid = null;
    if (egfrRows.length >= 2) {
      const x = egfrRows.map(r => (r.time - egfrRows[0].time) / (365.25 * 86400000));
      const y = egfrRows.map(r => r.egfr);
      const xAvg = x.reduce((a, b) => a + b) / x.length;
      const yAvg = y.reduce((a, b) => a + b) / y.length;
      const denom = x.reduce((s, v) => s + (v - xAvg) ** 2, 0);
      slope = x.reduce((s, v, i) => s + (v - xAvg) * (y[i] - yAvg), 0) / denom;
      span = (egfrRows[egfrRows.length - 1].time - egfrRows[0].time) / 86400000;
      if (span >= 365) rapid = slope < -5;
    }
    const warnings = [];
    if (creatStage === null && urineStage === null && !rrt) warnings.push('AKI stage not assessable: no eligible creatinine comparison or urine-output interval');
    if (urineStage === null) warnings.push('Urine-output staging unavailable; AKI may be missed');
    if (egfrRows.length < 2) warnings.push('At least two dated eGFR values are needed for slope');
    else if (span < 365) warnings.push('eGFR follow-up under 365 days: long-term rapid-decline flag withheld');
    if (latest.scr === null) warnings.push('Latest observation has no creatinine; serum-creatinine staging unavailable');
    warnings.push('Screening only: clinical context, baseline uncertainty, and non-steady-state eGFR require review');
    const round = (v, places) => v === null ? null : Number(v.toFixed(places));
    return { latest_timestamp: new Date(latest.time).toISOString().replace('.000Z', 'Z'), observation_count: data.length,
      aki_stage: akiStage, creatinine_stage: creatStage, urine_output_stage: urineStage,
      baseline_creatinine_7d_mg_dl: round(baseline, 4), creatinine_rise_48h_mg_dl: round(rise, 4),
      creatinine_ratio_7d: round(ratio, 4), egfr_slope_ml_min_1_73m2_per_year: round(slope, 3),
      egfr_span_days: round(span, 2), rapid_egfr_decline_flag: rapid, warnings };
  }
  function parseCSV(text) {
    if (text.length > 2e6) throw new Error('CSV exceeds 2 MB');
    const rows = [], row = [];
    let field = '', quoted = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (c === '"') {
        if (quoted && text[i + 1] === '"') { field += '"'; i++; }
        else if (quoted || field === '') quoted = !quoted;
        else throw new Error('Unexpected CSV quote');
      } else if (c === ',' && !quoted) { row.push(field.trim()); field = ''; }
      else if ((c === '\n' || c === '\r') && !quoted) {
        if (c === '\r' && text[i + 1] === '\n') i++;
        row.push(field.trim()); field = '';
        if (row.some(x => x !== '')) rows.push([...row]);
        row.length = 0;
      } else field += c;
    }
    if (quoted) throw new Error('Unterminated CSV quoted value');
    row.push(field.trim());
    if (row.some(x => x !== '')) rows.push(row);
    if (rows.length < 2) throw new Error('Include a CSV header and one or more observations');
    const keys = rows.shift().map(x => x.replace(/^\uFEFF/, '').toLowerCase());
    const timestamp = keys.indexOf('timestamp'), creatinine = keys.indexOf('creatinine_mg_dl'), egfr = keys.indexOf('egfr_ml_min_1_73m2');
    if (timestamp < 0 || (creatinine < 0 && egfr < 0)) throw new Error('Required columns: timestamp and creatinine_mg_dl and/or egfr_ml_min_1_73m2');
    if (new Set(keys).size !== keys.length) throw new Error('Duplicate CSV headers');
    if (rows.length > 10000) throw new Error('Maximum 10000 observations');
    return rows.map((r, i) => {
      if (r.length !== keys.length) throw new Error(`CSV row ${i + 2}: expected ${keys.length} columns`);
      return { timestamp: r[timestamp], creatinine_mg_dl: creatinine < 0 ? null : r[creatinine], egfr_ml_min_1_73m2: egfr < 0 ? null : r[egfr] };
    });
  }
  root.RenalTrajectory = { assessTrajectory, parseCSV };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.RenalTrajectory;
})(typeof window !== 'undefined' ? window : globalThis);
