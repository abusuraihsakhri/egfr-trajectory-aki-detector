'use strict';
(() => {
  const el = id => document.getElementById(id);
  const svgNS = 'http://www.w3.org/2000/svg';
  let last = null;
  const demo = 'timestamp,creatinine_mg_dl,egfr_ml_min_1_73m2\n2024-01-01,1.0,82\n2025-01-01,1.1,74\n2026-01-01,1.2,66';
  const add = (parent, tag, value, klass) => {
    const e = document.createElement(tag);
    e.textContent = String(value);
    if (klass) e.className = klass;
    parent.appendChild(e);
    return e;
  };
  function chart(rows) {
    const svg = el('chart');
    svg.replaceChildren();
    const data = rows.filter(r => r.egfr_ml_min_1_73m2 !== '' && r.egfr_ml_min_1_73m2 != null)
      .map(r => ({ x: new Date(r.timestamp).getTime(), y: Number(r.egfr_ml_min_1_73m2) }))
      .sort((a, b) => a.x - b.x);
    function shape(tag, attrs) {
      const e = document.createElementNS(svgNS, tag);
      for (const [key, value] of Object.entries(attrs)) e.setAttribute(key, String(value));
      svg.appendChild(e);
      return e;
    }
    if (!data.length) {
      shape('text', { x: 25, y: 87, fill: '#516477' }).textContent = 'No eGFR observations';
      return;
    }
    const start = data[0].x, span = Math.max(1, data[data.length - 1].x - start);
    const low = Math.min(...data.map(r => r.y)), high = Math.max(...data.map(r => r.y));
    const range = Math.max(5, high - low);
    const pts = data.map(r => [30 + (r.x - start) / span * 380, 145 - (r.y - low) / range * 120]);
    shape('line', { x1: 30, y1: 150, x2: 416, y2: 150, stroke: '#9ab2c4' });
    shape('polyline', { points: pts.map(p => p.join(',')).join(' '), fill: 'none', stroke: '#145b87', 'stroke-width': 2.5 });
    pts.forEach(p => shape('circle', { cx: p[0], cy: p[1], r: 4, fill: '#145b87' }));
    shape('text', { x: 12, y: 15, fill: '#516477', 'font-size': 12 }).textContent = 'eGFR range: ' + low.toFixed(1) + '–' + high.toFixed(1);
  }
  function analyze() {
    el('error').textContent = '';
    try {
      const rows = RenalTrajectory.parseCSV(el('csv').value);
      const result = RenalTrajectory.assessTrajectory(rows, {
        urine_output_ml_kg_h: el('rate').value,
        urine_duration_hours: el('duration').value,
        renal_replacement_therapy: el('rrt').checked
      });
      const box = el('results');
      box.replaceChildren();
      const stage = result.aki_stage === null ? 'AKI: not assessable' :
        result.aki_stage === 0 ? 'No criterion demonstrated in available data' : 'KDIGO AKI stage ' + result.aki_stage + ' criterion met';
      add(box, 'div', stage, 'outcome');
      const grid = add(box, 'div', '', 'metrics');
      const pairs = [
        ['Creatinine stage', result.creatinine_stage],
        ['Urine stage', result.urine_output_stage],
        ['48 h SCr rise (mg/dL)', result.creatinine_rise_48h_mg_dl],
        ['7 d baseline SCr (mg/dL)', result.baseline_creatinine_7d_mg_dl],
        ['7 d ratio', result.creatinine_ratio_7d],
        ['eGFR slope / year', result.egfr_slope_ml_min_1_73m2_per_year],
        ['Long-term rapid decline', result.rapid_egfr_decline_flag === null ? 'Not assessed' :
          result.rapid_egfr_decline_flag ? 'Flagged' : 'Not flagged'],
        ['Observation count', result.observation_count]
      ];
      for (const [label, value] of pairs) {
        const metric = add(grid, 'div', '', 'metric');
        add(metric, 'small', label);
        add(metric, 'strong', value == null ? 'Unavailable' : value);
      }
      el('warnings').replaceChildren();
      result.warnings.forEach(w => add(el('warnings'), 'li', w));
      chart(rows);
      last = result;
      el('export').disabled = false;
    } catch (error) {
      last = null;
      el('export').disabled = true;
      el('error').textContent = error.message || 'Unable to analyze observations';
    }
  }
  el('analyze').addEventListener('click', analyze);
  el('example').addEventListener('click', () => {
    el('csv').value = demo;
    el('rate').value = '';
    el('duration').value = '';
    el('rrt').checked = false;
    analyze();
  });
  el('upload').addEventListener('change', async event => {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 2000000) {
      el('error').textContent = 'CSV exceeds 2 MB';
      return;
    }
    try {
      el('csv').value = await file.text();
      el('error').textContent = '';
    } catch {
      el('error').textContent = 'Unable to read CSV';
    }
  });
  el('export').addEventListener('click', () => {
    if (!last) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(last, null, 2) + '\n'], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'renal-trajectory-result.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  analyze();
})();
